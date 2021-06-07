## Customize Makefile settings for chr
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

# NOW HANDLED FROM ROOT DIR
#edit:
#	wget https://data.monarchinitiative.org/ttl/monochrom.ttl -O chr-edit.ttl


# TODO: parse from yaml
BUILDS = hg16 dm6 mm10 danRer10 rn6

ALL_CHROMALIAS=$(patsubst %, $(TMPDIR)/%-chromAlias.tsv, $(BUILDS))
ALL_CYTOBAND=$(patsubst %, $(TMPDIR)/%-cytoBand.tsv, $(BUILDS))

$(TMPDIR)/%-chromAlias.tsv: | $(TMPDIR)
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/hg19/database/chromAlias.txt.gz | gzip -dc > $@
.PRECIOUS: $(TMPDIR)/%-chromAlias.tsv

$(TMPDIR)/%-cytoBand.tsv: | $(TMPDIR)
	curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/hg19/database/cytoBand.txt.gz | gzip -dc > $@
.PRECIOUS: $(TMPDIR)/%-cytoBand.tsv

$(TMPDIR)/ucsc.ofn: monochrom/monochrom.py $(ALL_CHROMALIAS) $(ALL_CYTOBAND) | $(TMPDIR)
	python $< $(TMPDIR)/*-cytoBand.tsv -o $@.tmp && mv $@.tmp $@

.PHONY: requirements
requirements:
	pip install -r requirements.txt

$(COMPONENTSDIR)/ucsc.owl: $(TMPDIR)/ucsc.ofn
	if [ $(IMP) = true ]; then $(ROBOT) merge -i $(TMPDIR)/ucsc.ofn \
	annotate --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) -o $@; fi
.PRECIOUS: $(COMPONENTSDIR)/ucsc.owl
