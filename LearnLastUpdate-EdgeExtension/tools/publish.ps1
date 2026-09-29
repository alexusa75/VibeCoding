<#
.SYNOPSIS
    Publishes this extension to GitHub (alexusa75/VibeCoding, folder LearnLastUpdate-EdgeExtension).

.DESCRIPTION
    1. With -Test, runs both end-to-end test suites and stops if any check fails.
    2. Builds and validates the upload zip with tools/package.py.
    3. Mirrors this folder into a local clone of the repository (cloned on first use).
    4. Commits the change and pushes it.
    5. Creates the GitHub release "learn-last-update-v<version>" with the zip attached,
       or replaces the zip if that release already exists.

    Git and the GitHub API use the alexusa75 credential stored by Git Credential Manager.

.EXAMPLE
    .\tools\publish.ps1 -Message "Fix date parsing on localized pages" -Test
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Message,
    [string] $Clone = (Join-Path $env:USERPROFILE 'source\repos\VibeCoding'),
    [switch] $Test,
    [switch] $SkipRelease
)

$Owner = 'alexusa75'
$Repo = "$Owner/VibeCoding"
$Folder = 'LearnLastUpdate-EdgeExtension'
$Src = Split-Path $PSScriptRoot -Parent
$Dest = Join-Path $Clone $Folder
# Always use Git Credential Manager for github.com, so the alexusa75 account is used even when
# another tool (for example the Copilot app) injects its own credential helper.
$GitAuth = @('-c', 'credential.https://github.com.helper=', '-c', 'credential.https://github.com.helper=manager')

function Invoke-Native([string] $What, [scriptblock] $Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE)." }
}

function Get-GitHubToken {
    $out = "protocol=https`nhost=github.com`nusername=$Owner`n`n" | git @GitAuth credential fill
    $line = $out | Where-Object { $_.StartsWith('password=') } | Select-Object -First 1
    if (-not $line) { throw "No GitHub credential for $Owner. Push once with Git to sign in, then try again." }
    $line.Substring('password='.Length)
}

function Invoke-GitHub([string] $Method, [string] $Uri, $Body, [string] $InFile) {
    $params = @{
        Method  = $Method
        Uri     = $Uri
        Headers = @{ Authorization = "Bearer $script:Token"; Accept = 'application/vnd.github+json'; 'User-Agent' = 'learn-last-update-publish' }
    }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json); $params.ContentType = 'application/json' }
    if ($InFile) { $params.InFile = $InFile; $params.ContentType = 'application/zip' }
    Invoke-RestMethod @params
}

if ($Test) {
    $env:PYTHONIOENCODING = 'utf-8'
    Invoke-Native 'End-to-end tests' { python (Join-Path $Src 'tests\test_e2e.py') msedge }
    Invoke-Native 'Navigation tests' { python (Join-Path $Src 'tests\test_navigation.py') }
}

Invoke-Native 'Packaging' { python (Join-Path $PSScriptRoot 'package.py') }
$version = (Get-Content (Join-Path $Src 'manifest.json') -Raw | ConvertFrom-Json).version
$zip = Join-Path $Src "store\learn-last-update-$version.zip"

if (-not (Test-Path (Join-Path $Clone '.git'))) {
    Invoke-Native 'git clone' { git @GitAuth clone "https://$Owner@github.com/$Repo.git" $Clone }
}
$branch = (git -C $Clone branch --show-current).Trim()
Invoke-Native 'git fetch' { git @GitAuth -C $Clone fetch --quiet origin }
git -C $Clone rev-parse --verify --quiet "refs/remotes/origin/$branch" *> $null
if ($LASTEXITCODE -eq 0) {
    Invoke-Native 'git merge' { git -C $Clone merge --quiet --ff-only "origin/$branch" }
}

robocopy $Src $Dest /MIR /XD (Join-Path $Src 'tests\output') __pycache__ .git /XF *.pyc *.zip desktop.ini /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Copying files to $Dest failed (robocopy exit code $LASTEXITCODE)." }

Invoke-Native 'git add' { git -C $Clone add -A -- $Folder }
git -C $Clone diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host 'No file changes to commit.'
} else {
    $msgFile = New-TemporaryFile
    [IO.File]::WriteAllText($msgFile.FullName, $Message.Trim() + "`n")
    try { Invoke-Native 'git commit' { git -C $Clone commit --quiet -F $msgFile.FullName } }
    finally { Remove-Item $msgFile -ErrorAction SilentlyContinue }
}
Invoke-Native 'git push' { git @GitAuth -C $Clone push --quiet -u origin $branch }
$commit = (git -C $Clone rev-parse --short HEAD).Trim()
Write-Host "Pushed $commit to https://github.com/$Repo/tree/$branch/$Folder"

if ($SkipRelease) { return }

$script:Token = Get-GitHubToken
$tag = "learn-last-update-v$version"
$assetName = Split-Path $zip -Leaf
try {
    $release = Invoke-GitHub GET "https://api.github.com/repos/$Repo/releases/tags/$tag"
} catch {
    if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) { $release = $null } else { throw }
}

if (-not $release) {
    $installUrl = "https://github.com/$Repo/tree/$branch/$Folder#install-in-microsoft-edge"
    $notes = @(
        'Microsoft Edge extension that shows when the Microsoft Learn article you are reading was last updated and who the technical writer is.',
        '',
        "**Install:** download ``$assetName`` below and extract it to a folder you will keep. In Edge, open ``edge://extensions``, turn on **Developer mode**, click **Load unpacked** and select that folder.",
        '',
        "Step-by-step instructions with troubleshooting: $installUrl"
    ) -join "`n"
    $release = Invoke-GitHub POST "https://api.github.com/repos/$Repo/releases" @{
        tag_name = $tag; target_commitish = $branch; name = "Learn Last Update $version"; body = $notes
    }
    Write-Host "Created release $tag"
} else {
    foreach ($a in @($release.assets | Where-Object { $_.name -eq $assetName })) {
        Invoke-GitHub DELETE "https://api.github.com/repos/$Repo/releases/assets/$($a.id)" | Out-Null
    }
    Write-Host "Release $tag already exists; replacing its zip. Bump 'version' in manifest.json for changes teammates should notice."
}

$uploadUrl = "https://uploads.github.com/repos/$Repo/releases/$($release.id)/assets?name=$([uri]::EscapeDataString($assetName))"
$asset = Invoke-GitHub POST $uploadUrl -InFile $zip
Write-Host "Uploaded $($asset.name) ($([math]::Round($asset.size / 1KB, 1)) KB): $($release.html_url)"
