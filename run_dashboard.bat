@echo off
cd /d "%~dp0"
echo Starting Cadence Analog CMOS dashboard on http://127.0.0.1:8765/
python -m cadence_mcp.dashboard
pause
