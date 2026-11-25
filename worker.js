// Cloudflare Worker entry point for the Autonodwell website.
// Serves the static site and handles POST /api/inquiry (the inquiry form and the
// dream home pop-up's "Send to a consultant"). The handler lives in
// functions/api/inquiry.js so the same code also works as a Pages Function.
// Settings (Worker > Settings > Variables and Secrets): RESEND_API_KEY (secret), INQUIRY_TO, INQUIRY_FROM.
import { onRequestPost } from "./functions/api/inquiry.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/inquiry") {
      if (request.method === "POST") return onRequestPost({ request, env, ctx });
      return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
    }
    return env.ASSETS.fetch(request);
  },
};
