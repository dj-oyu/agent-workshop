#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 0 ]; then
 cat "$ROOT/PLAYBOOK.md"
else
 python3 "$ROOT/loop.py" resume "$1"
fi
