$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Starts the API from the same configuration as the bot. Keep this window open
# while using the Vite dashboard in a separate terminal.
python -m uvicorn dashboard_api:app --host 127.0.0.1 --port 8000
