@echo off
REM Unified launcher for OikosNomos: starts Docker and Streamlit UI

echo Starting Docker services...
docker-compose up -d

REM Wait a moment for services to initialize
ping 127.0.0.1 -n 5 > nul

echo Launching Streamlit UI...
streamlit run ui/app.py
