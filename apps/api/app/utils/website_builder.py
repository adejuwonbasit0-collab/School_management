"""Generates and iteratively edits multi-file (HTML/CSS/JS) websites from a
text prompt — the engine behind Admin -> Website Builder.

Rebuilt around three complaints that made the old version unusable:

1. "It only ever produces one file" -- the AI is now asked for three
   clearly-delimited sections (HTML/CSS/JS) instead of one HTML blob with
   everything embedded in <style>/<script> tags, and the result is stored
   and downloadable as real separate files. Still no bundler/build step
   (this is a Flask app, not a Node toolchain) so "multiple programming
   languages" means real, separate, framework-idiomatic HTML/CSS/JS per
   page today -- not a compiled React/Vue/Next.js project. That's a much
   bigger architecture change (needs a build pipeline this server doesn't
   have) and isn't part of this pass.
2. "It can't continue a conversation" -- generate_site() now accepts
   chat_history and, in edit mode, the CURRENT html/css/js, so a follow-up
   prompt refines the existing site instead of the model starting from
   nothing with no memory of what it already built.
3. "It puts a second dashboard/admin chrome outside the one I asked for,
   uses generic hero/testimonial sections even for app UIs, and drops in
   random unrelated stock photos" -- the system prompt now branches on
   what's actually being described instead of always injecting a
   marketing-homepage skeleton, and every image is required to come from
   Pollinations with a prompt describing what's actually in that spot on
   the page (no more picsum.photos random photography).

Two generation paths, same as the rest of this batch's integrations:
1. External Website Builder API (optional, admin-configurable) -- used
   automatically if configured. Only really useful for single-file HTML
   output today (see _generate_via_external_api), so multi-file/edit mode
   always uses this site's own AI provider.
2. This site's own already-configured AI provider (Anthropic/Gemini/etc.)
   -- generates real, separate HTML+CSS+JS directly.
"""
import re
import requests as _requests
from app.utils.settings import get_setting

_SECTION_RE = re.compile(
    r"===HTML===\s*(.*?)\s*===CSS===\s*(.*?)\s*===JS===\s*(.*?)\s*(?:===END===\s*)?$",
    re.DOTALL,
)

_BASE_RULES = """You build real, production-quality websites and web apps from a
description, and you edit them on follow-up requests without throwing away
what already exists.

OUTPUT FORMAT -- always exactly this, nothing before or after:
===HTML===
<the full HTML document, no <style> or <script> content inline -- link
style.css and script.js instead: <link rel="stylesheet" href="style.css">
in <head>, <script src="script.js"></script> before </body>>
===CSS===
<the full contents of style.css>
===JS===
<the full contents of script.js -- empty is fine if nothing needs it>
===END===

CONTENT TYPE -- read the request and pick the right shape, don't force one
template onto everything:
- Marketing/landing/portfolio/brochure site -> hero, sections, footer,
  real copy for what's actually described (not generic lorem-style filler).
- Application, dashboard, admin panel, internal tool, or anything the user
  describes as having pages/views/data/CRUD -> build the actual interface:
  ONE persistent shell (one sidebar OR one topbar, never both stacked
  awkwardly, never a second nested sidebar/topbar inside the main content
  area), real-looking tables/cards/forms for the data described, and NO
  marketing sections (no hero banner, no testimonials, no "About Us") --
  those don't belong in an app UI and are the #1 reason generated
  dashboards look broken.
- If the request mixes both (e.g. "a SaaS site with a public homepage AND
  an admin dashboard"), treat them as genuinely separate pages/views with
  their own shells -- do not merge dashboard chrome into the marketing
  page's layout or vice versa.

IMAGES -- every image must be an AI-generated Pollinations URL, never a
stock-photo or placeholder service:
  https://image.pollinations.ai/prompt/<URL-ENCODED SPECIFIC DESCRIPTION>?width=W&height=H&nologo=true
The description inside the URL must describe exactly what that image is
depicting in context (e.g. a hero image for a bakery site gets a prompt
like "artisan sourdough bread loaves on a rustic wooden table, warm
natural light, professional food photography" -- not "hero image" and
never a generic/unrelated scene). Never use picsum.photos or any random
placeholder-image service -- those return photos with no relation to the
content, which looks broken.

DESIGN QUALITY: real color palette (not just black/white/gray), readable
type scale, generous spacing, mobile-responsive layout, subtle motion
where it helps (not gratuitous). Realistic, specific copy -- not "Lorem
ipsum" or "Company Name" placeholders.

FORMS: any <form> meant to collect visitor info (contact, signup, order,
booking, etc.) must have data-collect="true" and a name attribute on every
field, and must NOT have a real action/method -- a small script this
platform injects automatically will handle submission and storage, so
just build the form markup normally without wiring its submit handler
yourself.

INTERACTIVE BUTTONS: any button that implies an action -- "Complete Sale",
"Buy Now", "Save", "Add to Cart", "Delete", "Approve", toggle switches,
etc. -- must actually DO something in script.js when clicked: at minimum,
give real visible feedback (disable itself, show a confirmation message,
update on-page state/counters, add/remove a row from a list already
rendered on the page). Never leave a button that reads as actionable with
no click handler at all -- a dead button that visibly does nothing when
clicked is a broken page, not a finished one. This applies especially to
admin/dashboard-style pages with tables of records and action buttons per
row (Approve/Reject/Delete/Complete) -- those need real local JS behavior
against whatever mock data the page renders, not just static markup.

DATA BACKEND -- use this ONLY when the site you're building genuinely
needs data that persists across page loads and visits: e-commerce
(products, cart, orders), bookings/reservations, listings, a dashboard
that manages real records, or anything else where "add/edit/delete a
thing and see it again later" is actually part of what was asked for. Do
NOT reach for this on an ordinary marketing site, portfolio, landing
page, or anything where local page state (JS variables) is enough -- most
sites do not need this, and adding it where it isn't needed makes a
simple site unnecessarily complicated. When it IS needed:
  - Each named collection lives at:
    GET    /dashboard/sites/{slug}/data/{collection}
    POST   /dashboard/sites/{slug}/data/{collection}
    GET    /dashboard/sites/{slug}/data/{collection}/{id}
    PUT    /dashboard/sites/{slug}/data/{collection}/{id}
    DELETE /dashboard/sites/{slug}/data/{collection}/{id}
    (the actual {slug} value is injected for you -- see below)
  - POST/PUT bodies are a plain JSON object of whatever fields make sense
    (e.g. a product: {"name":"...", "price":1999, "image":"..."}); the
    server assigns "id" and "created_at"/"updated_at" automatically.
  - GET on the collection returns {"items":[...], "count": N}.
  - Use plain names for collections: "products", "orders", "bookings" --
    not one-off names per request.
  - Products/listings you're seeding as part of building the page should
    be created once (e.g. on first load, check if the collection is
    empty via GET, and if so POST the initial catalog) -- don't reseed
    on every page load.
  - For anything resembling a purchase/checkout: create an "orders" item
    on submit with the order details and a status field (e.g.
    "status": "pending_payment"). Do NOT fabricate a working payment
    charge, a fake Stripe/Paystack call, or pretend a card was charged --
    there is no real payment gateway wired in yet. Show a clear, honest
    message like "Order received -- payment integration coming soon" or
    similar instead of simulating a successful payment.
  - The actual site slug is available in JS as `window.__SITE_SLUG__`
    (injected automatically) -- build data endpoint URLs from that, e.g.
    `/dashboard/sites/${window.__SITE_SLUG__}/data/products`, never
    hard-code a slug."""

_CREATE_SYSTEM_PROMPT = _BASE_RULES + """

You are creating a NEW page from scratch based on the user's description."""

_EDIT_SYSTEM_PROMPT = _BASE_RULES + """

You are EDITING an existing page, not starting over. The user's current
HTML/CSS/JS is provided below, followed by what they want changed. Keep
everything that isn't part of the request exactly as it is -- same content,
same sections, same layout -- and change only what was asked for. This
includes images: leave existing image URLs untouched UNLESS the request is
about the images themselves (wrong/unrelated image, "fix the pictures",
"use a matching image", asking for different visuals, etc.) or the request
changes what a section is about (e.g. changing "Car Buying" copy to be
about something the current image no longer matches) -- in either of those
cases, replace that image with a new Pollinations URL whose prompt actually
describes the (possibly new) surrounding content, per the IMAGES rule
above. Never leave an image that doesn't match what the section is now
about just because "keep unrelated things the same" would suggest it.
Always output the FULL updated HTML/CSS/JS in the required format, not a
diff."""


def website_builder_configured():
    return bool((get_setting("website_builder_api_key") or "").strip() and (get_setting("website_builder_base_url") or "").strip())


def _generate_via_external_api(prompt):
    """Legacy single-file path for an admin-configured external website
    builder API. Left as-is for whichever "free website builder AI" the
    admin might have signed up with -- those APIs speak single-HTML-blob,
    not this build's HTML/CSS/JS split, so this is only used as a
    fallback source for brand-new single-page sites, never for edits."""
    api_key = (get_setting("website_builder_api_key") or "").strip()
    base_url = (get_setting("website_builder_base_url") or "").strip().rstrip("/")
    path = (get_setting("website_builder_api_path") or "/generate").strip()
    if not path.startswith("/"):
        path = "/" + path
    prompt_field = (get_setting("website_builder_prompt_field") or "prompt").strip() or "prompt"
    response_field = (get_setting("website_builder_response_field") or "html").strip() or "html"

    url = base_url + path
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={prompt_field: prompt},
            timeout=90,
        )
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach the website builder API at {url}: {e}"
    if resp.status_code >= 400:
        return None, f"Website builder API returned HTTP {resp.status_code}: {resp.text[:500]}"
    try:
        data = resp.json()
    except ValueError:
        return None, f"Website builder API's response wasn't JSON: {resp.text[:500]}"
    if isinstance(data, dict) and response_field in data:
        return data[response_field], None
    return None, (f"Got a 200 but couldn't find a '{response_field}' field in the response. "
                   f"Raw response so you can find the right field name: {str(data)[:500]}")


def _parse_sections(text):
    """Splits the model's ===HTML===/===CSS===/===JS=== response into a
    dict. Falls back to treating the whole thing as HTML (stripping any
    markdown fences) if the model didn't follow the format, so a single
    bad response never produces a fully broken page."""
    text = (text or "").strip()
    m = _SECTION_RE.search(text)
    if m:
        html, css, js = (g.strip() for g in m.groups())
        html = re.sub(r"^```[a-zA-Z]*\n?|```$", "", html).strip()
        css = re.sub(r"^```[a-zA-Z]*\n?|```$", "", css).strip()
        js = re.sub(r"^```[a-zA-Z]*\n?|```$", "", js).strip()
        return {"html": html, "css": css, "js": js}
    # Fallback: no section markers found -- treat as raw HTML.
    html = text
    if html.startswith("```"):
        html = html.split("\n", 1)[1] if "\n" in html else html
        if html.rstrip().endswith("```"):
            html = html.rstrip()[:-3]
    return {"html": html.strip(), "css": "", "js": ""}


def _extract_shared_chrome(html, css):
    """Pulls the <header>/<nav> and <footer> blocks plus any :root CSS
    custom properties out of a generated page, so later pages on the same
    site can be told to reuse them exactly instead of each page
    reinventing its own nav/footer/colors from scratch -- which is why
    pages on the same site used to look like they belonged to different
    sites. Best-effort regex extraction, not a real parser; if a page
    doesn't use <header>/<footer> tags or :root vars, this just returns
    empty strings and later pages fall back to matching by description
    only, same as before."""
    header_m = re.search(r"<header\b.*?</header>", html, re.DOTALL | re.I)
    nav_m = None if header_m else re.search(r"<nav\b.*?</nav>", html, re.DOTALL | re.I)
    footer_m = re.search(r"<footer\b.*?</footer>", html, re.DOTALL | re.I)
    root_vars_m = re.search(r":root\s*\{[^}]*\}", css, re.DOTALL | re.I)
    font_m = re.search(r"font-family\s*:\s*([^;]+);", css, re.I)
    return {
        "header": (header_m or nav_m).group(0).strip() if (header_m or nav_m) else "",
        "footer": footer_m.group(0).strip() if footer_m else "",
        "css_vars": root_vars_m.group(0).strip() if root_vars_m else "",
        "font_family": font_m.group(1).strip() if font_m else "",
    }


def _build_context_note(other_pages, page_name, site_chrome=None):
    """Tells the model what other pages already exist on this site so a
    newly generated page shares real, working nav links to them instead
    of each page being an island with no way to get to the others -- and,
    when available, hands over the site's established header/footer/CSS
    variables/font so this page reuses them exactly instead of the AI
    re-deciding the whole design per page, which is why pages on the same
    site used to look inconsistent with each other."""
    note = ""
    if other_pages:
        names = [p.get("name") for p in other_pages if p.get("name") and p.get("name") != page_name]
        if names:
            note += (f"\n\nThis site already has these other pages, in this order: {', '.join(names)}. "
                      f"Include a working navigation menu linking to each of them by filename "
                      f"(e.g. \"{names[0].lower().replace(' ', '_')}.html\") in addition to this page.")

    if site_chrome and any(site_chrome.values()):
        note += "\n\nTHIS SITE'S ESTABLISHED DESIGN -- reuse exactly, don't reinvent it for this page:"
        if site_chrome.get("header"):
            note += f"\n\nHeader/nav markup to reuse verbatim (only update which link is marked active for this page):\n{site_chrome['header']}"
        if site_chrome.get("footer"):
            note += f"\n\nFooter markup to reuse verbatim:\n{site_chrome['footer']}"
        if site_chrome.get("css_vars"):
            note += f"\n\nCSS custom properties already established -- reuse these exact values, don't invent a new palette:\n{site_chrome['css_vars']}"
        if site_chrome.get("font_family"):
            note += f"\n\nFont family already established for this site: {site_chrome['font_family']} -- use the same one."
    return note


def _summarize_turn(files, mode, prompt):
    """A short, honest, human-readable description of what this turn did
    -- generated from the actual HTML structure (section/image/form
    counts), not invented. This is what populates the chat sidebar and
    what gets stored in chat_history instead of the raw HTML/CSS/JS, so
    a long editing session doesn't compound into an ever-growing wall of
    full-page source re-sent to the AI on every single follow-up (that
    was a real bug in the first version of this: each edit re-embedded
    the previous turn's entire generated HTML/CSS/JS INTO chat_history,
    so turn 3 was re-sending turn 1 and turn 2's full page source too --
    a likely contributor to burning through provider token/rate quotas
    fast, which is very plausibly what surfaced as a Groq billing error)."""
    if mode == "edit":
        return f"Updated the page — {prompt.strip()[:180]}"
    html = files.get("html", "")
    sections = len(re.findall(r"<section\b", html, re.I))
    imgs = len(re.findall(r"<img\b", html, re.I))
    forms = len(re.findall(r"<form\b", html, re.I))
    parts = []
    if sections:
        parts.append(f"{sections} section{'s' if sections != 1 else ''}")
    if imgs:
        parts.append(f"{imgs} image{'s' if imgs != 1 else ''}")
    if forms:
        parts.append(f"{forms} form{'s' if forms != 1 else ''}")
    detail = f" — {', '.join(parts)}" if parts else ""
    return f"Built the page from your description{detail}."


FORM_CAPTURE_MARKER = "// -- Auto-injected by Website Builder: captures data-collect forms --"


def form_capture_snippet(website_slug):
    """Appended to every generated page's JS so any form the AI marked
    data-collect="true" actually posts somewhere real, instead of the
    Properties panel's "Form Submissions" list staying empty forever
    because nothing wired the two together. Posts by slug (works the
    moment a site is first generated) rather than by subdomain (which
    only exists after Publish), so submissions get captured in the
    preview/draft stage too, not just once live.

    Lives here (not in the route) so strip_form_capture_snippet() below
    can share the same marker string as the one source of truth -- it's
    what lets edit-mode context strip this back out before re-sending
    "current JS" to the AI (see generate_site_stream), instead of paying
    for ~1KB of our own boilerplate as "content" on every single edit."""
    return f"""
{FORM_CAPTURE_MARKER}
document.addEventListener('submit', function(e) {{
  var form = e.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (form.getAttribute('data-collect') !== 'true') return;
  e.preventDefault();
  var fields = {{}};
  new FormData(form).forEach(function(v, k) {{ fields[k] = v; }});
  fetch((window.location.origin || '') + '/dashboard/sites/submit-form-by-slug/{website_slug}', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ fields: fields }})
  }}).then(function(r) {{ return r.json(); }}).then(function() {{
    var note = document.createElement('p');
    note.textContent = 'Thanks! Your submission was received.';
    note.style.cssText = 'margin-top:12px;font-weight:600;color:#1DB954';
    form.reset();
    form.parentNode.insertBefore(note, form.nextSibling);
  }}).catch(function() {{ alert('Sorry, something went wrong submitting the form.'); }});
}});
"""


def strip_form_capture_snippet(js):
    """Removes our own injected snippet before using "current JS" as edit
    context, so every edit turn isn't spending tokens re-reading ~1KB of
    OUR boilerplate back to the AI. Re-injected fresh after generation by
    the route, so this is purely about what gets sent as context."""
    js = js or ""
    idx = js.find(FORM_CAPTURE_MARKER)
    return js[:idx].rstrip() if idx != -1 else js


def _extract_inline_assets(files):
    """Guarantees the HTML/CSS/JS split is real, not just requested.

    The system prompt tells the AI not to inline <style>/<script>, but
    that's a request, not a guarantee -- weaker/faster models routinely
    ignore formatting instructions like this under load, and any page
    generated before this split existed only ever had html with
    everything embedded. Either way, trusting the prompt alone meant the
    css/js "files" could come back genuinely empty while the page is
    visibly styled -- exactly the "you put an empty style.css there"
    complaint. This pulls any inline <style>/<script data-collect-free>
    blocks OUT of the html and INTO css/js for real, so the file tree
    reflects what's actually powering the page, not what was asked for."""
    html = files.get("html") or ""
    css = (files.get("css") or "").strip()
    js = (files.get("js") or "").strip()

    style_blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.DOTALL | re.I)
    if style_blocks:
        extracted = "\n\n".join(b.strip() for b in style_blocks if b.strip())
        css = (css + "\n\n" + extracted).strip() if css else extracted
        html = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.I)
        if "</head>" in html and '<link rel="stylesheet" href="style.css">' not in html:
            html = html.replace("</head>", '<link rel="stylesheet" href="style.css"></head>', 1)

    # Only inline <script> blocks with no src= are real embedded code to
    # extract -- a <script src="https://cdn...">, e.g. Tailwind's CDN
    # build, is a real external dependency and must stay put in the HTML.
    script_blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.DOTALL | re.I)
    if script_blocks:
        extracted = "\n\n".join(b.strip() for b in script_blocks if b.strip())
        js = (js + "\n\n" + extracted).strip() if js else extracted
        html = re.sub(r"<script(?![^>]*\bsrc=)[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
        if "</body>" in html and '<script src="script.js">' not in html:
            html = html.replace("</body>", '<script src="script.js"></script></body>', 1)

    return {"html": html, "css": css, "js": js}


def generate_site_stream(prompt, mode="create", current_files=None, other_pages=None,
                          page_name=None, chat_history=None, site_chrome=None):
    """Generator version of site generation: yields {"status": "..."} for
    each real pipeline stage as it's reached (not fabricated progress —
    these are the actual steps below, in the actual order they run), then
    a final {"done": True, "files", "history", "error", "source"} dict.
    The route wraps this directly into a server-sent-events stream so the
    UI can show what's actually happening instead of a spinner with no
    detail.

    chat_history: list of {"role","content"} dicts -- content is the
    PLAIN prompt text / a short summary (see _summarize_turn), not the
    full generated source, so history stays small and readable across a
    long editing session instead of re-sending the whole page's source
    on every follow-up.

    site_chrome: {"header","footer","css_vars","font_family"} extracted
    from this site's FIRST generated page (see _extract_shared_chrome) --
    passed to CREATE mode only, so a second/third/etc. page reuses the
    same header/footer/palette/font instead of each page on one site
    looking like it belongs to a different site.

    Final dict's "files" is {"html","css","js"} or None on error, and
    "source" is "external" or "own_ai".
    """
    from app.ai_tools.routes import _call_ai

    chat_history = list(chat_history or [])

    def build_user_turn(html_limit, css_limit, js_limit):
        if mode == "edit" and current_files:
            clean_js = strip_form_capture_snippet(current_files.get("js"))
            context = (
                "CURRENT HTML:\n" + (current_files.get("html") or "")[:html_limit] +
                "\n\nCURRENT CSS:\n" + (current_files.get("css") or "")[:css_limit] +
                "\n\nCURRENT JS:\n" + clean_js[:js_limit]
            )
            return _EDIT_SYSTEM_PROMPT, f"{context}\n\nREQUESTED CHANGE:\n{prompt}"
        return _CREATE_SYSTEM_PROMPT, prompt + _build_context_note(other_pages, page_name, site_chrome)

    if mode == "edit" and current_files:
        yield {"status": "Reading the current page so this builds on it, not over it"}
    else:
        yield {"status": "Preparing your request"}
    system_prompt, user_turn = build_user_turn(6000, 3000, 3000)

    if mode == "create" and not chat_history and website_builder_configured():
        yield {"status": "Sending your description to the configured Website Builder API"}
        html, err = _generate_via_external_api(user_turn)
        if not err:
            yield {"done": True, "files": {"html": html, "css": "", "js": ""},
                   "history": [], "error": None, "source": "external"}
            return
        # Fall through to this site's own AI rather than dead-ending.

    yield {"status": f"Sending your request to the AI ({'editing' if mode == 'edit' else 'creating'} \u201c{page_name or 'Home'}\u201d) — this can take 10–40 seconds"}
    messages = chat_history + [{"role": "user", "content": user_turn}]
    text, err = _call_ai(system_prompt, messages, max_tokens=8000)

    if err and ("too large" in err.lower() or "413" in err or "context_length" in err.lower() or "reduce" in err.lower()):
        # A real, honest cause for this: edit-mode context (the current
        # page's html/css/js) plus an 8000-token completion request can
        # exceed a free-tier provider's per-request token limit -- that's
        # what surfaces as "prompt too long"/"request too large", not a
        # length limit this app is imposing. Retry once with a much
        # smaller context/output budget rather than failing outright.
        yield {"status": "That request was too large for the AI provider's limit — retrying with a smaller context"}
        system_prompt, user_turn = build_user_turn(2000, 1000, 1000)
        messages = chat_history[-4:] + [{"role": "user", "content": user_turn}]
        text, err = _call_ai(system_prompt, messages, max_tokens=4000)

    if err:
        yield {"done": True, "files": None, "history": chat_history, "error": err, "source": None}
        return

    yield {"status": "Parsing the returned HTML, CSS and JavaScript"}
    files = _parse_sections(text)
    if "<html" not in files["html"].lower() and "<!doctype" not in files["html"].lower():
        yield {"done": True, "files": None, "history": chat_history,
               "error": "The AI didn't return a valid HTML document — try rephrasing the prompt or generating again.",
               "source": None}
        return

    yield {"status": "Splitting into real HTML/CSS/JS files"}
    files = _extract_inline_assets(files)

    yield {"status": "Saving the page"}
    summary = _summarize_turn(files, mode, prompt)
    updated_history = chat_history + [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": summary},
    ]
    # Cap turn count so a very long editing session doesn't grow forever --
    # entries are short (plain prompt + one-line summary) so this is a
    # generous cap, not the aggressive one a raw-content history would need.
    if len(updated_history) > 40:
        updated_history = updated_history[-40:]
    yield {"done": True, "files": files, "history": updated_history, "error": None, "source": "own_ai"}


def generate_site(prompt, mode="create", current_files=None, other_pages=None,
                   page_name=None, chat_history=None):
    """Synchronous wrapper around generate_site_stream() for callers that
    don't need live status (e.g. generate_website() below). Drains the
    generator and returns its final result.

    Returns (files, updated_chat_history, error, source).
    """
    result = None
    for event in generate_site_stream(prompt, mode=mode, current_files=current_files,
                                       other_pages=other_pages, page_name=page_name,
                                       chat_history=chat_history):
        if event.get("done"):
            result = event
    return result["files"], result["history"], result["error"], result["source"]


# -- Backward-compatible single-file wrapper (used by anything not yet
#    migrated to generate_site) -----------------------------------------
def generate_website(prompt):
    """Returns (html, error, source). HTML has CSS/JS inlined for
    call sites that only handle one blob."""
    files, _, err, source = generate_site(prompt, mode="create")
    if err:
        return None, err, None
    html = files["html"]
    if files.get("css"):
        html = html.replace("</head>", f"<style>{files['css']}</style></head>", 1) if "</head>" in html else html
    if files.get("js"):
        html = html.replace("</body>", f"<script>{files['js']}</script></body>", 1) if "</body>" in html else html
    return html, None, source
