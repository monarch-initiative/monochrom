from monochrom.chromschema import ChromosomePartCollection
from monochrom.monochrom import parse_cytoBand, parse_chromAlias, assign_info, validate, \
    make_ontology, load_collection, get_placement, placements_to_tsv
from linkml_runtime.dumpers.yaml_dumper import YAMLDumper
import os

cwd = os.path.abspath(os.path.dirname(__file__))
INPUT_DIR = os.path.join(cwd, 'inputs')
OUTPUT_DIR = os.path.join(cwd, 'outputs')


# build -> prefix of the test input files for that build
FIXTURES = {'hg38': 'fake38', 'fakeT2T': 'fakeT2T'}


def _load(builds):
    cpc = load_collection(os.path.join(INPUT_DIR, 'test_genomes.yaml'))
    for build in builds:
        prefix = FIXTURES[build]
        parse_cytoBand(cpc, build, os.path.join(INPUT_DIR, f'{prefix}-cytoBand.tsv'))
        parse_chromAlias(cpc, build, os.path.join(INPUT_DIR, f'{prefix}-chromAlias.tsv'))
    assign_info(cpc)
    validate(cpc)
    return cpc


def test_convert():
    outpath = os.path.join(OUTPUT_DIR, 'fake38.yaml')
    owlpath = os.path.join(OUTPUT_DIR, 'fake38.ofn')
    cpc = _load(['hg38'])
    YD = YAMLDumper()
    with open(outpath, 'w') as stream:
        stream.write(YD.dumps(cpc))
    o = make_ontology(cpc)
    with open(owlpath, 'w') as stream:
        stream.write(str(o))
    chr1 = cpc.has['CHR:9606-chr1']
    assert chr1.name == 'chromosome 1 (Human)'
    assert chr1.broad_synonyms == ['1']
    p = get_placement(chr1, 'hg38')
    assert p.start == 0
    assert 'refseq:NC_000001.10' in p.exact_mappings


def test_multiple_builds():
    """
    Two builds of the same genome share build-independent identifiers,
    with coordinates and accessions recorded per build
    """
    cpc = _load(['hg38', 'fakeT2T'])
    single = _load(['hg38'])
    assert set(cpc.has.keys()) == set(single.has.keys())
    band = cpc.has['CHR:9606-chr1p36.33']
    assert band.parent == 'CHR:9606-chr1p36.3'
    hg38 = get_placement(band, 'hg38')
    t2t = get_placement(band, 'fakeT2T')
    assert (hg38.start, hg38.end) == (0, 2300000)
    assert (t2t.start, t2t.end) == (0, 1735965)
    # parent ranges are inferred separately for each build
    arm = cpc.has['CHR:9606-chr1p']
    assert get_placement(arm, 'fakeT2T').end != get_placement(arm, 'hg38').end
    chr1 = cpc.has['CHR:9606-chr1']
    assert get_placement(chr1, 'fakeT2T').exact_mappings == ['insdc:CP068277.2', 'refseq:NC_060925.1']
    assert 'refseq:NC_000001.10' in get_placement(chr1, 'hg38').exact_mappings
    assert chr1.broad_synonyms == ['1']
    # chromosomes absent from a build get no placement for it
    assert get_placement(cpc.has['CHR:9606-chr10'], 'fakeT2T') is None
    assert get_placement(cpc.has['CHR:9606-chrX'], 'fakeT2T') is None
    ofn = str(make_ontology(cpc))
    assert 'Annotation( <https://w3id.org/biolink/vocab/genome_build> "fakeT2T" )' in ofn
    tsv = placements_to_tsv(cpc).splitlines()
    assert tsv[0].split('\t')[0:4] == ['id', 'name', 'taxon', 'build']
    assert 'CHR:9606-chr1p36.33\t1p36.33 (Human)\tNCBITaxon:9606\tfakeT2T\tchr1\tp36.33\t0\t1735965\tgneg\t' in tsv
