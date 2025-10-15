import json
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
import pandas as pd
import plotly.express as px

# --- Load precomputed artifacts ---
APP_DIR  = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

# coverage numbers & dataset metrics
metrics = json.loads((DATA_DIR / "metrics.json").read_text())
N_FOUND        = metrics["n_found"]
N_LISTED       = metrics["n_listed"]
N_MISSING      = metrics["n_missing"]
N_EXTRA        = metrics["n_extra"]
PARSED_HEADERS = metrics["parsed_headers"]
BAD_HEADERS    = metrics["bad_headers"]
N_RECORDINGS   = metrics["total_recordings"]
TOTAL_HMS      = metrics["total_duration_hms"]

# dataset structure (includes the ASCII trees)
structure    = json.loads((DATA_DIR / "structure.json").read_text())
files_top    = structure["top_level_files"]
shard_count  = structure["wfdb_shards_count"]
shard_sample = structure["wfdb_shards_sample"]
ex           = structure["example_record_summary"]
tree_top     = structure["tree_top"]
tree_example = structure["tree_example"]

# --- SNOMED codes figure (dataset-wide) ---
top_codes = pd.read_csv(DATA_DIR / "top_codes.csv")
top_codes["Snomed_CT"] = top_codes["Snomed_CT"].astype(str)
top_codes = top_codes.sort_values("count", ascending=True)
order = top_codes["Snomed_CT"].tolist()

fig_codes = px.bar(
    top_codes,
    x="count", y="Snomed_CT", color="status",
    orientation="h",
    title="Top SNOMED codes by frequency",
    labels={"count": "# records", "Snomed_CT": "SNOMED CT code", "status": ""},
)
fig_codes.update_layout(height=30 * len(top_codes) + 160,
                        margin=dict(l=160, r=20, t=60, b=40))
fig_codes.update_yaxes(categoryorder="array", categoryarray=order, automargin=True)

# --- Build stacked bars: Normal, Borderline, Arrhythmia (mapped), Unmapped (by code) ---
split = json.loads((DATA_DIR / "normal_split.json").read_text())
N_NORMAL     = split["normal"]
N_BORDERLINE = split["borderline"]
N_ARRHYTHMIA = split["arrhythmia"]
N_UNLABELED  = split["unlabeled"]
N_TOTAL      = split["total"]

rows = [{"category": "Normal", "sub": "Normal", "count": N_NORMAL}]
bfile = DATA_DIR / "borderline_breakdown.csv"

if bfile.exists():
    bdf = pd.read_csv(bfile)
    for _, r in bdf.iterrows():
        rows.append({
            "category": "Borderline",
            "sub": f"Borderline - {str(r['sub'])}",
            "count": int(r["count"])
        })
else:
    rows.append({"category": "Borderline", "sub": "Borderline (total)", "count": N_BORDERLINE})

# Read per-code arrhythmia coverage
arr_subtypes = pd.read_csv(DATA_DIR / "arrhythmia_subtypes.csv").sort_values("count", ascending=False)

# Split mapped vs unmapped (by name)
mapped    = arr_subtypes[arr_subtypes["Full_Name"] != "(unmapped)"]
unmapped  = arr_subtypes[arr_subtypes["Full_Name"] == "(unmapped)"]

# Arrhythmia (mapped): stack by human-friendly name
for _, r in mapped.iterrows():
    rows.append({
        "category": "Arrhythmia",
        "sub": f"Arrhythmia - {r['Full_Name']}",
        "count": int(r["count"])
    })

# Unmapped: its own bar, split by raw SNOMED code
for _, r in unmapped.iterrows():
    rows.append({
        "category": "Unmapped",
        "sub": f"Unmapped - {r['Snomed_CT']}",
        "count": int(r["count"])
    })

split_stack = pd.DataFrame(rows)

# --- Colors ---
color_map = {
    # Normal (greens)
    "Normal": "#2ca02c",
    # Borderline (ambers)
    "Borderline (total)": "#f0ad4e",
    "Borderline - Sinus Bradycardia": "#f7ca79",
    "Borderline - Sinus Tachycardia": "#f3b75a",
    "Borderline - Sinus Irregularity": "#eea43c",
}

# Shades of red for mapped arrhythmia subtypes
import matplotlib.cm as cm
import matplotlib.colors as mcolors

reds = cm.get_cmap("Reds", max(1, len(mapped)))
for i, name in enumerate(mapped["Full_Name"]):
    color_map[f"Arrhythmia - {name}"] = mcolors.rgb2hex(reds(i))

# Greys for unmapped codes
greys = cm.get_cmap("Greys", max(1, len(unmapped)))
for i, code in enumerate(unmapped["Snomed_CT"]):
    color_map[f"Unmapped - {code}"] = mcolors.rgb2hex(greys(min(i, greys.N - 1)))

fig_combined = px.bar(
    split_stack,
    x="count", y="category", color="sub",
    title="Normal vs Arrhythmia (arrhythmia subtypes mapped; separate UNMAPPED by code)",
    labels={"category": "", "count": "# records", "sub": "Subcategory"},
    barmode="stack",
    category_orders={"category": ["Arrhythmia", "Unmapped", "Borderline", "Normal"]},
    color_discrete_map=color_map,
    orientation="h",
)
fig_combined.update_layout(
    margin=dict(l=20, r=20, t=60, b=20),
    legend=dict(itemsizing="trace", title_text="Subcategory")
)

# -----------------------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap",
    ],
)
server = app.server

# Navbar
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.NavbarBrand("ECG Arrhythmia", className="text-white fs-2 fw-semibold"),
            html.Span("12-lead ECG dataset (PhysioNet)", className="text-white-50 ms-3"),
        ],
        fluid=True,
        className="py-3",
    ),
    color="primary",
    dark=True,
    className="mb-4",
)

# Layout
app.layout = dbc.Container(
    [
        navbar,
        html.P(
            "Exploratory data summary for the PhysioNet ECG Arrhythmia dataset, "
            "developed as part of a 3-member ML engineering project focused on "
            "arrhythmia classification from 12-lead ECGs.",
            className="text-center text-muted mb-4",
        ),

        # --- Dataset Overview (unchanged) ---
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4("Dataset Overview", className="card-title mb-3 fw-semibold"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H6("Recording Details", className="fw-semibold mb-2"),
                                    html.Ul(
                                        [
                                            html.Li(f"Total ECG recordings: {N_RECORDINGS:,}"),
                                            html.Li("12-lead ECGs from 45,152 patients."),
                                            html.Li("Sampling rate: 500 Hz."),
                                            html.Li("Recording length: 10 seconds per test."),
                                            html.Li(f"Total duration: {TOTAL_HMS} (hh:mm:ss)"),
                                            html.Li(
                                                f"Valid headers parsed: {PARSED_HEADERS:,} / {N_RECORDINGS:,} "
                                                f"(malformed: {BAD_HEADERS})"
                                            ),
                                            html.Li("Format: WFDB .hea (metadata) + .mat (signals)"),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    html.H6("How files are organized", className="fw-semibold mb-2"),
                                    html.Pre(
                                        tree_top,
                                        style={
                                            "backgroundColor": "#f8f9fa",
                                            "padding": "10px",
                                            "borderRadius": "8px",
                                            "fontSize": "0.85rem",
                                            "lineHeight": "1.2",
                                            "overflowX": "auto",
                                            "whiteSpace": "pre",
                                        },
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    html.H6("Example shard structure", className="fw-semibold mb-2"),
                                    html.Pre(
                                        tree_example,
                                        style={
                                            "backgroundColor": "#f8f9fa",
                                            "padding": "10px",
                                            "borderRadius": "8px",
                                            "fontSize": "0.85rem",
                                            "lineHeight": "1.2",
                                            "overflowX": "auto",
                                            "whiteSpace": "pre",
                                        },
                                    ),
                                ],
                                md=4,
                            ),
                        ],
                        className="g-4",
                    ),
                ]
            ),
            className="shadow-sm mb-4",
        ),

        # --- SNOMED Codes (unchanged) ---
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4("SNOMED Codes", className="card-title mb-3 fw-semibold"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H6("SNOMED Code Coverage", className="fw-semibold mb-2"),
                                    html.Ul(
                                        [
                                            html.Li(f"SNOMED codes present in dataset: {N_FOUND}"),
                                            html.Li(f"Codes listed in mapping file: {N_LISTED}"),
                                            html.Li(f"Codes in CSV but not in any header: {N_MISSING}"),
                                            html.Li(f"Codes in headers but not in CSV: {N_EXTRA}"),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                dcc.Graph(figure=fig_codes, config={"displayModeBar": False}),
                                md=8,
                            ),
                        ],
                        className="g-4",
                    ),
                ]
            ),
            className="shadow-sm mb-4",
        ),

        # --- Normal vs Healthy (full-width chart) ---
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4("Normal vs Healthy", className="card-title mb-3 fw-semibold"),

                    # Bullets (full width)
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Ul(
                                        [
                                            html.Li(f"Normal (Sinus Rhythm only): {N_NORMAL:,}"),
                                            html.Li(f"Borderline (sinus brady/tachy/irregularity only): {N_BORDERLINE:,}"),
                                            html.Li(f"Arrhythmia (any other code mix): {N_ARRHYTHMIA:,}"),
                                            html.Li(f"Unlabeled: {N_UNLABELED:,}"),
                                            html.Li(f"Total: {N_TOTAL:,}"),
                                        ],
                                        className="mb-0",
                                    ),
                                    html.Div(
                                        [
                                            html.Small("Normal = exactly Sinus Rhythm (426783006), no other labels.", className="text-muted d-block"),
                                            html.Small("Borderline = sinus variants only (Brady, Tachy, Irregular).", className="text-muted d-block"),
                                            html.Small("Arrhythmia = any code outside sinus set or mixed with non-sinus codes.", className="text-muted d-block"),
                                            html.Small("Unlabeled = header has no #Dx codes.", className="text-muted d-block"),
                                            html.Small("Unmapped = records with SNOMED codes not present in the mapping CSV (shown as 'Unmapped – <code>').", className="text-muted d-block"),
                                        ],
                                        className="mt-2",
                                    ),
                                ],
                                md=12,
                            ),
                        ],
                        className="g-2",
                    ),

                    # Chart (full width)
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(
                                    figure=fig_combined,
                                    config={"displayModeBar": False},
                                    style={"height": "520px"}
                                ),
                                md=12,
                            ),
                        ]
                    ),
                ]
            ),
            className="shadow-sm mb-4",
        ),
    ],
    fluid=True,
    style={"fontFamily": "Inter, -apple-system, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif"},
)

if __name__ == "__main__":
    app.run(debug=True)
