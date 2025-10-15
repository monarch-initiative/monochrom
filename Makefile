# TODO: parse from yaml
# https://hgdownload.soe.ucsc.edu/downloads.html
BUILDS = hg38 ce11 mm39 rn6 galGal6 calJac4 danRer11
# TODO: dm6
RUN = poetry run

all: all-chromAlias all-cytoBand src/ontology/components/ucsc.owl  all-components ontology
all-chromAlias: $(patsubst %, download/%-chromAlias.tsv, $(BUILDS))
all-cytoBand: $(patsubst %, download/%-cytoBand.tsv, $(BUILDS))

all-components: all-components-yaml all-components-owl

all-components-yaml: $(patsubst %, components/%.yaml, $(BUILDS))
all-components-owl: $(patsubst %, components/%.owl, $(BUILDS))

ontology:
	cd src/ontology && sh run.sh make prepare_release

test:
	pytest

download/%-chromAlias.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/$*/database/chromAlias.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
download/%-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/$*/database/cytoBandIdeo.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
#	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/$*/database/cytoBand.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
download/ce11-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/ce11/database/cytoBandIdeo.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
download/danRer10-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/danRer10/database/cytoBandIdeo.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
download/galGal6-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/galGal6/database/cytoBandIdeo.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
download/calJac4-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/calJac4/database/cytoBandIdeo.txt.gz | gzip -dc > $@.tmp && mv $@.tmp $@
components/%.owl: download/%-cytoBand.tsv download/%-chromAlias.tsv
	$(RUN) ucsc2owl $^ -o $@
components/%.yaml: download/%-cytoBand.tsv download/%-chromAlias.tsv
	$(RUN) ucsc2owl $^ -f yaml -o $@

download/ncit.owl:
	curl -L -s http://purl.obolibrary.org/obo/ncit.owl > $@.tmp && mv $@.tmp $@

download/ncit-chrom-terms.owl: download/ncit.owl config/ncit-chrom-terms.txt
	robot extract -i $< -m TOP -T config/ncit-chrom-terms.txt -o $@

# ODK will take things on from here
src/ontology/tmp/ucsc.ofn: monochrom/monochrom.py monochrom/chromschema.py
	$(RUN) ucsc2owl download/*-*.tsv -o $@.tmp && mv $@.tmp $@
.PRECIOUS: src/ontology/tmp/ucsc.ofn

ONTBASE=http://purl.obolibrary.org/obo/chr
VERSION=$(shell date +%Y-%m-%d)
src/ontology/components/ucsc.owl: src/ontology/tmp/ucsc.ofn
	robot merge -i $< annotate --ontology-iri $(ONTBASE)/$@ annotate -V $(ONTBASE)/releases/$(VERSION)/$@ --annotation owl:versionInfo $(VERSION) convert -o $@

## Schema

monochrom/chromschema.py: model/schema/chromo.yaml
	gen-pydantic model/schema/chromo.yaml > $@.tmp && mv $@.tmp $@

gendocs:
	gen-markdown -d docs model/schema/chromo.yaml


