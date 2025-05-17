# CCMM Vocabularies for NRP Invenio repositories

This module provides convertors that convert CCMM vocabularies to Invenio
vocabularies.

## Installation

To install the module, run the following command:

```bash
cd invenio
uv venv
uv sync
```

## Updating the vocabularies

Some of the vocabularies will be downloaded automatically from the web -
languages, resource types, file types and access rights. Just run the command
below to update them.

Licenses and subject_schemes are currently not covered by the list of vocabularies
techlib is curating and are placed manually in the invenio/input.

To update techlib curated vocabularies, please export the actual files from the CCMM vocabularies
excel stored at <https://researchinfracz.sharepoint.com/:x:/r/sites/PS_EOSC_CZ_implementation/_layouts/15/Doc.aspx?sourcedoc=%7BD3EA6931-567C-4159-8720-A213D9C2B84E%7D&file=CCMM_slovniky.xlsx&action=default&mobileredirect=true> and place them in the invenio/input directory
keeping the file names. Note that you have to use the unicode export option.

Then run the conversion script.

## Converting CCMM vocabularies to Invenio vocabularies

Run

```bash
cd invenio
uv run convert_vocabularies
```

Then commit and push the resulting files. In target repository, run the vocabulary
importing script. It will automatically connect to github and import the vocabularies
from there.

```bash
cd my-repository

scripts/import_ccmm_vocabularies.sh
```
