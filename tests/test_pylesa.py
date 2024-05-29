"""Regression test for running pylesa"""
from dataclasses import dataclass
import pandas as pd
from pathlib import Path
import pytest
from typing import List

from pylesa.main import main

@pytest.fixture
def fixed_order_input():
    return Path("tests/data/fixed_order.xlsx").resolve()

@pytest.fixture
def outdir():
    return Path("tests/data").resolve()

@pytest.fixture
def fixed_order_paths(fixed_order_input: Path, outdir: Path) -> List[Path]:
    runname = fixed_order_input.stem
    return [
        outdir / runname / "outputs" / "KPIs" / "KPI_economic_fixed_order.csv",
        outdir / runname / "outputs" / "KPIs" / "KPI_technical_fixed_order.csv",
        outdir / runname / "outputs" / "KPIs" / "output_fixed_order.csv"
    ]

class TestPylesa:
    def test_regression(self, fixed_order_input: Path, outdir: Path, fixed_order_paths: List[Path]):
        # Load existing results, these are committed to the repo
        targets = []
        for csvpath in fixed_order_paths:
            targets.append(pd.read_csv(csvpath))

        # Run pylesa
        main(fixed_order_input, outdir, overwrite=True)

        # Check new results
        for idx, outpath in enumerate(fixed_order_paths):
            expected = targets[idx]
            got = pd.read_csv(outpath)
            assert got.equals(expected)




