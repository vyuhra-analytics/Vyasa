import pytest
import pandas as pd

from vyasa.ingest import add_changes
from vyasa.rolls import flag_rolls
from vyasa.validate import validate
from vyasa.write import merge_years, write_parquet


def frame(rows):
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"]).assign(
        date=lambda d: pd.to_datetime(d["date"])
    )


def test_validate_rejects_bad_bars():
    df = frame([
        ("2026-01-01", 10, 11, 9, 10, 1),
        ("2026-01-02", 10, 9, 11, 10, 1),   # high < low
        ("2026-01-03", 10, 11, 9, 12, 1),   # close > high
        ("2026-01-04", 10, 11, 9, 10, -1),  # negative volume
        ("2026-01-05", 10, 11, 9, 10, 1),
    ])
    clean, bad = validate(df)
    assert len(clean) == 2
    assert set(bad.reason) == {"high_lt_low", "ohlc_outside_range", "bad_volume"}


def test_zero_volume_rejected():
    clean, bad = validate(frame([("2013-08-30", 3.5, 3.5, 3.5, 3.5, 0)]))
    assert clean.empty and list(bad.reason) == ["bad_volume"]


def test_negative_prices_kept():
    clean, bad = validate(frame([("2020-04-20", -30, -20, -40, -37, 1)]))
    assert len(clean) == 1 and bad.empty


def weekdays():
    d = pd.bdate_range("2025-11-01", "2026-04-30")
    return pd.DataFrame({"date": d, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1})


def test_roll_dates_ng_and_cl():
    ng = flag_rolls(weekdays(), "NYMEX:NG1!")
    assert "2026-01-28" in set(ng.date[ng.is_roll].dt.strftime("%Y-%m-%d"))  # Feb: 3 bd before Sun Feb 1
    cl = flag_rolls(weekdays(), "NYMEX:CL1!")
    assert "2026-02-19" in set(cl.date[cl.is_roll].dt.strftime("%Y-%m-%d"))  # Mar: expiry Fri Feb 20, TV rolls a bar earlier


def test_write_partitions(tmp_path):
    df = frame([("2025-12-31", 1, 2, 1, 1, 1), ("2026-01-02", 1, 2, 1, 1, 1)])
    paths = write_parquet(df, "NYMEX:CL1!", "1D", tmp_path)
    assert sorted(p.name for p in paths) == ["2025.parquet", "2026.parquet"]
    assert paths[0].parent.name == "crudeoil_1D"
    assert pd.read_parquet(paths[0]).symbol[0] == "NYMEX:CL1!"
    path = merge_years("NYMEX:CL1!", "1D", tmp_path, tmp_path / "ds")
    assert path.name == "crudeoil_1D_2025-2026.parquet"
    (tmp_path / "ds" / "crudeoil_1D_2000-2001.parquet").touch()
    assert merge_years("NYMEX:CL1!", "1D", tmp_path, tmp_path / "ds") == path
    assert [p.name for p in (tmp_path / "ds").iterdir()] == [path.name]
    merged = pd.read_parquet(path)
    assert len(merged) == 2 and merged.date.is_monotonic_increasing


def test_changes():
    df = add_changes(frame([("2026-01-01", 1, 2, 1, 100, 1), ("2026-01-02", 1, 2, 1, 105, 1)]))
    assert pd.isna(df.change[0]) and df.change[1] == 5 and df.change_pct[1] == pytest.approx(5)


def test_validate_drops_today():
    today = pd.Timestamp.now(tz="America/New_York").tz_localize(None).normalize()
    clean, bad = validate(frame([("2026-01-01", 10, 11, 9, 10, 1), (today, 10, 11, 9, 10, 1)]))
    assert len(clean) == 1 and list(bad.reason) == ["incomplete_bar"]
