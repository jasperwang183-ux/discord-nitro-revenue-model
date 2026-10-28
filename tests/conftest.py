import pytest

from nitro_model.assumptions import Assumptions
from nitro_model.cohorts import run
from nitro_model.params import build_params


@pytest.fixture(scope="session")
def assumptions() -> Assumptions:
    return Assumptions.load()


@pytest.fixture(scope="session")
def params(assumptions) -> dict:
    return build_params(assumptions, "base")


@pytest.fixture(scope="session")
def result(params) -> dict:
    return run(params)
