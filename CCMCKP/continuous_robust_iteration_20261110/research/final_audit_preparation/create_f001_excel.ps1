$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$statsPath = Join-Path $taskRoot 'formal\F001_I002_40x30\FINAL_AUDIT_STATS.json'
if (-not (Test-Path -LiteralPath $statsPath)) { throw 'Full independently audited real cohort is not ready; no workbook authoring started.' }
$stats = Get-Content -LiteralPath $statsPath -Raw | ConvertFrom-Json
if (-not $stats.integrity_passed -or $stats.registered_attempts -ne 1200 -or $stats.details.Count -ne 1200 -or $stats.summary.Count -ne 40) { throw 'Real complete cohort required.' }
$runtimeRoot = 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1104-2876-0_26.1104.2876.0_x64__3k8sg7r9htsxt\dependencies\node'
$nodeExe = Join-Path $runtimeRoot 'bin\node.exe'
$dependencyPath = Join-Path $runtimeRoot 'node_modules'
$junctionPath = Join-Path $taskRoot 'node_modules'
if (Test-Path -LiteralPath $junctionPath) {
    $junction = Get-Item -LiteralPath $junctionPath
    if ($junction.LinkType -ne 'Junction' -or $junction.Target -notcontains $dependencyPath) { throw 'Unexpected existing dependency path; do not modify it.' }
} else { New-Item -ItemType Junction -Path $junctionPath -Target $dependencyPath | Out-Null }
$operationFlag = Join-Path $taskRoot 'F001_ARTIFACT_OPERATION_STARTED.json'
if (-not (Test-Path -LiteralPath $operationFlag)) {
    $marker = 'C:\Users\Administrator\.codex\plugins\cache\openai-primary-runtime\spreadsheets\26.1104.22356\skills\spreadsheets\container_tools\mark_artifact_operation_started.mjs'
    & $nodeExe $marker --operation-kind create --expected-output-count 1 --output-format xlsx
    if ($LASTEXITCODE -ne 0) { throw 'Artifact operation marker failed; authoring stopped.' }
    @{operation='create'; format='xlsx'; count=1; time=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $operationFlag -Encoding UTF8
}
& $nodeExe (Join-Path $taskRoot 'build_f001_workbook.mjs')
if ($LASTEXITCODE -ne 0) { throw 'Workbook authoring or checks failed; inspect the builder output.' }
