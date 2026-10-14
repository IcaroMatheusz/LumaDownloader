$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Here '.build-venv\Scripts\python.exe'
$Packages = Join-Path $Here '.build-packages-new'
if (-not (Test-Path $VenvPython) -or -not (Test-Path $Packages)) {
    $VenvPython = Join-Path $Here '.luma-backend-venv\Scripts\python.exe'
    if (-not (Test-Path $VenvPython)) {
        $Launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($Launcher) { & $Launcher.Source -3 -m venv (Split-Path (Split-Path $VenvPython -Parent) -Parent) }
        else { python -m venv (Split-Path (Split-Path $VenvPython -Parent) -Parent) }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python backend build environment.' }
    }
    & $VenvPython -m pip install -r (Join-Path $Here 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install Python backend requirements.' }
} else {
    $env:PYTHONPATH = "$Packages;$Here\.build-packages"
}
$Out = Join-Path $Here 'backend-dist'
$Work = Join-Path $Here '.backend-build'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
& $VenvPython -m PyInstaller --noconfirm --clean --onefile --console --name LumaBackend `
    --distpath $Out --workpath $Work (Join-Path $Here 'backend_service.py')
if ($LASTEXITCODE -ne 0) { throw 'Python downloader backend build failed.' }
