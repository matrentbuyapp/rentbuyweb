"""Shared fixtures for test suite."""

import sys
import os
import pytest
import numpy as np

# Ensure api/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from market import HistoricalData


@pytest.fixture
def synthetic_data() -> HistoricalData:
    """Synthetic market data with known, simple properties.

    - CPI: flat 0.25% monthly growth (≈3% annual)
    - Stocks: flat 0.5% monthly growth (≈6% annual)
    - HPI: linear 0.3% monthly appreciation (≈3.6% annual)
    - Mortgage rates: flat 6.5%
    """
    n = 180
    cpi_growth = np.full(n, 1.0025)        # 0.25% per month
    cpi_growth[0] = 1.0                     # first month: no growth

    stock_growth = np.full(n, 1.005)        # 0.5% per month
    stock_growth[0] = 1.0

    hpi_cumulative = np.array([1.0 + 0.003 * i for i in range(n)])  # linear 0.3%/mo

    mortgage_rates = np.full(n, 6.5)        # flat 6.5%

    return HistoricalData(
        cpi_monthly_growth=cpi_growth,
        stock_monthly_growth=stock_growth,
        hpi_cumulative=hpi_cumulative,
        mortgage_rates=mortgage_rates,
    )
