"""The formula-driven workbook matches the Python engine to the dollar, every month.

pycel recalculates the workbook from its formulas (openpyxl writes no cached values), so this compares two
independent implementations: numpy convolutions vs. Excel SUMPRODUCTs over reversed curves.
"""
import ast

import numpy as np
import pytest

if not hasattr(ast, "Str"):  # pycel 1.0b30 still calls ast.Str, removed in Python 3.14
    ast.Str = lambda s="", **kw: ast.Constant(value=s)

from pycel import ExcelCompiler  # noqa: E402

from nitro_model.excel_export import col, export  # noqa: E402
from nitro_model.params import REGIONS  # noqa: E402


@pytest.fixture(scope="module")
def xl(tmp_path_factory):
    path = tmp_path_factory.mktemp("xl") / "model.xlsx"
    layout = export(path)
    return ExcelCompiler(filename=str(path)), layout


def _row(xl, sheet, row, T):
    return np.array([xl.evaluate(f"{sheet}!{col(t)}{row}") for t in range(T)], dtype=float)


def test_total_revenue_matches_to_the_dollar(xl, result):
    compiler, layout = xl
    excel = _row(compiler, "Revenue", layout["rows"][("Revenue", "TOTAL")], layout["T"])
    assert np.abs(excel - result["revenue"].sum(axis=(0, 1))).max() < 1.0


@pytest.mark.parametrize("line", ["opening", "new", "reactivated", "churned", "closing"])
def test_subscriber_lines_match(xl, result, line):
    compiler, layout = xl
    excel = _row(compiler, "Subs", layout["rows"][("Subs", line, "TOTAL")], layout["T"])
    assert np.abs(excel - result[line].sum(axis=(0, 1))).max() < 0.01


@pytest.mark.parametrize("region", REGIONS)
def test_segment_revenue_matches(xl, result, params, region):
    compiler, layout = xl
    i = REGIONS.index(region)
    for j, plan in enumerate(params["plans"]):
        excel = _row(compiler, "Revenue", layout["rows"][("Revenue", region, plan)], layout["T"])
        assert np.abs(excel - result["revenue"][i, j]).max() < 1.0, plan


def test_workbook_checks_all_true(xl):
    compiler, _ = xl
    for cell in ("C6", "C7", "C10", "C12"):  # roll-forward, cohort tie, calibration, public band
        assert bool(compiler.evaluate(f"Checks!{cell}")), cell


@pytest.mark.parametrize("shock", [1, -1])
def test_fx_shock_matches_in_workbook(tmp_path, params, shock):
    """The FX sheet applies the shock the same way the engine does."""
    from nitro_model.cohorts import run

    path = tmp_path / "shock.xlsx"
    layout = export(path, overrides={"fx_shock_dir": shock})
    compiler = ExcelCompiler(filename=str(path))
    expected = run(params | {"fx_shock_dir": shock})["revenue"].sum(axis=(0, 1))
    row = layout["rows"][("Revenue", "TOTAL")]
    for t in (11, 21, 22, 40, 71):
        assert compiler.evaluate(f"Revenue!{col(t)}{row}") == pytest.approx(expected[t], abs=1.0)
