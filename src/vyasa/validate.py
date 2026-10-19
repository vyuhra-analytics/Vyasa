"""Per-bar validation. Bad bars are flagged and dropped, never silently fixed.

No positive-price check: futures can settle negative (CL 2020-04-20 closed -37.63).
"""
import pandas as pd

from .ingest import COLS


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean, rejected). rejected has a `reason` column."""
    df = df.drop_duplicates("date", keep="last").copy()
    today = pd.Timestamp.now(tz="America/New_York").tz_localize(None).normalize()
    checks = {
        "incomplete_bar": df["date"] >= today,  # trade date still in session
        "null": df[COLS].isna().any(axis=1),
        # zero volume = placeholder bar (NG 2013-08-30); skipped when the source has no volume (FX)
        "bad_volume": (df["volume"] <= 0) & (df["volume"] > 0).any(),
        "high_lt_low": df["high"] < df["low"],
        "ohlc_outside_range": (
            (df[["open", "close"]].max(axis=1) > df["high"])
            | (df[["open", "close"]].min(axis=1) < df["low"])
        ),
    }
    reason = pd.Series("", index=df.index)
    for name, bad in checks.items():
        reason = reason.where(~bad | (reason != ""), name)
    bad = reason != ""
    return df[~bad].reset_index(drop=True), df[bad].assign(reason=reason[bad]).reset_index(drop=True)
