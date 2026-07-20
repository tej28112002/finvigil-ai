#!/bin/bash
set -e

echo "🚀 FinVigil Deploy Script"
echo "Merging current branch into main and pushing to Vercel..."

CURRENT=$(git symbolic-ref --short HEAD)
echo "Current branch: $CURRENT"

if [ "$CURRENT" = "main" ]; then
  echo "Already on main. Pushing..."
  git push origin main
else
  echo "Switching to main and merging $CURRENT..."
  git checkout main
  git pull origin main --rebase
  git merge "$CURRENT" --no-edit
  git push origin main
  echo "✅ Pushed to main. Vercel will deploy automatically."
  echo "Switching back to $CURRENT..."
  git checkout "$CURRENT"
fi

echo "Done. Check https://vercel.com for deployment status."
