import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Optional

import typer
import requests
from rich import print
from rich.table import Table

app = typer.Typer(help="OikosNomos CLI – interact with services without curl/docker.")

API = {
    "forecast": os.environ.get("FORECAST_URL", "http://localhost:8001"),
    "scenario": os.environ.get("SCENARIO_URL", "http://localhost:8002"),
    "rag": os.environ.get("RAG_URL", "http://localhost:8003"),
    "billing": os.environ.get("BILLING_URL", "http://localhost:8080"),
}

# -------- Common helpers --------

def _get(url: str):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(url: str, payload: dict):
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


# -------- Health --------
@app.command()
def health():
    """Check health of all services."""
    rows = []
    try:
        rows.append(("forecast", _get(f"{API['forecast']}/health")))
    except Exception as e:
        rows.append(("forecast", {"error": str(e)}))
    try:
        rows.append(("scenario", _get(f"{API['scenario']}/health")))
    except Exception as e:
        rows.append(("scenario", {"error": str(e)}))
    try:
        rows.append(("rag", _get(f"{API['rag']}/health")))
    except Exception as e:
        rows.append(("rag", {"error": str(e)}))
    try:
        rows.append(("billing", _get(f"{API['billing']}/billing/current")))
    except Exception as e:
        rows.append(("billing", {"error": str(e)}))

    table = Table(title="OikosNomos Service Health")
    table.add_column("Service")
    table.add_column("Status / Info")
    for name, data in rows:
        table.add_row(name, json.dumps(data, indent=2, default=str))
    print(table)


# -------- Billing --------
@app.command()
def billing_current():
    """Show current billing snapshot."""
    data = _get(f"{API['billing']}/billing/current")
    print(json.dumps(data, indent=2))


# -------- Forecast --------
forecast_app = typer.Typer(help="Forecast operations")
app.add_typer(forecast_app, name="forecast")


@forecast_app.command("train")
def forecast_train():
    """Train/retrain the forecasting model."""
    data = _post(f"{API['forecast']}/train", {})
    print(json.dumps(data, indent=2))


@forecast_app.command("predict")
def forecast_predict(home_id: str = "home_001", horizon_hours: int = 3):
    """Predict next N hours (kWh and cost)."""
    payload = {"home_id": home_id, "horizon_hours": horizon_hours}
    try:
        data = _post(f"{API['forecast']}/predict", payload)
        print(json.dumps(data, indent=2))
    except requests.HTTPError as e:
        print(f"[red]Error:[/red] {e.response.text}")
        raise typer.Exit(1)


# -------- Scenario --------
scenario_app = typer.Typer(help="Scenario operations")
app.add_typer(scenario_app, name="scenario")


@scenario_app.command("evaluate")
def scenario_evaluate(
    base_load: bool = True,
    office: bool = True,
    hvac: bool = True,
    garden_pump: bool = True,
    ev_charger: bool = False,
    entertainment: bool = True,
    kitchen: bool = True,
    name: Optional[str] = None,
    home_id: str = "home_001",
):
    """Evaluate a device mix scenario."""
    payload = {
        "home_id": home_id,
        "name": name,
        "device_mix": {
            "base_load": base_load,
            "office": office,
            "hvac": hvac,
            "garden_pump": garden_pump,
            "ev_charger": ev_charger,
            "entertainment": entertainment,
            "kitchen": kitchen,
        },
    }
    data = _post(f"{API['scenario']}/scenario/evaluate", payload)
    print(json.dumps(data, indent=2))


# -------- RAG --------
rag_app = typer.Typer(help="RAG operations")
app.add_typer(rag_app, name="rag")


@rag_app.command("ask")
def rag_ask(question: str, home_id: str = "home_001", citations: bool = True):
    """Ask a natural language question with RAG."""
    payload = {"question": question, "home_id": home_id, "include_citations": citations}
    try:
        data = _post(f"{API['rag']}/query", payload)
        print(json.dumps(data, indent=2))
    except requests.HTTPError as e:
        print(f"[red]Error:[/red] {e.response.text}")
        raise typer.Exit(1)


# -------- Data helpers --------
data_app = typer.Typer(help="Data operations")
app.add_typer(data_app, name="data")


@data_app.command("load")
def data_load(csv_path: str, home_id: str = "home_001"):
    """Load historical CSV into TimescaleDB using the loader script."""
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "load_historical.py"),
        "--file",
        csv_path,
        "--home-id",
        home_id,
    ]
    print("Running:", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise typer.Exit(rc)


@data_app.command("index-docs")
def data_index_docs():
    """Index docs for RAG service."""
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "index_docs.py")]
    print("Running:", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise typer.Exit(rc)


if __name__ == "__main__":
    app()
