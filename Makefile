# TODO: parse from yaml
BUILDS = hg38 ce11 mm10 rn6
# TODO: dm6

all: all-chromAlias all-cytoBand src/ontology/imports/ucsc.owl
all-chromAlias: $(patsubst %, download/%-chromAlias.tsv, $(BUILDS))
all-cytoBand: $(patsubst %, download/%-cytoBand.tsv, $(BUILDS))

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

src/ontology/imports/ucsc.ofn:
	python -m monochrom.monochrom download/*-*.tsv -o $@.tmp && mv $@.tmp $@

.PRECIOUS: src/ontology/imports/ucsc.ofn
src/ontology/imports/ucsc.owl: src/ontology/imports/ucsc.ofn
	robot convert -i $< -o $@

## Schema

monochrom/chromschema.py: model/schema/chromo.yaml
	gen-py-classes model/schema/chromo.yaml > $@