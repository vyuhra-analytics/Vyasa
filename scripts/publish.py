"""Publish datasets/*.parquet plus a dataset card to a Hugging Face dataset repo.

    hf auth login                      # once, enter your own token
    python scripts/publish.py vyuhra-analytics/vyasa            # private repo (default)
    python scripts/publish.py vyuhra-analytics/vyasa --public --tag v2026.10

Parquet files in the repo that are not in datasets/ are deleted.
"""
import argparse
import tempfile
from pathlib import Path

import pandas as pd
from vyasa.rolls import RULES

from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

NAMES = {"CL": "WTI Crude Oil", "NG": "Henry Hub Natural Gas", "USDINR": "US Dollar / Indian Rupee"}


def catalog(files) -> str:
    """Markdown table of every dataset file."""
    rows = ["| Instrument | File | Symbol | Timeframe | Range | Rows | Rolls |", "|---|---|---|---|---|---|---|"]
    for f in files:
        d = pd.read_parquet(f)
        root = d.symbol[0].split(":")[-1].rstrip("0123456789!")
        tf = f.stem.split("_")[1]
        rows.append(f"| {NAMES.get(root, root)} | `{f.name}` | `{d.symbol[0]}` | {tf} "
                    f"| {d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d} | {len(d):,} | {int(d.is_roll.sum()) if root in RULES else 'n/a'} |")
    return chr(10).join(rows)


def configs(files) -> str:
    """One viewer/load_dataset config per file, e.g. load_dataset(repo, "crudeoil_1d")."""
    out = []
    for f in files:
        name, tf = f.stem.split("_")[:2]
        out.append(f"  - config_name: {name}_{tf.lower()}")
        out.append(f"    data_files: {f.name}")
    return chr(10).join(out)


CARD = """---
pretty_name: "Vyasa: Daily OHLCV (WTI Crude Oil, Natural Gas, USD/INR)"
license: other
license_name: unspecified
task_categories:
- time-series-forecasting
tags:
- finance
- futures
- commodities
- energy
- crude-oil
- natural-gas
- wti
- nymex
- ohlcv
- candlestick
- time-series
- continuous-futures
- forex
- fx
- usdinr
- inr
size_categories:
- 1K<n<10K
configs:
{configs}
---
# Vyasa: Daily OHLCV

Clean daily OHLCV candles for NYMEX futures (WTI crude oil `CL1!`, Henry Hub natural gas `NG1!`)
and USD/INR spot FX (`FX_IDC:USDINR`), 2010 to present, with price change, percent change and contract-roll flags. Built for training,
validating and evaluating machine learning and LLM time-series models.

- Futures are continuous front-month, **unadjusted** (no back-adjustment). USDINR is spot FX.
- Files: `<instrument>_<timeframe>_<from>-<to>.parquet`, one per symbol.

## Datasets

{catalog}

- Columns: `date`, `open`, `high`, `low`, `close`, `volume`, `change` (close - prior close),
  `change_pct` (percent, abs prior close as denominator), `is_roll`, `symbol`.
- `is_roll` (futures only; always `False` for FX): first bar of the next contract (NYMEX expiry rules; NG on expiry day, CL one bar earlier).
  `change`/`change_pct` on that bar include the roll gap.
- Validation: bars with null/non-positive volume, inconsistent OHLC, duplicates and the in-progress
  bar are dropped. Negative prices are kept (CL settled at -37.63 on 2020-04-20).

## Known limitations
- USDINR has no volume in the source (`volume` is 0) and a few flat single-tick bars on holidays.
- Around exchange holidays the source has a low-volume partial-session bar on the holiday and no bar
  for the following day, so `change` there can span two sessions.
- CL roll offset was inferred from volume, not an official expiry list.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--src", default="datasets")
    ap.add_argument("--public", action="store_true")
    ap.add_argument("--tag")
    ap.add_argument("--catalog", action="store_true", help="print the dataset table and exit")
    a = ap.parse_args()

    files = sorted(Path(a.src).glob("*.parquet"))
    if not files:
        raise SystemExit(f"no parquet files in {a.src}/")
    if a.catalog:
        return print(catalog(files))
    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", private=not a.public, exist_ok=True)
    api.update_repo_settings(a.repo, repo_type="dataset", private=not a.public)  # exist_ok keeps old visibility
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "README.md").write_text(CARD.replace("{catalog}", catalog(files)).replace("{configs}", configs(files)))
        api.upload_file(path_or_fileobj=Path(tmp) / "README.md", path_in_repo="README.md", repo_id=a.repo, repo_type="dataset")
    new = {f.name for f in files}
    stale = [r for r in api.list_repo_files(a.repo, repo_type="dataset") if r.endswith(".parquet") and r not in new]
    api.create_commit(
        a.repo, repo_type="dataset", commit_message="Update datasets",
        operations=[*[CommitOperationAdd(f.name, f) for f in files],
                    *[CommitOperationDelete(s) for s in stale]],
    )
    if a.tag:
        api.create_tag(a.repo, tag=a.tag, repo_type="dataset")
    print(f"published {[f.name for f in files]} to {a.repo} ({'public' if a.public else 'private'})")


if __name__ == "__main__":
    main()
