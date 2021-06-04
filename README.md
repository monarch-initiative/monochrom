[![Build Status](https://travis-ci.org/monarch-initiative/monochrom.svg?branch=master)](https://travis-ci.org/monarch-initiative/monochrom)
[![DOI](https://zenodo.org/badge/13996/monarch-initiative/monochrom.svg)](https://zenodo.org/badge/latestdoi/13996/monarch-initiative/monochrom)

# Chromosome Ontology

Chromo (abbreviation CHR) is an automatically derived ontology of chrosomosomes are chromosome parts

More information can be found at http://obofoundry.org/ontology/chr (once this ontology is registered)

## Versions

### Stable release versions

The latest version of the ontology can always be found at:

http://purl.obolibrary.org/obo/chr.owl  (once this ontology is registered)

(note this will not show up until the request has been approved by obofoundry.org)

### Editors' version

Editors of this ontology should use the edit version, [src/ontology/chr-edit.owl](src/ontology/chr-edit.owl)

Note that this should be extremely minimal, as it imports the auto-generated ucsc.owl file

## Regenerating

Fromt the top level of this repo:

```bash
pip install -r requirements.txt
make
```

## Contact

Please use this GitHub repository's [Issue tracker](https://github.com/monarch-initiative/monochrom/issues) to request new terms/classes or report errors or specific concerns related to the ontology.

## Acknowledgements

This ontology repository was created using the [ontology starter kit](https://github.com/INCATools/ontology-starter-kit)
