"""The website runs cohorts.py in the browser (Pyodide), so the engine must stay numpy-only and its payload strict JSON."""
import ast
import json
from pathlib import Path

import numpy as np

from nitro_model import cohorts
from nitro_model.cohorts import layers, payload
from nitro_model.params import slider_specs


def test_engine_imports_only_numpy():
    tree = ast.parse(Path(cohorts.__file__).read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods <= {"numpy", "__future__"}, mods


def test_payload_is_strict_json(params):
    json.dumps(payload(params), allow_nan=False)


def test_engine_runs_on_json_roundtripped_params(params, result):
    """The browser hands the engine params that went through JSON; results must not change."""
    p = json.loads(json.dumps(params))
    out = payload(p)
    np.testing.assert_allclose(out["summary"]["revenue"], result["revenue"].sum(axis=(0, 1)))


def test_layers_sum_to_closing(params, result):
    stack = np.sum([np.array(v) for v in layers(params, result).values()], axis=0)
    np.testing.assert_allclose(stack, result["closing"].sum(axis=(0, 1)), atol=1e-3)


def test_sliders_bounded_and_finite(assumptions, params):
    for s in slider_specs(assumptions):
        assert np.isfinite([s["low"], s["value"], s["high"]]).all(), s["key"]
        assert s["low"] <= s["value"] <= s["high"], s["key"]
        assert s["key"] in params
