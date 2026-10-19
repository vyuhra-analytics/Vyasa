# Vyasa
Vyasa compiles market data into clean datasets. Collects historical OHLCV candles, validates every bar, flags futures contract rolls, and publishes versioned datasets to Hugging Face for model training.

The datasets live on Hugging Face, not in this repo: [`vyuhra-analytics/vyasa`](https://huggingface.co/datasets/vyuhra-analytics/vyasa).

## Datasets

| Instrument | File | Symbol | Timeframe | Range | Rows | Rolls |
|---|---|---|---|---|---|---|
| WTI Crude Oil | `crudeoil_1D_2010-2026.parquet` | `NYMEX:CL1!` | 1D | 2010-01-04 to 2026-10-16 | 4,227 | 201 |
| Henry Hub Natural Gas | `naturalgas_1D_2010-2026.parquet` | `NYMEX:NG1!` | 1D | 2010-01-04 to 2026-10-16 | 4,226 | 201 |

Unadjusted continuous front-month futures. Columns: `date`, `open`, `high`, `low`, `close`, `volume`, `change`, `change_pct`, `is_roll`, `symbol`. See the dataset card on Hugging Face for rules and known limitations. Regenerate this table with `python scripts/publish.py x --catalog`.

## Pipeline

```
TradingView Desktop --scripts/pull_tv.py--> data/raw/*.json
  --vyasa--> data/<instrument>_<tf>/<year>.parquet --merge--> datasets/<instrument>_<tf>_<from>-<to>.parquet
  --scripts/publish.py--> Hugging Face
```

1. Pull raw daily bars (TradingView Desktop with CDP, `tv` CLI from tradingview-mcp, B-ADJ off):
   `python scripts/pull_tv.py 'NYMEX:CL1!' --start 2010-01-01`
2. Validate, add changes and roll flags, write parquet: `vyasa 'NYMEX:CL1!' data/raw/NYMEX_CL1.json --since 2010`
3. Publish: `python scripts/publish.py vyuhra-analytics/vyasa`

`data/` and `datasets/` are gitignored. Source: `src/vyasa` (`ingest`, `validate`, `rolls`, `write`, `cli`); tests: `pytest`.
