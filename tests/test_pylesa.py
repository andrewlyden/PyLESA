"""Regression test for running pylesa"""

import numpy as np
import pandas as pd
from pathlib import Path
import pytest
from typing import List

from pylesa.main import main


@pytest.fixture
def fixed_order_input():
    return Path("tests/data/fixed_order.xlsx").resolve()

@pytest.fixture
def csvpaths():
    pth = Path()
    return [
        pth / "outputs" / "KPIs" / "KPI_economic_fixed_order.csv",
        pth / "outputs" / "KPIs" / "KPI_technical_fixed_order.csv",
        pth / "outputs" / "KPIs" / "output_fixed_order.csv",
    ]

@pytest.fixture
def fixed_order_paths(fixed_order_input: Path, csvpaths) -> List[Path]:
    runname = fixed_order_input.stem
    return [
        Path("tests/data").resolve() / runname / csvpth for csvpth in csvpaths
    ]

@pytest.fixture
def temp_paths(fixed_order_input: Path, tmpdir: Path, csvpaths) -> List[Path]:
    runname = fixed_order_input.stem
    return [
        tmpdir / runname / csvpth for csvpth in csvpaths
    ]

class TestPylesa:
    def test_regression(
        self, fixed_order_input: Path, fixed_order_paths: List[Path], tmpdir: Path, temp_paths: List[Path]
    ):
        # Load existing results, these are committed to the repo
        targets = []
        for csvpath in fixed_order_paths:
            targets.append(pd.read_csv(csvpath))

        # Run pylesa
        main(fixed_order_input, tmpdir)

        # Check new results
        for idx, outpath in enumerate(temp_paths):
            expected = targets[idx]
            got = pd.read_csv(outpath)
            assert expected.columns.all() == got.columns.all()
            assert np.allclose(expected.values, got.values)
