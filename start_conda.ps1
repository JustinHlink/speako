$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# Define target Conda environment name
$condaEnv = 'speako'

# Check if Conda is available in the system PATH
$condaCmd = Get-Command conda -ErrorAction SilentlyContinue

if ($condaCmd) {
    Write-Host "Conda detected. Attempting to use environment: $condaEnv ..." -ForegroundColor Cyan
    
    # Check if the specified Conda environment exists
    $envCheck = & conda env list | Select-String -Pattern "^\s*$condaEnv\s"
    if (-not $envCheck) {
        Write-Host "Conda environment '$condaEnv' was not found!" -ForegroundColor Red
        Write-Host "Please create the environment and install dependencies first:" -ForegroundColor Yellow
        Write-Host "  conda env create -f environment.yml"
        Write-Host "  # Or manually:"
        Write-Host "  # conda create -n $condaEnv python=3.10 -y; conda activate $condaEnv; pip install -r requirements.txt"
        exit 1
    }

    # Run database migrations within the Conda environment
    & conda run -n $condaEnv python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host 'Speako runs locally at http://127.0.0.1:8001/ . Keep this window open; Ctrl+C stops it.' -ForegroundColor Green
    
    # Launch Django development server with real-time console output
    & conda run -n $condaEnv --no-capture-output python manage.py runserver 127.0.0.1:8001 --insecure --noreload

} else {
    Write-Host "Conda was not found in system PATH. Falling back to default system Python..." -ForegroundColor Yellow
    
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        Write-Host "Python environment not found. Please ensure Conda or Python is properly configured." -ForegroundColor Red
        exit 1
    }

    # Run database migrations using system Python
    & python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host 'Speako runs locally at http://127.0.0.1:8001/ . Keep this window open; Ctrl+C stops it.' -ForegroundColor Green
    
    # Launch Django development server
    & python manage.py runserver 127.0.0.1:8001 --insecure --noreload
}
