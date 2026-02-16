#!/bin/bash
# sync.sh — 构建 Daily News 站点并推送到 GitHub
#
# 小虾的 cron 任务现在直接写入 content/，不再需要从 Learning/ 同步。
#
# 用法：
#   ./scripts/sync.sh              # 构建并推送
#   ./scripts/sync.sh --build-only # 只构建，不推送

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# --- 解析参数 ---
BUILD_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --build-only) BUILD_ONLY=true ;;
  esac
done

# --- 构建 ---
echo "Building site..."
npm run build

# --- Git commit & push ---
if [ "$BUILD_ONLY" = true ]; then
  echo "Build-only mode, skipping git."
  exit 0
fi

if git diff --quiet && git diff --cached --quiet; then
  echo "No changes to commit."
else
  git add content/ docs/ .gitignore
  DATE_STR=$(date +%Y-%m-%d)
  git commit -m "update: daily news $DATE_STR"
  git push
  echo "Pushed to remote."
fi
