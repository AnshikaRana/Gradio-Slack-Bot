@echo off
title Gradio Slack Bot - launcher
echo Starting the local Gradio app in a second window...
start "Gradio app (keep open)" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_logged.ps1" app
echo Waiting 25 seconds for the Gradio app to start...
timeout /t 25 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_logged.ps1" bot
