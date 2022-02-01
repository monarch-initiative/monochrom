## Customize Makefile settings for chr
##
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

# NOW HANDLED FROM ROOT DIR

humanpartrange_TEMPLATE="https://docs.google.com/spreadsheets/d/e/2PACX-1vSKTaa4xbpY_BxuNDj_BFKHbwVihxuzgKvrmQoef5y5MlgZCZzJIoaOpYjoUv4l2n6Q04zfnMnOWH40/pub?gid=103166927&single=true&output=tsv"

.PHONY: sync_humanpartrange

sync_google_sheets:
	wget $(humanpartrange_TEMPLATE) -O $(COMPONENTSDIR)/humanpartrange.tsv



$(COMPONENTSDIR)/%.owl: $(COMPONENTSDIR)/%.tsv $(SRC)
	$(ROBOT) merge -i $(SRC) template --template $< --prefix "CHR: http://purl.obolibrary.org/obo/CHR_" --output $@ && \
	$(ROBOT) annotate --input $@ --ontology-iri $(ONTBASE)/$@ -o $@
