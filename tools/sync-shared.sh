#!/bin/sh
# Copy shared/*.py into every skill that uses it. Each skill folder must
# work on its own (skills are pinned and installed one by one), so it carries
# its own copy; this keeps the copies identical. `--check` only compares.
set -eu
cd "$(dirname "$0")/.."
status=0
sync() {
  file=$1; shift
  for skill in "$@"; do
    dest="skills/$skill/scripts/$file"
    if [ "${CHECK:-}" = "1" ]; then
      cmp -s "shared/$file" "$dest" || { echo "out of date: $dest (run tools/sync-shared.sh)"; status=1; }
    else
      cp "shared/$file" "$dest"
    fi
  done
}
[ "${1:-}" = "--check" ] && CHECK=1
sync ooxml.py docx xlsx pptx
sync ooxml_images.py docx pptx
exit $status
