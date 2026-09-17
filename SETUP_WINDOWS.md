# Windows setup — khenzarr/chain-observatory

This setup creates a brand-new repository. It does not clone, open, modify, or push to any existing production repository.

## 1. Requirements

Install:

- Git
- Python 3.11+
- GitHub CLI (`gh`)

Then authenticate once:

```powershell
gh auth login
```

## 2. Extract and open the project

Example:

```powershell
cd C:\Users\mertb\Desktop\NODE\chain-observatory
```

## 3. Test locally before creating anything on GitHub

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

All tests must pass.

The live RPC collector may fail from networks that block a provider; this is not allowed to create a commit. Adjust `config/networks.json` only when a real endpoint needs replacement.

## 4. Get the exact commit email GitHub recognizes

Open GitHub → Settings → Emails.

Copy either:

- a verified email attached to your account, or
- the exact GitHub-provided `noreply` address shown there.

Do not invent or guess it. GitHub uses commit email attribution for the contribution graph.

## 5. Create the new public repository

From inside the extracted folder:

```powershell
.\bootstrap.ps1 -CommitEmail "PASTE_EXACT_GITHUB_EMAIL_HERE"
```

The script creates:

```text
khenzarr/chain-observatory
```

and sets repository variables `COMMIT_NAME` and `COMMIT_EMAIL`.

## 6. First manual run

On GitHub:

```text
chain-observatory
→ Actions
→ hourly-observation
→ Run workflow
```

Expected behavior:

```text
unit tests
→ live RPC probes
→ raw JSON observation
→ generated reports
→ one transparent data(auto) commit
```

If every endpoint fails, the workflow intentionally makes no commit.

## 7. Verify attribution

After the first generated commit, open that commit and verify the author resolves to your GitHub account.

GitHub may take time to refresh the profile contribution graph.

## 8. Do not change these guardrails

Keep these rules intact:

- no empty commits
- no timestamp-only file changes
- no backdating
- no generated PR/issue spam
- no production repository access
- generated commit messages must remain visibly automated
- no commit when the collector has no successful measurement

## 9. Cadence

The default cron is:

```cron
23 * * * *
```

This is one observation per hour, at minute 23 UTC, for a theoretical maximum of 24 scheduled data commits/day when runs succeed.

Do not convert this into minute-level commit generation. If more data resolution becomes genuinely useful, increase measurement resolution for an engineering reason and keep the repository transparent about the cadence.
