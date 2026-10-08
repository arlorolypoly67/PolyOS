param(
    [Parameter(Position = 0)]
    [string]$Message
)

if (-not $Message) {
    $Message = Read-Host 'Commit message'
}

Write-Host ''
Write-Host '== Git Status ==' -ForegroundColor Cyan
git status

Write-Host ''
$confirm = Read-Host 'Stage all changes? [Y/n]'

if ($confirm -and $confirm -notmatch '^[Yy]$') {
    Write-Host 'Cancelled.'
    exit 0
}

Write-Host ''
Write-Host '== Staging ==' -ForegroundColor Cyan
git add .

if ($LASTEXITCODE -ne 0) {
    Write-Host 'git add failed.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host '== Commit ==' -ForegroundColor Cyan
git commit -m $Message

if ($LASTEXITCODE -ne 0) {
    Write-Host 'git commit failed.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host '== Pull ==' -ForegroundColor Cyan
git pull --rebase

if ($LASTEXITCODE -ne 0) {
    Write-Host 'git pull failed. Resolve the problem before pushing.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host '== Push ==' -ForegroundColor Cyan
git push

if ($LASTEXITCODE -ne 0) {
    Write-Host 'git push failed.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host '✓ Done!' -ForegroundColor Green