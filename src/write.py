"""Write parquet partitioned data/<instrument>_<tf>/<year>.parquet."""
from pathlib import Path

import pandas as pd

from rolls import root

SLUGS = {"CL": "crudeoil", "NG": "naturalgas", "USDINR": "usdinr"}


def folder_name(symbol: str, timeframe: str) -> str:
    r = root(symbol)
    return f"{SLUGS.get(r, r.lower())}_{timeframe}"  # NYMEX:CL1!, 1D -> crudeoil_1D


def write_parquet(df: pd.DataFrame, symbol: str, timeframe: str, out: str | Path = "data") -> list[Path]:
    paths = []
    folder = folder_name(symbol, timeframe)
    for year, part in df.groupby(df["date"].dt.year):
        p = Path(out) / folder / f"{year}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        part.assign(symbol=symbol).to_parquet(p, index=False)
        paths.append(p)
    return paths


def merge_years(symbol: str, timeframe: str, data: str | Path = "data", out: str | Path = "datasets") -> Path:
    """Concatenate data/<symbol_tf>/<year>.parquet into datasets/<symbol_tf>_<from>-<to>.parquet."""
    parts = sorted((Path(data) / folder_name(symbol, timeframe)).glob("*.parquet"))
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True).sort_values("date")
    y0, y1 = df["date"].dt.year.min(), df["date"].dt.year.max()
    p = Path(out) / f"{folder_name(symbol, timeframe)}_{y0}-{y1}.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    for old in p.parent.glob(f"{folder_name(symbol, timeframe)}_*.parquet"):  # stale year ranges
        old.unlink()
    df.reset_index(drop=True).to_parquet(p, index=False)
    return p
