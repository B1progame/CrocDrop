Param(
    [string]$Version = "",
    [string]$Repo = "B1progame/CrocDrop",
    [string]$NotesFile = ".github/RELEASE_TEMPLATE.md",
    [string]$Title = "",
    [switch]$CreateTagFromMain
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Version)) {
    try {
        $Version = python -c "from app.version import APP_VERSION; print(APP_VERSION)"
        $Version = ($Version | Select-Object -First 1).ToString().Trim()
    }
    catch {
        throw "Could not resolve version. Pass -Version explicitly."
    }
}
if ([string]::IsNullOrWhiteSpace($Title)) {
    $Title = "CrocDrop v$Version"
}

$token = $env:GITHUB_TOKEN
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "GITHUB_TOKEN is not set. Create a PAT with repo scope and set it in your environment."
}

$notesPath = Join-Path $repoRoot $NotesFile
$notes = ""
if (Test-Path $notesPath) {
    $notes = Get-Content $notesPath -Raw -Encoding UTF8
}
if ([string]::IsNullOrWhiteSpace($notes)) {
    $notes = "Release $Version"
}

$assetPattern = "CrocDrop-Setup-$Version-*.exe"
$asset = Get-ChildItem (Join-Path $repoRoot "installer_output") -Filter $assetPattern -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $asset) {
    throw "No installer asset found in installer_output matching '$assetPattern'. Build installer first."
}

$headers = @{
    "Accept" = "application/vnd.github+json"
    "Authorization" = "Bearer $token"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "CrocDrop-Release-Publisher"
}

function Invoke-GitHubJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [object]$Body = $null
    )
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
    }
    $json = $Body | ConvertTo-Json -Depth 10
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -Body $json -ContentType "application/json; charset=utf-8"
}

$apiBase = "https://api.github.com/repos/$Repo"
$release = $null
try {
    $release = Invoke-GitHubJson -Method "GET" -Uri "$apiBase/releases/tags/$Version"
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -ne 404) {
        throw
    }
}

if (-not $release) {
    $createBody = @{
        tag_name = $Version
        target_commitish = "main"
        name = $Title
        body = $notes
        draft = $false
        prerelease = $false
    }
    if ($CreateTagFromMain) {
        $createBody["target_commitish"] = "main"
    }
    $release = Invoke-GitHubJson -Method "POST" -Uri "$apiBase/releases" -Body $createBody
    Write-Host "[CrocDrop] Created release $Version"
}
else {
    $updateBody = @{
        name = $Title
        body = $notes
        draft = $false
        prerelease = $false
    }
    $release = Invoke-GitHubJson -Method "PATCH" -Uri "$apiBase/releases/$($release.id)" -Body $updateBody
    Write-Host "[CrocDrop] Updated release $Version"
}

$existing = @($release.assets | Where-Object { $_.name -eq $asset.Name })
foreach ($item in $existing) {
    Invoke-GitHubJson -Method "DELETE" -Uri "$apiBase/releases/assets/$($item.id)" | Out-Null
    Write-Host "[CrocDrop] Deleted existing asset $($item.name)"
}

$uploadUrl = $release.upload_url -replace "\{\?name,label\}", ""
$encodedName = [System.Uri]::EscapeDataString($asset.Name)
$uploadTarget = "$uploadUrl?name=$encodedName"

$uploadHeaders = @{
    "Accept" = "application/vnd.github+json"
    "Authorization" = "Bearer $token"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "CrocDrop-Release-Publisher"
    "Content-Type" = "application/octet-stream"
}

Invoke-RestMethod -Method "POST" -Uri $uploadTarget -Headers $uploadHeaders -InFile $asset.FullName | Out-Null
Write-Host "[CrocDrop] Uploaded asset: $($asset.Name)"
Write-Host "[CrocDrop] Release URL: https://github.com/$Repo/releases/tag/$Version"
