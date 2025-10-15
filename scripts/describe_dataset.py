from pathlib import Path
import json

IGNORE = {".ipynb_checkpoints", ".DS_Store", "__pycache__"}

def compact_tree(root: Path, max_depth=2, max_items=12):
    root = Path(root)
    out = [root.name]

    def walk(p: Path, pref: str, depth: int):
        if depth > max_depth:
            return
        kids = [x for x in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                if x.name not in IGNORE]
        shown = kids[:max_items]
        hidden = len(kids) - len(shown)
        for i, x in enumerate(shown):
            last = (i == len(shown)-1 and hidden == 0)
            out.append(f"{pref}{'└── ' if last else '├── '}{x.name}")
            if x.is_dir():
                walk(x, pref + ("    " if last and hidden == 0 else "│   "), depth+1)
        if hidden > 0:
            out.append(f"{pref}└── … (+{hidden} more)")

    walk(root, "", 1)
    return "\n".join(out)

def first_record_dir(wfdb_root: Path):
    for p in wfdb_root.rglob("*"):
        if p.is_dir() and (list(p.glob("*.hea")) or list(p.glob("*.mat"))):
            return p
    return None

def summarize_record_dir(rec_dir: Path, sample_pairs: int = 8):
    heas = sorted(rec_dir.glob("*.hea"))
    mats = sorted(rec_dir.glob("*.mat"))
    stems_hea = {p.stem for p in heas}
    stems_mat = {p.stem for p in mats}
    paired = sorted(stems_hea & stems_mat)
    samples = [{"stem": s, "hea": f"{s}.hea", "mat": f"{s}.mat"} for s in paired[:sample_pairs]]
    return {
        "dir_name": rec_dir.name,
        "n_hea": len(heas),
        "n_mat": len(mats),
        "n_paired": len(paired),
        "samples": samples,
        "n_more_pairs": max(0, len(paired) - len(samples)),
    }

def main(root: Path, outdir: Path):
    data_root = Path(root)
    wfdb = data_root / "WFDBRecords"
    outdir.mkdir(parents=True, exist_ok=True)

    top_files = sorted([p.name for p in data_root.iterdir() if p.is_file() and p.name not in IGNORE])
    shards = sorted([p.name for p in wfdb.iterdir() if p.is_dir()])
    example_dir = first_record_dir(wfdb)
    example = summarize_record_dir(example_dir) if example_dir else None

    info = {
        "top_level_files": top_files,
        "wfdb_shards_count": len(shards),
        "wfdb_shards_sample": shards[:12],
        "example_record_summary": example,
        "tree_top": compact_tree(data_root, max_depth=2, max_items=12),
        "tree_example": compact_tree(example_dir, max_depth=2, max_items=8) if example_dir else "",
    }

    (outdir / "structure.json").write_text(json.dumps(info, indent=2))
    print("Wrote", outdir / "structure.json")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Path to .../ecg-arrhythmia/1.0.0")
    ap.add_argument("--outdir", default="dashboard/data")
    args = ap.parse_args()
    main(Path(args.root), Path(args.outdir))
