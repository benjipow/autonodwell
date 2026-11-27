# Autonodwell website

The marketing site for autonodwell.com. Static, no build step. It lives in this folder so it can be deployed on its own; the app in the rest of this repo is never published with it.

- `index.html`: the full site (Home, How it works, The vision, Partner with us, Privacy policy, Terms of service), with hash routing, the mobile menu, the pinned sliders and the dream home pop-up
- `hero.mp4` / `hero-poster.jpg`: home hero background video and its poster image
- `img/`: page photos; `img/styles/` holds the house style photos used in the pop-up
- `logo.png`: header logo and favicon
- `functions/api/inquiry.js`: Cloudflare Pages Function that emails form submissions

## Deploy on Cloudflare (Workers)

The live site (autonodwell.com, www.autonodwell.com) runs on the Cloudflare Worker named `autonodwell` in Sarah's Cloudflare account. Connected to this repo, every push to `main` that touches the site deploys it.

Build settings in Cloudflare (Worker > Settings > Builds):

- Production branch: `main`
- **Root directory: `website`**
- Build command: empty
- Deploy command: `npx wrangler deploy`

Files that make this work:

- `wrangler.jsonc`: Worker settings. The site files are served as static assets; `name` must match the Worker's name in Cloudflare.
- `worker.js`: serves the site and handles `POST /api/inquiry`.
- `.assetsignore`: keeps code and the README from being published.

### Form submissions

`functions/api/inquiry.js` (called by `worker.js`) receives the Partner page inquiry form and the pop-up's "Send to a consultant", and emails them through Resend. Add these in the Worker's Settings > Variables and Secrets (production), then redeploy:

- `RESEND_API_KEY` (secret): Resend API key
- `INQUIRY_TO`: inbox that receives submissions
- `INQUIRY_FROM`: sender on a Resend-verified domain, e.g. `Autonodwell <inquiries@autonodwell.com>`

No contact details appear on the site; all contact goes through the inquiry form.

### Dream home design pop-up

The "Try It Free" and "Design Your Dream Home, FREE!" buttons open the app's customer flow inside a pop-up:
01 Start (ZIP, land, lot, budget, land budget), 02 Plan & style, 03 Make it yours, 04 Your site, 05 Understand, then "Send to a consultant".

- The catalog, assumptions, sample markets and path stages are copied from `api/app/seed.py`, the ZIP-area land and construction data from `api/data/costs_by_zip3.csv`, and the estimate math from `api/app/services/estimate.py`. The numbers were checked against the app's API for several designs and match to the dollar. If prices change in the app, update the catalog block at the top of the pop-up script in `index.html`.
- "Send to a consultant" emails the full design, estimate and contact details through `/api/inquiry` (type "Dream home questionnaire").
- Style photos in `img/styles/` are resized from `web/public/styles/`.

## Before launch

- Finish the Resend setup so the forms send.
- Privacy Policy and Terms of Service still need legal review (including whether a DMCA agent and a second privacy-request method must be listed).
- All prices in the pop-up are the app's placeholder sample numbers. Replace them with real figures before launch.
- Verify the founder bio details.
