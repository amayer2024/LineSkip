# LineSkip

A Madrid take on [LineLeap](https://www.lineleap.com/): buy line-skip / cover passes for nightlife
venues and redeem them at the door. Assignment 2 splits the original monolith into two independently
deployed services, each with its own SQL Server database, running locally with Docker Compose and in
the cloud on Azure Container Apps behind a static UI.

## Architecture

Two Flask services, one database each, loosely coupled along a single seam (see `ADR.md` 2, 6):

```
            browser (static UI on Azure Storage $web)
               |                         |
               v                         v
        passes service  --POST /events-->  analytics service
               |                              |
          passes DB                      analytics DB
```

- **passes** — auth, venues, pass products, purchasing (no-oversell guard), one-time redemption
  codes, refunds. Owns `users`, `sessions`, `venues`, `pass_products`, `purchases`.
- **analytics** — records a sales event on each purchase/refund and reports revenue (total,
  per-venue, top venues, per-day). Owns `events` only.
- **seam** — on each purchase/refund, `passes` makes one HTTP `POST /events` to `analytics`
  (`ANALYTICS_URL`, `ANALYTICS_TIMEOUT_S`). If `analytics` is down the purchase still succeeds and
  the event is dropped and logged (ADR-6). Neither service reads the other's database.

The full system (services, env vars, the seam, Azure resources) is described in `system.yaml`,
validated in CI against the provided `system.schema.json`. Each service's HTTP API is in
`services/<svc>/openapi.yaml`.

## Run locally

Needs Docker Desktop. SQL Server runs as a container; a one-off `db-init` job creates the two
databases and their logins, then both services run their migrations on startup.

```bash
cp .env.example .env     # sets SA_PASSWORD, PASSES_PWD, ANALYTICS_PWD, UI_ORIGIN
docker compose up --build
```

| Service   | URL                     |
|-----------|-------------------------|
| passes    | http://localhost:8001   |
| analytics | http://localhost:8002   |
| UI        | http://localhost:8080   |

Health: `curl http://localhost:8001/health` and `:8002/health` → `{"status":"ok","db":"ok",...}`.

## Tests and CI

Each service's business logic (service + repository + auth modules) is tested against a real SQL
Server, with a ≥70% coverage gate (ADR-4, 9). Run one service's suite locally against the Compose
database:

```bash
docker compose up -d sqlserver
docker compose run --rm --no-deps --user root -w /src -v "$PWD/services/passes:/src" passes \
  sh -lc "python -m pytest -q"
```

`ci.yml` runs on every branch and pull request: **lint** (ruff), **specs** (both OpenAPI documents +
`system.yaml` against `system.schema.json`), **tests** for each service against a SQL Server service
container with the coverage gate, then **images** — building and (on `main` only) pushing
`ghcr.io/amayer2024/lineskip-<service>:<sha>` to GHCR.

## Deploy (CD)

`cd.yml` runs on push to `main`: it calls `ci.yml`, then signs in to Azure by OIDC, points each
Container App at the new `:<sha>` image, injects each `DATABASE_URL` from a GitHub secret, writes
`ui/config.js` with the live service URLs and uploads `ui/` to the static website, then fails unless
`/health` returns 200 on both services. Live UI:
<https://amayerieu2024ui.z28.web.core.windows.net/>.

## Azure setup (one-time)

Run once to create the infrastructure the pipeline then deploys into. `<prefix>` is the IE username
with dots replaced by hyphens (`amayer-ieu2024`); the region is one from the subscription's allowed
list (`az policy assignment list`). Passwords are shown as placeholders and never committed.

**1. Subscription and region.** Activate Azure for Students, then
`az account set --subscription <id>`. Confirm the region (here `francecentral`) is on your allowed
list.

**2. Providers and resource group.**
```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Sql
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.ManagedIdentity
az group create --name rg-amayer-ieu2024 --location francecentral
```

**3. UI: Storage static website.**
```bash
az storage account create --name amayerieu2024ui --resource-group rg-amayer-ieu2024 \
  --location francecentral --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2
az storage blob service-properties update --account-name amayerieu2024ui \
  --static-website --index-document index.html --404-document index.html --auth-mode login
# the "primaryEndpoints.web" value is the system's public_url and the only allowed CORS origin
```

**4. SQL server + two serverless databases.**
```bash
az sql server create --name amayer-ieu2024-sql --resource-group rg-amayer-ieu2024 \
  --location francecentral --admin-user sqladmin --admin-password '<admin-password>'
az sql server firewall-rule create -g rg-amayer-ieu2024 -s amayer-ieu2024-sql \
  -n AllowAzure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
# temporarily open your own IP (MyIP rule) to create the per-DB users, then delete it
for db in passes analytics; do
  az sql db create -g rg-amayer-ieu2024 -s amayer-ieu2024-sql -n amayer-ieu2024-$db-db \
    --edition GeneralPurpose --compute-model Serverless --family Gen5 --capacity 1 \
    --backup-storage-redundancy Local --use-free-limit true --free-limit-exhaustion-behavior AutoPause
done
```
Then, connected to each database as `sqladmin`, create one contained user scoped to that database:
```sql
CREATE USER passes_user WITH PASSWORD = '<passes-password>';
ALTER ROLE db_ddladmin ADD MEMBER passes_user;
ALTER ROLE db_datareader ADD MEMBER passes_user;
ALTER ROLE db_datawriter ADD MEMBER passes_user;
-- same in amayer-ieu2024-analytics-db for analytics_user
```

**5. Container Apps environment + two apps** (placeholder image; the first deploy replaces it):
```bash
az containerapp env create --name amayer-ieu2024-env --resource-group rg-amayer-ieu2024 \
  --location francecentral
az containerapp create --name amayer-ieu2024-analytics --resource-group rg-amayer-ieu2024 \
  --environment amayer-ieu2024-env --image mcr.microsoft.com/k8se/quickstart:latest \
  --target-port 8000 --ingress external --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
  --env-vars CORS_ORIGINS="https://amayerieu2024ui.z28.web.core.windows.net"
az containerapp create --name amayer-ieu2024-passes --resource-group rg-amayer-ieu2024 \
  --environment amayer-ieu2024-env --image mcr.microsoft.com/k8se/quickstart:latest \
  --target-port 8000 --ingress external --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
  --env-vars CORS_ORIGINS="https://amayerieu2024ui.z28.web.core.windows.net" \
            ANALYTICS_URL="https://<analytics-fqdn>" ANALYTICS_TIMEOUT_S=2
```
CORS is enforced in the service code (Flask-CORS reading `CORS_ORIGINS`), never on the Container Apps
ingress.

**6. Pipeline identity (OIDC).**
```bash
az identity create --name amayer-ieu2024-github --resource-group rg-amayer-ieu2024 --location francecentral
az role assignment create --assignee-object-id <identity-principal-id> \
  --assignee-principal-type ServicePrincipal --role Contributor \
  --scope /subscriptions/<sub-id>/resourceGroups/rg-amayer-ieu2024
az identity federated-credential create --name github-main \
  --identity-name amayer-ieu2024-github --resource-group rg-amayer-ieu2024 \
  --issuer https://token.actions.githubusercontent.com \
  --subject "repo:amayer2024/LineSkip:ref:refs/heads/main" --audiences api://AzureADTokenExchange
# register the numeric-ID subject form too (repo:<owner>@<id>/<repo>@<id>:ref:refs/heads/main) —
# GitHub presents that form, and azure/login fails until it is registered.
```

**7. GitHub secrets and variables.**
```bash
gh secret set AZURE_CLIENT_ID --body "<identity-client-id>"
gh secret set AZURE_TENANT_ID --body "<tenant-id>"
gh secret set AZURE_SUBSCRIPTION_ID --body "<subscription-id>"
printf '%s' '<passes-password>'    | gh secret set PASSES_DB_PASSWORD
printf '%s' '<analytics-password>' | gh secret set ANALYTICS_DB_PASSWORD
gh variable set PREFIX --body "amayer-ieu2024"
gh variable set RESOURCE_GROUP --body "rg-amayer-ieu2024"
gh variable set UI_STORAGE --body "amayerieu2024ui"
```

After this, only the pipeline changes anything: push to `main` runs CI and deploys. New GHCR
packages are private by default — make `lineskip-passes` and `lineskip-analytics` public once so
Azure can pull them.

See `ADR.md` for the reasoning behind each decision.
