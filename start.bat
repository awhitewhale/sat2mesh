@echo off

echo Starting Streamlit...
start "" streamlit run "D:\OneDrive\OneDrive - McMaster University\code\sat2mesh\app.py"

timeout /t 5 >nul

echo Starting ngrok...
start "" ngrok http 7860

pause
