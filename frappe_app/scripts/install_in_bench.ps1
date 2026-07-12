param(
  [Parameter(Mandatory=$true)][string]$BenchPath,
  [Parameter(Mandatory=$true)][string]$SiteName
)
$ErrorActionPreference = "Stop"
$appPath = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $BenchPath
try {
  bench get-app $appPath
  bench --site $SiteName install-app factorypulse_erp
  bench --site $SiteName migrate
  bench --site $SiteName run-tests --app factorypulse_erp
} finally {
  Pop-Location
}
