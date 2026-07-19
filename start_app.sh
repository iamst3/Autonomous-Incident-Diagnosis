cd /workspace/shared
source agent026_env/bin/activate
python -m streamlit run app.py \
--server.address 0.0.0.0 \
--server.port 8502 \
--server.enableCORS false \
--server.enableXsrfProtection false \
--browser.gatherUsageStats false
