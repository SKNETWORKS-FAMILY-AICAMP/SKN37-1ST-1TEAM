@echo off
cd /d "%~dp0"
if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" call "%USERPROFILE%\miniconda3\Scripts\activate.bat"
python -m streamlit run app.py --server.headless true --server.port 8503
pause
