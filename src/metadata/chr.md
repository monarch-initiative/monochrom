---
layout: ontology_detail
id: chr
title: monochrom
jobs:
  - id: https://travis-ci.org/monarch-initiative/monochrom
    type: travis-ci
build:
  checkout: git clone https://github.com/monarch-initiative/monochrom.git
  system: git
  path: "."
contact:
  email: 
  label: 
  github: 
description: monochrom is an ontology...
domain: stuff
homepage: https://github.com/monarch-initiative/monochrom
products:
  - id: chr.owl
    name: "monochrom main release in OWL format"
  - id: chr.obo
    name: "monochrom additional release in OBO format"
  - id: chr.json
    name: "monochrom additional release in OBOJSon format"
  - id: chr/chr-base.owl
    name: "monochrom main release in OWL format"
  - id: chr/chr-base.obo
    name: "monochrom additional release in OBO format"
  - id: chr/chr-base.json
    name: "monochrom additional release in OBOJSon format"
dependencies:
- id: ro
- id: so

tracker: https://github.com/monarch-initiative/monochrom/issues
license:
  url: http://creativecommons.org/licenses/by/3.0/
  label: CC-BY
activity_status: active
---

Enter a detailed description of your ontology here. You can use arbitrary markdown and HTML.
You can also embed images too.

