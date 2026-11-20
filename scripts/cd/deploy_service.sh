#!/usr/bin/env bash
# Deploy one service to its Azure Container App: set the DB connection string as a
# secret, then roll out the SHA-tagged image and point DATABASE_URL at that secret.
#
# `secret set` and `update` are two control-plane writes; the update can read the
# app's template before the just-set secret has propagated and fail with
# ContainerAppSecretRefNotFound. So the update is retried a few times.
#
# Expects RG, PREFIX, OWNER, SHA in the environment. Args: <service> <db-user> <db-password>
set -euo pipefail

svc="$1"; db_user="$2"; db_pass="$3"
sql_fqdn="${PREFIX}-sql.database.windows.net"
app="${PREFIX}-${svc}"

az containerapp secret set -g "$RG" -n "$app" \
  --secrets "db-url=mssql://${db_user}:${db_pass}@${sql_fqdn}:1433/${PREFIX}-${svc}-db" >/dev/null

for attempt in 1 2 3 4 5; do
  if az containerapp update -g "$RG" -n "$app" \
       --image "ghcr.io/${OWNER}/lineskip-${svc}:${SHA}" \
       --set-env-vars "DATABASE_URL=secretref:db-url" "GIT_SHA=${SHA}"; then
    echo "${svc}: deployed (attempt ${attempt})"
    exit 0
  fi
  echo "${svc}: update attempt ${attempt} failed (secret still propagating?); retrying in 15s"
  sleep 15
done

echo "::error::${svc}: update failed after retries"
exit 1
