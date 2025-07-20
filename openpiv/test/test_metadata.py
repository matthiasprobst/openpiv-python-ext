import pathlib

import rdflib

from openpiv import windef, metadata


def test_save_metadata():
    settings = windef.PIVSettings()

    meta_filename = metadata.save_metadata(settings, 'test_metadata.ttl')
    assert pathlib.Path(meta_filename).exists()
    g = rdflib.Graph()
    g.parse(source=meta_filename, format='turtle')
    res = g.query("""
    PREFIX pivmeta: <https://matthiasprobst.github.io/pivmeta#>
    PREFIX m4i: <http://w3id.org/nfdi4ing/metadata4ing#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?method ?windowWeightingFunction ?label
    WHERE {
        ?method a pivmeta:CorrelationMethod .
        ?method m4i:hasParameter ?parameter .
        ?method pivmeta:hasWindowWeightingFunction ?windowWeightingFunction .
        ?parameter rdfs:label ?label
    }
    """)
    results = list(res)
    assert len(results) == 1, "No correlation method found in metadata"
    assert str(results[0][rdflib.Variable("windowWeightingFunction")]) == "https://matthiasprobst.github.io/pivmeta#SquareWindow"
    assert str(results[0][rdflib.Variable("label")]) == "normalized correlation"