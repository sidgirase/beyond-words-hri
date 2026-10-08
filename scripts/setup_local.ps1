# Local setup script for Windows users (PowerShell)

Write-Host "Setting up local Python virtual environment..."
python -m venv .venv

Write-Host "Activating virtual environment and installing requirements..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt

Write-Host "Setup complete! To activate the environment, run:"
Write-Host ".\.venv\Scripts\Activate.ps1" -ForegroundColor Green
