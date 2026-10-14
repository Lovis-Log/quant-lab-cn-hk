param(
    [switch]$SkipTests,
    [switch]$BuildInstaller
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$specFile = Join-Path $projectRoot 'QuantLab.spec'
$version = (Get-Content -LiteralPath (Join-Path $projectRoot 'VERSION') -Raw).Trim()
if ($version -notmatch '^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$') {
    throw 'VERSION must contain a semantic version.'
}
$fileVersion = "$($Matches[1]).$($Matches[2]).$($Matches[3]).0"
$payloadRoot = Join-Path $projectRoot "dist\packages\$version"
$payloadDir = Join-Path $payloadRoot 'QuantLab'
$exeFile = Join-Path $payloadDir 'QuantLab.exe'
$recordDir = Join-Path $projectRoot "dist\release\$version"
$runnerFile = Join-Path $projectRoot 'tools\run_logged.py'
$logFile = Join-Path $recordDir 'build.log'
$buildStarted = [DateTime]::UtcNow.ToString('o')
New-Item -ItemType Directory -Path $recordDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Missing virtual environment: $pythonExe. Create it and install requirements-desktop.txt first."
}
if (-not (Test-Path -LiteralPath $specFile)) {
    throw "Missing PyInstaller spec: $specFile"
}

Push-Location -LiteralPath $projectRoot
try {
    if (Test-Path -LiteralPath $payloadDir) {
        $resolvedPayload = (Resolve-Path -LiteralPath $payloadDir).Path
        if (-not $resolvedPayload.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Build payload must stay inside the project workspace.'
        }
        $runningPayload = Get-Process | Where-Object {
            $_.Path -and $_.Path.StartsWith($resolvedPayload + '\', [StringComparison]::OrdinalIgnoreCase)
        }
        if ($runningPayload) { throw "This version is running from $resolvedPayload. Close it before rebuilding this version." }
    }
    $sourceCommit = (& git rev-parse HEAD).Trim()
    $sourceDirty = [bool](& git status --porcelain)
    "$buildStarted version=$version source_commit=$sourceCommit source_dirty=$sourceDirty" | Set-Content -LiteralPath $logFile -Encoding UTF8
    $testStatus = 'skipped'
    if (-not $SkipTests) {
        & $pythonExe $runnerFile --log $logFile -- $pythonExe -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
        $testStatus = 'passed'
    }
    & $pythonExe $runnerFile --log $logFile -- $pythonExe -m PyInstaller --noconfirm --clean --distpath $payloadRoot $specFile
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $exeFile)) {
        throw "PyInstaller did not produce $exeFile."
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
        & $pythonExe $runnerFile --log $logFile -- $compilerPath "/DMyAppVersion=$version" "/DMyAppFileVersion=$fileVersion" "/DMyPayloadDir=$payloadDir" (Join-Path $projectRoot 'installer\QuantLab.iss')
        if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
        Write-Output "Installer built: $(Join-Path $projectRoot 'dist\installer\QuantLab-CN-HK-Setup.exe')"
        $versionedInstaller = Join-Path $projectRoot "dist\installer\QuantLab-CN-HK-$version-Setup.exe"
        Copy-Item -LiteralPath (Join-Path $projectRoot 'dist\installer\QuantLab-CN-HK-Setup.exe') -Destination $versionedInstaller
    }
    $assetFiles = @($exeFile)
    if ($BuildInstaller) { $assetFiles += $versionedInstaller }
    $manifestAssets = foreach ($assetFile in $assetFiles) {
        $assetInfo = Get-Item -LiteralPath $assetFile
        @{ name = $assetInfo.Name; size = $assetInfo.Length;
           sha256 = (Get-FileHash -LiteralPath $assetFile -Algorithm SHA256).Hash.ToLowerInvariant() }
    }
    $manifest = @{ version = $version; source_commit = $sourceCommit;
        payload_dir = $payloadDir;
        source_dirty = $sourceDirty; tests = $testStatus;
        started_at_utc = $buildStarted; completed_at_utc = [DateTime]::UtcNow.ToString('o');
        python = (& $pythonExe --version); assets = @($manifestAssets) }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $recordDir 'build-manifest.json') -Encoding UTF8
    Write-Output "Build record: $recordDir"
}
finally {
    Pop-Location
}
