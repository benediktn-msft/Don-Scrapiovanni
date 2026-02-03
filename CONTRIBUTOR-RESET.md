# How to Have Only Yourself as Contributor

GitHub shows contributors based on **commit history**. To show only yourself:

## Option A: Replace the existing repo (keep same URL)

1. In this folder (`Don-Scrapiovanni`), initialize git and make a single commit:

   ```bash
   cd /root/Don-Scrapiovanni
   git init
   git add .
   git commit -m "Initial commit: Wiener Staatsoper scraper"
   ```

2. Add your GitHub repo as remote and force-push (this **overwrites** all existing history):

   ```bash
   git remote add origin https://github.com/benediktn-msft/Don-Scrapiovanni.git
   git branch -M main
   git push --force origin main
   ```

3. After the push, the repo will have only your commits, so only you will appear as contributor.

**Warning:** `git push --force` removes all previous commits. Anyone who cloned the old repo will need to re-clone. Use only if you own the repo and are sure.

## Option B: Create a new repo

1. Create a **new** empty repository on GitHub (e.g. `Don-Scrapiovanni-new`).

2. In this folder:

   ```bash
   cd /root/Don-Scrapiovanni
   git init
   git add .
   git commit -m "Initial commit: Wiener Staatsoper scraper"
   git remote add origin https://github.com/benediktn-msft/YOUR-NEW-REPO-NAME.git
   git branch -M main
   git push -u origin main
   ```

3. You will be the only contributor. You can then rename or replace the old repo if you want.
