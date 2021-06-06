from monochrom.chromschema import ChromosomePartCollection
from monochrom.monochrom import parse_cytoBand, parse_chromAlias, assign_info, validate, get_spmap, make_ontology
from linkml_runtime.dumpers.yaml_dumper import YAMLDumper
import os

cwd = os.path.abspath(os.path.dirname(__file__))
INPUT_DIR = os.path.join(cwd, 'inputs')
OUTPUT_DIR = os.path.join(cwd, 'outputs')

def test_convert():
    cytopath = os.path.join(INPUT_DIR, 'fake38-cytoBand.tsv')
    aliaspath = os.path.join(INPUT_DIR, 'fake38-chromAlias.tsv')
    outpath = os.path.join(OUTPUT_DIR, 'fake38.yaml')
    owlpath = os.path.join(OUTPUT_DIR, 'fake38.ofn')
    items = parse_cytoBand('hg38', cytopath)
    parse_chromAlias('hg38', items, aliaspath)
    spmap = get_spmap(os.path.join(INPUT_DIR, 'test_genomes.yaml'))
    assign_info(items, spmap)
    validate(items)
    YD = YAMLDumper()
    cpc = ChromosomePartCollection(has=items)
    with open(outpath, 'w') as stream:
        stream.write(YD.dumps(cpc))
    o = make_ontology(items)
    with open(owlpath, 'w') as stream:
        stream.write(str(o))