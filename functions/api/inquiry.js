// Cloudflare Pages Function: POST /api/inquiry
// Sends each website inquiry by email through Resend (https://resend.com).
// The destination address is never in the site code. Set these in
// Cloudflare Pages > Settings > Environment variables (as encrypted secrets):
//   RESEND_API_KEY  your Resend API key
//   INQUIRY_TO      the inbox that receives inquiries
//   INQUIRY_FROM    a sender on a domain verified in Resend, e.g. "Autonodwell <inquiries@autonodwell.com>"

const TYPES = [
  "Dream home questionnaire",
  "Exclusive offers signup",
  "Future homeowner: early access",
  "Investor",
  "Lender or underwriter",
  "Builder or delivery partner",
  "Developer or landowner",
  "Privacy, legal or copyright request",
  "Other",
];

const clean = (v, max) => String(v ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
const escapeHtml = s => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

export async function onRequestPost({ request, env }) {
  if (!env.RESEND_API_KEY || !env.INQUIRY_TO || !env.INQUIRY_FROM) return json({ ok: false, error: "not_configured" }, 500);

  let data;
  try { data = await request.json(); } catch { return json({ ok: false, error: "bad_request" }, 400); }

  // Honeypot: real visitors never fill this hidden field.
  if (clean(data.website, 200)) return json({ ok: true });

  const name = clean(data.name, 120);
  const email = clean(data.email, 200);
  const type = TYPES.includes(data.type) ? data.type : "Other";
  const location = clean(data.location, 200);
  const org = clean(data.org, 200);
  const message = String(data.message ?? "").trim().slice(0, 5000);

  if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return json({ ok: false, error: "invalid" }, 400);

  const rows = [["Name", name], ["Email", email], ["Interested as", type], ["Location or market", location || "-"], ["Organization", org || "-"]];
  const text = rows.map(([k, v]) => `${k}: ${v}`).join("\n") + "\n\n" + (message || "(no message)");
  const html = `<table cellpadding="6" style="font-family:Arial,sans-serif;font-size:14px">${rows.map(([k, v]) => `<tr><td style="color:#6b5662">${k}</td><td><b>${escapeHtml(v)}</b></td></tr>`).join("")}</table><p style="font-family:Arial,sans-serif;font-size:14px;white-space:pre-wrap">${escapeHtml(message || "(no message)")}</p>`;

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: env.INQUIRY_FROM,
      to: [env.INQUIRY_TO],
      reply_to: email,
      subject: `Autonodwell inquiry: ${type} (${name})`,
      text,
      html,
    }),
  });

  if (!res.ok) {
    // Resend's reason (e.g. domain not verified, key restricted, invalid key). Never logs the key.
    let reason = "";
    try { reason = (await res.text()).slice(0, 300); } catch {}
    console.error(`Resend refused the inquiry email: ${res.status} ${reason} (from: ${env.INQUIRY_FROM})`);
    return json({ ok: false, error: "send_failed" }, 502);
  }
  return json({ ok: true });
}

