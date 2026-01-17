# Deploy Helper Script for Iller5
# Usage: ./deploy.ps1 "Your commit message"

param (
    [string]$message = "Update content"
)

Write-Host "--- Iller5 Deployment Helper ---" -ForegroundColor Cyan

# 1. Run Bundler locally (just to be safe and sanity check)
Write-Host "1. Running Bundler..." -ForegroundColor Yellow
python scripts/bundle.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Bundler failed. Fix errors before pushing." -ForegroundColor Red
    exit 1
}

# 2. Git Operations
Write-Host "2. Adding files..." -ForegroundColor Yellow
git add .

Write-Host "3. Committing..." -ForegroundColor Yellow
git commit -m "$message"

Write-Host "4. Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

Write-Host "--- Success! ---" -ForegroundColor Green
Write-Host "GitHub Actions will now build and deploy your site."
Write-Host "Check progress here: https://github.com/okface/iller5/actions" -ForegroundColor Cyan
