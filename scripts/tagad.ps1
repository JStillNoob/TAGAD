param(
    [Parameter(Position = 0)]
    [ValidateSet('check', 'start', 'stop', 'status')]
    [string]$Action = 'start'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackendDirectory = Join-Path $RepoRoot 'backend'
$FrontendDirectory = Join-Path $RepoRoot 'frontend'
$PipelineDirectory = Join-Path $RepoRoot 'pipeline'
$RuntimeDirectory = Join-Path $RepoRoot '.runtime'
$PidFile = Join-Path $RuntimeDirectory 'tagad-processes.json'
$ControllerStopFile = Join-Path $RuntimeDirectory 'controller.stop'
$BackendPython = Join-Path $BackendDirectory 'venv\Scripts\python.exe'
$PipelinePython = Join-Path $PipelineDirectory '.venv\Scripts\python.exe'
$ViteScript = Join-Path $FrontendDirectory 'node_modules\vite\bin\vite.js'
$BackendEnvFile = Join-Path $BackendDirectory '.env'
$CameraConfig = Join-Path $PipelineDirectory 'camera_sources.local.json'
$ModelDirectory = Join-Path $BackendDirectory 'model_artifacts'
$ArtifactManifest = Join-Path $PipelineDirectory 'artifact-manifest.json'
$script:PipelineApiKey = $null

function Get-DotEnvValue {
    param([string]$Path, [string]$Name)

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $parts = $trimmed -split '=', 2
        if ($parts.Count -ne 2 -or $parts[0].Trim() -ne $Name) { continue }
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        )) {
            return $value.Substring(1, $value.Length - 2)
        }
        return $value
    }
    return $null
}

function Invoke-ExternalCheck {
    param(
        [string]$Executable,
        [object[]]$CommandArguments,
        [string]$WorkingDirectory,
        [string]$Description
    )

    Push-Location $WorkingDirectory
    try {
        $output = & $Executable @CommandArguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($exitCode -ne 0) {
        $details = ($output | Out-String).Trim()
        throw "$Description failed.`n$details"
    }
}

function Test-TcpPort {
    param([string]$HostName, [int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        return $task.Wait(300) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Wait-HttpEndpoint {
    param([string]$Url, [int]$TimeoutSeconds = 30)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Assert-Preflight {
    $requiredFiles = @(
        $BackendPython,
        $PipelinePython,
        $ViteScript,
        $BackendEnvFile,
        $CameraConfig,
        $ArtifactManifest
    )
    foreach ($path in $requiredFiles) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required local file is missing: $path"
        }
    }
    if (-not (Test-Path -LiteralPath $ModelDirectory -PathType Container)) {
        throw "Model directory is missing: $ModelDirectory"
    }

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $nodeCommand) {
        throw 'Node.js is not available on PATH.'
    }

    $script:PipelineApiKey = Get-DotEnvValue -Path $BackendEnvFile -Name 'PIPELINE_API_KEY'
    if (-not $script:PipelineApiKey -or $script:PipelineApiKey -match '^replace-') {
        throw 'Set a private PIPELINE_API_KEY in backend\.env before starting the controller.'
    }

    try {
        $cameraSettings = Get-Content -LiteralPath $CameraConfig -Raw | ConvertFrom-Json
    } catch {
        throw 'pipeline\camera_sources.local.json is not valid JSON.'
    }
    if (-not $cameraSettings.cameras -or @($cameraSettings.cameras).Count -lt 1) {
        throw 'pipeline\camera_sources.local.json must define at least one camera source.'
    }
    foreach ($camera in @($cameraSettings.cameras)) {
        if ($camera.source_type -ne 'simulated') { continue }
        $sourcePath = [string]$camera.source
        if (-not [System.IO.Path]::IsPathRooted($sourcePath)) {
            $sourcePath = Join-Path $PipelineDirectory $sourcePath
        }
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "Simulated $($camera.position) camera file is missing: $sourcePath"
        }
    }

    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = $PipelineDirectory
    try {
        Invoke-ExternalCheck -Executable $BackendPython `
            -CommandArguments @('manage.py', 'check') `
            -WorkingDirectory $BackendDirectory `
            -Description 'Django system check'
        Invoke-ExternalCheck -Executable $BackendPython `
            -CommandArguments @('manage.py', 'migrate', '--check') `
            -WorkingDirectory $BackendDirectory `
            -Description 'Django migration check'
        Invoke-ExternalCheck -Executable $BackendPython `
            -CommandArguments @('manage.py', 'check_model_setup') `
            -WorkingDirectory $BackendDirectory `
            -Description 'Model setup check'
        $artifactCode = 'import sys; from pathlib import Path; from tagad_pipeline.artifacts import verify_artifacts; verify_artifacts(Path(sys.argv[1]), Path(sys.argv[2]))'
        Invoke-ExternalCheck -Executable $PipelinePython `
            -CommandArguments @('-c', $artifactCode, $ModelDirectory, $ArtifactManifest) `
            -WorkingDirectory $RepoRoot `
            -Description 'Pipeline artifact checksum check'
        $cudaCode = 'import torch; assert torch.cuda.is_available(), "CUDA is unavailable"; print(torch.cuda.get_device_name(0))'
        Invoke-ExternalCheck -Executable $PipelinePython `
            -CommandArguments @('-c', $cudaCode) `
            -WorkingDirectory $RepoRoot `
            -Description 'CUDA check'
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }

    Write-Host 'TAGAD preflight passed: Django, database, models, camera configuration, frontend, and CUDA are ready.' -ForegroundColor Green
}

function Get-TrackedProcesses {
    if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) { return @() }
    try {
        return @((Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json))
    } catch {
        throw 'The TAGAD process file is invalid. Remove .runtime\tagad-processes.json only after confirming no TAGAD processes are running.'
    }
}

function Get-MatchingProcess {
    param($Record)

    $process = Get-Process -Id $Record.id -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    $recordedStart = [DateTime]::Parse($Record.started_at).ToUniversalTime()
    $actualStart = $process.StartTime.ToUniversalTime()
    if ([Math]::Abs(($actualStart - $recordedStart).TotalSeconds) -gt 1) {
        return $null
    }
    return $process
}

function Stop-ProcessTree {
    param([int]$ProcessId)

    $children = @(
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" `
            -ErrorAction SilentlyContinue
    )
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $ProcessId -Force
        $process.WaitForExit(5000) | Out-Null
    }
}

function Get-UntrackedTagadProcesses {
    return @(Get-CimInstance Win32_Process | Where-Object {
        $commandLine = [string]$_.CommandLine
        $normalized = $commandLine.TrimStart('"')
        (
            $normalized.StartsWith($BackendPython, [StringComparison]::OrdinalIgnoreCase) -and
            $commandLine -match 'manage\.py\s+runserver'
        ) -or (
            $commandLine.IndexOf($FrontendDirectory, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
            $commandLine -match 'vite(?:\.js)?'
        ) -or (
            $normalized.StartsWith($PipelinePython, [StringComparison]::OrdinalIgnoreCase) -and
            $commandLine -match 'tagad_pipeline\.controller'
        )
    })
}

function Show-Status {
    $records = @(Get-TrackedProcesses)
    if (-not $records.Count) {
        Write-Host 'TAGAD is not tracked as running.'
        return
    }
    foreach ($record in $records) {
        $process = Get-MatchingProcess $record
        $state = if ($process) { 'Running' } else { 'Stopped' }
        Write-Host ("{0}: {1} (PID {2})" -f $record.name, $state, $record.id)
    }
}

function Stop-TrackedProcesses {
    $records = @(Get-TrackedProcesses)

    $controllerRecord = $records | Where-Object { $_.name -eq 'controller' } | Select-Object -First 1
    if ($controllerRecord -and (Get-MatchingProcess $controllerRecord)) {
        New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
        Set-Content -LiteralPath $ControllerStopFile -Value 'stop' -Encoding ascii
        $deadline = (Get-Date).AddSeconds(20)
        while ((Get-Date) -lt $deadline -and (Get-MatchingProcess $controllerRecord)) {
            Start-Sleep -Milliseconds 250
        }
    }

    foreach ($record in $records) {
        $process = Get-MatchingProcess $record
        if ($process) {
            Stop-ProcessTree -ProcessId $process.Id
        }
    }
    foreach ($process in @(Get-UntrackedTagadProcesses)) {
        Stop-ProcessTree -ProcessId $process.ProcessId
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ControllerStopFile -Force -ErrorAction SilentlyContinue
    Write-Host 'TAGAD services stopped.' -ForegroundColor Green
}

function Start-Tagad {
    Assert-Preflight
    if (@(Get-TrackedProcesses | Where-Object { Get-MatchingProcess $_ }).Count) {
        throw 'TAGAD already has tracked running processes. Run scripts\tagad.ps1 status or stop first.'
    }
    if (Test-TcpPort -HostName '127.0.0.1' -Port 8000) {
        throw 'Port 8000 is already in use.'
    }
    if (Test-TcpPort -HostName '127.0.0.1' -Port 5173) {
        throw 'Port 5173 is already in use.'
    }

    New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
    Remove-Item -LiteralPath $ControllerStopFile -Force -ErrorAction SilentlyContinue
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $nodePath = (Get-Command node.exe).Source
    $previousPythonPath = $env:PYTHONPATH
    $previousPipelineKey = $env:TAGAD_PIPELINE_API_KEY
    $previousPythonUnbuffered = $env:PYTHONUNBUFFERED
    $env:PYTHONPATH = $PipelineDirectory
    $env:TAGAD_PIPELINE_API_KEY = $script:PipelineApiKey
    $env:PYTHONUNBUFFERED = '1'
    $started = @()

    try {
        $backend = Start-Process -FilePath $BackendPython `
            -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') `
            -WorkingDirectory $BackendDirectory -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $RuntimeDirectory "backend-$stamp.out.log") `
            -RedirectStandardError (Join-Path $RuntimeDirectory "backend-$stamp.err.log")
        $started += [PSCustomObject]@{ name = 'backend'; process = $backend }

        $frontend = Start-Process -FilePath $nodePath `
            -ArgumentList @($ViteScript, '--host', 'localhost', '--port', '5173', '--strictPort') `
            -WorkingDirectory $FrontendDirectory -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $RuntimeDirectory "frontend-$stamp.out.log") `
            -RedirectStandardError (Join-Path $RuntimeDirectory "frontend-$stamp.err.log")
        $started += [PSCustomObject]@{ name = 'frontend'; process = $frontend }

        $controller = Start-Process -FilePath $PipelinePython `
            -ArgumentList @('-m', 'tagad_pipeline.controller', '--stop-file', $ControllerStopFile) `
            -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $RuntimeDirectory "controller-$stamp.out.log") `
            -RedirectStandardError (Join-Path $RuntimeDirectory "controller-$stamp.err.log")
        $started += [PSCustomObject]@{ name = 'controller'; process = $controller }

        $records = @($started | ForEach-Object {
            [PSCustomObject]@{
                name = $_.name
                id = $_.process.Id
                started_at = $_.process.StartTime.ToUniversalTime().ToString('o')
            }
        })
        ConvertTo-Json -InputObject $records | Set-Content -LiteralPath $PidFile -Encoding utf8

        if (-not (Wait-HttpEndpoint 'http://127.0.0.1:8000/api/health/live/' 30)) {
            throw 'Django did not become healthy within 30 seconds.'
        }
        if (-not (Wait-HttpEndpoint 'http://localhost:5173/' 30)) {
            throw 'Vite did not become available within 30 seconds.'
        }
        Start-Sleep -Seconds 3
        if (-not (Get-Process -Id $controller.Id -ErrorAction SilentlyContinue)) {
            throw 'The camera controller exited during startup. Check .runtime\controller-*.err.log.'
        }

        Write-Host 'TAGAD is running at http://localhost:5173' -ForegroundColor Green
        Write-Host 'Use .\scripts\tagad.ps1 status or .\scripts\tagad.ps1 stop.'
    } catch {
        foreach ($item in $started) {
            $process = Get-Process -Id $item.process.Id -ErrorAction SilentlyContinue
            if ($process) { Stop-ProcessTree -ProcessId $process.Id }
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        throw
    } finally {
        $env:PYTHONPATH = $previousPythonPath
        $env:TAGAD_PIPELINE_API_KEY = $previousPipelineKey
        $env:PYTHONUNBUFFERED = $previousPythonUnbuffered
        $script:PipelineApiKey = $null
    }
}

try {
    switch ($Action) {
        'check' { Assert-Preflight }
        'start' { Start-Tagad }
        'stop' { Stop-TrackedProcesses }
        'status' { Show-Status }
    }
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
