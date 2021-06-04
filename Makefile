# TODO: parse from yaml
BUILDS = hg16 dm6 mm10 danRer10 rn6

all: all-chromAlias all-cytoBand src/ontology/imports/ucsc.owl
all-chromAlias: $(patsubst %, download/%-chromAlias.tsv, $(BUILDS))
all-cytoBand: $(patsubst %, download/%-cytoBand.tsv, $(BUILDS))

download/%-chromAlias.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/hg19/database/chromAlias.txt.gz | gzip -dc > $@
download/%-cytoBand.tsv:
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/hg19/database/cytoBand.txt.gz | gzip -dc > $@

src/ontology/imports/ucsc.ofn:
	python monochrom/monochrom.py download/*-cytoBand.tsv -o $@.tmp && mv $@.tmp $@

.PRECIOUS: src/ontology/imports/ucsc.ofn
src/ontology/imports/ucsc.owl: src/ontology/imports/ucsc.ofn
	robot convert -i $< -o $@
