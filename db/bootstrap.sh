#!/bin/sh
set -eu
# Uses generated environment values; normal startup never resets a database.
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONPATH="$(pwd)/apps/api:$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
exec python -m app.cli bootstrap --students "${SEED_STUDENTS:-100000}"
