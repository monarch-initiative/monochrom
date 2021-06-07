from monochrom.chromschema import ChromosomePart, ChromosomePartCollection, EntityType, BandDescriptor, slots as cslots
from monochrom.monochrom import make_ontology

def test_model():
    bd = BandDescriptor('p1')
    cp = ChromosomePart(id='CHR:1', band_descriptor=bd,
                        chromosome_name='chr1', build='hg38', name='Chr1p (Human)', type=EntityType.chromosome,
                        exact_synonyms=['foo', 'bar'])
    print()
    print(cp)
    assert(True)
    slots = cslots()
    print()
    cpc = ChromosomePartCollection()
    cpc.has[cp.id] = cp
    o = make_ontology(cpc)
    print(o)

