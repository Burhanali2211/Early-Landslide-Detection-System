@echo off
echo Installing requirements...
pip install -r requirements
cd src
echo Starting ALPROS server...
start http://127.0.0.1:5000/dashboard
python app.py
