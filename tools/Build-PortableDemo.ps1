[CmdletBinding()]
param(
    [string]$ReleaseName = "ProfilirovanieDemo_Windows_x64_20260526",
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $projectRoot "release"
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
if (-not $outputRoot.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDirectory must remain inside the project directory."
}

$buildRoot = Join-Path $outputRoot "_build"
$appRoot = Join-Path $buildRoot "app"
$sfxSource = Join-Path $buildRoot "sfx"
$payloadPath = Join-Path $sfxSource "ProfilirovanieDemo_payload.zip"
$sfxPath = Join-Path $outputRoot ($ReleaseName + ".exe")
$sfxCmdPath = Join-Path $outputRoot ($ReleaseName + "_self_extract.cmd")
$sedPath = Join-Path $buildRoot "package.sed"
$sourcePython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $sourcePython)) {
    throw "Developer .venv is missing. Prepare it before building a portable package."
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "frontend\dist\index.html"))) {
    throw "frontend\dist is missing. Run the frontend build before packaging."
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "backend\data\demo.sqlite"))) {
    throw "backend\data\demo.sqlite is missing."
}

if (Test-Path -LiteralPath $buildRoot) {
    $resolvedBuild = [System.IO.Path]::GetFullPath($buildRoot)
    if (-not $resolvedBuild.StartsWith($outputRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a build directory outside release output."
    }
    Remove-Item -LiteralPath $resolvedBuild -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $appRoot, $sfxSource, $outputRoot | Out-Null

function Invoke-RobocopyChecked {
    param([string[]]$Arguments)
    & robocopy.exe @Arguments | Out-Host
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed with exit code $LASTEXITCODE."
    }
}

function New-SelfExtractingCmd {
    param(
        [string]$Payload,
        [string]$Destination
    )

    $payloadBase64 = [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes($Payload))
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.AddRange([string[]]@(
        "@echo off",
        "setlocal EnableExtensions",
        "set ""APP_FOLDER=ProfilirovanieDemo""",
        "set ""SELF=%~f0""",
        "set ""TMPZIP=%TEMP%\ProfilirovanieDemo_payload_%RANDOM%%RANDOM%.zip""",
        "",
        "if defined PROFILER_INSTALL_DIR (",
        "  set ""TARGET=%PROFILER_INSTALL_DIR%""",
        ") else (",
        "  for /f ""usebackq delims="" %%D in (`powershell.exe -NoProfile -Command ""[Environment]::GetFolderPath('Desktop')""`) do set ""DESKTOP=%%D""",
        "  set ""TARGET=%DESKTOP%\%APP_FOLDER%""",
        "  if exist ""%TARGET%"" set ""TARGET=%DESKTOP%\%APP_FOLDER%_new""",
        ")",
        "",
        "echo.",
        "echo Job profiling demo - self-extracting portable package",
        "echo ======================================================",
        "echo Destination: %TARGET%",
        "echo.",
        "",
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ""`$self=`$env:SELF; `$marker='__PROFILIROVANIE_PAYLOAD_BELOW__'; `$lines=[System.IO.File]::ReadAllLines(`$self); `$index=[Array]::IndexOf(`$lines,`$marker); if (`$index -lt 0) { throw 'Payload marker was not found.' }; `$payload=(`$lines[(`$index + 1)..(`$lines.Length - 1)] -join ''); [System.IO.File]::WriteAllBytes(`$env:TMPZIP,[Convert]::FromBase64String(`$payload))""",
        "if errorlevel 1 (",
        "  echo [ERROR] Could not decode the embedded payload.",
        "  pause",
        "  exit /b 1",
        ")",
        "",
        "if not exist ""%TARGET%"" mkdir ""%TARGET%""",
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ""Expand-Archive -LiteralPath `$env:TMPZIP -DestinationPath `$env:TARGET -Force""",
        "if errorlevel 1 (",
        "  echo [ERROR] Could not unpack the portable demo.",
        "  del ""%TMPZIP%"" >nul 2>nul",
        "  pause",
        "  exit /b 1",
        ")",
        "",
        "del ""%TMPZIP%"" >nul 2>nul",
        "echo [OK] Portable demo was unpacked.",
        "",
        "if defined PROFILER_NO_AUTOSTART (",
        "  echo [INFO] Automatic start skipped.",
        "  exit /b 0",
        ")",
        "",
        "start """" ""%TARGET%""",
        "start """" ""%TARGET%\start_demo.bat""",
        "exit /b 0",
        "__PROFILIROVANIE_PAYLOAD_BELOW__"
    ))

    for ($offset = 0; $offset -lt $payloadBase64.Length; $offset += 76) {
        $length = [Math]::Min(76, $payloadBase64.Length - $offset)
        $lines.Add($payloadBase64.Substring($offset, $length))
    }
    [System.IO.File]::WriteAllLines($Destination, $lines, [System.Text.Encoding]::ASCII)
}

Write-Host "[1/6] Copying application repository..."
$repoCopyArgs = @(
    $projectRoot,
    $appRoot,
    "/E", "/R:1", "/W:1", "/NP",
    "/XD",
    (Join-Path $projectRoot ".venv"),
    (Join-Path $projectRoot ".pytest_cache"),
    (Join-Path $projectRoot "release"),
    (Join-Path $projectRoot "frontend\node_modules"),
    (Join-Path $projectRoot "backend\tests"),
    "pytest-*",
    "__pycache__",
    "/XF",
    "*.pyc",
    "*.log",
    "demo.sqlite",
    "migration_check*.sqlite",
    "ollama_integration_check*.sqlite"
)
Invoke-RobocopyChecked -Arguments $repoCopyArgs

Write-Host "[2/6] Creating a consistent SQLite database copy..."
$sourceDb = Join-Path $projectRoot "backend\data\demo.sqlite"
$targetDb = Join-Path $appRoot "backend\data\demo.sqlite"
& $sourcePython -c "import sqlite3, sys; source=sqlite3.connect(sys.argv[1]); target=sqlite3.connect(sys.argv[2]); source.backup(target); target.close(); source.close()" $sourceDb $targetDb
if ($LASTEXITCODE -ne 0) {
    throw "SQLite database backup failed."
}

Write-Host "[3/6] Building bundled Python runtime..."
$pythonHome = (& $sourcePython -c "import sys; print(sys.base_prefix)").Trim()
if (-not (Test-Path -LiteralPath (Join-Path $pythonHome "python.exe"))) {
    throw "Base Python runtime was not found at $pythonHome."
}
$runtimeRoot = Join-Path $appRoot "runtime\python"
$runtimeCopyArgs = @(
    $pythonHome,
    $runtimeRoot,
    "/E", "/R:1", "/W:1", "/NP",
    "/XD",
    (Join-Path $pythonHome "Lib\site-packages"),
    "__pycache__",
    "/XF",
    "*.pyc"
)
Invoke-RobocopyChecked -Arguments $runtimeCopyArgs

$sitePackagesSource = Join-Path $projectRoot ".venv\Lib\site-packages"
$sitePackagesTarget = Join-Path $runtimeRoot "Lib\site-packages"
$packageCopyArgs = @(
    $sitePackagesSource,
    $sitePackagesTarget,
    "/E", "/R:1", "/W:1", "/NP",
    "/XD", "__pycache__",
    "/XF", "*.pyc"
)
Invoke-RobocopyChecked -Arguments $packageCopyArgs

$bundledPython = Join-Path $runtimeRoot "python.exe"
& $bundledPython -c "import fastapi, uvicorn, sqlalchemy, alembic; print('Bundled Python runtime: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Bundled Python runtime validation failed."
}

@"
Portable demo package for Windows x64.
Bundled runtime: Python 3.12 with backend dependencies.
Frontend is prebuilt; Python and Node.js are not required on the target computer.
Start: start_demo.bat
Stop: stop_demo.bat
"@ | Set-Content -LiteralPath (Join-Path $appRoot "PORTABLE_BUILD.txt") -Encoding UTF8

Write-Host "[4/6] Compressing payload..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $payloadPath) {
    Remove-Item -LiteralPath $payloadPath -Force
}
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $appRoot,
    $payloadPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Copy-Item -LiteralPath (Join-Path $projectRoot "tools\portable\install_portable.cmd") -Destination $sfxSource

Write-Host "[5/6] Building Windows self-extracting executable..."
if (Test-Path -LiteralPath $sfxPath) {
    Remove-Item -LiteralPath $sfxPath -Force
}
if (Test-Path -LiteralPath $sfxCmdPath) {
    Remove-Item -LiteralPath $sfxCmdPath -Force
}
$sedContent = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$sfxPath
FriendlyName=Profilirovanie Demo Portable
AppLaunched=install_portable.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=install_portable.cmd
UserQuietInstCmd=install_portable.cmd
SourceFiles=SourceFiles
[Strings]
FILE0="ProfilirovanieDemo_payload.zip"
FILE1="install_portable.cmd"
[SourceFiles]
SourceFiles0=$sfxSource\
[SourceFiles0]
%FILE0%=
%FILE1%=
"@
$sedContent | Set-Content -LiteralPath $sedPath -Encoding Default
& (Join-Path $env:WINDIR "System32\iexpress.exe") /N $sedPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $sfxPath)) {
    Write-Warning "IExpress did not create an .exe package. Creating a self-extracting .cmd package instead."
    New-SelfExtractingCmd -Payload $payloadPath -Destination $sfxCmdPath
}

$archivePath = $sfxPath
if (-not (Test-Path -LiteralPath $archivePath)) {
    $archivePath = $sfxCmdPath
}
$archive = Get-Item -LiteralPath $archivePath
Write-Host "[6/6] Portable package ready:"
Write-Host ("      " + $archive.FullName)
Write-Host ("      Size: {0:N1} MB" -f ($archive.Length / 1MB))
