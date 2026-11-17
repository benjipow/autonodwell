# Autonodwell website

Static site. No build step.

- `index.html`: the full site (Home, How it works, The vision, Partner with us), with hash routing, the mobile menu transition and the pinned problem section
- `hero.mp4` / `hero-poster.jpg`: home hero background video and its poster image
- `logo.png`: header logo and favicon
- `autonodwell-app/`: a copy of the Autonodwell customer app (from `Arcitu/autonodwell-app`): React web app, FastAPI API, migrations and deploy pipeline. See its own README. It is not part of the website; `_redirects` keeps it from being served.

## Deploy on Cloudflare Pages

Connect this repo in Cloudflare Pages. Framework preset: None. Build command: empty. Output directory: `/`.

### Inquiry form

`functions/api/inquiry.js` receives the Partner form and emails it through Resend. Add these in Pages > Settings > Environment variables (encrypted):

- `RESEND_API_KEY`: Resend API key
- `INQUIRY_TO`: inbox that receives inquiries
- `INQUIRY_FROM`: sender on a Resend-verified domain, e.g. `Autonodwell <inquiries@autonodwell.com>`

### Dream home questionnaire

The "Try It Free" and "Design Your Dream Home, FREE!" buttons open a pop-up that asks the app's step 1 questions (ZIP, land, lot, budget). Its "Pick your home" button hands the answers to the app at `APP_URL/design/new?zip=…&land=…&budget=…`. The app (`autonodwell-app/web/src/pages/design/DesignFlow.tsx`, `prefillFromUrl`) fills in step 1 and continues the normal path: "Pick your home" creates the design (`POST /api/v1/designs`), then plan & style, finishes, site, estimate, and "Review with a consultant" (`POST /api/v1/designs/{id}/submit`), which creates the sales lead and syncs it to the CRM.

`APP_URL` is set near the top of the questionnaire script in `index.html` (default `https://app.autonodwell.com`). Set it to `""` to email the answers through `/api/inquiry` instead, until the app is live.

## Before launch

- Finish the Resend setup so the inquiry form sends.
- Privacy Policy and Terms of Service are published; they still need legal review.
- Deploy the app at `APP_URL` (see `autonodwell-app/README.md`) before the questionnaire goes live, or set `APP_URL` to `""`.
- Verify the founder bio details.
