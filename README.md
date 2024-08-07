![Build Status](https://github.com/monarch-initiative/monochrom/workflows/CI/badge.svg)

# Chromosome Ontology

Chromo (abbreviation CHR) is an automatically derived ontology of chrosomosomes are chromosome parts

This ontology may eventually be housed at http://obofoundry.org/ontology/chr

Currently we use obolibrary PURLs, but this could potentially be changed to e.g. w3ids, depending on discussion re databases in OBO

Until this is released, you can browse either:

 * chr.owl -- multiple species in one ontology, with minimal imports merged
 * [components](components/) -- one file per species, both OWL and YAML

## About

This "ontology" is a direct conversion of metadata about chromosomes and chromosome bands obtained from [UCSC chromosome and cytoband data](https://genome.ucsc.edu/cgi-bin/hgTables?db=hg38&hgta_group=map&hgta_track=cytoBand&hgta_table=cytoBand&hgta_doSchema=describe+table+schema)

Each chromosome and chromosomal region is represented as an OWL class, with the following properties:

 * id/IRI
 * name
 * [taxon](https://monarch-initiative.github.io/monochrom/taxon/)
 * [part-parent](https://monarch-initiative.github.io/monochrom/parent/)
 * coordinates + build
 * aliases and exact mappings (e.g. to NCBI/INSDC as well as ENSEMBL)

To browse the schema, see [the schema docs](http://monarch-initiative.github.io/monochrom/)

See the [schema](model/schema/) for more details.

The use cases for this "ontology" are:

 * To provide standardized identifiers and PURLs for chromosomes and chromosome parts
 * To be used as an import to other ontologies; e.g. to define trisomies for diseases
 * To provide a source of nodes in knowledge graphs
 * For text mining purposes
 * As a nexus for mapping efforts where other terminologies have incorporated chrosomes or their parts (NCIT, MESH, etc)

This ontology is intended primary as a way to provide ontology edges
for classes in disease and phenotype ontologies that must reference
chromosomes, e.g. to define trisomies, etc.

Note that unlike many ontologies, the ontology is not curated - it is a programmatic transform

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

Currently only a small number of genomes are provided - it should be relatively easy to extend this to other genomes so long as they are covered by UCSC.

Protege screenshot:

![image](https://user-images.githubusercontent.com/50745/121618393-863cee80-ca1b-11eb-8fff-f7cfe309986a.png)

## TODO

Align with karyotype ontology:

https://arxiv.org/pdf/1305.3758.pdf

## Versions

The latest version of the ontology can always be found at:

http://purl.obolibrary.org/obo/chr.owl  (once this ontology is registered)

(note this will not show up until the request has been approved by obofoundry.org)

## Instructions for maintainers

From the top level of this repo:

```bash
poetry install
make
```

This will update the monochrom component in `src/ontology/components/ucsc.owl`. To produce and official ODK release:

```bash
cd src/ontology
make prepare_release
```

The [Makefile](Makefile) and the metadata file [genomes.yaml](genomes.yaml) drive the python code in [monochrom/](monochrom/).

To add more genomes, it is necessary to extend both the Makefile and the genomes metadata file, but this could be made more elegant in the future.

If you wish to modify the code, here is how it is structured, and the underlying philosophy.

Everything is driven by a LinkML schema, see [schema](model/schema/)

This defines a few core classes:

 * [ChromosomePart](https://monarch-initiative.github.io/monochrom/ChromosomePart)
 * [Genome](https://monarch-initiative.github.io/monochrom/Genome)
 * [OrganismTaxon](https://monarch-initiative.github.io/monochrom/OrganismTaxon)


These have properties (slots) such as id, start, end, ...

The schema has extensive mappings to standard URIs either from OBO or from the wider world of semantics

The code monochrom.py takes care of

 - parsing files to the chromo datamodel
    - cytoBand.txt files - with the core coordinate info
    - chromAliases.txt files - with alternate names and mappings
 - additional processing
    - assigning synonyms
    - inferring parent bands and arms (UCSC files only give coordinates for most granular subdivisions)
    - validation, e.g. range checking
 - mapping the chromo datamodel
    - mapping to OWL
    - (TODO) mapping tp KGX via Koza

Note that the chromo objects will naturally serialize to YAML. See the components/ directory for examples. We provide both OWL and YAML

The mapping to OWL is handled with relatively generic code that uses slot and class uris defined in the LinkML schema - thus keeping things relaively generic. In future we may instead emit a CSV and use ROBOT templates (mapping from LinkML to robot templates is in the works)

## Contact

Please use this GitHub repository's [Issue tracker](https://github.com/monarch-initiative/monochrom/issues) to request new terms/classes or report errors or specific concerns related to the ontology.

## Acknowledgements

This ontology repository was created using the [ontology development kit](https://github.com/INCATools/ontology-development-kit)
