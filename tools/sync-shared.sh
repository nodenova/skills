#!/bin/sh
# Copy shared/ooxml.py into every skill that uses it. Each skill folder must
# work on its own (skills are pinned and installed one by one), so it carries
# its own copy; this keeps the copies identical. `--check` only compares.
set -eu
cd "$(dirname "$0")/.."
status=0
for skill in docx xlsx pptx; do
  dest="skills/$skill/scripts/ooxml.py"
  if [ "${1:-}" = "--check" ]; then
    cmp -s shared/ooxml.py "$dest" || { echo "out of date: $dest (run tools/sync-shared.sh)"; status=1; }
  else
    cp shared/ooxml.py "$dest"
  fi
done
exit $status
