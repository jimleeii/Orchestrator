#!/usr/bin/env pwsh
try {
    python -m pip install -r requirements-dev.txt
    $exit = $LASTEXITCODE
    if ($exit -ne 0) { exit $exit }
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
