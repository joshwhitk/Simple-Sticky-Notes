param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    python -m pip install -r requirements.txt
    python -m pip install pyinstaller

    $distDir = Join-Path $repoRoot "dist"
    $buildDir = Join-Path $repoRoot "build"

    if (Test-Path $distDir) {
        Remove-Item -Recurse -Force $distDir
    }
    if (Test-Path $buildDir) {
        Remove-Item -Recurse -Force $buildDir
    }

    python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name "Simple Sticky Notes" `
        --icon "assets/icons/simple-sticky-notes.ico" `
        --add-data "assets;assets" `
        --hidden-import "pystray._win32" `
        main.py

    if (-not $SkipInstaller) {
        $candidateIsccPaths = @(
            (Join-Path $env:LOCALAPPDATA "Programs\\Inno Setup 6\\ISCC.exe"),
            "C:\Program Files\Inno Setup 6\ISCC.exe",
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        )
        $iscc = $candidateIsccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $iscc) {
            $iscc = (Get-Command ISCC.exe -ErrorAction Stop).Source
        }
        & $iscc (Join-Path $PSScriptRoot "SimpleStickyNotes.iss")
    }
}
finally {
    Pop-Location
}
