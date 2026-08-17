# Bazillin Studio — Batch 11

## 1. Settings overflow — real fix this time
Found the actual bug: `.a-grid-3` (used by Email Configuration and others)
was `grid-template-columns: 1fr 1fr 1fr`. Bare `1fr` tracks can still be
forced wider than their share by a child's intrinsic content width, even
with `min-width:0` on the child (that only fixes flex, not grid tracks).
Changed every `.a-grid-*` and `.responsive-grid-2` to
`grid-template-columns: repeat(N, minmax(0,1fr))` — this is the standard,
guaranteed-robust CSS Grid pattern that caps each column's growth at the
track level, not just the child level. That's why the SMTP Host field
(column 1) was going missing while columns 2-3 still showed: the grid
itself had grown past its container.

## 2. Telegram/bot proxy issue — diagnosed and fixed
Your test — `{"ok":true,"result":true,...}` — almost certainly ran from a
PythonAnywhere **Bash console**, which sources your `.bashrc`/shell profile
where the proxy env vars live. Your actual **web app** runs as a separate
WSGI process that does NOT source that file, so it has no proxy configured
at all even though the console does — that's exactly the
`ProxyError`/`Tunnel connection failed: 503` you saw, and why it looks like
"nothing's wrong on Telegram's side" (there isn't).

Fixed: added Admin → Settings → **Network / Outbound Proxy** — set your
proxy URL there (PythonAnywhere's documented one is
`http://proxy.server:3128`, but check their Internet Access help page for
your plan) and every bot request (Telegram/WhatsApp/Facebook/Instagram)
will use it directly, regardless of how the web process was started. This
likely applies to other outbound calls too (URL downloader, etc.) if your
plan needs a proxy for those as well.

## 3. Database Backups (Admin → System Health)
- **Run Backup Now** — instant backup, downloadable from a list right there
- **Auto Backup** — toggle on, set "run every N days" (1=daily, 7=weekly,
  30=monthly, or literally any number including a specific day count you
  want), and it tracks last-run itself
- Uses direct SQLite file copy (byte-perfect) since that's this project's
  default DB; falls back to a JSON table dump for Postgres/MySQL
- Same "needs an external nudge" pattern as reminders — the page explains
  exactly how to set up a PythonAnywhere Scheduled Task for it, with the
  URL to use

## 4. Cloudinary storage (Admin → Settings → Media Storage)
Toggle between Local Storage and Cloudinary, with Cloud Name/API Key/API
Secret fields. Every upload path in the app (Media Library page AND the
media-picker widget used across every admin form) now goes through one
shared storage function, so switching the toggle actually takes effect
everywhere, not just in one place. Delete also cleans up the right backend.

**Needs `pip install cloudinary`** on your server (added to
requirements.txt in this zip) — run that before switching the toggle on.
Get your keys free at cloudinary.com/console.

## Explanations (no code change needed, just clearing these up)

**Social Bots vs. Automation** — Social Bots (Admin → Social Bots) is the
messaging layer: connects an actual WhatsApp/Telegram/Facebook/Instagram
account and handles the conversation (auto-reply, product cards, human
takeover). Automation (Admin → Automation) is the "if this happens, do
these things" engine — it doesn't own any channel itself, but a bot
message is one of the triggers it can react to, and sending a channel
reply is one of the actions it can take. Think of Social Bots as the
phone line, Automation as the switchboard that can also plug into email,
webhooks, Slack, Zapier, etc. off the exact same events.

**Reminders — will you get a message on your phone?** Not by default, no.
Two things happen today: (1) an in-app toast while you're logged into
admin, and (2) an email via the same cron pattern as backups. Neither is a
push notification or SMS to your phone. If you want an actual phone alert,
the realistic options are: email-to-SMS via your carrier's gateway address
(free but carrier-dependent and a bit unreliable), or a push service like
Pushover/ntfy (small one-time setup, then real phone notifications) — say
which one you want and I'll wire it in.

## Still queued (large, separate builds — not attempted this batch)
- Meeting/call scheduling with customers (a real booking system — availability, calendar sync, confirmations)
- Multi-tenant bot delivery: provisioning a bot/automation setup per client, tied into your existing Client Projects + Invoices so what you charge for it shows up in Financials
- Full "how to get every API key" walkthrough written into the Site Guide (Telegram, WhatsApp, Facebook, Instagram, Stripe/Paystack/Flutterwave/PayPal, crypto wallets, Cloudinary, SMTP/Resend — all of them, step by step)
- Page speed — I checked the existing check (measures real server response time honestly, links to Google PageSpeed Insights for full metrics) and couldn't find what's broken without seeing it fail. Send a screenshot of what you're seeing there and I'll fix the actual issue.
