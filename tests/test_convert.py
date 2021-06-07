from monochrom.chromschema import ChromosomePartCollection
from monochrom.monochrom import parse_cytoBand, parse_chromAlias, assign_info, validate, \
    make_ontology, load_collection
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
    cpc = load_collection(os.path.join(INPUT_DIR, 'test_genomes.yaml'))
    parse_cytoBand(cpc, 'hg38', cytopath)
    parse_chromAlias(cpc, 'hg38', aliaspath)
    assign_info(cpc)
    validate(cpc)
    YD = YAMLDumper()
    with open(outpath, 'w') as stream:
        stream.write(YD.dumps(cpc))
    o = make_ontology(cpc)
    with open(owlpath, 'w') as stream:
        stream.write(str(o))