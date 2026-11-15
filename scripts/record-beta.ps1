param(
    [double]$Minutes = 60,
    [string]$OutputRoot = 'C:\TAGAD_PRIVATE_PILOT',
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$recorderRepo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$recorderPython = Join-Path $recorderRepo 'pipeline\.venv\Scripts\python.exe'
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $recorderRepo 'pipeline'
    $recorderArguments = @(
        '-m', 'tagad_pipeline.camera_recording',
        '--minutes', $Minutes.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        '--output-root', $OutputRoot
    )
    if ($Check) { $recorderArguments += '--check' }
    & $recorderPython @recorderArguments
    $recorderExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
exit $recorderExitCode
