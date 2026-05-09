# Setup script for the Orchestrator Copilot Chat agent.
#
# Extracts the agent ZIP or copies files into `.github/agents/Orchestrator`,
# installs prompt files into `.github/prompts`, optionally unblocks files,
# sets PowerShell execution policy, creates a Python virtual environment and
# installs `requirements.txt`, and can run a smoke test using the included
# `scripts/handle_request.py` wrapper.
#
# Usage examples:
#   .\setup_orchestrator.ps1 -Force -InstallDeps -SmokeTest

[CmdletBinding()]
param(
    [string]$AgentZipPath = "Orchestrator.zip",
    [string]$DestRoot = ".github/agents",
    [string]$AgentName = "Orchestrator",
    [switch]$Flatten,
    [switch]$Force,
    [switch]$RemoveDocs,
    [switch]$InstallDeps,
    [switch]$SmokeTest
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

function Install-PromptFolder {
    param(
        [Parameter(Mandatory = $true)] [string]$SourceRoot,
        [Parameter(Mandatory = $true)] [string]$RepoRoot,
        [switch]$RemoveSource,
        [switch]$Force
    )

    $SourcePrompts = Join-Path $SourceRoot 'prompts'
    if (-not (Test-Path $SourcePrompts)) {
        Write-Warn "No prompts folder found at $SourcePrompts; skipping .github prompt install."
        return
    }

    $GithubRoot = Join-Path $RepoRoot '.github'
    $DestPrompts = Join-Path $GithubRoot 'prompts'

    if ($Force -and (Test-Path $DestPrompts)) {
        Remove-Item -Recurse -Force -LiteralPath $DestPrompts
    }

    New-Item -ItemType Directory -Force -Path $GithubRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $DestPrompts | Out-Null

    Write-Info "Installing prompts to $DestPrompts"
    Copy-Item -Path (Join-Path $SourcePrompts '*') -Destination $DestPrompts -Recurse -Force

    if ($RemoveSource) {
        Remove-Item -Recurse -Force -LiteralPath $SourcePrompts
    }
}

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot = Resolve-Path (Join-Path $ScriptDir ".")
    $RepoRoot = $RepoRoot.Path

    Write-Info "Repo root: $RepoRoot"

    # Resolve zip path relative to repo root when needed
    $ZipCandidate = if ([System.IO.Path]::IsPathRooted($AgentZipPath)) { $AgentZipPath } else { Join-Path $RepoRoot $AgentZipPath }

    $DestParent = Join-Path $RepoRoot $DestRoot
    $PromptSourceRoot = $RepoRoot
    $RemovePromptSource = $false
    if ($Flatten) {
        $FinalDest = $DestParent
    } else {
        $FinalDest = $DestParent
    }

    Write-Info "Destination: $FinalDest"

    if (Test-Path $FinalDest) {
        if ($Force) {
            Write-Info "Removing existing destination ($FinalDest) because -Force was specified"
            Remove-Item -Recurse -Force -LiteralPath $FinalDest
        } else {
            Write-Err "Destination already exists: $FinalDest. Use -Force to overwrite. Exiting."
            exit 1
        }
    }

    if (Test-Path $ZipCandidate) {
        Write-Info "Found ZIP: $ZipCandidate. Extracting..."
        if ($Flatten) {
            $TempExtract = Join-Path $env:TEMP ("orch_extract_{0}" -f ([DateTime]::UtcNow.ToString("yyyyMMddHHmmss")))
            New-Item -ItemType Directory -Force -Path $TempExtract | Out-Null
            Expand-Archive -Path $ZipCandidate -DestinationPath $TempExtract -Force

            # If archive extracted a single top-level folder, copy its children into DestParent
            $children = Get-ChildItem -LiteralPath $TempExtract
            if ($children.Count -eq 1 -and $children[0].PSIsContainer) {
                New-Item -ItemType Directory -Force -Path $DestParent | Out-Null
                Write-Info "Flattening contents into $DestParent"
                Copy-Item -Path (Join-Path $children[0].FullName '*') -Destination $DestParent -Recurse -Force
            } else {
                New-Item -ItemType Directory -Force -Path $DestParent | Out-Null
                Copy-Item -Path (Join-Path $TempExtract '*') -Destination $DestParent -Recurse -Force
            }

            Remove-Item -Recurse -Force $TempExtract
        } else {
            # Extract to parent so the archive's top-level folder (e.g., Orchestrator) is created under DestParent
            New-Item -ItemType Directory -Force -Path $DestParent | Out-Null
            Expand-Archive -Path $ZipCandidate -DestinationPath $DestParent -Force

            # Determine the actual final destination directory where the agent files were extracted.
            # Prefer a folder named as the agent ($AgentName) if present; otherwise try to find a
            # recently modified directory that contains expected files (scripts/ or setup_orchestrator.ps1).
            $candidate = Join-Path $DestParent $AgentName
            if (Test-Path $candidate) {
                $FinalDest = $candidate
            } else {
                $FinalDest = $null
                $dirs = Get-ChildItem -Path $DestParent -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
                foreach ($d in $dirs) {
                    if (Test-Path (Join-Path $d.FullName 'scripts\handle_request.py') -or Test-Path (Join-Path $d.FullName 'setup_orchestrator.ps1')) {
                        $FinalDest = $d.FullName
                        break
                    }
                }
                if (-not $FinalDest) { $FinalDest = $DestParent }
            }
            $PromptSourceRoot = $FinalDest
            $RemovePromptSource = $true
        }
    } else {
        Write-Warn "ZIP not found at $ZipCandidate. Falling back to copying files from repository root."
        New-Item -ItemType Directory -Force -Path $FinalDest | Out-Null

        $itemsToCopy = @(
            'orchestrator.agent.md', 'AGENTS.md', 'orchestrator-tools.md', 'requirements.txt', 'Orchestrator.md'
        )
        foreach ($it in $itemsToCopy) {
            $src = Join-Path $RepoRoot $it
            if (Test-Path $src) { Copy-Item -Path $src -Destination $FinalDest -Force }
        }

        foreach ($d in @('templates','skills','src','scripts')) {
            $srcd = Join-Path $RepoRoot $d
            if (Test-Path $srcd) { Copy-Item -Path $srcd -Destination $FinalDest -Recurse -Force }
        }
    }

    Install-PromptFolder -SourceRoot $PromptSourceRoot -RepoRoot $RepoRoot -RemoveSource:$RemovePromptSource -Force:$Force

    # Install hook config files (log_cycle.json, rtk-rewrite.json) into .github/hooks
    try {
        $GithubHooksDir = Join-Path $RepoRoot '.github\hooks'
        New-Item -ItemType Directory -Force -Path $GithubHooksDir | Out-Null

        # Debug: surface candidate source locations and contents to help diagnose packaging layout
        Write-Info "Hook install: PromptSourceRoot = $PromptSourceRoot"
        Write-Info "Hook install: RepoRoot = $RepoRoot"
        try {
            Write-Info "Listing PromptSourceRoot contents (top-level):"
            Get-ChildItem -Path $PromptSourceRoot -ErrorAction SilentlyContinue | ForEach-Object { Write-Info "  $($_.FullName)" }
        } catch {}
        try {
            Write-Info "Listing PromptSourceRoot\hooks contents:"
            Get-ChildItem -Path (Join-Path $PromptSourceRoot 'hooks') -ErrorAction SilentlyContinue | ForEach-Object { Write-Info "  $($_.FullName)" }
        } catch {}
        try {
            Write-Info "Listing RepoRoot files (root):"
            Get-ChildItem -Path $RepoRoot -File -ErrorAction SilentlyContinue | ForEach-Object { Write-Info "  $($_.Name)" }
        } catch {}
        try {
            Write-Info "Listing RepoRoot\hooks contents:"
            Get-ChildItem -Path (Join-Path $RepoRoot 'hooks') -ErrorAction SilentlyContinue | ForEach-Object { Write-Info "  $($_.FullName)" }
        } catch {}

        # Try multiple candidate source locations. Prefer PromptSourceRoot (extracted package),
        # then fall back to the repository root so a local repo copy always installs hooks.
        # Also check inside a 'hooks' subfolder which is commonly present in packaged agents.
        $hookCandidates = @(
            @{ name='log_cycle.json'; paths=@(
                [System.IO.Path]::Combine($PromptSourceRoot, 'log_cycle.json'),
                [System.IO.Path]::Combine($PromptSourceRoot, 'hooks', 'log_cycle.json'),
                [System.IO.Path]::Combine($RepoRoot, 'log_cycle.json'),
                [System.IO.Path]::Combine($RepoRoot, 'hooks', 'log_cycle.json')
            ) },
            @{ name='rtk-rewrite.json'; paths=@(
                [System.IO.Path]::Combine($PromptSourceRoot, 'rtk-rewrite.json'),
                [System.IO.Path]::Combine($PromptSourceRoot, 'hooks', 'rtk-rewrite.json'),
                [System.IO.Path]::Combine($RepoRoot, 'rtk-rewrite.json'),
                [System.IO.Path]::Combine($RepoRoot, 'hooks', 'rtk-rewrite.json')
            ) }
        )

        foreach ($hc in $hookCandidates) {
            $src = $null
            foreach ($p in $hc.paths) {
                Write-Info "Checking candidate path: $p"
                if (Test-Path $p) { $src = $p; break }
            }
            if ($src) {
                $dest = Join-Path $GithubHooksDir $hc.name
                if (Test-Path $dest) {
                    if ($Force) { Remove-Item -Force -LiteralPath $dest }
                }
                Copy-Item -Path $src -Destination $dest -Force
                Write-Info "Installed hook: $dest (from $src)"
            } else {
                Write-Warn "Source $($hc.name) not found in expected locations; skipping hook install."
            }
        }
    } catch {
        Write-Warn "Failed to install hook files: $_"
    }

    if ($RemoveDocs) {
        $docPath = Join-Path $FinalDest 'Orchestrator.md'
        if (Test-Path $docPath) {
            Remove-Item -Force $docPath
            Write-Info "Removed $docPath"
        }
    }

    # Unblock files on Windows (safe to call on non-Windows but may no-op)
    try {
        foreach ($pathToUnblock in @($FinalDest, (Join-Path $RepoRoot '.github\prompts'))) {
            if (Test-Path $pathToUnblock) {
                Write-Info "Unblocking files under $pathToUnblock"
                Get-ChildItem -Path $pathToUnblock -Recurse -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Warn "Unblock operation failed or not supported on this platform: $_"
    }

    # Set PowerShell execution policy for the current user so .ps1 scripts can run
    try {
        Write-Info "Setting ExecutionPolicy CurrentUser to Bypass (no prompt)."
        Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force
    } catch {
        Write-Warn "Failed to set execution policy: $_"
    }

    # Optionally install Python dependencies into a venv under the agent folder
    if ($InstallDeps) {
        # Locate a Python executable
        $python = (Get-Command python -ErrorAction SilentlyContinue).Path
        if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Path }
        if (-not $python) { Write-Warn "No Python executable found on PATH. Skipping dependency installation." }
        else {
            $venvPath = Join-Path $FinalDest '.venv'
            $venvPython = Join-Path $venvPath 'Scripts\python.exe'
            if (-not (Test-Path $venvPython)) {
                Write-Info "Creating venv at $venvPath"
                & $python -m venv $venvPath
            } else { Write-Info "Reusing existing venv at $venvPath" }

            if (Test-Path $venvPython) {
                Write-Info "Upgrading pip in venv"
                & $venvPython -m pip install --upgrade pip | Out-Null

                $req = Join-Path $FinalDest 'requirements.txt'
                if (Test-Path $req) {
                    Write-Info "Installing requirements from $req"
                    & $venvPython -m pip install -r $req
                } else {
                    Write-Warn "No requirements.txt found at $req"
                }
            } else {
                Write-Warn "Failed to create or find venv python. Skipping pip installs."
            }
        }
    }

    # Optional smoke test
    if ($SmokeTest) {
        Write-Info "Running smoke test via scripts/handle_request.py"
        $handleScript = Join-Path $FinalDest 'scripts\handle_request.py'
        if (-not (Test-Path $handleScript)) { Write-Err "handle_request.py not found at $handleScript. Skipping smoke test." }
        else {
            # Use venv python if available
            $runner = $null
            if ($InstallDeps -and (Test-Path (Join-Path $FinalDest '.venv\Scripts\python.exe'))) {
                $runner = Join-Path $FinalDest '.venv\Scripts\python.exe'
            } else {
                $runner = (Get-Command python -ErrorAction SilentlyContinue).Path
                if (-not $runner) { $runner = (Get-Command py -ErrorAction SilentlyContinue).Path }
            }

            if (-not $runner) { Write-Warn "No Python runner available for smoke test." }
            else {
                Push-Location $RepoRoot
                try {
                    $args = @('--prompt', 'orchestrator smoke test', '--user', 'setup', '--run-skill', 'contract-validator')
                    Write-Info "Invoking: $runner $handleScript $($args -join ' ')"
                    & $runner $handleScript @args
                } finally { Pop-Location }
            }
        }
    }

    Write-Info "Setup complete. Reload VS Code / Copilot Chat to discover the new agent."
    Write-Info "Agent installed at: $FinalDest"
    Write-Host ""
    Write-Info "If you installed dependencies, activate the venv with:" 
    Write-Host "  . $FinalDest\.venv\Scripts\Activate.ps1" -ForegroundColor Green
    Write-Info "Then run smoke test manually if you skipped -SmokeTest." 
    exit 0
} catch {
    Write-Err "Setup failed: $_"
    exit 2
}
