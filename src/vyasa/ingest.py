"""Raw TradingView MCP `data_get_ohlcv` JSON -> DataFrame."""
import json
from pathlib import Path

import pandas as pd

COLS = ["open", "high", "low", "close", "volume"]


def load_raw(path: str | Path) -> pd.DataFrame:
    """Accepts the MCP response ({"bars": [...]}) or a bare list of bars."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, list) and data and "text" in data[0]:  # MCP content wrapper
        data = json.loads(data[0]["text"])
    bars = data["bars"] if isinstance(data, dict) else data
    df = pd.DataFrame(bars)
    # TV stamps the session open the evening before the trade date.
    # Futures: 18:00 ET (UTC hour moves with DST) -> +6h in ET lands on the trade date.
    # FX: fixed 22:00 UTC (constant UTC hour) -> +2h in UTC.
    utc = pd.to_datetime(df.pop("time"), unit="s", utc=True)
    if utc.dt.hour.nunique() == 1:
        shifted = (utc + pd.Timedelta(hours=2)).dt.tz_localize(None)
    else:
        shifted = (utc.dt.tz_convert("America/New_York") + pd.Timedelta(hours=6)).dt.tz_localize(None)
    df["date"] = shifted.dt.normalize()
    df[COLS[:4]] = df[COLS[:4]].round(6)  # strip back-adjust float noise
    return df[["date", *COLS]].sort_values("date").reset_index(drop=True)


def add_changes(df: pd.DataFrame) -> pd.DataFrame:
    """change = close - prev close; change_pct in percent. Compute before any year filter."""
    out = df.copy()
    out["change"] = out["close"].diff().round(6)
    out["change_pct"] = out["change"] / out["close"].shift().abs() * 100  # abs: prior close can be negative
    return out
