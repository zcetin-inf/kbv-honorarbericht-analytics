import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import data_check  # noqa: E402


@pytest.fixture(scope="module")
def df():
    if not data_check.LONG.exists():
        pytest.skip("Erst 'python src/etl.py' ausführen (CSV fehlt).")
    return data_check.load()


def test_no_duplicate_keys(df):
    assert data_check.check_duplicates(df).empty


def test_grid_is_complete(df):
    assert data_check.check_complete_grid(df) == 0


def test_quarters_are_consecutive(df):
    assert data_check.check_periods(df) == []


def test_alte_plus_neue_equals_total(df):
    assert data_check.check_alte_plus_neue(df).empty


def test_regions_sum_to_total_when_complete(df):
    assert data_check.check_regions_sum_to_total(df).empty


def test_missing_values_are_all_or_nothing(df):
    assert data_check.check_nan_pattern(df).empty


@pytest.mark.parametrize("target", list(data_check.DERIVED_RULES))
def test_derived_kpis_match_recomputation(df, target):
    assert data_check.check_derived_kpis(df)[target].empty


def test_auszahlungsquote_is_a_fraction_not_percent(df):
    lo, hi = data_check.auszahlungsquote_range(df)
    assert 0 < lo and hi < 2
