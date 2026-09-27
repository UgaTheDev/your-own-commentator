#!/usr/bin/env bash
# Run before `sam build`/`sam deploy`: bundles the schema this Lambda validates against, since
# CodeUri (this directory) doesn't include the repo-level schemas/ dir. See handlers.py SCHEMA_PATH.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p schemas
cp ../../schemas/messages.schema.json schemas/messages.schema.json
