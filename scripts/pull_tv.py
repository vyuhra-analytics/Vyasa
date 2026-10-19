"""Pull every loaded daily bar for a TradingView symbol into data/raw/<EXCHANGE_SYMBOL>.json.

Needs TradingView Desktop running with CDP and the `tv` CLI from tradingview-mcp:
    set TV_MCP_DIR=F:\tradingview-mcp
    python scripts/pull_tv.py 'NYMEX:CL1!' --start 2010-01-01
B-ADJ (adjust for contract changes) must be OFF so prices stay unadjusted.
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

DIR = os.environ.get("TV_MCP_DIR", r"F:\tradingview-mcp")
BARS = "window.TradingViewApi._activeChartWidgetWV.value()._chartWidget.model().mainSeries().bars()"
DUMP = f"(function(){{var b={BARS},r=[];for(var i=b.firstIndex();i<=b.lastIndex();i++){{var v=b.valueAt(i);if(v)r.push({{time:v[0],open:v[1],high:v[2],low:v[3],close:v[4],volume:v[5]||0}})}}return r}})()"
BADJ = "(function(){var b=[].find.call(document.querySelectorAll('button'),function(x){return /B-ADJ/.test(x.textContent)});return b?b.getAttribute('aria-pressed'):null})()"


def tv(*args: str):
    out = subprocess.run(["node", "src/cli/index.js", *args], cwd=DIR, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()

    if tv("ui", "eval", BADJ).get("result") == "true":
        raise SystemExit("B-ADJ is ON: turn it off (bottom-right of chart) for unadjusted prices.")
    tv("symbol", a.symbol)
    tv("timeframe", "D")
    time.sleep(4)
    start = int(datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc).timestamp())
    tv("range", "--from", str(start), "--to", str(int(time.time())))
    bars = tv("ui", "eval", DUMP)["result"]
    out = Path(a.out) / (a.symbol.replace(":", "_").replace("!", "") + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"symbol": a.symbol, "bars": bars}))
    first = datetime.fromtimestamp(bars[0]["time"], timezone.utc).date()
    print(f"{a.symbol}: {len(bars)} bars from {first} -> {out}")


if __name__ == "__main__":
    main()
