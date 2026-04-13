# BFG History Rewrite Plan

**Purpose:** Remove the file `docs/superpowers/plans/2026-04-05-session3-connectors.md` from all git history, eliminating the committed Strava and Hevy credentials.

**Prerequisites:**
- Actions 1 and 2 in `MANUAL-ACTIONS.md` MUST be completed first (rotate credentials before rewriting)
- Java runtime installed (BFG requires JVM): `java -version`
- No open PRs or in-flight branches (you are a solo developer — confirm with `git branch -a`)

**⚠️ WARNING: This operation rewrites git history and force-pushes. It is irreversible.**

---

## Step 1 — Download BFG Repo Cleaner

```bash
# Download BFG jar (one-time)
curl -L https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar -o ~/bfg.jar
java -jar ~/bfg.jar --version
```

Expected: `bfg 1.14.0`

---

## Step 2 — Clone a fresh mirror of the repo

```bash
cd ~/Desktop  # or any temp location outside the repo
git clone --mirror https://github.com/simlirette/resilio-plus.git resilio-plus-mirror.git
cd resilio-plus-mirror.git
```

---

## Step 3 — Run BFG to delete the file from history

The target file is `docs/superpowers/plans/2026-04-05-session3-connectors.md`.

```bash
java -jar ~/bfg.jar \
  --delete-files "2026-04-05-session3-connectors.md" \
  resilio-plus-mirror.git
```

Expected output includes: `Cleaning commits: ... Deleted text matching: ...`

---

## Step 4 — Expire reflog and GC

```bash
cd resilio-plus-mirror.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## Step 5 — Verify the file is gone

```bash
git log --all --oneline -- "docs/superpowers/plans/2026-04-05-session3-connectors.md"
```

Expected: **no output** (file no longer in any commit).

---

## Step 6 — Force push

```bash
git push --force
```

---

## Step 7 — Update local clone

Back in your working copy (`C:\Users\simon\resilio-plus`):

```bash
git fetch --all
git reset --hard origin/main
```

---

## Step 8 — Verify on GitHub

1. Go to `https://github.com/simlirette/resilio-plus/commit/38c951f`
2. Confirm: "This commit does not belong to any branch on this repository" or 404
3. Search GitHub for `31d0dea45c6a0c9ea7df168b03fbd13beae24fba` — should return no results

---

## CONFIRMATION GATE

**Do not execute Step 6 (force push) without re-reading this document and confirming all prerequisites are met.**

Checklist before force push:
- [ ] Strava client secret rotated and verified dead
- [ ] Hevy API key rotated and verified dead
- [ ] BFG output confirmed file deleted in Step 3
- [ ] `git log --all` confirms file gone in Step 5
- [ ] No open PRs or collaborator branches
