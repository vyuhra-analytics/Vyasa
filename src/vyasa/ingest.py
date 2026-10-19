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
    # TV stamps the session open: 09:30 ET (CL) or 18:00 ET the evening before (NG).
    # +6h lands both on the trade date.
    et = pd.to_datetime(df.pop("time"), unit="s", utc=True).dt.tz_convert("America/New_York")
    df["date"] = (et + pd.Timedelta(hours=6)).dt.tz_localize(None).dt.normalize()
    df[COLS[:4]] = df[COLS[:4]].round(6)  # strip back-adjust float noise
    return df[["date", *COLS]].sort_values("date").reset_index(drop=True)


def add_changes(df: pd.DataFrame) -> pd.DataFrame:
    """change = close - prev close; change_pct in percent. Compute before any year filter."""
    out = df.copy()
    out["change"] = out["close"].diff().round(6)
    out["change_pct"] = out["change"] / out["close"].shift().abs() * 100  # abs: prior close can be negative
    return out
