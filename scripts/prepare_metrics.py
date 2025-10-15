from pathlib import Path
import pandas as pd
import re, json, argparse
from collections import Counter, defaultdict

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

# === APPEND BELOW (after metrics.json is rewritten) ==========================
# Build per-record code sets (record_id -> set of SNOMED strings)
record_codes = defaultdict(set)
for hea in WFDB.rglob("*.hea"):
    rec_id = hea.stem
    for line in hea.read_text(errors="ignore").splitlines():
        if line.startswith("#Dx:"):
            cs = [c.strip() for c in re.split(r"[,:\s]+", line.split(":", 1)[1]) if c.strip()]
            record_codes[rec_id].update(cs)

# Define code sets
SINUS_RHYTHM   = {"426783006"}  # Normal
BORDERLINE_ONLY = {
    "426177001",  # Sinus Bradycardia
    "427084000",  # Sinus Tachycardia
    "427393009",  # Sinus Irregularity
}

# Coarse buckets for Arrhythmia breakdown (tweak as needed)
AF_AFL = {
    "164889003",  # Atrial Fibrillation
    "164890007",  # Atrial Flutter
    "713422000",  # Atrial Tachycardia (grouped here)
}
BLOCKS = {
    "270492004", "195042002", "54016002", "28189009", "27885002",
    "698252002", "59118001", "164909002", "233917008", "233897008", "426761007",
}
ST_T = {
    "429622005", "164930006", "164931005", "428750005",
    "164934002", "59931005",
}

# Tally split & sub-breakdowns
n_normal = n_border = n_arr = n_unlabeled = 0
b_brady = b_tachy = b_irreg = 0
a_afafl = a_blocks = a_stt = 0

for rec_id, codes in record_codes.items():
    if not codes:
        n_unlabeled += 1
        continue

    cset = set(codes)

    if cset == SINUS_RHYTHM:
        n_normal += 1
        continue

    if cset.issubset(BORDERLINE_ONLY):
        n_border += 1
        # presence counts (a borderline record can increment multiple)
        if "426177001" in cset:  # brady
            b_brady += 1
        if "427084000" in cset:  # tachy
            b_tachy += 1
        if "427393009" in cset:  # irregularity
            b_irreg += 1
        continue

    # Arrhythmia
    n_arr += 1
    if cset & AF_AFL:
        a_afafl += 1
    elif cset & BLOCKS:
        a_blocks += 1
    elif cset & ST_T:
        a_stt += 1
    # else falls into "Other" below

# Write split summary for the chart & bullets
normal_split = {
    "normal": n_normal,
    "borderline": n_border,
    "arrhythmia": n_arr,
    "unlabeled": n_unlabeled,
    "total": len(record_codes),
}
(OUT / "normal_split.json").write_text(json.dumps(normal_split, indent=2))

# Write sub-breakdowns used for stacked bars
pd.DataFrame([
    {"sub": "Sinus Bradycardia",  "count": b_brady},
    {"sub": "Sinus Tachycardia",  "count": b_tachy},
    {"sub": "Sinus Irregularity", "count": b_irreg},
]).to_csv(OUT / "borderline_breakdown.csv", index=False)

a_other = max(0, n_arr - (a_afafl + a_blocks + a_stt))
pd.DataFrame([
    {"sub": "AF/AFL",        "count": a_afafl},
    {"sub": "Blocks",        "count": a_blocks},
    {"sub": "ST/T changes",  "count": a_stt},
    {"sub": "Other",         "count": a_other},
]).to_csv(OUT / "arrhythmia_breakdown.csv", index=False)

print("Wrote:", OUT / "normal_split.json")
print("Wrote:", OUT / "borderline_breakdown.csv")
print("Wrote:", OUT / "arrhythmia_breakdown.csv")
# ============================================================================

# --- Arrhythmia per-code coverage (records per SNOMED) ---
# Count records for each arrhythmia SNOMED code (exclude normal & borderline-only)
arr_per_code = Counter()
for rec_id, codes in record_codes.items():
    if not codes:
        continue
    cset = set(codes)
    if cset == SINUS_RHYTHM:
        continue
    if cset.issubset(BORDERLINE_ONLY):
        continue
    # count each arrhythmia label once per record
    for c in cset:
        if c not in SINUS_RHYTHM and c not in BORDERLINE_ONLY:
            arr_per_code[c] += 1

arr_df = (
    pd.DataFrame(
        [{"Snomed_CT": k, "count": v} for k, v in arr_per_code.items()]
    )
    .assign(Full_Name=lambda d: d["Snomed_CT"].map(code2name).fillna("(unmapped)"))
    .sort_values("count", ascending=False)
)

arr_df.to_csv(OUT / "arrhythmia_subtypes.csv", index=False)
print("Wrote:", OUT / "arrhythmia_subtypes.csv")

# --- Optional: pre-render one example record so the dashboard is self-contained ---
try:
    import wfdb, io
    import matplotlib.pyplot as plt
    # pick a stable example; change if needed
    example_path = next(WFDB.rglob("JS*.hea")).with_suffix("")  # first JS* record
    rec = wfdb.rdrecord(str(example_path))
    fig = wfdb.plot_wfdb(record=rec, figsize=(15, 10), return_fig=True)

    png_path = OUT / "example_record.png"
    fig.savefig(png_path, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)

    # labels for the example
    hea_text = (example_path.with_suffix(".hea")).read_text(errors="ignore")
    dx_line = next((l for l in hea_text.splitlines() if l.startswith("#Dx:")), None)
    codes = [] if dx_line is None else [c.strip() for c in dx_line.split(":", 1)[1].split(",") if c.strip()]
    example_labels = (
        pd.DataFrame({"Snomed_CT": pd.Series(codes, dtype=str)})
          .assign(Full_Name=lambda d: d["Snomed_CT"].map(code2name).fillna("(unmapped)"))
    )
    example_labels.to_csv(OUT / "example_labels.csv", index=False)

    print("Wrote:", png_path)
    print("Wrote:", OUT / "example_labels.csv")
except Exception as e:
    print("Example preview not created:", e)
