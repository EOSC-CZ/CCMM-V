import logging
from functools import partial
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError

from rdflib import SKOS, Graph, URIRef
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm.contrib.concurrent import process_map

from .base import VocabularyReader

# Set up logging to see retry attempts
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom retry configuration
RETRY_CONFIG: dict[str, Any] = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, min=2, max=30),  # 2s, 4s, 8s, etc. up to 30s
    "retry": retry_if_exception_type((URLError, HTTPError, ConnectionError)),
    "before_sleep": before_sleep_log(logger, logging.WARNING),
    "reraise": True,
}


@retry(**RETRY_CONFIG)
def parse_source(url: str, format: str = "xml") -> Graph:
    """Parse RDF with automatic retries for transient errors."""
    g = Graph()
    try:
        g.parse(url, format=format)
        return g
    except Exception as e:
        logger.warning(f"Attempt failed for {url}: {str(e)}")
        raise  # Re-raise for tenacity to handle


class SPARQLReader(VocabularyReader):
    def __init__(
        self,
        name: str,
        endpoint: str,
        skos_concept: str,
        extra: Path | None = None,  # turtle serialization of extra triples
        load_subgraphs: bool = True,
        format: str = "xml",
    ):
        super().__init__(name)
        self.endpoint = endpoint
        self.skos_concept = skos_concept
        self.extra = extra
        self.load_subgraphs = load_subgraphs
        self.format = format

    def data(self) -> list[dict[str, str]]:
        """Convert CCMM from SPARQL to YAML that can be imported to NRP Invenio.

        The query must return the following columns:
        - id
        - iri
        - title_cs
        - title_en
        - definition_cs
        - definition_en
        """

        # whole_graph: Graph = parse_source("file:///tmp/ccmm.ttl", format="turtle")
        whole_graph: Graph = parse_source(self.endpoint, format=self.format)

        if self.load_subgraphs:
            self._load_subgraphs(whole_graph)

        # add extra triples to the graph
        if self.extra:
            extra_graph = Graph()
            with open(self.extra, "r", encoding="utf-8") as extra_file:
                extra_graph.parse(extra_file, format="turtle")
            whole_graph += extra_graph

        # # save the whole graph to a turtle file /tmp/ccmm.ttl
        # whole_graph.serialize("/tmp/ccmm.ttl", format="turtle")

        rows = whole_graph.query(
            """
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?concept ?label_cs ?label_en ?identifier
    WHERE {
    ?concept a skos:Concept ;
                skos:inScheme ?scheme .

        # Get English label (prefLabel first, then altLabel)
    OPTIONAL {
        { ?concept skos:prefLabel ?prefLabel_en FILTER(lang(?prefLabel_en) = "en") }
        UNION
        { ?concept skos:altLabel ?altLabel_en }
        BIND(COALESCE(?prefLabel_en, ?altLabel_en) AS ?label_en)
    }
    
    # Get Czech label (prefLabel first, then english label)
    OPTIONAL {
        { ?concept skos:prefLabel ?label_cs FILTER(lang(?label_cs) = "cs") }
    }
    
    # Get dc:identifier if available
    OPTIONAL { ?concept dc:identifier ?identifier }
    }
    ORDER BY ?concept                                            
                        """,
            initBindings={
                "scheme": URIRef(self.skos_concept),
            },
        )
        terms: list[dict[str, Any]] = []
        converted: dict[str, Any] = {}
        for row in cast(tuple[Any, ...], rows):
            iri, title_cs, title_en, term_id = [
                str(x) if x is not None else None for x in row
            ]
            # Skip empty rows
            if not iri:
                continue
            # Skip rows without titles
            if title_cs is None and title_en is None:
                continue

            # set term_id if it was not provided
            if not term_id:
                term_id = iri.split("/")[-1]
                term_id = term_id.split("#")[-1]

            if term_id in converted:
                continue
            term: dict[str, Any] = {
                "id": term_id,
                "title": {
                    "cs": title_cs or title_en,
                    "en": title_en or title_cs,
                },
                "props": {
                    "iri": iri,
                },
            }
            converted[term_id] = term
            terms.append(term)
        return terms

    def _load_subgraphs(self, whole_graph: Graph) -> None:
        """Load all subgraphs from the SKOS concept scheme and merge them into the whole graph."""

        # Get all concepts
        scheme = URIRef(self.skos_concept)
        subjects = [str(x) for x in whole_graph.subjects(SKOS.inScheme, scheme)]

        # enrich graph with all the subjects
        for subject_graph in process_map(
            partial(parse_source, format=self.format),
            subjects,
            max_workers=20,
            chunksize=10,
            leave=False,
            unit="subgraph",
        ):
            whole_graph += cast(Graph, subject_graph)
