"""vyasa build <symbol> <raw.json> [--out data]"""
import argparse

from ingest import add_changes, load_raw
from rolls import flag_rolls
from validate import validate
from write import merge_years, write_parquet


def main() -> None:
    ap = argparse.ArgumentParser(prog="vyasa")
    ap.add_argument("symbol")
    ap.add_argument("raw")
    ap.add_argument("--out", default="data")
    ap.add_argument("--timeframe", default="1D", help="label for the pulled timeframe, used in file names")
    ap.add_argument("--since", type=int, help="keep bars from this year on (changes use prior close)")
    a = ap.parse_args()
    clean, bad = validate(load_raw(a.raw))
    clean = flag_rolls(add_changes(clean), a.symbol)
    if a.since:
        clean = clean[clean["date"].dt.year >= a.since].reset_index(drop=True)
    paths = write_parquet(clean, a.symbol, a.timeframe, a.out)
    dataset = merge_years(a.symbol, a.timeframe, a.out)
    print(f"{a.symbol}: {len(clean)} bars, {int(clean.is_roll.sum())} rolls, {len(bad)} rejected -> {len(paths)} files, {dataset}")
    if len(bad):
        print(bad.to_string())


if __name__ == "__main__":
    main()
