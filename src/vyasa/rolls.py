"""Flag contract rolls on a continuous front-month series from the NYMEX expiry rules.

`is_roll` marks the first bar showing the next contract. TradingView's 1! switches
on the last trading day for NG (median |gap| 1.9% vs 0.4% normally, volume x2.4) and
one bar earlier for CL (volume jumps >20% on 53% of those bars vs 18% of all days;
gaps are too small to see). That bar's change/change_pct include the roll gap.

CL: last trade = 3 business days before the 25th of the month before delivery
    (if the 25th is not a business day, before the preceding business day).
NG: last trade = 3 business days before the 1st of the delivery month.

Business days are the dates present in the data (holidays have no bars), so the
series must be complete for the span. ponytail: first roll of a series is missed
if its expiry needs bars before the first date; rolls after the last bar are unknown.
"""
import pandas as pd


def _cl(td: pd.DatetimeIndex, y: int, m: int) -> int | None:
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    ref = pd.Timestamp(py, pm, 25)
    if not td[0] <= ref <= td[-1]:  # reference must lie inside the data
        return None
    return td.searchsorted(ref, side="right") - 1  # last bar <= 25th


def _ng(td: pd.DatetimeIndex, y: int, m: int) -> int | None:
    i = td.searchsorted(pd.Timestamp(y, m, 1), side="left")  # first bar >= 1st
    return i if 0 < i < len(td) else None


RULES = {"CL": (_cl, -1), "NG": (_ng, 0)}  # (last-trade bar finder, roll bar offset from it)


def root(symbol: str) -> str:
    """NYMEX:CL1! -> CL"""
    return symbol.split(":")[-1].rstrip("0123456789!")


def flag_rolls(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    out = df.copy()
    if root(symbol) not in RULES:  # no contracts to roll (e.g. FX spot)
        out["is_roll"] = False
        return out
    base, shift = RULES[root(symbol)]
    td = pd.DatetimeIndex(df["date"])
    bases = (base(td, y, m) for y in range(td[0].year, td[-1].year + 1) for m in range(1, 13))
    idx = {b - 3 + shift for b in bases if b is not None}
    out["is_roll"] = [i in idx for i in range(len(df))]
    return out
