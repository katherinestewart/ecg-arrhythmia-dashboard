import os
import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

# --- Hardcoded metrics for deployment (no data needed) ---
N_FOUND  = 94   # SNOMED codes present in dataset
N_LISTED = 55   # codes listed in mapping file
N_MISSING = 4   # in CSV but not in any header
N_EXTRA   = 43  # in headers but not in CSV
# ---------------------------------------------------------

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
                                            html.Li(f"SNOMED codes present in dataset: {N_FOUND}"),
                                            html.Li(f"Codes listed in mapping file: {N_LISTED}"),
                                            html.Li(f"Codes in CSV but not in any header: {N_MISSING}"),
                                            html.Li(f"Codes in headers but not in CSV: {N_EXTRA}"),
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
