#!/bin/bash
# sync.sh — 从 Learning/Daily News/ 同步 markdown 到 repo content/，然后构建并推送
#
# 用法：
#   ./scripts/sync.sh              # 同步所有新/更新的 .md 文件
#   ./scripts/sync.sh 2026-02-16   # 只同步指定日期
#   ./scripts/sync.sh --build-only # 只构建，不同步

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="$HOME/Library/CloudStorage/Dropbox/CC/Learning/Daily News"
CONTENT_DIR="$REPO_DIR/content"

cd "$REPO_DIR"

# --- 解析参数 ---
BUILD_ONLY=false
TARGET_DATE=""

for arg in "$@"; do
  case "$arg" in
    --build-only) BUILD_ONLY=true ;;
    *) TARGET_DATE="$arg" ;;
  esac
done

# --- 同步 ---
if [ "$BUILD_ONLY" = false ]; then
  if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory not found: $SOURCE_DIR"
    exit 1
  fi

  SYNCED=0

  if [ -n "$TARGET_DATE" ]; then
    # 同步指定日期
    for f in "$SOURCE_DIR"/${TARGET_DATE}*.md; do
      [ -f "$f" ] || continue
      cp "$f" "$CONTENT_DIR/"
      echo "  + $(basename "$f")"
      SYNCED=$((SYNCED + 1))
    done
  else
    # 同步所有 .md 文件（只复制更新的）
    for f in "$SOURCE_DIR"/*.md; do
      [ -f "$f" ] || continue
      base="$(basename "$f")"
      target="$CONTENT_DIR/$base"
      if [ ! -f "$target" ] || ! diff -q "$f" "$target" > /dev/null 2>&1; then
        cp "$f" "$target"
        echo "  + $base"
        SYNCED=$((SYNCED + 1))
      fi
    done
  fi

  if [ "$SYNCED" -eq 0 ]; then
    echo "No new or updated files to sync."
  else
    echo "Synced $SYNCED file(s)."
  fi
fi

# --- 构建 ---
echo ""
echo "Building site..."
npm run build

# --- Git commit & push ---
if git diff --quiet && git diff --cached --quiet; then
  echo "No changes to commit."
else
  git add content/ docs/
  DATE_STR=$(date +%Y-%m-%d)
  git commit -m "update: daily news $DATE_STR"
  git push
  echo "Pushed to remote."
fi
