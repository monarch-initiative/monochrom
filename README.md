[![Build Status](https://travis-ci.org/monarch-initiative/monochrom.svg?branch=master)](https://travis-ci.org/monarch-initiative/monochrom)
[![DOI](https://zenodo.org/badge/13996/monarch-initiative/monochrom.svg)](https://zenodo.org/badge/latestdoi/13996/monarch-initiative/monochrom)

# Chromosome Ontology

Chromo (abbreviation CHR) is an automatically derived ontology of chrosomosomes are chromosome parts

This ontology may eventually be housed at http://obofoundry.org/ontology/chr

Currently we use obolibrary PURLs, but this could potentially be changed to e.g. w3ids, depending on discussion re databases in OBO

## About

This "ontology" is a direct conversion of metadata about chromosomes and chromosome bands obtained from UCSC

Each chromosome and chromosomal region is represented as an OWL class, with the following properties:

 * id/IRI
 * name
 * taxon
 * part-parent
 * coordinates + build

See the [schema](model/schema/) for more details.

This ontology is intended primary as a way to provide ontology edges
for classes in disease and phenotype ontologies that must reference
chromosomes, e.g. to define trisomies, etc.

Note that unlike many ontologies, the ontology is not curated - it is a transform

There are some parallels to the OBO version of the NCBI taxonomy
(http://obofoundry.org/ontology/chr)[http://obofoundry.org/ontology/chr),
in that we do not curate any ontological information, we simply
perform a direct transform.

Unlike the NCBI Taxonomy, there is no class hierarchy for chromosomes and chromosome bands. Instead things are arranged as a *partonomy*

 * chr1
    * chr1p
       * chr1p1
          * chr1p11

We deliberately do not create fake grouping classes such as "Human
chromosome". Note that this ontology may therefore look unusual in
ontology browsers, where there is an implicit assumption of some
hierarchy.




## Versions

The latest version of the ontology can always be found at:

http://purl.obolibrary.org/obo/chr.owl  (once this ontology is registered)

(note this will not show up until the request has been approved by obofoundry.org)

## Instructions for maintainers

From the top level of this repo:

```bash
pip install -r requirements.txt
make
```

## Contact

Please use this GitHub repository's [Issue tracker](https://github.com/monarch-initiative/monochrom/issues) to request new terms/classes or report errors or specific concerns related to the ontology.

## Acknowledgements

This ontology repository was created using the [ontology starter kit](https://github.com/INCATools/ontology-starter-kit)
