import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="OikosNomos Dashboard", layout="wide")

API_BASE = "http://localhost:8001"
SCENARIO_API = "http://localhost:8002"
RAG_API = "http://localhost:8003"


# Sidebar: Branding and Home selection
with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/2e86ab/eco-energy.png", width=60)
    st.markdown("<h2 style='color:#2e86ab;'>OikosNomos</h2>", unsafe_allow_html=True)
    st.markdown("<small>Smart Energy Management</small>", unsafe_allow_html=True)
    st.markdown("---")
    home_names = {
        "home_001": "Main House",
        "home_002": "Guest House",
        "home_003": "Apartment",
        "home_005": "Cottage",
        "home_006": "Studio"
    }
    home_id = st.selectbox("Select Home", list(home_names.keys()), format_func=lambda x: home_names[x])
    st.markdown("---")
    st.info("Switch homes to view data for each property.")

st.markdown("<h1 style='color:#163d56;'>OikosNomos Energy System</h1>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .main {
        background-color: #f7f9fa;
    }
    .stApp {
        background: linear-gradient(120deg, #e0eafc 0%, #cfdef3 100%);
    }
    .sidebar .sidebar-content {
        background: #2e4057;
        color: #fff;
    }
    .stButton>button {
        background-color: #2e86ab;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1.5em;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #163d56;
        color: #fff;
    }
    .stMetric {
        background: #fff;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(44, 62, 80, 0.08);
        padding: 1em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs([
    "🏠 Dashboard", "📊 Scenario Analysis", "🤖 Ask AI (RAG)"])

with tab1:
    st.header("Dashboard")
    col1, col2, col3 = st.columns(3)
    # Current billing
    try:
        resp = requests.get(f"{API_BASE}/billing/current", params={"home_id": home_id}, timeout=5)
        billing = resp.json()
        col1.metric("Current Billing ($)", f"{billing.get('current_bill', 'N/A')}")
    except Exception:
        col1.metric("Current Billing ($)", "N/A")
    # Forecast (next 24h)
    try:
        resp = requests.post(f"{API_BASE}/predict", json={"home_id": home_id, "horizon_hours": 24}, timeout=10)
        forecast = resp.json()
        col2.metric("Forecast (24h)", f"{forecast.get('forecast_total', 'N/A')}")
    except Exception:
        col2.metric("Forecast (24h)", "N/A")
    # Model status
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        health = resp.json()
        col3.metric("Model Status", "Loaded" if health.get("model_loaded") else "Not Loaded")
    except Exception:
        col3.metric("Model Status", "Unknown")
    st.markdown("---")
    st.header("Forecast Chart")
    try:
        resp = requests.post(f"{API_BASE}/predict", json={"home_id": home_id, "horizon_hours": 24}, timeout=10)
        forecast = resp.json()
        if "forecast" in forecast:
            df = pd.DataFrame(forecast["forecast"])
            fig = px.line(df, x="timestamp", y="predicted_kwh", title="Predicted Consumption (Next 24h)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No forecast data available.")
    except Exception as e:
        st.error(f"Error loading forecast: {e}")
    st.markdown("---")
    if st.button("Train Model", key="train_model_btn"):
        with st.spinner("Training model..."):
            try:
                resp = requests.post(f"{API_BASE}/train", timeout=60)
                result = resp.json()
                st.success(f"Model trained! Metrics: RMSE={result['metrics']['rmse']:.2f}, MAE={result['metrics']['mae']:.2f}, MAPE={result['metrics']['mape']:.2f}")
            except Exception as e:
                st.error(f"Training failed: {e}")

with tab2:
    st.header("Scenario Analysis")
    st.write("Evaluate device mixes and see cost impact.")
    device_mix = {
        "base_load": st.checkbox("Base Load", value=True),
        "office": st.checkbox("Office", value=True),
        "hvac": st.checkbox("HVAC", value=True),
        "garden_pump": st.checkbox("Garden Pump", value=True),
        "ev_charger": st.checkbox("EV Charger", value=True),
        "entertainment": st.checkbox("Entertainment", value=True),
        "kitchen": st.checkbox("Kitchen", value=True)
    }
    scenario_name = st.text_input("Scenario Name", "My Scenario")
    if st.button("Evaluate Scenario", key="eval_scenario_btn"):
        with st.spinner("Evaluating scenario..."):
            try:
                payload = {
                    "home_id": home_id,
                    "name": scenario_name,
                    "device_mix": device_mix
                }
                resp = requests.post(f"{SCENARIO_API}/scenario/evaluate", json=payload, timeout=20)
                result = resp.json()
                st.success(f"Monthly Cost: ${result['monthly_cost']:.2f}, Daily Cost: ${result['daily_cost']:.2f}, Savings vs Current: ${result.get('savings_vs_current', 0):.2f}")
                st.write("Devices Active:", result.get("devices_active", {}))
            except Exception as e:
                st.error(f"Scenario evaluation failed: {e}")

with tab3:
    st.header("Ask AI (RAG Q&A)")
    question = st.text_input("Ask a question about your energy usage or tariffs:")
    if st.button("Ask", key="rag_ask_btn") and question:
        with st.spinner("Getting answer..."):
            try:
                payload = {"question": question, "home_id": home_id, "include_citations": True}
                resp = requests.post(f"{RAG_API}/query", json=payload, timeout=30)
                result = resp.json()
                st.write("**Answer:**", result.get("answer", "No answer."))
                if result.get("citations"):
                    st.write("**Citations:**")
                    for cite in result["citations"]:
                        st.write(f"- {cite['doc_id']}: {cite['content'][:80]}...")
            except Exception as e:
                st.error(f"RAG query failed: {e}")

# TODO: Add tabs for scenarios, RAG Q&A, billing history, device toggles, etc.
