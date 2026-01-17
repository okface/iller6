# Deployment Guide for Iller5

This guide explains how to get your app online using GitHub Pages.

## 0. Prerequisite: Create the Repo
1. Go to [GitHub.com/new](https://github.com/new).
2. Repository name: `iller5` (or whatever you like).
3. **Public** or **Private** (GitHub Pages works for both, but Private requires Pro if you want Pages). *Recommendation: Public is easier if free.*
4. Do NOT check "Add README", "Add .gitignore", etc. Create an empty repo.
5. Click **Create repository**.

## 1. Connect Local Code to GitHub
Open your terminal (in the project folder) and run these commands (copy from GitHub's "…or push an existing repository from the command line"):

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/iller5.git
git push -u origin main
```

*(Replace `YOUR_USERNAME` with your actual GitHub username)*

## 2. Configure GitHub Pages
1. Go to your Repo Settings on GitHub.
2. Click **Pages** (in the left sidebar).
3. Under **Build and deployment** > **Source**, select **GitHub Actions**.
4. That's it! The workflow file I created (`.github/workflows/deploy.yml`) handles the rest.

## 3. Important: Fix the `base` URL
Since your site will likely be hosted at `username.github.io/iller5/`, you need to tell Vite about this subfolder.

1. Open `vite.config.js`.
2. Add `base: '/iller5/',` (replace `iller5` with your repo name).

Example:
```javascript
export default defineConfig({
  base: '/iller5/', // <--- ADD THIS LINE
  plugins: [vue()],
  // ...
})
```
3. Commit and push this change.

## 4. How to Update in the Future
Whenever you generate new questions or change code:

1. Run the helper script:
   ```powershell
   ./deploy.ps1 "Added new cardiology questions"
   ```
2. Wait ~60 seconds.
3. Your site creates/updates automatically.
