import traceback
from functools import partial
from pathlib import Path

import click
import yaml
from tqdm import tqdm

from invenio_ccmm.base import VocabularyReader
from invenio_ccmm.ccmm_copy import CopyReader  # noqa
from invenio_ccmm.ccmm_csv import CSVReader  # noqa
from invenio_ccmm.ccmm_filtered import DescendantsOfFilter, FilteredReader  # noqa
from invenio_ccmm.ccmm_sparql import SPARQLReader  # noqa


@click.command()
def convert_vocabularies() -> None:
    root_dir = Path(__file__).parent.parent

    converters: list[tuple[VocabularyReader, Path]] = [
        (
            CSVReader("Agent Role", root_dir / "input/CCMM_slovniky(AgentRole).csv"),
            root_dir / "fixtures/ccmm_agent_role.yaml",
        ),
        (
            CSVReader(
                "Alternate Title",
                root_dir / "input/CCMM_slovniky(AlternateTitle).csv",
            ),
            root_dir / "fixtures/ccmm_alternate_title.yaml",
        ),
        (
            CSVReader(
                "Location Relation",
                root_dir / "input/CCMM_slovniky(LocationRelation).csv",
            ),
            root_dir / "fixtures/ccmm_location_relation.yaml",
        ),
        (
            CSVReader(
                "Relation Type",
                root_dir / "input/CCMM_slovniky(RelationType).csv",
            ),
            root_dir / "fixtures/ccmm_relation_type.yaml",
        ),
        (
            CSVReader(
                "Subject Category",
                root_dir / "input/CCMM_slovniky(SubjectCategory).csv",
            ),
            root_dir / "fixtures/ccmm_subject_category.yaml",
        ),
        (
            CSVReader(
                "Time Reference",
                root_dir / "input/CCMM_slovniky(TimeReference).csv",
            ),
            root_dir / "fixtures/ccmm_time_reference.yaml",
        ),
        (
            SPARQLReader(
                "Languages",
                "http://publications.europa.eu/resource/authority/language",
                "http://publications.europa.eu/resource/authority/language",
            ),
            root_dir / "fixtures/ccmm_languages.yaml",
        ),
        (
            SPARQLReader(
                "Access Rights",
                "https://vocabularies.coar-repositories.org/access_rights/access_rights.nt",
                "http://purl.org/coar/access_right/scheme",
                format="turtle",
                load_subgraphs=False,
                extra=root_dir / "input/addon_access_rights.ttl",
            ),
            root_dir / "fixtures/ccmm_access_rights.yaml",
        ),
        (
            SPARQLReader(
                "Resource types",
                "https://vocabularies.coar-repositories.org/resource_types/resource_types.nt",
                "http://purl.org/coar/resource_type/scheme",
                format="turtle",
                load_subgraphs=False,
            ),
            root_dir / "fixtures/ccmm_resource_types.yaml",
        ),
        (
            SPARQLReader(
                "File types",
                "http://publications.europa.eu/resource/authority/file-type",
                "http://publications.europa.eu/resource/authority/file-type",
            ),
            root_dir / "fixtures/ccmm_file_types.yaml",
        ),
        (
            CopyReader(
                "Licenses",
                root_dir / "input/licenses.yaml",
            ),
            root_dir / "fixtures/ccmm_licenses.yaml",
        ),
        (
            CopyReader(
                "Subject schemes",
                root_dir / "input/subject_schemes.yaml",
            ),
            root_dir / "fixtures/ccmm_subject_schemes.yaml",
        ),
        (
            FilteredReader(
                "Contributor type",
                root_dir / "fixtures/ccmm_agent_role.yaml",
                filter_cls=partial(
                    DescendantsOfFilter,
                    descendants_of={
                        "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Contributor"
                    },
                ),
            ),
            root_dir / "fixtures/ccmm_contributor_type.yaml",
        ),
    ]

    with_progress = tqdm(converters, leave=False, unit="vocab")
    for reader, output_path in with_progress:
        try:
            with_progress.set_description(reader.name)
            with_progress.refresh()
            data = reader.data()
            with open(output_path, "w", encoding="utf-8") as output_file:
                yaml.safe_dump_all(
                    data,
                    output_file,
                    allow_unicode=True,
                    default_flow_style=False,
                )
        except Exception as e:
            print(f"Error converting {reader.name}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    convert_vocabularies()
