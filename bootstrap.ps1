param(
    [string]$RepoName = "chain-observatory",
    [Parameter(Mandatory=$true)]
    [string]$CommitEmail,
    [string]$CommitName = "khenzarr"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required: https://cli.github.com/"
}

& gh auth status | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Run 'gh auth login' first."
}

$login = (& gh api user --jq .login).Trim()
if (-not $login) { throw "Could not determine GitHub login." }

Write-Host "Creating public repository $login/$RepoName ..."
& gh repo create "$login/$RepoName" --public --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw "Repository creation failed." }

& gh variable set COMMIT_NAME --body $CommitName --repo "$login/$RepoName"
& gh variable set COMMIT_EMAIL --body $CommitEmail --repo "$login/$RepoName"

Write-Host ""
Write-Host "Repository created and automation variables configured."
Write-Host "Next: open Actions -> hourly-observation -> Run workflow for the first manual test."
Write-Host ""
Write-Host "Important: CommitEmail must be a verified email connected to your GitHub account"
Write-Host "or the exact noreply address shown under GitHub Settings -> Emails."
