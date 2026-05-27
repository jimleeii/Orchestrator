$RepoRoot = 'C:\Users\wei_li.EDDYFINDT\source\repos\agents\Orchestrator'
$PromptSourceRoot = $RepoRoot
$FinalDest = $RepoRoot
$wikiDir = Join-Path $RepoRoot '.wiki\\orchestrator'
New-Item -ItemType Directory -Force -Path $wikiDir | Out-Null

$cfgCandidates = @(
    "$PromptSourceRoot\templates\config.json",
    "$FinalDest\templates\config.json",
    "$PromptSourceRoot\config.json",
    "$FinalDest\config.json",
    "$RepoRoot\templates\config.json",
    "$RepoRoot\config.json"
)

$foundCfg = $null
foreach ($cc in $cfgCandidates) {
    if ([string]::IsNullOrEmpty($cc)) { continue }
    if (Test-Path $cc) { $foundCfg = $cc; break }
}

if ($foundCfg) {
    $destCfg = Join-Path $wikiDir 'config.json'
    Copy-Item -Path $foundCfg -Destination $destCfg -Force
    Write-Host "COPIED: $foundCfg to $destCfg"
} else {
    Write-Host "NOT FOUND"
}

Write-Host "Done"
