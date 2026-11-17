# Autonodwell — Customer Home Design App (MVP)

Customers design a starter home within a monthly budget in four steps, then send it to an
Autonodwell consultant. The sales team works the leads in a built-in console, and every lead is
pushed to GoHighLevel (swappable).

| Step | Customer sees | Backed by |
|---|---|---|
| 01 Dream | Model One / Two / Three + monthly budget slider | `GET /catalog`, `POST /estimate` |
| 02 Make it yours | Siding, kitchen, flooring, upgrades with live cost change | `PATCH /designs/{id}` |
| 03 Discover | ZIP → path home: Design, Site, Financing, Approvals, Construction, Keys | market data + `path_stages` |
| 04 Understand | Full estimate, monthly cost, cash needed → **Review with a consultant** | `POST /designs/{id}/submit` → lead + CRM |

**Stack:** React + TypeScript (Vite) · Python FastAPI on Cloud Run · Postgres on Cloud SQL ·
Firebase Auth / Identity Platform · Alembic migrations · Firebase Hosting (`/api/**` → Cloud Run).

```
api/        FastAPI app, SQLAlchemy models, Alembic migrations, tests
web/        React web app (customer flow, My homes, Sales console, Admin)
deploy/     Cloud Build pipeline (build → migrate → deploy API → deploy web)
docs/       ARCHITECTURE.md — data model, decisions, roadmap
```

## Run it locally

**With Docker** (easiest):
```bash
docker compose up
```
Then open http://localhost:5173. API docs are at http://localhost:8000/api/docs.

**Without Docker:**
```bash
# Postgres running locally with a database named "autonodwell"
cd api && pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head && python -m app.seed --demo
uvicorn app.main:app --reload --port 8000

cd web && npm install && npm run dev
```

Local mode uses **dev sign-in** (no Firebase needed): any email works.
`sales@example.com` opens the Sales console and `admin@example.com` opens Admin.

**Tests:** `cd api && pytest` runs against a real Postgres database built from the migrations.

## Everyday tasks

| Task | How |
|---|---|
| Change prices, finishes, financing assumptions, market numbers | **Admin** screen in the app (no code, no DB dashboard) |
| Give a teammate sales access | They sign in once → Admin › Team → set role to Sales |
| Change the database schema | Edit `api/app/models.py` → `alembic revision --autogenerate -m "what changed"` → review the file → commit. CI fails if models and migrations disagree. |
| Change an API endpoint | Edit `api/app/schemas.py`/routers → `cd web && npm run gen:api` to regenerate the typed client. CI fails if it's stale. |
| Switch CRM | Set `CRM_PROVIDER=ghl`, `webhook` (Zapier/Make/n8n) or `none`. To add HubSpot etc., add an adapter in `api/app/services/crm/adapters.py`. |
| Export leads | Sales console → Export CSV (respects the current filters) |

## Deploying to GCP (one-time setup)

Run these with the founder's GCP access. Region assumed `us-central1`.

1. **Enable APIs:** Cloud Run, Cloud SQL Admin, Artifact Registry, Secret Manager, Cloud Build, Identity Toolkit.
2. **Cloud SQL:** create a Postgres 16 instance `autonodwell-db`, a database `autonodwell` and a user `app`.
3. **Secrets (Secret Manager):**
   - `DATABASE_URL` = `postgresql+psycopg://app:PASSWORD@/autonodwell?host=/cloudsql/PROJECT:us-central1:autonodwell-db`
   - `GHL_PRIVATE_TOKEN`, `GHL_LOCATION_ID`: from GoHighLevel › Settings › Private Integrations. The token needs the contacts and opportunities scopes.
   - `ADMIN_EMAILS` = the founder's email
4. **Service account** `autonodwell-api` with these roles: Cloud SQL Client, Secret Manager Secret Accessor, Firebase Authentication Admin.
5. **Artifact Registry** Docker repo named `autonodwell`.
6. **Firebase:** add Firebase to the GCP project. Enable Authentication with the providers **Anonymous**, **Google** and **Email/Password**. Add `app.autonodwell.com` to the authorized domains.
7. **Deploy:** `gcloud builds submit --config deploy/cloudbuild.yaml --substitutions=_TAG=$(git rev-parse --short HEAD),_FIREBASE_API_KEY=...,_FIREBASE_APP_ID=...,_FIREBASE_MEASUREMENT_ID=...`. Or connect a Cloud Build trigger to the GitHub repo so every push to `main` deploys. To turn on GoHighLevel later, add the two GHL secrets and set CRM_PROVIDER=ghl in the deploy step. Leave `_FIREBASE_MEASUREMENT_ID` empty to ship without Google Analytics.
8. **Domain (Cloudflare DNS):** in Firebase Hosting, add the custom domain `app.autonodwell.com` and create the DNS records Firebase shows in Cloudflare. Set them to **DNS only** (grey cloud) so Firebase can issue the SSL certificate.

The deploy pipeline runs migrations as a Cloud Run Job **before** the new API version takes traffic.

## Placeholders to replace before launch

- Prices, options, assumptions and all market data are **sample numbers** (`api/app/seed.py`). Edit them in Admin.
- Floor plans and the exterior preview are schematic (`web/src/components/Drawings.tsx`). Set `image_url` on each model, or swap the component.
- The privacy policy, terms and consent wording need legal review. The consent text is stored with every lead.
