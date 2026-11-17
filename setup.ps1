# One-step setup for Windows. Double-click setup.bat, or run: powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$check = 'import sys, venv, ensurepip; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)'

function Test-Python([string[]]$command) {
    try {
        $exe, $rest = $command
        & $exe @rest -c $check *> $null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host 'Looking for Python 3.10 to 3.13 ...'
    $found = $null
    foreach ($candidate in @(@('py', '-3.12'), @('py', '-3.13'), @('py', '-3.11'), @('py', '-3.10'), @('python'))) {
        if (Test-Python $candidate) { $found = $candidate; break }
    }
    if ($found) {
        $exe, $rest = $found
        Write-Host "Using $(& $exe @rest --version). Creating the virtual environment .venv ..."
        & $exe @rest -m venv .venv
    } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host 'Creating the virtual environment .venv with uv (Python 3.12) ...'
        uv venv --python 3.12 --seed .venv
    } else {
        Write-Host 'Setup stopped: Python 3.10 to 3.13 was not found.' -ForegroundColor Red
        Write-Host '  Install Python 3.12 from https://www.python.org/downloads/ and tick "Add python.exe to PATH".'
        Write-Host '  Or run in PowerShell: winget install -e --id Python.Python.3.12'
        Write-Host 'Then run setup.bat again.'
        exit 1
    }
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host 'Setup stopped: the virtual environment .venv was not created.' -ForegroundColor Red
        exit 1
    }
}

& $venvPython setup_local.py
exit $LASTEXITCODE
