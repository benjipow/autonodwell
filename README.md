# Autonodwell website

Static site. No build step.

- `index.html`: the full site (Home, How it works, The vision, Partner with us), with hash routing, the mobile menu transition and the pinned problem section
- `hero.mp4` / `hero-poster.jpg`: home hero background video and its poster image
- `logo.png`: header logo and favicon
- `autonodwell-app/`: a copy of the Autonodwell customer app (from `Arcitu/autonodwell-app`): React web app, FastAPI API, migrations and deploy pipeline. See its own README. It is not part of the website; `_redirects` keeps it from being served.

## Deploy on Cloudflare (Workers)

This repo is connected to the Cloudflare Worker named `autonodwell` (Workers & Pages, Sarah's account). Every push to `main` deploys automatically.

- `wrangler.jsonc`: Worker settings. The site files are served as static assets; `name` must match the Worker's name in Cloudflare.
- `worker.js`: serves the site and handles `POST /api/inquiry`.
- `.assetsignore`: keeps code, the README and the `autonodwell-app/` folder from being published.

Build settings in Cloudflare: build command empty, deploy command `npx wrangler deploy`, root directory empty.

### Inquiry form

`functions/api/inquiry.js` (called by `worker.js`) receives the Partner form and emails it through Resend. Add these in the Worker's Settings > Variables and Secrets, then redeploy:

- `RESEND_API_KEY`: Resend API key
- `INQUIRY_TO`: inbox that receives inquiries
- `INQUIRY_FROM`: sender on a Resend-verified domain, e.g. `Autonodwell <inquiries@autonodwell.com>`

### Dream home design pop-up

The "Try It Free" and "Design Your Dream Home, FREE!" buttons open the app's customer flow inside a pop-up:
01 Start (ZIP, land, lot, budget, land budget), 02 Plan & style, 03 Make it yours, 04 Your site, 05 Understand, then "Send to a consultant".

- The catalog, assumptions, sample markets and path stages are copied from `autonodwell-app/api/app/seed.py`, the ZIP-area land and construction data from `autonodwell-app/api/data/costs_by_zip3.csv`, and the estimate math from `autonodwell-app/api/app/services/estimate.py`. The numbers were checked against the app's API for several designs and match to the dollar. If prices change in the app, update the catalog block at the top of the pop-up script in `index.html`.
- "Send to a consultant" emails the full design, estimate and contact details through `/api/inquiry` (type "Dream home questionnaire").
- Style photos are in `img/styles/` (resized from the app's `web/public/styles/`).
- When the app is live, it can also take the step 1 answers directly: `/design/new?zip=…&land=…&budget=…&monthly=…&total=…&cash=…&address=…&lot_price=…` (see `prefillFromUrl` in `autonodwell-app/web/src/pages/design/DesignFlow.tsx`).

## Before launch

- Finish the Resend setup so the inquiry form sends.
- Privacy Policy and Terms of Service are published; they still need legal review.
- All prices in the pop-up are the app's placeholder sample numbers. Replace them with real figures before launch.
- Verify the founder bio details.
