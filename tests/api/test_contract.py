"""Compare l'API réellement générée par FastAPI avec le contrat ``openapi.yml`` fourni.

Seules les opérations de la séance 1 sont attendues (``x-session``) : on ne vérifie pas
ce qui n'est pas encore livré.
"""

from pathlib import Path

import pytest
import yaml

from eligibilite_livraison.api.app import create_app

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "openapi.yml"
CURRENT_SESSION = 1
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def generated(container) -> dict:
    return create_app(container).openapi()


def _resolve(spec: dict, schema: dict) -> dict:
    while "$ref" in schema:
        node = spec
        for part in schema["$ref"].removeprefix("#/").split("/"):
            node = node[part]
        schema = node
    return schema


def _expected_operations(contract: dict):
    for path, item in contract["paths"].items():
        for method, operation in item.items():
            if method in HTTP_METHODS and operation.get("x-session", 1) <= CURRENT_SESSION:
                yield path, method, operation


def _operations_ids(contract: dict) -> list[str]:
    return [f"{m.upper()} {p}" for p, m, _ in _expected_operations(contract)]


def test_every_session_1_operation_is_implemented(contract, generated):
    for path, method, operation in _expected_operations(contract):
        assert path in generated["paths"], f"{path} absent de l'API"
        implemented = generated["paths"][path].get(method)
        assert implemented is not None, f"{method.upper()} {path} absent de l'API"
        assert implemented["operationId"] == operation["operationId"]


def test_declared_status_codes_are_documented(contract, generated):
    for path, method, operation in _expected_operations(contract):
        implemented = set(generated["paths"][path][method]["responses"])
        expected = set(operation["responses"])
        assert expected <= implemented, f"{method.upper()} {path} : manque {expected - implemented}"


def test_nothing_beyond_the_contract_is_exposed(contract, generated):
    allowed = {
        (path, method)
        for path, item in contract["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }
    exposed = {
        (path, method)
        for path, item in generated["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }
    assert exposed <= allowed


def test_order_features_schema_matches_contract(contract, generated):
    expected = contract["components"]["schemas"]["OrderFeatures"]
    actual = generated["components"]["schemas"]["OrderFeatures"]

    assert set(actual["required"]) == set(expected["required"])
    assert set(actual["properties"]) == set(expected["properties"])
    assert actual["additionalProperties"] is False
    for name, spec in expected["properties"].items():
        resolved_expected = _resolve(contract, spec)
        resolved_actual = _resolve(generated, actual["properties"][name])
        for keyword in ("minimum", "maximum", "enum"):
            if keyword in resolved_expected:
                assert resolved_actual.get(keyword) == resolved_expected[keyword], (name, keyword)


@pytest.mark.parametrize("schema", ["Prediction", "OrderAccepted", "HealthStatus", "Error"])
def test_response_schemas_expose_the_required_fields(contract, generated, schema):
    generated_name = "ErrorResponse" if schema == "Error" else schema
    expected = contract["components"]["schemas"][schema]
    actual = generated["components"]["schemas"][generated_name]

    assert set(expected["required"]) <= set(actual.get("required", [])) | {
        name for name, spec in actual["properties"].items() if "default" in spec
    }
    assert set(expected["properties"]) <= set(actual["properties"])
