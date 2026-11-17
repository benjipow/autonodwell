# Architecture & decisions

## Shape

```
 Web app (React)          Native app (later, React Native/Expo)      Sales console / Admin (in web app)
        \                          |                                      /
         \__________  HTTPS + Firebase ID token  ________________________/
                                   |
                        FastAPI on Cloud Run   (/api/v1/…  — the ONLY way to reach data)
                         |        |         \
              Cloud SQL Postgres  |      Outbox → CRM adapter (GoHighLevel | webhook | none)
                                  |
                      Firebase Auth / Identity Platform (identity only; roles live in Postgres)
```

**Rules that keep this easy to grow**
1. **One API.** Clients never touch the database. The web app and future native apps use the same `/api/v1` endpoints.
2. **The API contract is code.** FastAPI generates `openapi.json`, and the web app's typed client is generated from it (`npm run gen:api`). A native app, or an investor's developers, can generate their own client from the same spec in any language.
3. **Schema changes are migrations.** `alembic` files in `api/alembic/versions` are the history of the database. CI runs `alembic check` so the models and the migrations can't drift apart.
4. **Business logic lives server-side.** Prices, monthly payments and budget fit are computed only in `services/estimate.py`, so every client shows the same numbers.
5. **Integrations go through an outbox.** Each CRM push is a row in `integration_events`, with its status, error and retry count. Adding email, SMS or lender APIs later uses the same pattern.

## Data model (Postgres)

| Table | Purpose | Notes |
|---|---|---|
| `users` | Everyone: customers (anonymous → signed in), sales, admin | `firebase_uid` links to Firebase. `role` is customer / sales / admin. |
| `home_models` | Model One/Two/Three | Editable price, image, active flag |
| `option_categories`, `options` | Siding, kitchen, flooring, upgrades | `pricing_mode` is flat or per ft². Single- or multi-select per category. |
| `assumption_sets` | Interest rate, term, down payment, soft costs, contingency, delivery | **Never edited in place**: saving creates a new version, so old estimates stay explainable. |
| `markets`, `zip_prefixes` | Regional cost data by ZIP prefix | MVP = labeled samples. Swapped for the location database later. |
| `path_stages` | Step 3 timeline content | Editable copy and durations |
| `designs` | A customer's home | UUID id, selections, budget, ZIP, step. `submitted_estimate` freezes what the customer saw. Soft-deleted. |
| `leads` | Consultation requests | Contact snapshot, status pipeline, owner, consent text, CRM ids, sync status |
| `lead_activities` | Append-only history | Notes, status changes, assignments, CRM sync results |
| `integration_events` | Outbox for CRM and other integrations | Retryable, auditable |

Money is stored in integer cents and rates in basis points. UUIDs are used for customer-facing records.

**Lead pipeline:** `new → contacted → consultation_scheduled → qualified → financing → won | lost`

## Auth flow

1. A first-time visitor is signed into Firebase **anonymously**, so their design is saved from the first click.
2. At step 4 (or under "My homes"), the customer creates an account with Google or email. Firebase **links** the account to the anonymous one, so the UID stays the same and their designs follow them.
3. The API verifies the Firebase ID token on every request and maps the UID to a `users` row. Roles come from the database (`ADMIN_EMAILS` bootstraps the first admin), and staff are managed in Admin › Team.

## Who can manage what

- **Customers:** create, rename, duplicate and delete designs. Edit their profile. Download all their data (`GET /me/export`). Delete their account (`DELETE /me` removes designs and personal data from leads).
- **Sales:** lead list with status tabs, search, owner filter, CSV export. Lead detail with the frozen estimate, status, owner, notes and "Sync now".
- **Admin:** everything Sales can do, plus prices, options, assumptions, market data and team roles.

## CRM: GoHighLevel, swappable

`services/crm/adapters.py` → `GoHighLevelCRM` (API v2, Private Integration token):
1. `POST /contacts/upsert`
2. `POST /contacts/{id}/tags`. Tags are added separately because tags sent on upsert overwrite the existing ones.
3. `POST /contacts/{id}/notes`: model, ZIP, estimate, budget, message and a deep link to the sales console.
4. Optional `POST /opportunities/` in the pipeline/stage you configure (once per lead).

Sync runs when a lead is created or resubmitted, on every status change, and on manual "Sync now". To move to another CRM, add an adapter class with `push_lead()` and set `CRM_PROVIDER`.
`CRM_PROVIDER=webhook` posts a signed JSON body to any URL (Zapier, Make, n8n), with no code needed.

## Roadmap hooks (where the next pieces plug in)

| Next | Where it goes |
|---|---|
| **Autonodwell location database** (MLS, zoning, permits, utilities by ZIP) | New tables (for example `zip_codes`, `parcels`, `jurisdictions`, `permit_requirements`, `listings`) plus ingestion jobs (Cloud Run Jobs + Cloud Scheduler). Replace `resolve_market()` in `services/estimate.py`. Note: MLS data requires licensed IDX/RESO feeds through a participating broker. |
| **Lender handoff ("Qualify")** | A new integration adapter using the outbox pattern. The `submitted_estimate` snapshot is the start of the lender data package. |
| **Native app** | React Native/Expo using the same generated client and Firebase Auth SDK. Endpoints are versioned (`/api/v2` for breaking changes), so installed apps keep working. |
| **Real plans and renders** | `home_models.image_url` / `floor_plan_key`. Options could later map to BIM assemblies and BOM quantities. |
| **Reporting for investors** | Read-only replica or BigQuery export of `leads` and `designs`. Analytics events need a consent review first. |
| **Email/SMS to customers** | Outbox adapter (SendGrid/Twilio, or GHL workflows triggered by tags) |
