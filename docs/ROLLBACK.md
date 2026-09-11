# Rollback

Know your way out before you need it.

**This project is deployed and has state, so rollback is NOT just git.** The hosted
service runs on the VPS from `/opt/settleflow` under systemd, and it keeps a SQLite
database (`saas/settleflow.db`) holding every run and captured lead. A `git revert`
rolls back *code*; it does nothing to the server's files, the unit, or the data.

For a bad deploy, use the script — it restores the previous release, restarts, health
-checks, and canaries, and it backs up what is live first so the rollback is itself
reversible:

```bash
bash scripts/rollback.sh --list      # available backups
bash scripts/rollback.sh latest      # restore + restart + verify
```

A backup is **code only**: the deploy and rollback tarballs deliberately exclude
`*.db` and `.deploy.env`. Restoring an old database over the live one would destroy
runs created since — the deploy script also asserts the live run count never goes
downwards, for the same reason.

## Baseline (git history)

- The codebase's commits are chronological and linear. Do not rewrite them.
- Reference commits (chronological): `ccf753b` baseline, `aad10fc` Razorpay parser,
  `f2a9b92` relocate+rename, `ca3f592` docs, `9becf0e` Phases 2-5 + monetization,
  `04eceba` verify manifest, `14c6824` Phase 3 schemas, `e2f16e4` SBI delimiter fix.

## Undo a bad commit (preferred: revert)

```bash
git revert <sha>            # creates a new commit that undoes <sha>; history intact
```

## Undo uncommitted work

```bash
git status -s              # see what changed
git checkout -- <file>     # discard one file's changes
git restore .              # discard all uncommitted changes
```

## Reset to a known-good state (only if the bad commits are local, never pushed)

```bash
git reset --hard <good-sha>   # destructive; use only before any push
```

## GitHub rollback

- The remote is created with `gh repo create settleflow --private`. If the push is
  wrong, delete the remote repo (`gh repo delete <owner>/settleflow --yes`) and recreate;
  it is private, so no public history is harmed.
- Never `git push --force` once the repo is public.

## What to do first

1. `git status` and `git log --oneline -5` to see where you are.
2. Prefer `git revert` (traceable) over `reset --hard` (destructive).
3. Re-run `python tests/test_matching.py` after any rollback to confirm green.
