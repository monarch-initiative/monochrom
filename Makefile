# Builds to include; each must be declared in the builds section of genomes.yaml.
# Several builds of the same genome share build-independent identifiers.
# https://hgdownload.soe.ucsc.edu/downloads.html
BUILDS = hg38 hs1 ce11 mm39 rn6 galGal6 calJac4 danRer11
# TODO: dm6
RUN = poetry run

all: all-chromAlias all-cytoBand src/ontology/components/ucsc.owl chr-placements.tsv all-components ontology
all-chromAlias: $(patsubst %, download/%-chromAlias.tsv, $(BUILDS))
all-cytoBand: $(patsubst %, download/%-cytoBand.tsv, $(BUILDS))

all-components: all-components-yaml all-components-owl

all-components-yaml: $(patsubst %, components/%.yaml, $(BUILDS))
all-components-owl: $(patsubst %, components/%.owl, $(BUILDS))

ontology:
	cd src/ontology && sh run.sh make prepare_release

test:
	pytest

# source URLs come from genomes.yaml (default: UCSC database tables for the build)
download/%-chromAlias.tsv:
	$(RUN) chr-download $* chromAlias -o $@.tmp && mv $@.tmp $@
download/%-cytoBand.tsv:
	$(RUN) chr-download $* cytoBand -o $@.tmp && mv $@.tmp $@
components/%.owl: download/%-cytoBand.tsv download/%-chromAlias.tsv
	$(RUN) ucsc2owl $^ -o $@
components/%.yaml: download/%-cytoBand.tsv download/%-chromAlias.tsv
	$(RUN) ucsc2owl $^ -f yaml -o $@

download/ncit.owl:
	curl -L -s http://purl.obolibrary.org/obo/ncit.owl > $@.tmp && mv $@.tmp $@

download/ncit-chrom-terms.owl: download/ncit.owl config/ncit-chrom-terms.txt
	robot extract -i $< -m TOP -T config/ncit-chrom-terms.txt -o $@

# ODK will take things on from here
# Generate list of input files based on BUILDS variable to avoid conflicts
UCSC_INPUT_FILES = $(foreach build,$(BUILDS),download/$(build)-cytoBand.tsv download/$(build)-chromAlias.tsv)
src/ontology/tmp/ucsc.ofn: monochrom/monochrom.py monochrom/chromschema.py $(UCSC_INPUT_FILES)
	$(RUN) ucsc2owl $(UCSC_INPUT_FILES) -o $@.tmp && mv $@.tmp $@
.PRECIOUS: src/ontology/tmp/ucsc.ofn

# one row per chromosome part per build, with build-specific coordinates and accessions
chr-placements.tsv: monochrom/monochrom.py monochrom/chromschema.py $(UCSC_INPUT_FILES)
	$(RUN) ucsc2owl $(UCSC_INPUT_FILES) -f tsv -o $@.tmp && mv $@.tmp $@

ONTBASE=http://purl.obolibrary.org/obo/chr
VERSION=$(shell date +%Y-%m-%d)
src/ontology/components/ucsc.owl: src/ontology/tmp/ucsc.ofn
	robot merge -i $< annotate --ontology-iri $(ONTBASE)/$@ annotate -V $(ONTBASE)/releases/$(VERSION)/$@ --annotation owl:versionInfo $(VERSION) convert -o $@

## Schema

monochrom/chromschema.py: model/schema/chromo.yaml
	gen-python model/schema/chromo.yaml > $@.tmp && mv $@.tmp $@

gendocs:
	gen-markdown -d docs model/schema/chromo.yaml


