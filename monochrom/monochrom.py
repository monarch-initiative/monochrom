"""
Generates OWL or YAML from UCSC bands files

replaced dipper Monochrom.py
"""
import click
import csv
import gzip
import io
import urllib.request
from pathlib import Path
import logging
from linkml_runtime.loaders.yaml_loader import YAMLLoader
from linkml_runtime.dumpers.yaml_dumper import YAMLDumper
from linkml_runtime.dumpers.json_dumper import JSONDumper
from enum import Enum, unique
from rdflib import RDFS
from funowl import OntologyDocument, Ontology, ObjectSomeValuesFrom, AnnotationAssertion, Annotation, Prefix
import re
from typing import List, Optional, Tuple
from .chromschema import ChromosomePart, ChromosomePartPlacement, EntityType,ChromosomePartCollection, Genome, \
    ChromosomePartId, GenomeBuildId, GenomeId, ChromosomeNameType, BandDescriptor, \
    LocationType, SexChromosomeType, AutosomeVsSexChromosome
import monochrom.chromschema as schema

INTERVAL = Tuple[int,int]

def make_ontology(cpc: ChromosomePartCollection, name='Chromosome Ontology') -> OntologyDocument:
    """
    Translates a dict of ChromosomeParts to an ontology

    Build-specific values (coordinates and sequence accessions) are emitted as annotation
    assertions with an axiom annotation naming the genome build, e.g.

        AnnotationAssertion(Annotation(biolink:genome_build "hs1") gff:start CHR:9606-chr1p36.33 0)

    NOTE: this may be replaced by a robot template in future, or a linkml runtime dumper
    :param bands:
    :return:
    """
    bands = cpc.has
    o = Ontology("http://purl.obolibrary.org/obo/chr.owl")
    o.annotation(RDFS.label, name)
    doc = OntologyDocument(schema.CHR, o)
    # this is a bit awkward; revisit after https://github.com/hsolbrig/funowl/issues/18
    doc.prefixDeclarations.append(Prefix('refseq', schema.REFSEQ))
    doc.prefixDeclarations.append(Prefix('insdc', schema.INSDC))
    doc.prefixDeclarations.append(Prefix('CHR', schema.CHR))
    doc.prefixDeclarations.append(Prefix('NCBITaxon', schema.NCBITAXON))
    all_slots = schema.slots()
    type_slots = [all_slots.type, all_slots.somal_type, all_slots.sex_chromosome_type]
    ann_slots = [all_slots.name, all_slots.exact_synonyms, all_slots.broad_synonyms]
    placement_slots = [all_slots.start, all_slots.end, all_slots.exact_mappings]
    svf_slots = [all_slots.parent, all_slots.taxon, all_slots.cell_location]
    for band_id, band in bands.items():
        c = band_id
        for s in type_slots:
            v = band._get(s.name)
            if v is not None:
                o.subClassOf(c, v.meaning)
        for s in ann_slots:
            # Annotation Assertions
            v = band._get(s.name)
            if v is not None:
                if isinstance(v, list):
                    for v1 in v:
                        o.axioms.append(AnnotationAssertion(s.uri, c, v1))
                else:
                    o.axioms.append(AnnotationAssertion(s.uri, c, v))
        for placement in band.placements:
            build = str(placement.build)
            o.axioms.append(AnnotationAssertion(all_slots.build.uri, c, build))
            for s in placement_slots:
                v = placement._get(s.name)
                if v is None:
                    continue
                for v1 in (v if isinstance(v, list) else [v]):
                    qualifier = Annotation(all_slots.build.uri, build)
                    o.axioms.append(AnnotationAssertion(s.uri, c, v1, [qualifier]))
        for s in svf_slots:
            # SubClassOf SomeValuesFrom
            filler = band._get(s.name)
            if filler is not None:
                if 'meaning' in filler:
                    filler = filler.meaning
                o.subClassOf(c, ObjectSomeValuesFrom(s.uri, filler))
    return doc

def get_genome_id(cpc: ChromosomePartCollection, build: GenomeBuildId) -> GenomeId:
    """
    Looks up the genome (species code, e.g. hg) for a build (e.g. hs1)

    Builds must be declared in the builds section of the genomes YAML file
    :param build:
    :return:
    """
    if build not in cpc.builds:
        raise Exception(f'Build {build} is not declared in the builds section of the genomes file')
    return cpc.builds[build].genome

def get_placement(part: ChromosomePart, build: GenomeBuildId, create=False) -> Optional[ChromosomePartPlacement]:
    """
    Returns the placement of a ChromosomePart in a given build

    :param part:
    :param build:
    :param create: if True, add an empty placement if none exists
    :return:
    """
    for placement in part.placements:
        if placement.build == build:
            return placement
    if create:
        placement = ChromosomePartPlacement(build=build)
        part.placements.append(placement)
        return placement
    return None

def get_band_id(cpc: ChromosomePartCollection, sp: GenomeId, chr: ChromosomeNameType, band: BandDescriptor):
    """
    generate CURIE for a ChromosomePart

    The CURIE is independent of the genome build, so the same band in two builds
    of the same genome shares an identifier

    :param sp:
    :param chr:
    :param band:
    :return:
    """
    t = cpc.genomes[sp].taxon.replace('NCBITaxon:', '')
    return f'CHR:{t}-{chr}{band}'

def get_parent_band_name(s: BandDescriptor, spcode: GenomeId):
    """
    The UCSC files only has most granular sub-bands - parent bands, arms, and chroms are implicit

    In general the rule to infer a parent is to pop a character from the end, ignoring periods, e.g.

    p31.1 -> p31 -> p3 -> p

    But sometimes there are exceptions; e.g 'cen' denotes a centromere

    :param s:
    :return:
    """
    if s == '':
        return None
    if spcode == 'dm':
        # Dmel uses a different system; for now just flatten
        # TODO: 30B10 => 30B => 30 => ''
        return ''
    if s.endswith('cen'):
        # see https://github.com/monarch-initiative/monochrom/issues/23
        return s.replace('cen', '')
    s2 = s[0:-1]
    if s2 == '':
        return ''
    elif s2.endswith('.'):
        return get_parent_band_name(s2, spcode)
    else:
        return s2

def within(range: INTERVAL, parent: INTERVAL) -> bool:
    """
    Seq interval range check
    :param range:
    :param parent:
    :return:
    """
    s,e = range
    ps,pe = parent
    if s < e:
        if ps >= pe:
            return False
        else:
            return ps <= s and pe >= e
    elif s > e:
        if ps <= pe:
            return False
        else:
            return ps >= s and pe <= e

def validate(ccp: ChromosomePartCollection):
    """
    validation checks on bands

    Coordinates are checked within each build. Bands that are present in some but not all
    of the builds for a genome are reported as warnings.

    :param bands:
    :return:
    """
    bands = ccp.has
    for band_id, band in bands.items():
        if band.taxon is None:
            raise Exception(f'No taxon {band}')
        if band.name is None:
            raise Exception(f'No label {band}')
        if band.type is None:
            raise Exception(f'No type {band}')
        if band.parent is not None:
            p = bands[band.parent]
            if band.taxon != p.taxon:
                raise Exception(f'Taxon{band} {p}')
            for placement in band.placements:
                if placement.start is None:
                    continue
                pp = get_placement(p, placement.build)
                if pp is None or pp.start is None:
                    raise Exception(f'No placement in {placement.build} for parent of {band}')
                if not within((placement.start, placement.end), (pp.start, pp.end)):
                    raise Exception(f'Not within in {placement.build}: {band} {p}')
    genome_builds = {}
    for build_id, build in ccp.builds.items():
        genome_builds.setdefault(build.genome, set())
    for band_id, band in bands.items():
        for placement in band.placements:
            genome_builds[get_genome_id(ccp, placement.build)].add(placement.build)
    for genome, builds in genome_builds.items():
        if len(builds) < 2:
            continue
        for build in sorted(builds):
            missing = [band_id for band_id, band in bands.items()
                       if get_genome_id(ccp, band.placements[0].build) == genome
                       and get_placement(band, build) is None]
            if missing:
                logging.warning(f'{len(missing)} parts of genome {genome} are not in {build}, e.g. {missing[0:5]}')

def assign_ranges(cpc: ChromosomePartCollection, band: ChromosomePart, build: GenomeBuildId) -> None:
    """
    Infers the range of a part in a build from the ranges of its children in that build

    :param cpc:
    :param band:
    :param build:
    :return:
    """
    parts = cpc.has
    placement = get_placement(band, build)
    if placement is None or placement.start is not None:
        return
    children = [parts[c] for c in band.children if get_placement(parts[c], build) is not None]
    for child in children:
        assign_ranges(cpc, child, build)
    child_placements = [get_placement(c, build) for c in children]
    child_placements = [p for p in child_placements if p.start is not None]
    if not child_placements:
        return
    starts = [p.start for p in child_placements]
    ends = [p.end for p in child_placements]
    if starts[0] < ends[0]:
        placement.start = min(starts)
        placement.end = max(ends)
    else:
        placement.start = max(starts)
        placement.end = min(ends)

def assign_info(cpc: ChromosomePartCollection):
    """
    Assign additional info, including inference of start/end for parent bands,
    and assigning labels

    :param cpc:
    :return:
    """
    bands = cpc.has
    spmap = cpc.genomes
    for _, band in bands.items():
        genome_ids = {get_genome_id(cpc, p.build) for p in band.placements}
        if len(genome_ids) != 1:
            raise Exception(f'Expected exactly one genome for {band.id}, got {genome_ids}')
        genome = spmap[genome_ids.pop()]
        spname = genome.name
        chr = band.chromosome_name.replace('chr', '')
        band.taxon = genome.taxon
        if band.band_descriptor == '':
            band.name = f'chromosome {chr} ({spname})'
            type = EntityType.chromosome
            n = band.chromosome_name.replace('chr', '')
            if n == 'M':
                band.cell_location = LocationType.mitochondrion
            else:
                ## TODO: bacteria or other cytosolic chromosomes
                band.cell_location = LocationType.nucleus
                if n in ['X', 'Y', 'W', 'Z']:
                    band.somal_type = AutosomeVsSexChromosome.sex_chromosome
                    band.sex_chromosome_type = SexChromosomeType[n]
                else:
                    band.somal_type = AutosomeVsSexChromosome.autosome
                    if not n.isdigit() and n not in ['I', 'II', 'III', 'IV', 'V']:
                        logging.error(f'Cannot parse chromosome: {n}')

        else:
            band.name = f'{chr}{band.band_descriptor} ({spname})'
            type = EntityType.chromosome_part
        band.type = type
        for placement in band.placements:
            assign_ranges(cpc, band, placement.build)

def _add_alias(band: ChromosomePart, placement: ChromosomePartPlacement, name: str, src: str) -> None:
    if src == 'assembly' or src == 'ensembl':
        if name not in band.broad_synonyms:
            band.broad_synonyms.append(name)
    elif src == 'refseq':
        placement.exact_mappings.append(f'refseq:{name}')
    elif src == 'genbank':
        placement.exact_mappings.append(f'insdc:{name}')
    elif src in ('ucsc', 'ncbi'):
        # ucsc is the name used as the primary key; ncbi duplicates assembly
        pass
    else:
        logging.warning(f'Do not know what to do with {src}')

def parse_chromAlias(cpc: ChromosomePartCollection, build: GenomeBuildId, f: str):
    """
    Parses a UCSC aliases file

    Two formats are supported:

     - the UCSC database chromAlias table: alias, chrom, comma-separated sources
     - the UCSC hub chromAlias.txt: a header line beginning with '#' naming the sources,
       one column per source, one row per sequence (used for hub assemblies such as hs1)

    Accessions are attached to the placement of the chromosome in this build

    :param cpc:
    :param build:
    :param f:
    :return:
    """
    spcode = get_genome_id(cpc, build)
    bands = cpc.has
    n = 0

    def add(chr: str, name: str, src: str):
        nonlocal n
        id = get_band_id(cpc, spcode, chr, '')
        if id not in bands:
            return
        placement = get_placement(bands[id], build)
        if placement is None:
            return
        n += 1
        _add_alias(bands[id], placement, name, src)

    with open(f, 'r') as tsvfile:
        lines = [line.rstrip('\n') for line in tsvfile if line.strip()]
    if lines and lines[0].startswith('#'):
        header = lines[0].lstrip('#').split()
        if 'ucsc' not in header:
            raise Exception(f'No ucsc column in {f}')
        ucsc_ix = header.index('ucsc')
        for line in lines[1:]:
            row = line.split('\t')
            chr = row[ucsc_ix]
            for src, name in zip(header, row):
                if name != '':
                    add(chr, name, src)
    else:
        for line in lines:
            [name, chr, srcs] = line.split('\t')
            for src in srcs.split(","):
                add(chr, name, src)
    if n == 0:
        raise Exception(f'No bands recognized in {f}')


def parse_cytoBand(cpc: ChromosomePartCollection, build: GenomeBuildId, f: str):
    """
    parses a UCSC cytoBand.txt (or cytoband BED) file into ChromosomeParts

    Parts are keyed by build-independent identifiers; if a part has already been
    created from another build of the same genome, a placement for this build is added to it

    :param build:
    :param f:
    :return:
    """
    spcode = get_genome_id(cpc, build)
    bands = cpc.has
    with open(f, 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            [chr, s, e, band_descriptor, rtype] = row[0:5]
            if '_' in chr:
                # skipping entries such as chr4_KL567938v1_random
                continue
            id = get_band_id(cpc, spcode, chr, band_descriptor)
            if id not in bands:
                bands[id] = ChromosomePart(id=id, band_descriptor=band_descriptor, chromosome_name=chr)
            band = bands[id]
            placement = get_placement(band, build, create=True)
            placement.start = int(s)
            placement.end = int(e)
            placement.stain = rtype
            parent_band_descriptor = get_parent_band_name(band.band_descriptor, spcode)
            current = band
            while parent_band_descriptor is not None:
                parent_id = get_band_id(cpc, spcode, chr, parent_band_descriptor)
                if parent_id not in bands:
                    bands[parent_id] = ChromosomePart(id=parent_id, band_descriptor=parent_band_descriptor, chromosome_name=chr)
                parent_band = bands[parent_id]
                get_placement(parent_band, build, create=True)
                if current.parent is not None and current.parent != parent_id:
                    raise Exception(f'Inconsistent parents for {current.id}: {current.parent} {parent_id}')
                current.parent = parent_id
                if current.id not in parent_band.children:
                    # TODO: get linkml pygen to emit Sets
                    parent_band.children.append(current.id)
                parent_band_descriptor = get_parent_band_name(parent_band.band_descriptor, spcode)
                current = parent_band

PLACEMENT_COLUMNS = ['id', 'name', 'taxon', 'build', 'chromosome_name', 'band_descriptor',
                     'start', 'end', 'stain', 'sequence_accessions']

def placements_to_tsv(cpc: ChromosomePartCollection) -> str:
    """
    Dumps one row per (part, build) placement

    :param cpc:
    :return:
    """
    out = io.StringIO()
    w = csv.writer(out, delimiter='\t', lineterminator='\n')
    w.writerow(PLACEMENT_COLUMNS)
    for band_id, band in cpc.has.items():
        for p in band.placements:
            w.writerow([band_id, band.name, band.taxon, p.build, band.chromosome_name, band.band_descriptor,
                        '' if p.start is None else p.start, '' if p.end is None else p.end,
                        p.stain or '', '|'.join(p.exact_mappings)])
    return out.getvalue()

@unique
class OutputFormat(Enum):
    ofn = 'ofn'
    yaml = 'yaml'
    json = 'json'
    tsv = 'tsv'
    @staticmethod
    def list():
        return list(map(lambda c: c.value, OutputFormat))

def load_collection(f: str) -> ChromosomePartCollection:
    """
    Loads an initial ChromosomePartCollection

    This should be seeded with the list of genomes
    :param f:
    :return:
    """
    with open(f) as stream:
        cpc: ChromosomePartCollection = YAMLLoader().load(stream, target_class=ChromosomePartCollection)
    return cpc

@click.command()
@click.option('-o', '--output',
              help='output ontology in functional syntax to this path')
@click.option('-f', '--to_format', default='ofn',
              type=click.Choice(OutputFormat.list()),
              help='output format')
@click.option('-C', '--config',
              default='genomes.yaml',
              help='YAML source file')
@click.argument('files', nargs=-1)
def cli(files: List[str], to_format, output, config='genomes.yaml'):
    """
    parses files download from UCSC into OWL

    Assumes certain naming conventions - see the Makefile

    TODO: parse chromAliases
    """
    cpc = load_collection(config)
    fmap = {}
    for f in files:
        bn = Path(f).stem
        [build, ftype] = bn.split('-')
        if build not in fmap:
            fmap[build] = {}
        fmap[build][ftype] = f
    for build, fdict in fmap.items():
        if 'cytoBand' not in fdict:
            raise Exception(f'No cytoBand file for {build} in {files}')
        parse_cytoBand(cpc, build, fdict['cytoBand'])
        if 'chromAlias' not in fdict:
            logging.warning(f'No alias found for {build}')
        else:
            parse_chromAlias(cpc, build, fdict['chromAlias'])
    assign_info(cpc)
    validate(cpc)
    if output is not None:
        if to_format == 'yaml':
            dump = YAMLDumper().dumps(cpc)
        elif to_format == 'json':
            dump = JSONDumper().dumps(cpc)
        elif to_format == 'ofn':
            o = make_ontology(cpc)
            dump = str(o)
        elif to_format == 'tsv':
            dump = placements_to_tsv(cpc)
        else:
            raise Exception(f'Cannot handle {to_format}')
        with open(output, "w") as out:
            out.write(dump)


UCSC_DATABASE_URL = 'https://hgdownload.soe.ucsc.edu/goldenPath/{build}/database/{table}.txt.gz'

def source_url(cpc: ChromosomePartCollection, build: GenomeBuildId, ftype: str) -> str:
    """
    Returns the download URL for a build's cytoBand or chromAlias file

    Uses the URL declared for the build in the genomes file, defaulting to the
    UCSC database tables (cytoBandIdeo, chromAlias)

    :param build:
    :param ftype: cytoBand or chromAlias
    :return:
    """
    get_genome_id(cpc, build)
    b = cpc.builds[build]
    if ftype == 'cytoBand':
        return b.cytoband_url or UCSC_DATABASE_URL.format(build=build, table='cytoBandIdeo')
    elif ftype == 'chromAlias':
        return b.chromalias_url or UCSC_DATABASE_URL.format(build=build, table='chromAlias')
    raise Exception(f'Unknown file type {ftype}')

@click.command()
@click.option('-o', '--output', required=True, help='path to write the uncompressed file to')
@click.option('-C', '--config', default='genomes.yaml', help='YAML source file')
@click.argument('build')
@click.argument('ftype', type=click.Choice(['cytoBand', 'chromAlias']))
def download(build, ftype, output, config):
    """
    Downloads a cytoBand or chromAlias file for a build declared in the genomes file
    """
    cpc = load_collection(config)
    url = source_url(cpc, build, ftype)
    with urllib.request.urlopen(url) as response:
        data = response.read()
    if url.endswith('.gz'):
        data = gzip.decompress(data)
    with open(output, 'wb') as out:
        out.write(data)


if __name__ == '__main__':
    cli()
