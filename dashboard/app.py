import json
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
import pandas as pd
import plotly.express as px

# --- Load precomputed artifacts ---
APP_DIR  = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

# coverage numbers
metrics = json.loads((DATA_DIR / "metrics.json").read_text())
N_FOUND      = metrics["n_found"]
N_LISTED     = metrics["n_listed"]
N_MISSING    = metrics["n_missing"]
N_EXTRA      = metrics["n_extra"]
PARSED_HEADERS = metrics["parsed_headers"]
BAD_HEADERS    = metrics["bad_headers"]
N_RECORDINGS = metrics["total_recordings"]
TOTAL_HMS    = metrics["total_duration_hms"]

# dataset structure (includes the ASCII trees)
structure = json.loads((DATA_DIR / "structure.json").read_text())
files_top    = structure["top_level_files"]
shard_count  = structure["wfdb_shards_count"]
shard_sample = structure["wfdb_shards_sample"]
ex           = structure["example_record_summary"]
tree_top     = structure["tree_top"]
tree_example = structure["tree_example"]

# top codes figure
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

        # --- Dataset Overview ---
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4("Dataset Overview", className="card-title mb-3 fw-semibold"),
                    dbc.Row(
                        [
                            # Left: recording details (UPDATED)
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
                                            html.Li(f"Valid headers parsed: {PARSED_HEADERS:,} / {N_RECORDINGS:,} "
                                                    f"(malformed: {BAD_HEADERS})"),
                                            html.Li("Format: WFDB .hea (metadata) + .mat (signals)"),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                md=6,
                            ),

                            # Right: ASCII trees of storage layout
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
                                        },
                                    ),
                                    html.H6("Example shard structure", className="fw-semibold mt-3 mb-2"),
                                    html.Pre(
                                        tree_example,
                                        style={
                                            "backgroundColor": "#f8f9fa",
                                            "padding": "10px",
                                            "borderRadius": "8px",
                                            "fontSize": "0.85rem",
                                            "lineHeight": "1.2",
                                            "overflowX": "auto",
                                        },
                                    ),
                                ],
                                md=6,
                            ),
                        ],
                        className="g-4",
                    ),
                ]
            ),
            className="shadow-sm mb-4",
        ),

        # --- SNOMED Codes (coverage + bar chart) ---
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
    ],
    fluid=True,
    style={"fontFamily": "Inter, -apple-system, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif"},
)

if __name__ == "__main__":
    app.run(debug=True)
