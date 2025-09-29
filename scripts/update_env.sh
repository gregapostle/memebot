#!/bin/bash
set -e

echo "🔄 Syncing .env with .env.example..."

# Ensure .env exists
if [ ! -f .env ]; then
  echo "⚠️  No .env found. Creating one from .env.example"
  cp .env.example .env
  exit 0
fi

# Backup old env
cp .env .env.bak

# Add missing vars from .env.example
while IFS= read -r line; do
  # Skip empty/comment lines
  if [[ -z "$line" || "$line" =~ ^# ]]; then
    continue
  fi

  key=$(echo "$line" | cut -d= -f1)
  if ! grep -q "^$key=" .env; then
    echo "$line" >> .env
    echo "➕ Added missing var: $key"
  fi
done < .env.example

echo "✅ Done. Backup saved to .env.bak"

