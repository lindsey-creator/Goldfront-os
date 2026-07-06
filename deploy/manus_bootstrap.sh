#!/usr/bin/env bash
# One command on Manus: curl -fsSL https://raw.githubusercontent.com/lindsey-creator/Goldfront-os/master/deploy/manus_bootstrap.sh | bash
set -euo pipefail

BRAIN_PARENT="${BRAIN_PARENT:-$HOME/Documents/Claude/Projects/Brain}"
GO_URL="${GO_URL:-https://github.com/lindsey-creator/Goldfront-os.git}"
CC_URL="${CC_URL:-https://github.com/lindsey-creator/conrad-command-center.git}"

mkdir -p "$BRAIN_PARENT"
cd "$BRAIN_PARENT"

if [ -d goldfront-os/.git ]; then
  (cd goldfront-os && git pull --ff-only)
else
  git clone "$GO_URL" goldfront-os
fi

if [ -d conrad-command-center/.git ]; then
  (cd conrad-command-center && git pull --ff-only)
else
  git clone "$CC_URL" conrad-command-center
fi

exec bash "$BRAIN_PARENT/goldfront-os/deploy/FINISH_ON_MANUS.sh"
