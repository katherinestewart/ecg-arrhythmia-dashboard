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

# total paired recordings (hea ∩ mat)
hea_stems = {p.stem for p in (WFDB.rglob("*.hea"))}
mat_stems = {p.stem for p in (WFDB.rglob("*.mat"))}
total_recordings = len(hea_stems & mat_stems)

# parse headers to get fs, leads, durations
fs_counts = Counter()
lead_counts = Counter()
dur_secs = []
bad_headers = 0

for hea in WFDB.rglob("*.hea"):
    try:
        first = next(l for l in hea.read_text(errors="ignore").splitlines() if not l.startswith("#"))
        parts = first.split()  # WFDB: <record> <n_sig> <fs> <nsamp> ...
        n_sig = int(parts[1]); fs = float(parts[2]); nsamp = int(parts[3])
        lead_counts[n_sig] += 1
        fs_counts[fs] += 1
        dur_secs.append(nsamp / fs)
    except Exception:
        bad_headers += 1

modal_fs = max(fs_counts, key=fs_counts.get) if fs_counts else None
modal_leads = max(lead_counts, key=lead_counts.get) if lead_counts else None
total_duration_seconds = int(sum(dur_secs))
h = total_duration_seconds // 3600
m = (total_duration_seconds % 3600) // 60
s = total_duration_seconds % 60
total_duration_hms = f"{h:02d}:{m:02d}:{s:02d}"

# merge into existing metrics dict and rewrite
metrics.update({
    "total_recordings": total_recordings,
    "parsed_headers": len(dur_secs),
    "bad_headers": bad_headers,
    "modal_fs_hz": modal_fs,
    "modal_leads": modal_leads,
    "total_duration_seconds": total_duration_seconds,
    "total_duration_hms": total_duration_hms,
})
(OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
