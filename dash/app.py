import dash
import dash_bootstrap_components as dbc
from dash import Dash, html
import pandas as pd
from pathlib import Path
import re

# Paths
ROOT = Path.cwd().parent
DATASET = ROOT / "data" / "files" / "ecg-arrhythmia" / "1.0.0" / "WFDBRecords"
DATA = ROOT / "data" / "files" / "ecg-arrhythmia" / "1.0.0"

# App
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap",
    ],
)
server = app.server

# Data
conditions = pd.read_csv(DATA / "ConditionNames_SNOMED-CT.csv")
n_codes = conditions["Snomed_CT"].nunique()

# --- SNOMED stats from headers ---
headers = list(DATASET.rglob("*.hea"))
found_codes = set()
for hea in headers:
    for line in hea.read_text().splitlines():
        if line.startswith("#Dx:"):
            cand = re.split(r"[,\s]+", line.split(":", 1)[1].strip())
            found_codes.update(c for c in cand if c)

all_codes = set(conditions["Snomed_CT"].astype(str))
missing_in_data = all_codes - found_codes
extra_in_data = found_codes - all_codes

n_found = len(found_codes)
n_listed = len(all_codes)
n_missing = len(missing_in_data)
n_extra = len(extra_in_data)
# ---------------------------------

# Navbar (dark strip)
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

        # concise, employer-facing context
        html.P(
            "Exploratory data summary for the PhysioNet ECG Arrhythmia dataset, "
            "developed as part of a 3-member ML engineering project focused on "
            "arrhythmia classification from 12-lead ECGs.",
            className="text-center text-muted mb-4",
        ),

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
                                            html.Li("12-lead ECGs from 45,152 patients."),
                                            html.Li("Sampling rate: 500 Hz."),
                                            html.Li("Recording length: 10 seconds per test."),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                md=6,
                            ),
                            dbc.Col(
                                [
                                    html.H6("SNOMED Code Coverage", className="fw-semibold mb-2"),
                                    html.Ul(
                                        [
                                            html.Li(f"SNOMED codes present in dataset: {n_found}"),
                                            html.Li(f"Codes listed in mapping file: {n_listed}"),
                                            html.Li(f"Codes in CSV but not in any header: {n_missing}"),
                                            html.Li(f"Codes in headers but not in CSV: {n_extra}"),
                                        ],
                                        className="mb-0",
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
    ],
    fluid=True,
    style={"fontFamily": "Inter, -apple-system, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif"},
)

if __name__ == "__main__":
    app.run(debug=True)
