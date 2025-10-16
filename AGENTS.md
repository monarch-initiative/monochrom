# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Monochrom is a chromosome ontology project that automatically generates standardized identifiers and OWL classes for chromosomes and chromosomal parts across species. The project combines:

1. **LinkML Schema**: Core data model definition in `model/schema/chromo.yaml`
2. **Python Pipeline**: Data processing and OWL generation in `monochrom/`
3. **ODK Ontology**: Traditional ontology development using Ontology Development Kit in `src/ontology/`

## Repository Management

This repo uses **Poetry** for Python dependency management (not uv, despite what some older files suggest). The `pyproject.toml` uses Poetry configuration.

Key command: `poetry run <command>` or `poetry install` to set up environment.

## Core Architecture

### Data Flow
1. **Data Sources**: UCSC Genome Browser cytoBand and chromAlias files
2. **Python Processing**: `monochrom/monochrom.py` downloads, parses, and processes genome data
3. **Schema**: LinkML schema (`model/schema/chromo.yaml`) defines data structures
4. **Output Generation**: Multiple formats (OWL, YAML) for each genome build
5. **ODK Integration**: Traditional ontology release process via `src/ontology/`

### Key Classes (LinkML Schema)
- `ChromosomePart`: Individual chromosomes, arms, bands
- `Genome`: Genome build information
- `OrganismTaxon`: Species taxonomy information
- `ChromosomePartCollection`: Container for all chromosome data

### File Structure
- `monochrom/monochrom.py`: Main processing pipeline and CLI
- `monochrom/chromschema.py`: Generated Pydantic classes from LinkML schema
- `genomes.yaml`: Genome metadata and taxon mappings
- `components/`: Generated OWL and YAML files per genome (e.g., `hg38.owl`, `mm39.yaml`)
- `download/`: Cached UCSC data files
- `src/ontology/`: ODK-managed ontology development

## Common Commands

### Building/Generation
```bash
# Generate all components (downloads data, creates OWL/YAML files)
make all

# Generate specific components
make all-components        # Both OWL and YAML
make all-components-owl    # OWL only
make all-components-yaml   # YAML only

# Generate final ontology release
make ontology             # Calls ODK prepare_release

# Regenerate Python schema from LinkML
make monochrom/chromschema.py
```

### Testing
```bash
# Run tests
make test
# OR
pytest
```

### Development
```bash
# Install dependencies
poetry install

# Run CLI directly
poetry run ucsc2owl <args>

# Generate documentation
make gendocs
```

### Data Download
Individual genome data is downloaded automatically by make targets, but manual download:
```bash
# Example for human genome hg38
curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/hg38/database/chromAlias.txt.gz | gzip -dc > download/hg38-chromAlias.tsv
curl -L -s http://hgdownload.cse.ucsc.edu/goldenPath/hg38/database/cytoBandIdeo.txt.gz | gzip -dc > download/hg38-cytoBand.tsv
```

## Supported Genome Builds

Current builds (defined in Makefile `BUILDS`): hg38, ce11, mm39, rn6, galGal6, calJac4, danRer11

To add new genomes: Edit both `Makefile` and `genomes.yaml`.

## Key Design Principles

- **Automated Generation**: No manual curation - direct transform from UCSC data
- **Partonomy Structure**: Hierarchical part-of relationships (chr1 → chr1p → chr1p1 → chr1p11)
- **Multi-species Support**: Single schema handles all supported organisms
- **Multiple Output Formats**: OWL for ontology use, YAML for data interchange
- **Standard Mappings**: Maps to OBO, NCBI, INSDC, Ensembl identifiers

## ODK Integration

The `src/ontology/` directory follows standard ODK patterns:
- `chr-edit.owl`: Hand-edited ontology file
- `Makefile`: ODK-generated build system
- `components/`: Import modules
- `reports/`: Quality control reports

ODK commands run from `src/ontology/`:
```bash
cd src/ontology
make prepare_release    # Full ODK release process
```

## CLI Usage

Main CLI entry point: `ucsc2owl`

```bash
# Convert UCSC files to OWL
poetry run ucsc2owl download/hg38-cytoBand.tsv download/hg38-chromAlias.tsv -o hg38.owl

# Convert to YAML
poetry run ucsc2owl download/hg38-cytoBand.tsv download/hg38-chromAlias.tsv -f yaml -o hg38.yaml
```