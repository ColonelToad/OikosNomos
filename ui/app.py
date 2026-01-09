import os
from pathlib import Path
import json
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="OikosNomos Dashboard", layout="wide", initial_sidebar_state="expanded")

API_BASE = "http://localhost:8001"
SCENARIO_API = "http://localhost:8002"
RAG_API = "http://localhost:8003"

# Demo mode: when True the UI will use bundled sample CSVs instead of calling backends.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data" / "processed"

class DemoResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        try:
            self.text = json.dumps(data)
        except Exception:
            self.text = str(data)

    def json(self):
        return self._data

def _load_sample_series():
    # Load a sample consumption series from the provided CSVs
    paths = [DATA_DIR / "historical_load_sample.csv", DATA_DIR / "historical_load.csv"]
    for p in paths:
        try:
            df = pd.read_csv(p, parse_dates=["timestamp"])
            if "consumption_kwh" in df.columns:
                return df
        except Exception:
            continue
    return None

_SAMPLE_DF = _load_sample_series()

def _demo_forecast(horizon_hours=24):
    if _SAMPLE_DF is None:
        vals = [0.5] * horizon_hours
        start_time = datetime.utcnow().isoformat()
    else:
        vals = _SAMPLE_DF["consumption_kwh"].astype(float).tolist()
        if len(vals) < horizon_hours:
            vals = vals * ((horizon_hours // max(1, len(vals))) + 1)
        vals = vals[:horizon_hours]
        start_time = _SAMPLE_DF["timestamp"].iloc[0].isoformat()
    return {"forecast_kwh": vals, "timestamp": start_time}

def _demo_billing(home_id):
    # Simple demo billing: sum of next 24h * rate
    fc = _demo_forecast(24)["forecast_kwh"]
    rate = 0.20
    bill = sum(fc) * rate
    return {"current_bill": round(bill, 2)}

def _demo_scenario_evaluate(payload):
    # payload expected to contain device_mix and home_id
    fc = _demo_forecast(24)["forecast_kwh"]
    daily_cost = sum(fc) * 0.20
    monthly_cost = daily_cost * 30
    return {
        "monthly_cost": round(monthly_cost, 2),
        "daily_cost": round(daily_cost, 2),
        "savings_vs_current": 0.0,
        "devices_active": payload.get("device_mix", {}),
    }

def _demo_rag_query(payload):
    return {"answer": "This is a demo answer — deploy backends for live results.", "citations": []}

def api_get(url, params=None, timeout=5):
    if DEMO_MODE:
        if url.endswith("/health"):
            return DemoResponse({"model_loaded": True, "db_connected": True})
        if "/billing/current" in url:
            return DemoResponse(_demo_billing(None))
        return DemoResponse({})
    return requests.get(url, params=params, timeout=timeout)

def api_post(url, json=None, timeout=10):
    if DEMO_MODE:
        if url.endswith("/predict"):
            horizon = (json or {}).get("horizon_hours", 24)
            return DemoResponse(_demo_forecast(horizon))
        if url.endswith("/train"):
            return DemoResponse({"metrics": {"rmse": 0.5, "mae": 0.3, "mape": 5.2}})
        if "/scenario/evaluate" in url:
            return DemoResponse(_demo_scenario_evaluate(json or {}))
        if url.endswith("/query"):
            return DemoResponse(_demo_rag_query(json or {}))
        return DemoResponse({})
    return requests.post(url, json=json, timeout=timeout)

# Initialize session state for theme toggle
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

# Theme toggle function
def toggle_theme():
    st.session_state.dark_mode = not st.session_state.dark_mode

# Custom CSS with dynamic theming
def apply_theme():
    if st.session_state.dark_mode:
        # Dark Mode Styles
        theme_css = """
        <style>
        /* Dark Mode */
        .stApp {
            background: linear-gradient(135deg, #0a2342 0%, #163d56 100%);
        }
        
        /* Fix metric boxes - white background with black text in dark mode */
        div[data-testid="metric-container"] {
            background-color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        div[data-testid="metric-container"] > label[data-testid="stMetricLabel"] > div {
            color: #000000 !important;
            font-weight: 600;
            font-size: 14px;
        }
        
        div[data-testid="metric-container"] > div[data-testid="stMetricValue"] > div {
            color: #000000 !important;
            font-size: 32px;
            font-weight: 700;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: #1a2332;
        }
        
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        
        /* General text colors for dark mode */
        .main * {
            color: #ffffff;
        }
        
        /* Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #2e86ab 0%, #1c5d7a 100%);
            color: white;
            border-radius: 10px;
            padding: 0.6em 2em;
            font-weight: 600;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background: linear-gradient(135deg, #1c5d7a 0%, #163d56 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(46, 134, 171, 0.4);
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(255, 255, 255, 0.05);
            padding: 8px;
            border-radius: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            color: #ffffff;
            border-radius: 8px;
            padding: 10px 20px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #2e86ab !important;
        }
        
        /* Info/Warning boxes */
        .stAlert {
            background-color: rgba(46, 134, 171, 0.2);
            border-left: 4px solid #2e86ab;
            border-radius: 8px;
        }
        </style>
        """
    else:
        # Light Mode Styles
        theme_css = """
        <style>
        /* Light Mode */
        .stApp {
            background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%);
        }
        
        /* Fix metric boxes - darker background with white text in light mode */
        div[data-testid="metric-container"] {
            background: linear-gradient(135deg, #2e86ab 0%, #1c5d7a 100%) !important;
            border: 1px solid rgba(46, 134, 171, 0.3);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(46, 134, 171, 0.2);
        }
        
        div[data-testid="metric-container"] > label[data-testid="stMetricLabel"] > div {
            color: #ffffff !important;
            font-weight: 600;
            font-size: 14px;
        }
        
        div[data-testid="metric-container"] > div[data-testid="stMetricValue"] > div {
            color: #ffffff !important;
            font-size: 32px;
            font-weight: 700;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: #2e4057;
        }
        
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        
        /* General text colors for light mode */
        .main * {
            color: #0a2342;
        }
        
        /* Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #2e86ab 0%, #1c5d7a 100%);
            color: white;
            border-radius: 10px;
            padding: 0.6em 2em;
            font-weight: 600;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background: linear-gradient(135deg, #1c5d7a 0%, #163d56 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(46, 134, 171, 0.4);
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(46, 134, 171, 0.1);
            padding: 8px;
            border-radius: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            color: #0a2342;
            border-radius: 8px;
            padding: 10px 20px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #2e86ab !important;
            color: #ffffff !important;
        }
        
        /* Info/Warning boxes */
        .stAlert {
            background-color: rgba(46, 134, 171, 0.15);
            border-left: 4px solid #2e86ab;
            border-radius: 8px;
        }
        </style>
        """
    
    st.markdown(theme_css, unsafe_allow_html=True)

apply_theme()

# Sidebar: Branding and Home selection
with st.sidebar:
    # Use a local icon or emoji instead of external URL to fix broken image
    st.markdown("<div style='text-align: center; font-size: 60px;'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='color:#2e86ab; text-align: center;'>OikosNomos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; opacity: 0.8;'>Smart Energy Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.subheader("Select Home")
    home_names = {
        "home_001": "Main House",
        "home_002": "Guest House",
        "home_003": "Apartment",
        "home_005": "Cottage",
        "home_006": "Studio"
    }
    home_id = st.selectbox("Select Home", list(home_names.keys()), format_func=lambda x: home_names[x], label_visibility="collapsed")
    
    st.markdown("---")
    st.info("💡 Switch homes to view data for each property.")

# Enhanced Header with Theme Toggle
header_col1, header_col2 = st.columns([0.9, 0.1])
with header_col1:
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #2e86ab 0%, #163d56 100%); 
                    padding: 30px; 
                    border-radius: 15px; 
                    margin-bottom: 20px;
                    box-shadow: 0 6px 20px rgba(46, 134, 171, 0.3);'>
            <h1 style='color: #ffffff; margin: 0; font-size: 42px; font-weight: 700;'>
                ⚡ OikosNomos Energy System
            </h1>
            <p style='color: rgba(255, 255, 255, 0.9); margin: 10px 0 0 0; font-size: 18px;'>
                Intelligent Energy Management & Forecasting
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with header_col2:
    # Theme toggle button
    theme_icon = "🌙" if st.session_state.dark_mode else "☀️"
    if st.button(theme_icon, key="theme_toggle", help="Toggle Dark/Light Mode"):
        toggle_theme()
        st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs([
    "🏠 Dashboard", "📊 Scenario Analysis", "🤖 Ask AI (RAG)"])

with tab1:
    st.subheader("Real-Time Metrics")
    col1, col2, col3 = st.columns(3)
    
    # Backend health check
    try:
        health = api_get(f"{API_BASE}/health", timeout=5).json()
        model_loaded = health.get("model_loaded", False)
        db_connected = health.get("db_connected", False)
    except Exception:
        model_loaded = False
        db_connected = False
    
    # Current billing
    try:
        resp = api_get(f"{API_BASE}/billing/current", params={"home_id": home_id}, timeout=5)
        billing = resp.json()
        bill_val = billing.get('current_bill', None)
        if bill_val is not None and bill_val != 'N/A' and bill_val != 0:
            col1.metric("Current Billing ($)", f"${bill_val:.2f}")
        else:
            col1.metric("Current Billing ($)", "N/A")
            st.warning("⚠️ No billing data for this home or zero usage.")
    except Exception as e:
        col1.metric("Current Billing ($)", "N/A")
        st.warning("⚠️ Could not load billing data. Check backend and data for this home.")
    
    # Forecast (next 24h)
    try:
        resp = api_post(f"{API_BASE}/predict", json={"home_id": home_id, "horizon_hours": 24}, timeout=10)
        forecast = resp.json()
        forecast_kwh = forecast.get("forecast_kwh")
        if forecast_kwh and isinstance(forecast_kwh, list) and sum(forecast_kwh[:24]) > 0:
            forecast_total = sum(forecast_kwh[:24])
            col2.metric("Forecast (24h)", f"{forecast_total:.2f} kWh")
        else:
            col2.metric("Forecast (24h)", "N/A")
            st.info("ℹ️ No forecast data available for this home or zero usage.")
    except Exception as e:
        col2.metric("Forecast (24h)", "N/A")
        st.warning("⚠️ Could not load forecast data. Check backend and data for this home.")
    
    # Action Items (replace Model Status)
    col3.metric("Action Items", "")
    with col3:
        st.markdown("<ul style='font-size:15px;'><li>Install smart thermostat for automated savings</li><li>Enable device scheduling for off-peak hours</li><li>Review appliance upgrade opportunities</li></ul>", unsafe_allow_html=True)
    if not db_connected:
        st.error("❌ Database is not connected. Backend may be down.")
    
    st.markdown("---")
    
    st.subheader("📈 Energy Consumption Forecast")
    try:
        resp = api_post(f"{API_BASE}/predict", json={"home_id": home_id, "horizon_hours": 24}, timeout=10)
        forecast = resp.json()
        forecast_kwh = forecast.get("forecast_kwh")
        start_time = forecast.get("timestamp")
        
        if forecast_kwh and isinstance(forecast_kwh, list) and start_time:
            import datetime
            start_dt = pd.to_datetime(start_time)
            chart_data = [
                {"timestamp": (start_dt + pd.Timedelta(hours=i)), "predicted_kwh": kwh}
                for i, kwh in enumerate(forecast_kwh[:24])
            ]
            df = pd.DataFrame(chart_data)
            
            # Enhanced chart with better styling
            fig = px.line(df, x="timestamp", y="predicted_kwh", 
                         title="Predicted Energy Consumption (Next 24 Hours)",
                         labels={"timestamp": "Time", "predicted_kwh": "Consumption (kWh)"})
            fig.update_traces(line_color='#2e86ab', line_width=3)
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2e86ab' if not st.session_state.dark_mode else '#ffffff'),
                hovermode='x unified'
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("ℹ️ No forecast data available for this home. Try training the model.")
    except Exception as e:
        if not model_loaded:
            st.warning("⚠️ Model is not trained. Please train the model to enable forecasting.")
        else:
            st.error(f"❌ Error loading forecast: {e}")
    
    st.markdown("---")
    
    col_train1, col_train2, col_train3 = st.columns([1, 1, 2])
    with col_train1:
        if st.button("🔄 Train Model", key="train_model_btn", width='stretch'):
            with st.spinner("Training model..."):
                try:
                    resp = api_post(f"{API_BASE}/train", timeout=60)
                    result = resp.json()
                    st.success(f"✅ Model trained! RMSE={result['metrics']['rmse']:.2f}, MAE={result['metrics']['mae']:.2f}, MAPE={result['metrics']['mape']:.2f}")
                except Exception as e:
                    st.error(f"❌ Training failed: {e}")

with tab2:
    st.subheader("📊 Scenario Analysis")
    st.write("Evaluate different device configurations and see their cost impact.")
    
    st.markdown("##### Device Mix Configuration")
    col1, col2 = st.columns(2)
    
    with col1:
        device_mix = {
            "base_load": st.checkbox("🔌 Base Load", value=True),
            "office": st.checkbox("💻 Office", value=True),
            "hvac": st.checkbox("🌡️ HVAC", value=True),
            "garden_pump": st.checkbox("💧 Garden Pump", value=True),
        }
    
    with col2:
        device_mix.update({
            "ev_charger": st.checkbox("🚗 EV Charger", value=True),
            "entertainment": st.checkbox("📺 Entertainment", value=True),
            "kitchen": st.checkbox("🍳 Kitchen", value=True)
        })
    
    st.markdown("---")
    scenario_name = st.text_input("📝 Scenario Name", "My Scenario")
    
    if st.button("🔍 Evaluate Scenario", key="eval_scenario_btn"):
        with st.spinner("Evaluating scenario..."):
            try:
                payload = {
                    "home_id": home_id,
                    "name": scenario_name,
                    "device_mix": device_mix
                }
                resp = api_post(f"{SCENARIO_API}/scenario/evaluate", json=payload, timeout=20)
                
                if resp.status_code == 200:
                    result = resp.json()
                    
                    # Display results in metrics
                    res_col1, res_col2, res_col3 = st.columns(3)
                    res_col1.metric("Monthly Cost", f"${result['monthly_cost']:.2f}")
                    res_col2.metric("Daily Cost", f"${result['daily_cost']:.2f}")
                    res_col3.metric("Savings", f"${result.get('savings_vs_current', 0):.2f}")
                    
                    st.success("✅ Scenario evaluation complete!")
                    with st.expander("📋 Active Devices Details"):
                        st.json(result.get("devices_active", {}))
                else:
                    st.error(f"❌ Scenario evaluation failed: {resp.text}")
                    
            except Exception as e:
                st.error(f"❌ Scenario evaluation failed: {e}")

with tab3:
    st.subheader("🤖 AI-Powered Energy Assistant")
    st.write("Ask questions about your energy usage, tariffs, or get recommendations.")
    
    question = st.text_area("💬 Your Question:", placeholder="e.g., What are my peak consumption hours?", height=100)
    
    if st.button("🚀 Ask AI", key="rag_ask_btn") and question:
        with st.spinner("Getting answer from AI..."):
            try:
                payload = {"question": question, "home_id": home_id, "include_citations": True}
                resp = api_post(f"{RAG_API}/query", json=payload, timeout=30)
                
                if resp.status_code == 200:
                    result = resp.json()
                    
                    st.markdown("### 💡 Answer")
                    st.write(result.get("answer", "No answer available."))
                    
                    if result.get("citations"):
                        with st.expander("📚 View Citations"):
                            for i, cite in enumerate(result["citations"], 1):
                                st.markdown(f"**{i}. {cite['doc_id']}**")
                                st.text(cite['content'][:200] + "...")
                                st.markdown("---")
                else:
                    st.error(f"❌ RAG query failed: {resp.text}")
                    
            except Exception as e:
                st.error(f"❌ RAG query failed: {e}")
