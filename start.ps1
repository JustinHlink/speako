$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$speakoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $speakoPython)) {
    Write-Host 'Create the virtual environment first: py -m venv .venv'
    Write-Host 'Then install dependencies: .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}
& $speakoPython manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Speako runs locally at http://127.0.0.1:8000/ . Keep this window open; Ctrl+C stops it.'
& $speakoPython manage.py runserver 127.0.0.1:8000 --insecure --noreload
