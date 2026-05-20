<#
scripts/rtkp.ps1

Lightweight RTK -> PowerShell wrapper script.

Usage:
  # interactive pwsh session through rtk
  pwsh -NoProfile -File .\scripts\rtkp.ps1

  # run a PowerShell command (safer quoting via EncodedCommand)
  pwsh -NoProfile -File .\scripts\rtkp.ps1 Remove-Item -Path 'Foo.txt' -Force

  # run a local script file directly
  pwsh -NoProfile -File .\scripts\rtkp.ps1 .\myscript.ps1

This script is intended to be dot-sourced from your PowerShell profile or
invoked directly. It calls `rtk pwsh -NoProfile -EncodedCommand <base64>` to
avoid nested-quoting problems when running PowerShell cmdlets through the
`rtk` proxy.
#>

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

function _Encode-Command {
    param([string]$text)
    return [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($text))
}

if (-not $Args -or $Args.Count -eq 0) {
    # Open an interactive pwsh through rtk
    & rtk pwsh -NoProfile
    exit $LASTEXITCODE
}

# If the single argument is a path to a file, run it with -File
if ($Args.Count -eq 1 -and (Test-Path $Args[0])) {
    $filePath = (Resolve-Path -Path $Args[0]).ProviderPath
    & rtk pwsh -NoProfile -File $filePath
    exit $LASTEXITCODE
}

# Otherwise join remaining args into a single command string and encode
$command = $Args -join ' '
$b64 = _Encode-Command -text $command
& rtk pwsh -NoProfile -EncodedCommand $b64
exit $LASTEXITCODE
