# Autonodwell website

Static site. No build step.

- `index.html`: the full site (Home, How it works, The vision, Partner with us), with hash routing, the mobile menu transition and the pinned problem section
- `hero.mp4` / `hero-poster.jpg`: home hero background video and its poster image
- `logo.png`: header logo and favicon

## Deploy on Cloudflare Pages

Connect this repo in Cloudflare Pages. Framework preset: None. Build command: empty. Output directory: `/`.

### Inquiry form

`functions/api/inquiry.js` receives the Partner form and emails it through Resend. Add these in Pages > Settings > Environment variables (encrypted):

- `RESEND_API_KEY`: Resend API key
- `INQUIRY_TO`: inbox that receives inquiries
- `INQUIRY_FROM`: sender on a Resend-verified domain, e.g. `Autonodwell <inquiries@autonodwell.com>`

## Before launch

- Finish the Resend setup so the inquiry form sends.
- Privacy Policy and Terms of Use are still waiting on legal review.
- Verify the founder bio details.
