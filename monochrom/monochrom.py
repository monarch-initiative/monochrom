"""
Generates OWL or YAML from UCSC bands files

replaced dipper Monochrom.py
"""
import click
import csv
from pathlib import Path
import yaml
import logging
from linkml_runtime.loaders.yaml_loader import YAMLLoader
from linkml_runtime.dumpers.yaml_dumper import YAMLDumper
from linkml_runtime.dumpers.json_dumper import JSONDumper
from enum import Enum, unique
from rdflib import RDFS, Namespace
from funowl import OntologyDocument, Ontology, ObjectSomeValuesFrom, AnnotationAssertion, Prefix
import re
from typing import List, Dict, Tuple
from .chromschema import ChromosomePart, EntityType,ChromosomePartCollection, Genome, \
    ChromosomePartId, GenomeBuildId, ChromosomeNameType, BandDescriptor
import monochrom.chromschema as schema

def get_spmap(f):
    YL = YAMLLoader()
    with open(f) as stream:
        cpc: ChromosomePartCollection = YL.load(stream, target_class=ChromosomePartCollection)
        return cpc.genomes
        #return yaml.safe_load(stream)

INTERVAL = Tuple[int,int]
SP = str

BAND_DICT = Dict[ChromosomePartId, ChromosomePart]

def make_ontology(bands: BAND_DICT, name='Chromosome Ontology') -> OntologyDocument:
    """
    Translates a dict of ChromosomeParts to an ontology

    NOTE: this may be replaced by a robot template in future, or a linkml runtime dumper
    :param bands:
    :return:
    """
    o = Ontology("http://purl.obolibrary.org/obo/chr.owl")
    o.annotation(RDFS.label, name)
    doc = OntologyDocument(schema.CHR, o)
    doc.prefixDeclarations.append(Prefix('refseq', schema.REFSEQ))
    doc.prefixDeclarations.append(Prefix('insdc', schema.INSDC))
    doc.prefixDeclarations.append(Prefix('CHR', schema.CHR))
    doc.prefixDeclarations.append(Prefix('NCBITaxon', schema.NCBITAXON))
    #doc.prefixes.append(insdc = schema.INSDC)
    all_slots = schema.slots()
    ann_slots = [all_slots.name, all_slots.build, all_slots.start, all_slots.end,
                 all_slots.exact_mappings, all_slots.exact_synonyms, all_slots.broad_synonyms]
    svf_slots = [all_slots.parent, all_slots.taxon]
    for band_id, band in bands.items():
        c = band_id
        o.subClassOf(c, band.type.meaning)
        for s in ann_slots:
            # Annotation Assertions
            v = band._get(s.name)
            if v is not None:
                if isinstance(v, list):
                    for v1 in v:
                        o.axioms.append(AnnotationAssertion(s.uri, c, v1))
                else:
                    o.axioms.append(AnnotationAssertion(s.uri, c, v))
        for s in svf_slots:
            # SubClassOf SomeValuesFrom
            filler = band._get(s.name)
            if filler is not None:
                o.subClassOf(c, ObjectSomeValuesFrom(s.uri, filler))
    return doc

def split_build_string(build: GenomeBuildId) -> Tuple[str, str]:
    """
    Splits a build string, e.g. mm10 into a tuple of species code and build number
    :param build:
    :return:
    """
    return re.findall(r'([a-zA-Z]+)([\d+])', build)[0]

def get_band_id(sp: SP, chr: ChromosomeNameType, band: BandDescriptor):
    """
    generate CURIE for a ChromosomePart

    :param sp:
    :param chr:
    :param band:
    :return:
    """
    return f'CHR:{sp}-{chr}{band}'

def get_parent_band_name(s: BandDescriptor, spcode: SP):
    """
    The UCSC files only has most granular sub-bands - parent bands, arms, and chroms are implicit

    :param s:
    :return:
    """
    if s == '':
        return None
    if spcode == 'dm':
        # Dmel uses a different system; for now just flatten
        # TODO: 30B10 => 30B => 30 => ''
        return ''
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

def validate(bands: BAND_DICT):
    """
    validation checks on bands

    :param bands:
    :return:
    """
    for band_id, band in bands.items():
        if band.taxon is None:
            raise Exception(f'No taxon {band}')
        if band.name is None:
            raise Exception(f'No label {band}')
        if band.type is None:
            raise Exception(f'No type {band}')
        if band.parent is not None:
            p = bands[band.parent]
            if not within( (band.start, band.end), (p.start, p.end)):
                raise Exception(f'Not within {band} {p}')
            if band.taxon != p.taxon:
                raise Exception(f'Taxon{band} {p}')


def assign_ranges(bands: BAND_DICT, band: ChromosomePart):
    if band.start is not None:
        return
    for child in band.children:
        assign_ranges(bands, bands[child])
    if band.start is None:
        starts = [bands[b].start for b in band.children]
        ends = [bands[b].end for b in band.children]
        if starts[0] < ends[0]:
            band.start = min(starts)
            band.end = max(ends)
        else:
            band.start = max(starts)
            band.end = min(ends)

def assign_info(bands: BAND_DICT, spmap: dict):
    """
    Assign additional info, including inference of start/end for parent bands,
    and assigning labels

    :param bands:
    :param spmap:
    :return:
    """
    for _, band in bands.items():
        spcode, _ = split_build_string(band.build)
        sp = spmap[spcode]
        spname = sp["name"]
        band.name = f'{band.chromosome_name}{band.band_descriptor} ({spname})'
        band.taxon = sp["taxon"]
        if band.band_descriptor == '':
            type = EntityType.chromosome
        else:
            type = EntityType.chromosome_part
        band.type = type
        assign_ranges(bands, band)

def parse_chromAlias(build: GenomeBuildId, bands: BAND_DICT, f: str):
    spcode, buildnum = split_build_string(build)
    with open(f, 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        n = 0
        for [name,id,src] in reader:
            id = get_band_id(spcode, id, '')
            if id in bands:
                band = bands[id]
                n += 1
                if src == 'assembly':
                    band.broad_synonyms = [name]
                elif src == 'refseq':
                    band.exact_mappings.append(f'refseq:{name}')
                elif src == 'genbank':
                    band.exact_mappings.append(f'insdc:{name}')
                else:
                    logging.warning(f'Do not know what to do with {src}')
        if n == 0:
            raise Exception(f'No bands recognized in {f}')


def parse_cytoBand(build: GenomeBuildId, f: str) -> BAND_DICT:
    """
    parses a UCSC cytoBand.txt file to a dict of ChromosomeParts

    :param build:
    :param f:
    :return:
    """
    spcode, buildnum = split_build_string(build)
    bands = {}
    with open(f, 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            [chr, s, e, bandname, rtype] = row
            if '_' in chr:
                # skipping chr4_KL567938v1_random
                continue
            id = get_band_id(spcode, chr, bandname)
            band = ChromosomePart(id=id, band_descriptor=bandname, chromosome_name=chr, start=int(s), end=int(e), build=build)
            bands[id] = band
            parent_band_name = get_parent_band_name(band.band_descriptor, spcode)
            current = band
            while parent_band_name is not None:
                #print(f'curr={current} parent_band_name={parent_band_name}')
                parent_id = get_band_id(spcode, chr, parent_band_name)
                if parent_id not in bands:
                    bands[parent_id] = ChromosomePart(id=parent_id, band_descriptor=parent_band_name, chromosome_name=chr, build=build)
                parent_band = bands[parent_id]
                current.parent = parent_id
                if current.id not in parent_band.children:
                    # TODO: gte linkml pygen to emit Sets
                    parent_band.children.append(current.id)
                parent_band_name = get_parent_band_name(parent_band.band_descriptor, spcode)
                current = parent_band

    return bands

@unique
class OutputFormat(Enum):
    ofn = 'ofn'
    yaml = 'yaml'
    json = 'json'
    @staticmethod
    def list():
        return list(map(lambda c: c.value, OutputFormat))

@click.command()
@click.option('-o', '--output',
              help='output ontology in functional syntax to this path')
@click.option('-f', '--to_format', default='ofn',
              type=click.Choice(OutputFormat.list()),
              help='output format')
@click.argument('files', nargs=-1)
def cli(files: List[str], to_format, output):
    """
    parses files download from UCSC into OWL

    Assumes certain naming conventions - see the Makefile

    TODO: parse chromAliases
    """
    spmap = get_spmap('species.yaml')
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
        items = parse_cytoBand(build, fdict['cytoBand'])
        if 'chromAlias' not in fdict:
            logging.warning(f'No alias found for {build}')
        else:
            parse_chromAlias(build, items, fdict['chromAlias'])
        assign_info(items, spmap)
        validate(items)
        if output is not None:
            if to_format == 'yaml':
                dump = YAMLDumper().dumps(items)
            elif to_format == 'json':
                dump = JSONDumper().dumps(items)
            elif to_format == 'ofn':
                o = make_ontology(items)
                dump = str(o)
            else:
                raise Exception(f'Cannot handle {to_format}')
            with open(output, "w") as out:
                out.write(dump)

if __name__ == '__main__':
    cli()