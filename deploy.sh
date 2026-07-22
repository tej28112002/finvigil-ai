#!/bin/bash
set -e

echo "🚀 FinVigil Deploy Script"
echo "Pushing current HEAD directly to origin main..."

CURRENT=$(git symbolic-ref --short HEAD)
echo "Current branch: $CURRENT"

# Pushes this branch's HEAD commit straight onto the remote main ref,
# without checking out or merging into a local main branch. This is what
# makes it safe to run from a worktree: `git checkout main` fails there
# whenever main is already checked out in another worktree, but this
# never touches a local main branch at all.
#
# It only succeeds as a fast-forward. If origin/main has commits this
# branch doesn't (e.g. other work merged directly into main elsewhere),
# the push is rejected rather than silently overwriting — fetch/rebase
# onto origin/main first in that case.
git push origin HEAD:main

echo "✅ Pushed to main. Vercel will deploy automatically."
echo "Done. Check https://vercel.com for deployment status."
