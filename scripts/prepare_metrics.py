from pathlib import Path
import pandas as pd
import re, json, argparse
from collections import Counter

# --- paths & args ---
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parent
DEFAULT_OUTDIR = REPO_ROOT / "dashboard" / "data"   # <- write here by default

parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True, help="Path to .../ecg-arrhythmia/1.0.0")
parser.add_argument("--topn", type=int, default=15)
parser.add_argument(
    "--outdir",
    default=str(DEFAULT_OUTDIR),
    help=f"Output directory (default: {DEFAULT_OUTDIR})"
)
args = parser.parse_args()

DATA = Path(args.root)
WFDB = DATA / "WFDBRecords"
COND = DATA / "ConditionNames_SNOMED-CT.csv"

OUT = Path(args.outdir)
OUT.mkdir(parents=True, exist_ok=True)

# --- mapping ---
conditions = pd.read_csv(COND)
conditions["Snomed_CT"] = conditions["Snomed_CT"].astype(str)
code2name = dict(zip(conditions["Snomed_CT"], conditions["Full Name"]))

# --- collect all Dx codes ---
codes_all, found_codes = [], set()
for hea in WFDB.rglob("*.hea"):
    for line in hea.read_text().splitlines():
        if line.startswith("#Dx:"):
            cs = [c.strip() for c in re.split(r"[,:\s]+", line.split(":", 1)[1]) if c.strip()]
            codes_all.extend(cs)
            found_codes.update(cs)

all_codes = set(conditions["Snomed_CT"])
metrics = {
    "n_found": len(found_codes),
    "n_listed": len(all_codes),
    "n_missing": len(all_codes - found_codes),
    "n_extra": len(found_codes - all_codes),
}

# --- save outputs ---
(OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))

freq = Counter(codes_all)
top_df = (
    pd.DataFrame(freq.items(), columns=["Snomed_CT", "count"])
      .sort_values("count", ascending=False)
      .head(args.topn)
      .assign(
          name=lambda d: d["Snomed_CT"].map(code2name).fillna("(unmapped)"),
          status=lambda d: d["name"].eq("(unmapped)").map({True: "Unmapped", False: "Mapped"})
      )
)
top_df.to_csv(OUT / "top_codes.csv", index=False)

print(f"Wrote: {OUT / 'metrics.json'} and {OUT / 'top_codes.csv'}")
