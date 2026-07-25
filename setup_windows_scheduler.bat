@echo off
set "TASK_NAME=VineethJobsLocalLLMOrchestrator"
set "PYTHON_EXE=C:\Users\vinee\vineeth_jobs\venv\Scripts\python.exe"
set "SCRIPT_PATH=orchestrator.py"
set "START_DIR=C:\Users\vinee\vineeth_jobs"
set "SCHEDULE_TIME=08:00"

echo ========================================================
echo Setting up Windows Scheduled Task for Vineeth LLM Pipeline
echo ========================================================

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_EXE%\" \"%SCRIPT_PATH%\"" /sc daily /st 00:00 /ri 360 /du 24:00 /f

REM schtasks has no flag for the "start in" working directory, so set it via PowerShell.
REM Without this, orchestrator.py's relative "orchestrator.log" path resolves against
REM whatever cwd Task Scheduler defaults to, not this repo.
powershell -NoProfile -Command "$a = New-ScheduledTaskAction -Execute '%PYTHON_EXE%' -Argument '%SCRIPT_PATH%' -WorkingDirectory '%START_DIR%'; Set-ScheduledTask -TaskName '%TASK_NAME%' -Action $a"

echo.
echo The task "%TASK_NAME%" has been scheduled to run 4 times a day.
echo It will run completely silently in the background.
echo.
