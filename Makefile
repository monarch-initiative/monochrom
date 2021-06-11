# TODO: parse from yaml
BUILDS = hg38 ce11 mm10 rn6
# TODO: dm6

all: all-chromAlias all-cytoBand src/ontology/components/ucsc.owl
all-chromAlias: $(patsubst %, download/%-chromAlias.tsv, $(BUILDS))
all-cytoBand: $(patsubst %, download/%-cytoBand.tsv, $(BUILDS))

test:
	pytest

download/%-chromAlias.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/$*/database/chromAlias.txt.gz | gzip -dc > $@
download/%-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/$*/database/cytoBand.txt.gz | gzip -dc > $@
download/ce11-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/ce11/database/cytoBandIdeo.txt.gz | gzip -dc > $@
download/danRer10-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/danRer10/database/cytoBandIdeo.txt.gz | gzip -dc > $@
components/%.owl: download/%-cytoBand.tsv download/%-chromAlias.tsv
	python -m monochrom.monochrom $^ -o $@
components/%.yaml: download/%-cytoBand.tsv download/%-chromAlias.tsv
	python -m monochrom.monochrom $^ -f yaml -o $@

download/ncit.owl:
	curl -L -s http://purl.obolibrary.org/obo/ncit.owl > $@

download/ncit-chrom-terms.owl: download/ncit.owl config/ncit-chrom-terms.txt
	robot extract -i $< -m TOP -T config/ncit-chrom-terms.txt -o $@

src/ontology/tmp/ucsc.ofn: monochrom/monochrom.py
	python -m monochrom.monochrom download/*-*.tsv -o $@.tmp && mv $@.tmp $@
.PRECIOUS: src/ontology/tmp/ucsc.ofn

ONTBASE=http://purl.obolibrary.org/obo/chr
VERSION=$(shell date +%Y-%m-%d)
src/ontology/components/ucsc.owl: src/ontology/tmp/ucsc.ofn
	robot merge -i $< annotate --ontology-iri $(ONTBASE)/$@ annotate -V $(ONTBASE)/releases/$(VERSION)/$@ --annotation owl:versionInfo $(VERSION) convert -o $@

## Schema

monochrom/chromschema.py: model/schema/chromo.yaml
	gen-py-classes model/schema/chromo.yaml > $@

gendocs:
	gen-markdown -d docs model/schema/chromo.yaml


