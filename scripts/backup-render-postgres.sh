#!/usr/bin/env bash
# Export a private Render Postgres snapshot to the ignored local backups/ folder.
# This script reads production data, but never modifies it or runs a restore.
set -Eeuo pipefail
umask 077

if [[ -z "${RENDER_EXTERNAL_DATABASE_URL:-}" ]]; then
  echo "Configure RENDER_EXTERNAL_DATABASE_URL with the external Render connection URL." >&2
  exit 2
fi
if [[ ! "${RENDER_EXTERNAL_DATABASE_URL}" =~ ^postgres(ql)?:// ]]; then
  echo "RENDER_EXTERNAL_DATABASE_URL must be a PostgreSQL URL." >&2
  exit 2
fi
for tool in pg_dump pg_restore shasum; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing local command: $tool" >&2
    exit 2
  fi
done

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
destination="$root/backups"
mkdir -p -- "$destination"
timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
# BSD mktemp on macOS requires the Xs at the end of the template.
temp="$(mktemp "$destination/.pending-XXXXXXXX")"
nonce="${temp##*/}"
nonce="${nonce#.pending-}"
archive="$destination/atrio-render-$timestamp-$nonce.dump"
manifest="${archive%.dump}.manifest.txt"
checksum="$archive.sha256"
completed=0
cleanup() {
  if [[ "$completed" != 1 ]]; then
    rm -f "$temp" "$archive" "$manifest" "$checksum"
  fi
}
trap cleanup EXIT

# SSL is required for external access. No URI or credential is printed.
PGSSLMODE=require pg_dump \
  --dbname="$RENDER_EXTERNAL_DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="$temp"

# A readable table-of-contents is a quick validity check, not a test restore.
pg_restore --list "$temp" > "$manifest"
if [[ ! -s "$temp" || ! -s "$manifest" ]]; then
  echo "The archive or its manifest is empty." >&2
  exit 1
fi
mv "$temp" "$archive"
shasum -a 256 "$archive" > "$checksum"
completed=1

printf 'Exported: %s\n' "$archive"
printf 'Manifest: %s\n' "$manifest"
printf 'SHA-256:  %s\n' "$checksum"
printf '%s\n' 'Next step: restore into an isolated, disposable PostgreSQL instance.'
