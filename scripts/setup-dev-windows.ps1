# Album Print Flow - Windows dev environment setup
# Run from repo root: .\scripts\setup-dev-windows.ps1

$ErrorActionPreference = "Stop"
# Script lives in repo/scripts/; repo root is parent of scripts
$repoRoot = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $repoRoot "pyproject.toml"))) {
    Write-Error "pyproject.toml not found. Run from repo root: .\scripts\setup-dev-windows.ps1"
}
Set-Location $repoRoot

# Prefer py launcher; fallback to python
$py = $null
$tried = @()
foreach ($cmd in @("py -3.11", "py -3.12", "py -3", "python3", "python")) {
    $parts = $cmd -split " "
    $exe = $parts[0]
    $args = $parts[1..($parts.Length - 1)]
    try {
        $v = & $exe @args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $tried += "$cmd -> $v"
        if ($v) {
            $major = [int]($v.Split(".")[0])
            $minor = [int]($v.Split(".")[1])
            if ($major -ge 3 -and $minor -ge 11) {
                if ($cmd.StartsWith("py ")) { $py = "$exe $($args -join ' ')" } else { $py = $exe }
                break
            }
        }
    } catch {
        $tried += "$cmd -> (error)"
    }
}

# If not on PATH, check standard install locations (e.g. winget installed but PATH not updated)
$pyCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"),
    (Join-Path $env:ProgramFiles "Python312"),
    (Join-Path ${env:ProgramFiles(x86)} "Python312")
)
if (-not $py) {
    foreach ($dir in $pyCandidates) {
        $pythonExe = Join-Path $dir "python.exe"
        if (Test-Path $pythonExe) {
            try {
                $v = & $pythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($v) {
                    $major = [int]($v.Split(".")[0])
                    $minor = [int]($v.Split(".")[1])
                    if ($major -ge 3 -and $minor -ge 11) {
                        $scriptsDir = Join-Path $dir "Scripts"
                        if (Test-Path $scriptsDir) { $env:Path = "$dir;$scriptsDir;" + $env:Path }
                        else { $env:Path = "$dir;" + $env:Path }
                        $py = $pythonExe
                        Write-Host "Using Python from: $dir (added to PATH for this session)" -ForegroundColor Green
                        break
                    }
                }
            } catch {}
        }
    }
}

if (-not $py) {
    Write-Host "Python 3.11+ not found. Tried: $($tried -join '; ')" -ForegroundColor Yellow
    Write-Host ""

    $wingetPath = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetPath) {
        Write-Host "winget is not installed. It's the easiest way to install Python on Windows." -ForegroundColor Cyan
        Write-Host "Install winget (App Installer) from: https://aka.ms/getwinget" -ForegroundColor Cyan
        $open = Read-Host "Open that page in your browser now? (Y/n)"
        if ($open -ne "n" -and $open -ne "N") {
            Start-Process "https://aka.ms/getwinget"
        }
        Write-Host ""
        Write-Host "After installing winget, run this script again. It will offer to install Python." -ForegroundColor Green
        exit 1
    }

    Write-Host "We can install Python 3.12 via winget (adds 'py' launcher and python to PATH)." -ForegroundColor Cyan
    $install = Read-Host "Install Python 3.12 now? (Y/n)"
    if ($install -eq "n" -or $install -eq "N") {
        Write-Host "Skipped. Install Python 3.11+ from https://www.python.org/downloads/ or run this script again and choose Y." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Running: winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements ..." -ForegroundColor Green
    $wingetOut = & winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements 2>&1 | Out-String
    $wingetOk = ($LASTEXITCODE -eq 0) -or ($wingetOut -match "already installed|No available upgrade|No newer package")
    if (-not $wingetOk) {
        Write-Host "winget install failed. You can try manually: winget install Python.Python.3.12" -ForegroundColor Yellow
        exit 1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Python is already installed; adding to PATH and continuing ..." -ForegroundColor Green
    }

    # Winget often doesn't add Python to PATH in this session (or at all). Add known install locations.
    $pyCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"),
        (Join-Path $env:ProgramFiles "Python312"),
        (Join-Path ${env:ProgramFiles(x86)} "Python312")
    )
    $pathAdded = $false
    foreach ($dir in $pyCandidates) {
        $pythonExe = Join-Path $dir "python.exe"
        if (Test-Path $pythonExe) {
            $scriptsDir = Join-Path $dir "Scripts"
            if (Test-Path $scriptsDir) {
                $env:Path = "$dir;$scriptsDir;" + $env:Path
                $pathAdded = $true
            } else {
                $env:Path = "$dir;" + $env:Path
                $pathAdded = $true
            }
            Write-Host "Added to PATH for this session: $dir" -ForegroundColor Green
            break
        }
    }
    if (-not $pathAdded) {
        Write-Host "Python was installed but not found in standard locations. Close this window, open a new PowerShell, then run the script again." -ForegroundColor Yellow
        exit 1
    }

    # Re-detect Python in this session
    $py = $null
    foreach ($cmd in @("py -3.12", "py -3.11", "py -3", "python")) {
        $parts = $cmd -split " "
        $exe = $parts[0]
        $args = $parts[1..($parts.Length - 1)]
        try {
            $v = & $exe @args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($v) {
                $major = [int]($v.Split(".")[0])
                $minor = [int]($v.Split(".")[1])
                if ($major -ge 3 -and $minor -ge 11) {
                    if ($cmd.StartsWith("py ")) { $py = "$exe $($args -join ' ')" } else { $py = $exe }
                    break
                }
            }
        } catch {}
    }
    # Fallback: use python.exe from the dir we added to PATH
    if (-not $py) {
        foreach ($dir in $pyCandidates) {
            $pythonExe = Join-Path $dir "python.exe"
            if (Test-Path $pythonExe) {
                $py = $pythonExe
                break
            }
        }
    }
    if (-not $py) {
        Write-Host "Could not run Python after install. Open a new PowerShell and run this script again." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Continuing with dev setup in this session ..." -ForegroundColor Green
    Write-Host ""
}

Write-Host "Using: $py" -ForegroundColor Cyan

$venvPath = Join-Path $repoRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at .venv ..." -ForegroundColor Green
    $pyParts = $py -split " "
    $pyRest = if ($pyParts.Length -gt 1) { $pyParts[1..($pyParts.Length - 1)] } else { @() }
    & $pyParts[0] ($pyRest + "-m", "venv", ".venv")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Using existing .venv" -ForegroundColor Green
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
$python = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $pip)) {
    Write-Error "Expected .venv\Scripts\pip.exe; venv may be broken."
}

Write-Host "Upgrading pip ..." -ForegroundColor Green
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installing requirements.txt ..." -ForegroundColor Green
& $pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installing package in editable mode with dev extras ..." -ForegroundColor Green
& $pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installing pre-commit hooks ..." -ForegroundColor Green
& $python -m pre_commit install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Dev environment ready." -ForegroundColor Green
Write-Host "Activate with:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "Run app:        .\.venv\Scripts\python.exe -m album_print_flow" -ForegroundColor Cyan
Write-Host "Lint:           .\.venv\Scripts\pre-commit run --all-files" -ForegroundColor Cyan
Write-Host ""
Write-Host "If 'python' is not found in new terminals, add Python to your user PATH:" -ForegroundColor Gray
Write-Host "  %LocalAppData%\Programs\Python\Python312  and  %LocalAppData%\Programs\Python\Python312\Scripts" -ForegroundColor Gray
