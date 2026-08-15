# Rollback

Know your way out before you need it. This project is a pure git repository (no
database, no deploy) until Phase 4, so rollback is git.

## Baseline

- The codebase's commits are chronological and linear. Do not rewrite them.
- Reference commits (chronological): `ccf753b` baseline, `aad10fc` Razorpay parser,
  `f2a9b92` relocate+rename.

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
