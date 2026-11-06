#!/bin/sh
# Run the office skills' acceptance test inside NodeNova Desk's agent image.
#
#   tests/desk/run.sh [image]        default image: nn-desk-agent:dev
#
# Build the image from the desk repo with these skills baked in first:
#   node nodenova/build/nn.mjs runtime-build
#   docker build --build-context skills=<this repo> -f nodenova/runtime/Dockerfile -t nn-desk-agent:dev .
#
# The test drives the image's own tool server (the Rust tools the agent calls),
# with the shell's network blocked as in a real run. Nothing leaves the
# container; the work folder is a fresh temporary one.
set -eu
image=${1:-nn-desk-agent:dev}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
chmod 777 "$work"
name="nn-skills-e2e-$$"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

docker run -d --name "$name" --cap-add NET_ADMIN -e NN_MODEL=none -e NN_API_KEY=off \
  -v "$work:/work" -v "$here:/e2e:ro" "$image" >/dev/null
i=0
until docker exec "$name" test -S /run/nn/tools.sock 2>/dev/null; do
  i=$((i + 1)); [ "$i" -lt 100 ] || { docker logs "$name"; exit 1; }
  sleep 0.2
done
docker exec -u nn-agent "$name" python3 /e2e/e2e.py
