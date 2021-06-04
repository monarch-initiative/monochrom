import click
import csv
import os
from pathlib import Path
import yaml
import logging
import tempfile
import subprocess
import shutil
from rdflib import RDFS, OWL, Namespace, URIRef
from funowl import OntologyDocument, Ontology, ObjectSomeValuesFrom, AnnotationAssertion
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set

CHRNS = Namespace("http://purl.obolibrary.org/obo/CHR_")
NCBITaxon = Namespace("http://purl.obolibrary.org/obo/NCBITaxon_")
SO = Namespace("http://purl.obolibrary.org/obo/SO_")
GO = Namespace("http://purl.obolibrary.org/obo/GO_")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
RO = Namespace("http://purl.obolibrary.org/obo/RO_")
PART_OF = BFO['0000050']
IN_TAXON = RO['0002162']
BIOLINK = Namespace("https://w3id.org/biolink/vocab/")

CHROMOSOME_PART = SO['0000830']
CHROMOSOME = SO['0000340']

def get_spmap(f):
    with open(f) as stream:
        return yaml.safe_load(stream)

BUILD_ID = str
CHROMPART_ID = str
BAND_LOCALNAME = str
CHR = str
SP = str
STRAND = int
@dataclass
class ChromosomePart():
    """
    A Chromosome or a part of a chromosome (includes whole chromosomes, arms, and bands)
    """
    id: CHROMPART_ID
    localname: BAND_LOCALNAME
    chr: CHR
    build: str
    label: str = None
    type: str = None
    is_autosome: bool = False
    is_band: bool = False
    taxon: str = None
    start: Optional[int] = None
    end: Optional[int] = None
    strand: STRAND = None
    children: Optional[Set[CHROMPART_ID]] = field(default_factory=lambda:set())
    parent: Optional[CHROMPART_ID] = None

BAND_DICT = Dict[CHROMPART_ID, ChromosomePart]

def cls_iri(id: CHROMPART_ID) -> URIRef:
    pfx, localid = id.split(':')
    if pfx == 'CHR':
        return CHRNS[localid]
    elif pfx == 'NCBITaxon':
        return NCBITaxon[localid]


def make_ontology(bands: BAND_DICT):
    o = Ontology("http://purl.obolibrary.org/obo/chr.owl")
    o.annotation(RDFS.label, "Chromosome Ontology")
    for band_id, band in bands.items():
        c = cls_iri(band_id)
        aa = AnnotationAssertion(RDFS.label, c, band.label)
        o.axioms.append(aa)
        o.axioms.append(AnnotationAssertion(BIOLINK.start_interbase_coordinate,
                                            c, band.start))
        o.axioms.append(AnnotationAssertion(BIOLINK.end_interbase_coordinate,
                                            c, band.end))
        o.axioms.append(AnnotationAssertion(BIOLINK.genome_build,
                                            c, band.build))
        pid = band.parent
        if band.type == 'chromosome':
            type_cls = CHROMOSOME
        else:
            type_cls = CHROMOSOME_PART
        tax_cls = cls_iri(band.taxon)
        o.subClassOf(c, ObjectSomeValuesFrom(IN_TAXON, tax_cls))
        if pid is not None:
            p = cls_iri(pid)
            o.subClassOf(c, ObjectSomeValuesFrom(PART_OF, cls_iri(pid)))
    doc = OntologyDocument(CHRNS, o)
    return doc

def split_build_string(build: BUILD_ID) -> Tuple[str, str]:
    return re.findall(r'([a-zA-Z]+)([\d+])', build)[0]

def band_id(sp: SP, chr: CHR, band: BAND_LOCALNAME):
    return f'CHR:{sp}-{chr}{band}'

def get_parent_band_name(s: BAND_LOCALNAME):
    if s == '':
        return None
    s2 = s[0:-1]
    if s2 == '':
        return ''
    elif s2.endswith('.'):
        return get_parent_band_name(s2)
    else:
        return s2

def within( range, parent):
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
    for band_id, band in bands.items():
        if band.taxon is None:
            raise Exception(f'No taxon {band}')
        if band.label is None:
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
    for _, band in bands.items():
        spcode, _ = split_build_string(band.build)
        sp = spmap[spcode]
        spname = sp["name"]
        band.label = f'{band.chr}{band.localname} ({spname})'
        band.taxon = sp["id"]
        if band.localname == '':
            type = 'chromosome'
        else:
            type = 'chromosome_arm'
        band.type = type
        assign_ranges(bands, band)

def parse_chromAlias(build: BUILD_ID, f: str, bands: BAND_DICT):
    with open(f, 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            [alias, chr, src] = row

def parse_cytoBand(build: BUILD_ID, f: str):
    spcode, buildnum = split_build_string(build)
    bands = {}
    with open(f, 'r') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            [chr, s, e, bandname, rtype] = row
            id = band_id(spcode, chr, bandname)
            band = ChromosomePart(id=id, localname=bandname, chr=chr, start=int(s), end=int(e), build=build)
            bands[id] = band
            parent_band_name = get_parent_band_name(band.localname)
            current = band
            while parent_band_name is not None:
                #print(f'curr={current} parent_band_name={parent_band_name}')
                parent_id = band_id(spcode, chr, parent_band_name)
                if parent_id not in bands:
                    bands[parent_id] = ChromosomePart(id=parent_id, localname=parent_band_name, chr=chr, build=build)
                parent_band = bands[parent_id]
                current.parent = parent_id
                parent_band.children.add(current.id)
                parent_band_name = get_parent_band_name(parent_band.localname)
                current = parent_band

    return bands



@click.command()
@click.option('-o', '--output', help='output ontology in functional syntax')
@click.argument('files', nargs=-1)
def cli(files: List[str], output):
    spmap = get_spmap('species.yaml')
    for f in files:
        bn = Path(f).stem
        [build, ftype] = bn.split('-')
        bands = parse_cytoBand(build, f)
        assign_info(bands, spmap)
        for band_id, band in bands.items():
            print(band)
        validate(bands)
        if output is not None:
            o = make_ontology(bands)
            with open(output, "w") as out:
                out.write(str(o))

if __name__ == '__main__':
    cli()
