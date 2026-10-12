param(
    [switch]$SkipTests,
    [switch]$BuildInstaller
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$specFile = Join-Path $projectRoot 'QuantLab.spec'
$exeFile = Join-Path $projectRoot 'dist\QuantLab\QuantLab.exe'

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Missing virtual environment: $pythonExe. Create it and install requirements-desktop.txt first."
}
if (-not (Test-Path -LiteralPath $specFile)) {
    throw "Missing PyInstaller spec: $specFile"
}

Push-Location -LiteralPath $projectRoot
try {
    if (-not $SkipTests) {
        & $pythonExe -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    }
    & $pythonExe -m PyInstaller --noconfirm --clean $specFile
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $exeFile)) {
        throw 'PyInstaller did not produce dist\QuantLab\QuantLab.exe.'
    }
    Write-Output "EXE built: $exeFile"

    if ($BuildInstaller) {
        $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if (-not $compiler) {
            $candidates = @((Join-Path $projectRoot '.tools\InnoSetup7\ISCC.exe'))
            if (${env:ProgramFiles(x86)}) {
                $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 7\ISCC.exe')
                $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
            }
            if ($env:ProgramFiles) {
                $candidates += (Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe')
                $candidates += (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
            }
            foreach ($candidate in $candidates) {
                if (Test-Path -LiteralPath $candidate) {
                    $compiler = $candidate
                    break
                }
            }
        }
        if (-not $compiler) {
            throw 'Inno Setup compiler ISCC.exe was not found. The EXE build is complete.'
        }
        $compilerPath = if ($compiler -is [string]) { $compiler } else { $compiler.Source }
        & $compilerPath (Join-Path $projectRoot 'installer\QuantLab.iss')
        if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
        Write-Output "Installer built: $(Join-Path $projectRoot 'dist\installer\QuantLab-CN-HK-Setup.exe')"
    }
}
finally {
    Pop-Location
}
