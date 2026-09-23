@echo off
cd /d "%~dp0"
call "C:\Users\playdata2\car_faq_env\Scripts\activate.bat"
python -m streamlit run app.py --server.headless true --server.port 8502
pause
