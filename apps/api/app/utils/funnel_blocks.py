"""Drag-and-drop Block Builder for Sales Funnel pages.

A funnel page built in "blocks" mode stores a flat, ordered list of
blocks (FunnelPage.blocks) instead of raw HTML. Each block is:

    {"id": "b_xxxxx", "type": "heading", "data": {...fields...}}

`BLOCK_SCHEMAS` is the single source of truth for what a block of each
type can hold — the front-end reads it (via a template context var) to
generate the settings form for whichever block is selected, so adding a
new block type only means adding one entry here, not writing a bespoke
form by hand on the client.

`render_blocks_to_html()` turns that structured list into a real,
self-contained HTML page (Tailwind via CDN, matching the rest of the
platform's own UI), which is what actually gets saved to
FunnelPage.html_content and served to visitors — the blocks JSON is the
edit-time representation, html_content stays the single thing the
"serve funnel" route has to know how to render.
"""

import html as _html


# ── Schema: field types the generic settings form knows how to render ──
# text | textarea | url | number | color | select | list(subfields)
# `group` clusters fields into labeled sections in the Design tab UI.
DESIGN_SCHEMA = [
    # Color — solid or gradient background, plus text color
    {"key": "bg_type", "label": "Background Type", "type": "select", "options": ["solid", "gradient", "none"], "group": "Color"},
    {"key": "bg_color", "label": "Background Color", "type": "color", "group": "Color"},
    {"key": "gradient_from", "label": "Gradient Start", "type": "color", "group": "Color"},
    {"key": "gradient_to", "label": "Gradient End", "type": "color", "group": "Color"},
    {"key": "gradient_angle", "label": "Gradient Angle (deg)", "type": "number", "group": "Color"},
    {"key": "text_color", "label": "Text Color", "type": "color", "group": "Color"},

    # Typography
    {"key": "font_family", "label": "Font Family", "type": "select", "options": ["default", "serif", "mono", "rounded"], "group": "Typography"},
    {"key": "font_size", "label": "Font Size Scale", "type": "select", "options": ["sm", "default", "lg", "xl"], "group": "Typography"},
    {"key": "font_weight", "label": "Font Weight", "type": "select", "options": ["normal", "medium", "semibold", "bold", "extrabold"], "group": "Typography"},
    {"key": "line_height", "label": "Line Height", "type": "select", "options": ["tight", "normal", "relaxed"], "group": "Typography"},
    {"key": "letter_spacing", "label": "Letter Spacing", "type": "select", "options": ["tight", "normal", "wide", "widest"], "group": "Typography"},

    # Layout / Spacing / Alignment
    {"key": "align", "label": "Content Alignment", "type": "select", "options": ["left", "center", "right"], "group": "Layout"},
    {"key": "container_width", "label": "Container Width", "type": "select", "options": ["narrow", "medium", "wide", "full"], "group": "Layout"},
    {"key": "padding_y", "label": "Vertical Padding (px)", "type": "number", "group": "Spacing"},
    {"key": "padding_x", "label": "Horizontal Padding (px)", "type": "number", "group": "Spacing"},
    {"key": "margin_top", "label": "Margin Top (px)", "type": "number", "group": "Spacing"},
    {"key": "margin_bottom", "label": "Margin Bottom (px)", "type": "number", "group": "Spacing"},
    {"key": "border_radius", "label": "Corner Radius (px)", "type": "number", "group": "Spacing"},

    # Motion
    {"key": "animation", "label": "Entrance Animation", "type": "select",
     "options": ["none", "fade-up", "fade-in", "zoom-in", "slide-left", "slide-right"], "group": "Animation"},
    {"key": "animation_speed", "label": "Animation Speed", "type": "select", "options": ["fast", "normal", "slow"], "group": "Animation"},
]

# Legacy preset kept for backward compatibility with pages saved before the
# padding_y/padding_x numeric controls existed.
_LEGACY_PADDING_PRESETS = {"compact": 32, "comfortable": 64, "spacious": 110}


BLOCK_SCHEMAS = {
    "heading": {
        "label": "Heading", "icon": "heading",
        "fields": [
            {"key": "text", "label": "Text", "type": "text"},
            {"key": "level", "label": "Size", "type": "select", "options": ["h1", "h2", "h3"]},
            {"key": "align", "label": "Align", "type": "select", "options": ["left", "center", "right"]},
        ],
        "defaults": {"text": "Your Headline Here", "level": "h1", "align": "center"},
    },
    "paragraph": {
        "label": "Paragraph", "icon": "align-left",
        "fields": [
            {"key": "text", "label": "Text", "type": "textarea"},
            {"key": "align", "label": "Align", "type": "select", "options": ["left", "center", "right"]},
        ],
        "defaults": {"text": "Write a short description here.", "align": "center"},
    },
    "image": {
        "label": "Image", "icon": "image",
        "fields": [
            {"key": "src", "label": "Image URL", "type": "url"},
            {"key": "alt", "label": "Alt text", "type": "text"},
        ],
        "defaults": {"src": "https://picsum.photos/1200/600", "alt": ""},
    },
    "button": {
        "label": "Button", "icon": "mouse-pointer-click",
        "fields": [
            {"key": "text", "label": "Button Text", "type": "text"},
            {"key": "url", "label": "Link URL (leave blank if using Nav below)", "type": "url"},
            {"key": "nav", "label": "Funnel Nav", "type": "select", "options": ["none", "next", "accept", "decline"]},
            {"key": "style", "label": "Style", "type": "select", "options": ["primary", "secondary", "custom"]},
            {"key": "align", "label": "Align", "type": "select", "options": ["left", "center", "right"]},
            {"key": "button_color", "label": "Button Color (when Style = custom)", "type": "color"},
            {"key": "text_color", "label": "Text Color (when Style = custom)", "type": "color"},
            {"key": "shape", "label": "Shape", "type": "select", "options": ["pill", "rounded", "square"]},
            {"key": "size", "label": "Size", "type": "select", "options": ["small", "medium", "large"]},
        ],
        "defaults": {"text": "Get Started", "url": "", "nav": "next", "style": "primary", "align": "center",
                     "button_color": "#111111", "text_color": "#ffffff", "shape": "pill", "size": "medium"},
    },
    "spacer": {
        "label": "Spacer", "icon": "move-vertical",
        "fields": [{"key": "height", "label": "Height (px)", "type": "number"}],
        "defaults": {"height": 40},
    },
    "video": {
        "label": "Video Embed", "icon": "play-circle",
        "fields": [{"key": "url", "label": "YouTube/Vimeo embed URL", "type": "url"}],
        "defaults": {"url": ""},
    },
    "countdown": {
        "label": "Countdown Timer", "icon": "timer",
        "fields": [
            {"key": "end_date", "label": "End Date/Time (ISO, e.g. 2026-12-31T23:59)", "type": "text"},
            {"key": "label", "label": "Label", "type": "text"},
        ],
        "defaults": {"end_date": "", "label": "Offer ends in:"},
    },
    "testimonial": {
        "label": "Testimonials", "icon": "quote",
        "fields": [
            {"key": "items", "label": "Testimonials", "type": "list", "subfields": [
                {"key": "quote", "label": "Quote", "type": "textarea"},
                {"key": "name", "label": "Name", "type": "text"},
                {"key": "role", "label": "Role / Company", "type": "text"},
            ]},
        ],
        "defaults": {"items": [{"quote": "This changed everything for us.", "name": "Jane Doe", "role": "CEO, Acme"}]},
    },
    "pricing_table": {
        "label": "Pricing Table", "icon": "credit-card",
        "fields": [
            {"key": "plans", "label": "Plans", "type": "list", "subfields": [
                {"key": "name", "label": "Plan Name", "type": "text"},
                {"key": "price", "label": "Price", "type": "text"},
                {"key": "features", "label": "Features (one per line)", "type": "textarea"},
                {"key": "cta_text", "label": "Button Text", "type": "text"},
                {"key": "highlighted", "label": "Highlight this plan", "type": "select", "options": ["no", "yes"]},
            ]},
        ],
        "defaults": {"plans": [
            {"name": "Starter", "price": "$29/mo", "features": "Feature one\nFeature two", "cta_text": "Choose Plan", "highlighted": "no"},
            {"name": "Pro", "price": "$79/mo", "features": "Everything in Starter\nFeature three\nFeature four", "cta_text": "Choose Plan", "highlighted": "yes"},
        ]},
    },
    "faq": {
        "label": "FAQ", "icon": "help-circle",
        "fields": [
            {"key": "items", "label": "Questions", "type": "list", "subfields": [
                {"key": "q", "label": "Question", "type": "text"},
                {"key": "a", "label": "Answer", "type": "textarea"},
            ]},
        ],
        "defaults": {"items": [{"q": "How does this work?", "a": "Explain it here."}]},
    },
    "accordion": {
        "label": "Accordion", "icon": "chevrons-down-up",
        "fields": [
            {"key": "items", "label": "Sections", "type": "list", "subfields": [
                {"key": "title", "label": "Title", "type": "text"},
                {"key": "content", "label": "Content", "type": "textarea"},
            ]},
        ],
        "defaults": {"items": [{"title": "Section One", "content": "Content for this section."}]},
    },
    "tabs": {
        "label": "Tabs", "icon": "layout-panel-top",
        "fields": [
            {"key": "items", "label": "Tabs", "type": "list", "subfields": [
                {"key": "label", "label": "Tab Label", "type": "text"},
                {"key": "content", "label": "Tab Content", "type": "textarea"},
            ]},
        ],
        "defaults": {"items": [
            {"label": "Overview", "content": "Overview content."},
            {"label": "Details", "content": "Details content."},
        ]},
    },
    "progress_bar": {
        "label": "Progress Bar", "icon": "gauge",
        "fields": [
            {"key": "label", "label": "Label", "type": "text"},
            {"key": "percent", "label": "Percent (0-100)", "type": "number"},
            {"key": "color", "label": "Bar Color", "type": "color"},
        ],
        "defaults": {"label": "Spots remaining", "percent": 80, "color": "#000000"},
    },
    "icon": {
        "label": "Icon", "icon": "sparkles",
        "fields": [
            {"key": "name", "label": "Lucide Icon Name (e.g. star, shield-check, zap)", "type": "text"},
            {"key": "caption", "label": "Caption", "type": "text"},
            {"key": "color", "label": "Icon Color", "type": "color"},
        ],
        "defaults": {"name": "star", "caption": "", "color": "#000000"},
    },
    "success_animation": {
        "label": "Animated Success (checkmark + confetti)", "icon": "party-popper",
        "fields": [
            {"key": "heading", "label": "Heading", "type": "text"},
            {"key": "color", "label": "Accent Color", "type": "color"},
        ],
        "defaults": {"heading": "Payment Successful!", "color": "#16a34a"},
    },
    "social_links": {
        "label": "Social Links", "icon": "share-2",
        "fields": [
            {"key": "items", "label": "Links", "type": "list", "subfields": [
                {"key": "platform", "label": "Platform (facebook/twitter/instagram/linkedin/youtube/tiktok/whatsapp)", "type": "text"},
                {"key": "url", "label": "URL", "type": "url"},
            ]},
        ],
        "defaults": {"items": [{"platform": "instagram", "url": ""}]},
    },
    "custom_html": {
        "label": "Custom HTML / Code", "icon": "code-2",
        "fields": [
            {"key": "html", "label": "Raw HTML/CSS/JS", "type": "textarea"},
        ],
        "defaults": {"html": "<!-- Your custom HTML/CSS/JS goes here -->"},
    },
    "map_embed": {
        "label": "Map Embed", "icon": "map-pin",
        "fields": [
            {"key": "embed_url", "label": "Google Maps Embed URL (Maps → Share → Embed a map → copy the src=\"...\" URL)", "type": "url"},
        ],
        "defaults": {"embed_url": ""},
    },
    "rating": {
        "label": "Star Rating", "icon": "star",
        "fields": [
            {"key": "score", "label": "Score (0-5)", "type": "number"},
            {"key": "caption", "label": "Caption", "type": "text"},
        ],
        "defaults": {"score": 5, "caption": "Rated 5/5 by our customers"},
    },
    "logo_cloud": {
        "label": "Logo Cloud / Badges", "icon": "badge-check",
        "fields": [
            {"key": "heading", "label": "Heading", "type": "text"},
            {"key": "items", "label": "Logos", "type": "list", "subfields": [
                {"key": "name", "label": "Name (shown as text)", "type": "text"},
                {"key": "image", "label": "Logo Image URL (optional)", "type": "url"},
            ]},
        ],
        "defaults": {"heading": "As seen in", "items": [{"name": "Brand One", "image": ""}, {"name": "Brand Two", "image": ""}]},
    },
    "comparison_table": {
        "label": "Comparison Table", "icon": "table-2",
        "fields": [
            {"key": "columns", "label": "Column Headers (comma-separated)", "type": "text"},
            {"key": "rows", "label": "Rows", "type": "list", "subfields": [
                {"key": "feature", "label": "Feature", "type": "text"},
                {"key": "values", "label": "Values (comma-separated, matching columns)", "type": "text"},
            ]},
        ],
        "defaults": {"columns": "Basic, Pro", "rows": [{"feature": "Users", "values": "1, Unlimited"}, {"feature": "Support", "values": "Email, Priority"}]},
    },
    "divider": {
        "label": "Divider", "icon": "minus",
        "fields": [
            {"key": "style", "label": "Style (line / dots / space)", "type": "text"},
        ],
        "defaults": {"style": "line"},
    },
    "container": {
        "label": "Container / Banner", "icon": "square",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow (small text above heading)", "type": "text"},
            {"key": "heading", "label": "Heading", "type": "text"},
            {"key": "text", "label": "Body Text", "type": "textarea"},
            {"key": "button_text", "label": "Button Text (optional)", "type": "text"},
            {"key": "button_url", "label": "Button URL", "type": "url"},
            {"key": "button_nav", "label": "Funnel Nav", "type": "select", "options": ["none", "next", "accept", "decline"]},
            {"key": "bg_image", "label": "Background Image URL (optional)", "type": "url"},
            {"key": "min_height", "label": "Min Height (px, 0 = auto)", "type": "number"},
            {"key": "content_align", "label": "Content Align", "type": "select", "options": ["left", "center", "right"]},
        ],
        "defaults": {"eyebrow": "", "heading": "Section Heading", "text": "", "button_text": "", "button_url": "",
                     "button_nav": "none", "bg_image": "", "min_height": 0, "content_align": "center"},
    },
    "hero_split": {
        "label": "Hero (Split / Text + Image)", "icon": "columns-2",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow / Badge Text", "type": "text"},
            {"key": "heading", "label": "Heading", "type": "text"},
            {"key": "text", "label": "Description", "type": "textarea"},
            {"key": "stat_line", "label": "Small proof line (e.g. '120,000+ students, 4.5/5 rating')", "type": "text"},
            {"key": "button_text", "label": "Button Text", "type": "text"},
            {"key": "button_url", "label": "Button URL", "type": "url"},
            {"key": "button_nav", "label": "Funnel Nav", "type": "select", "options": ["none", "next", "accept", "decline"]},
            {"key": "media_type", "label": "Media Type", "type": "select", "options": ["image", "video"]},
            {"key": "image", "label": "Image URL", "type": "url"},
            {"key": "video_url", "label": "Video Embed URL (if Media Type = video)", "type": "url"},
            {"key": "media_side", "label": "Media Side", "type": "select", "options": ["right", "left"]},
        ],
        "defaults": {"eyebrow": "", "heading": "A Bold Promise, Backed By Proof", "text": "One clear sentence about the transformation this delivers.",
                     "stat_line": "", "button_text": "Get Started", "button_url": "", "button_nav": "next",
                     "media_type": "image", "image": "https://picsum.photos/id/180/900/700", "video_url": "", "media_side": "right"},
    },
    "video_section": {
        "label": "Video + Text Section", "icon": "clapperboard",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow", "type": "text"},
            {"key": "heading", "label": "Heading", "type": "text"},
            {"key": "text", "label": "Description", "type": "textarea"},
            {"key": "video_url", "label": "Video Embed URL", "type": "url"},
            {"key": "button_text", "label": "Button Text (optional)", "type": "text"},
            {"key": "button_url", "label": "Button URL", "type": "url"},
            {"key": "media_side", "label": "Video Side", "type": "select", "options": ["right", "left"]},
        ],
        "defaults": {"eyebrow": "", "heading": "See It In Action", "text": "A short line about what they're about to watch.",
                     "video_url": "", "button_text": "", "button_url": "", "media_side": "right"},
    },
    "feature_grid": {
        "label": "Feature Grid (icon cards)", "icon": "grid-2x2",
        "fields": [
            {"key": "heading", "label": "Section Heading (optional)", "type": "text"},
            {"key": "columns", "label": "Columns", "type": "select", "options": ["2", "3", "4"]},
            {"key": "items", "label": "Features", "type": "list", "subfields": [
                {"key": "icon", "label": "Lucide Icon Name", "type": "text"},
                {"key": "title", "label": "Title", "type": "text"},
                {"key": "text", "label": "Description", "type": "textarea"},
            ]},
        ],
        "defaults": {"heading": "", "columns": "4", "items": [
            {"icon": "play-circle", "title": "Video Lessons", "text": "Bite-sized lessons you can go through at your own pace."},
            {"icon": "star", "title": "Premium Access", "text": "Everything unlocked the moment you join."},
            {"icon": "file-text", "title": "Supporting Materials", "text": "Guides and resources to back up every lesson."},
            {"icon": "message-circle", "title": "Community", "text": "A members-only space to ask questions and share wins."},
        ]},
    },
    "checklist": {
        "label": "Checklist", "icon": "list-checks",
        "fields": [
            {"key": "heading", "label": "Heading (optional)", "type": "text"},
            {"key": "items", "label": "Items", "type": "list", "subfields": [
                {"key": "text", "label": "Item Text", "type": "text"},
            ]},
            {"key": "check_color", "label": "Check Color", "type": "color"},
        ],
        "defaults": {"heading": "", "check_color": "#111111", "items": [
            {"text": "Punished your body five days a week…"},
            {"text": "Put your joints and ligaments on the line…"},
            {"text": "Spent a ton of energy managing your diet…"},
        ]},
    },
    "stat_bar": {
        "label": "Stat Bar", "icon": "trending-up",
        "fields": [
            {"key": "caption", "label": "Caption (e.g. 'Trusted by')", "type": "text"},
            {"key": "items", "label": "Stats", "type": "list", "subfields": [
                {"key": "number", "label": "Number", "type": "text"},
                {"key": "label", "label": "Label", "type": "text"},
            ]},
        ],
        "defaults": {"caption": "Trusted by", "items": [
            {"number": "126,000+", "label": "Companies"},
            {"number": "4.9/5", "label": "Average Rating"},
            {"number": "40+", "label": "Countries"},
        ]},
    },
    "announcement_bar": {
        "label": "Announcement Bar", "icon": "megaphone",
        "fields": [
            {"key": "text", "label": "Bar Text", "type": "text"},
            {"key": "button_text", "label": "Button Text (optional)", "type": "text"},
            {"key": "button_url", "label": "Button URL", "type": "url"},
            {"key": "bg_color", "label": "Bar Background Color", "type": "color"},
            {"key": "text_color", "label": "Bar Text Color", "type": "color"},
        ],
        "defaults": {"text": "Limited-time offer — ends soon.", "button_text": "Join Now", "button_url": "",
                     "bg_color": "#2D9CDB", "text_color": "#ffffff"},
    },
    "form": {
        "label": "Form (Lead Capture)", "icon": "clipboard-list",
        "fields": [
            {"key": "heading", "label": "Heading (optional)", "type": "text"},
            {"key": "fields", "label": "Fields", "type": "list", "subfields": [
                {"key": "key", "label": "Field Key (no spaces, e.g. email)", "type": "text"},
                {"key": "label", "label": "Field Label", "type": "text"},
                {"key": "field_type", "label": "Type (text / email / tel / textarea)", "type": "text"},
                {"key": "required", "label": "Required? (yes/no)", "type": "text"},
            ]},
            {"key": "submit_text", "label": "Submit Button Text", "type": "text"},
            {"key": "success_message", "label": "Message shown after submit", "type": "textarea"},
            {"key": "on_success_nav", "label": "After Submit, Go To", "type": "select", "options": ["stay", "next", "accept"]},
        ],
        "defaults": {
            "heading": "Get Instant Access",
            "fields": [
                {"key": "name", "label": "Your Name", "field_type": "text", "required": "no"},
                {"key": "email", "label": "Your Email", "field_type": "email", "required": "yes"},
            ],
            "submit_text": "Submit", "success_message": "Thanks! Check your email shortly.",
            "on_success_nav": "stay",
        },
    },
}

ALIGN_CLASS = {"left": "text-left", "center": "text-center", "right": "text-right"}


def _e(value):
    """Escape for safe HTML embedding."""
    return _html.escape(str(value or ""), quote=True)


def default_blocks_for_type(page_type):
    """A sensible starting set of blocks so a new page in Block mode
    isn't a blank canvas."""
    if page_type in ("upsell", "downsell"):
        return [
            {"id": "b1", "type": "heading", "data": {**BLOCK_SCHEMAS["heading"]["defaults"], "text": "Wait! One-Time Offer"}},
            {"id": "b2", "type": "paragraph", "data": BLOCK_SCHEMAS["paragraph"]["defaults"]},
            {"id": "b3", "type": "button", "data": {**BLOCK_SCHEMAS["button"]["defaults"], "text": "Yes, Add This!", "nav": "accept"}},
            {"id": "b4", "type": "button", "data": {**BLOCK_SCHEMAS["button"]["defaults"], "text": "No thanks", "nav": "decline", "style": "secondary"}},
        ]
    return [
        {"id": "b1", "type": "heading", "data": BLOCK_SCHEMAS["heading"]["defaults"]},
        {"id": "b2", "type": "paragraph", "data": BLOCK_SCHEMAS["paragraph"]["defaults"]},
        {"id": "b3", "type": "button", "data": BLOCK_SCHEMAS["button"]["defaults"]},
    ]


def _render_block(block, page_id=None):
    btype = block.get("type")
    data = block.get("data") or {}
    schema = BLOCK_SCHEMAS.get(btype)
    if not schema:
        return ""
    defaults = schema["defaults"]
    d = {**defaults, **data}

    if btype == "heading":
        tag = d["level"] if d["level"] in ("h1", "h2", "h3") else "h1"
        size = {"h1": "text-4xl md:text-5xl", "h2": "text-3xl md:text-4xl", "h3": "text-2xl md:text-3xl"}[tag]
        return f'<{tag} class="{size} font-extrabold {ALIGN_CLASS.get(d["align"], "text-center")} mb-4">{_e(d["text"])}</{tag}>'

    if btype == "paragraph":
        return f'<p class="text-lg text-gray-600 {ALIGN_CLASS.get(d["align"], "text-center")} max-w-2xl mx-auto mb-6">{_e(d["text"])}</p>'

    if btype == "image":
        return f'<div class="flex justify-center mb-6"><img src="{_e(d["src"])}" alt="{_e(d["alt"])}" class="rounded-2xl shadow-xl max-w-full h-auto"></div>'

    if btype == "button":
        shape_radius = {"pill": "9999px", "rounded": "12px", "square": "4px"}.get(d.get("shape", "pill"), "9999px")
        size_pad = {"small": "10px 20px", "medium": "14px 32px", "large": "18px 44px"}.get(d.get("size", "medium"), "14px 32px")
        size_text = {"small": "0.85rem", "medium": "1rem", "large": "1.15rem"}.get(d.get("size", "medium"), "1rem")
        if d.get("style") == "custom":
            btn_style = (f'background:{_e(d.get("button_color") or "#111111")}; '
                         f'color:{_e(d.get("text_color") or "#ffffff")}; ')
            style_class = ""
        elif d.get("style") == "primary":
            btn_style = ""
            style_class = "bg-black text-white hover:opacity-90"
        else:
            btn_style = ""
            style_class = "bg-gray-100 text-black hover:bg-gray-200"
        nav_attr = f' data-funnel-nav="{_e(d["nav"])}"' if d.get("nav") and d["nav"] != "none" else ""
        href = _e(d["url"]) if d.get("url") else "#"
        justify = "justify-center" if d["align"] == "center" else ("justify-start" if d["align"] == "left" else "justify-end")
        inline = f'border-radius:{shape_radius}; padding:{size_pad}; font-size:{size_text}; {btn_style}'
        return (f'<div class="flex mb-6 {justify}">'
                f'<a href="{href}"{nav_attr} style="{inline}" class="{style_class} font-bold transition-all inline-block">{_e(d["text"])}</a></div>')

    if btype == "spacer":
        try:
            h = int(d.get("height", 40))
        except (TypeError, ValueError):
            h = 40
        return f'<div style="height:{h}px"></div>'

    if btype == "video":
        if not d.get("url"):
            return ""
        return f'<div class="mb-8 max-w-3xl mx-auto aspect-video"><iframe src="{_e(d["url"])}" class="w-full h-full rounded-2xl shadow-xl" allowfullscreen></iframe></div>'

    if btype == "countdown":
        return f'''<div class="text-center mb-8">
            <p class="text-sm uppercase tracking-wider text-gray-500 mb-2">{_e(d["label"])}</p>
            <div class="funnel-countdown text-3xl font-bold" data-end="{_e(d["end_date"])}">--:--:--</div>
        </div>'''

    if btype == "testimonial":
        items = d.get("items") or []
        cards = "".join(
            f'''<div class="bg-gray-50 rounded-2xl p-6 shadow-sm">
                <p class="text-gray-700 italic mb-4">&ldquo;{_e(it.get("quote"))}&rdquo;</p>
                <p class="font-bold">{_e(it.get("name"))}</p>
                <p class="text-sm text-gray-500">{_e(it.get("role"))}</p>
            </div>''' for it in items
        )
        cols = min(max(len(items), 1), 3)
        return f'<div class="grid md:grid-cols-{cols} gap-6 mb-10 max-w-5xl mx-auto">{cards}</div>'

    if btype == "pricing_table":
        plans = d.get("plans") or []
        cards = "".join(
            f'''<div class="rounded-2xl p-8 shadow-lg {"bg-black text-white scale-105" if p.get("highlighted") == "yes" else "bg-white border border-gray-200"}">
                <h3 class="text-xl font-bold mb-2">{_e(p.get("name"))}</h3>
                <p class="text-3xl font-extrabold mb-4">{_e(p.get("price"))}</p>
                <ul class="space-y-2 mb-6 text-sm {"text-gray-300" if p.get("highlighted") == "yes" else "text-gray-600"}">
                    {"".join(f"<li>&check; {_e(feat)}</li>" for feat in (p.get("features") or "").split(chr(10)) if feat.strip())}
                </ul>
                <a href="#" data-funnel-nav="next" class="block text-center py-3 rounded-full font-bold {"bg-white text-black" if p.get("highlighted") == "yes" else "bg-black text-white"}">{_e(p.get("cta_text") or "Choose Plan")}</a>
            </div>''' for p in plans
        )
        cols = min(max(len(plans), 1), 3)
        return f'<div class="grid md:grid-cols-{cols} gap-6 mb-10 max-w-5xl mx-auto">{cards}</div>'

    if btype == "faq":
        items = d.get("items") or []
        rows = "".join(
            f'''<details class="border-b border-gray-200 py-4">
                <summary class="font-bold cursor-pointer">{_e(it.get("q"))}</summary>
                <p class="text-gray-600 mt-2">{_e(it.get("a"))}</p>
            </details>''' for it in items
        )
        return f'<div class="max-w-2xl mx-auto mb-10">{rows}</div>'

    if btype == "accordion":
        items = d.get("items") or []
        rows = "".join(
            f'''<details class="border border-gray-200 rounded-xl p-4 mb-3">
                <summary class="font-bold cursor-pointer">{_e(it.get("title"))}</summary>
                <p class="text-gray-600 mt-2 whitespace-pre-line">{_e(it.get("content"))}</p>
            </details>''' for it in items
        )
        return f'<div class="max-w-2xl mx-auto mb-10">{rows}</div>'

    if btype == "tabs":
        items = d.get("items") or []
        uid = f"tabs_{abs(hash(str(items))) % 100000}"
        buttons = "".join(
            f'''<button onclick="document.querySelectorAll('#{uid} .tab-panel').forEach(p=>p.style.display='none');
                document.getElementById('{uid}_panel_{i}').style.display='block';
                document.querySelectorAll('#{uid} .tab-btn').forEach(b=>b.classList.remove('bg-black','text-white'));
                this.classList.add('bg-black','text-white');"
                class="tab-btn px-5 py-2 rounded-full font-semibold text-sm border border-gray-200 {'bg-black text-white' if i == 0 else ''}">{_e(it.get("label"))}</button>'''
            for i, it in enumerate(items)
        )
        panels = "".join(
            f'<div id="{uid}_panel_{i}" class="tab-panel text-gray-600 whitespace-pre-line" style="display:{"block" if i == 0 else "none"}">{_e(it.get("content"))}</div>'
            for i, it in enumerate(items)
        )
        return f'<div id="{uid}" class="max-w-2xl mx-auto mb-10"><div class="flex flex-wrap gap-2 mb-4 justify-center">{buttons}</div><div>{panels}</div></div>'

    if btype == "progress_bar":
        try:
            pct = max(0, min(100, int(d.get("percent", 80))))
        except (TypeError, ValueError):
            pct = 80
        color = _e(d.get("color") or "#000000")
        return f'''<div class="max-w-md mx-auto mb-8">
            <p class="text-sm font-medium text-gray-600 mb-2">{_e(d.get("label"))}</p>
            <div class="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div style="width:{pct}%;background:{color}" class="h-full rounded-full"></div>
            </div>
        </div>'''

    if btype == "icon":
        color = _e(d.get("color") or "#000000")
        return f'''<div class="flex flex-col items-center text-center mb-6">
            <i data-lucide="{_e(d.get("name") or "star")}" style="color:{color}" class="w-10 h-10 mb-2"></i>
            {f'<p class="text-sm text-gray-600">{_e(d.get("caption"))}</p>' if d.get("caption") else ""}
        </div>'''

    if btype == "success_animation":
        color = _e(d.get("color") or "#16a34a")
        heading = _e(d.get("heading") or "Success!")
        # Pure CSS/SVG — a drawn checkmark (stroke-dasharray animation) plus
        # a burst of falling confetti pieces, no JS animation library needed.
        confetti_colors = [color, "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
        pieces = "".join(
            f'<i class="confetti-piece" style="left:{(i * 37) % 100}%; '
            f'background:{confetti_colors[i % len(confetti_colors)]}; '
            f'animation-delay:{(i % 10) * 0.15}s; animation-duration:{2.2 + (i % 5) * 0.3}s;"></i>'
            for i in range(28)
        )
        return f'''<div class="success-anim-wrap relative flex flex-col items-center text-center mb-6 overflow-hidden">
            <div class="confetti-field" aria-hidden="true">{pieces}</div>
            <svg viewBox="0 0 100 100" class="w-24 h-24 mb-4 relative z-10">
                <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="6"
                        stroke-linecap="round" class="success-circle"/>
                <path d="M28 52 L43 66 L74 34" fill="none" stroke="{color}" stroke-width="7"
                      stroke-linecap="round" stroke-linejoin="round" class="success-check"/>
            </svg>
            <h2 class="text-2xl font-extrabold relative z-10">{heading}</h2>
            <style>
                .success-circle {{
                    stroke-dasharray: 283; stroke-dashoffset: 283;
                    animation: successCircleDraw 0.6s ease-out forwards;
                }}
                .success-check {{
                    stroke-dasharray: 60; stroke-dashoffset: 60;
                    animation: successCheckDraw 0.4s ease-out 0.5s forwards;
                }}
                @keyframes successCircleDraw {{ to {{ stroke-dashoffset: 0; }} }}
                @keyframes successCheckDraw {{ to {{ stroke-dashoffset: 0; }} }}
                .confetti-field {{ position: absolute; inset: 0; pointer-events: none; }}
                .confetti-piece {{
                    position: absolute; top: -12px; width: 8px; height: 14px;
                    opacity: 0.9; animation-name: confettiFall; animation-timing-function: ease-in;
                    animation-iteration-count: 1; animation-fill-mode: forwards;
                }}
                @keyframes confettiFall {{
                    0% {{ transform: translateY(-20px) rotate(0deg); opacity: 1; }}
                    100% {{ transform: translateY(220px) rotate(540deg); opacity: 0; }}
                }}
            </style>
        </div>'''

    if btype == "social_links":
        icon_map = {"facebook": "facebook", "twitter": "twitter", "x": "twitter", "instagram": "instagram",
                    "linkedin": "linkedin", "youtube": "youtube", "tiktok": "music-2", "whatsapp": "message-circle"}
        items = d.get("items") or []
        links = "".join(
            f'''<a href="{_e(it.get("url") or "#")}" target="_blank" rel="noopener"
                class="w-11 h-11 rounded-full border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors">
                <i data-lucide="{icon_map.get((it.get("platform") or "").lower(), "link")}" class="w-5 h-5"></i></a>'''
            for it in items
        )
        return f'<div class="flex justify-center gap-3 mb-8">{links}</div>'

    if btype == "custom_html":
        # Intentionally unescaped — this is the same trust boundary as the
        # existing Code builder mode (a funnel owner can already write raw
        # HTML/CSS/JS for a whole page); this block just lets them do it
        # for one section while staying in Blocks mode.
        return f'<div class="mb-6">{d.get("html") or ""}</div>'

    if btype == "map_embed":
        if not d.get("embed_url"):
            return ""
        return f'<div class="mb-8 max-w-3xl mx-auto aspect-video"><iframe src="{_e(d["embed_url"])}" class="w-full h-full rounded-2xl shadow-xl border-0" loading="lazy" allowfullscreen></iframe></div>'

    if btype == "rating":
        try:
            score = max(0, min(5, float(d.get("score", 5))))
        except (TypeError, ValueError):
            score = 5
        full = int(score)
        stars = "".join('<i data-lucide="star" style="fill:#F2C94C;color:#F2C94C" class="w-6 h-6"></i>' for _ in range(full))
        stars += "".join('<i data-lucide="star" style="color:#d1d5db" class="w-6 h-6"></i>' for _ in range(5 - full))
        return f'''<div class="flex flex-col items-center text-center mb-8">
            <div class="flex gap-1 mb-2">{stars}</div>
            {f'<p class="text-sm text-gray-600">{_e(d.get("caption"))}</p>' if d.get("caption") else ""}
        </div>'''

    if btype == "logo_cloud":
        items = d.get("items") or []
        logos = "".join(
            f'<img src="{_e(it.get("image"))}" alt="{_e(it.get("name"))}" class="h-8 object-contain opacity-70">'
            if it.get("image") else
            f'<span class="text-sm font-bold text-gray-400 tracking-wide">{_e(it.get("name"))}</span>'
            for it in items
        )
        heading = f'<p class="text-center text-xs uppercase tracking-widest text-gray-400 mb-6">{_e(d.get("heading"))}</p>' if d.get("heading") else ""
        return f'<div class="mb-10">{heading}<div class="flex flex-wrap items-center justify-center gap-10">{logos}</div></div>'

    if btype == "comparison_table":
        columns = [c.strip() for c in (d.get("columns") or "").split(",") if c.strip()]
        rows = d.get("rows") or []
        header = "<th class=\"text-left py-3 px-4 text-sm font-semibold text-gray-500\">Feature</th>" + "".join(
            f'<th class="text-center py-3 px-4 text-sm font-semibold text-gray-900">{_e(c)}</th>' for c in columns
        )
        body_rows = ""
        for r in rows:
            vals = [v.strip() for v in (r.get("values") or "").split(",")]
            cells = "".join(f'<td class="text-center py-3 px-4 text-sm text-gray-600">{_e(v)}</td>' for v in vals)
            body_rows += f'<tr class="border-t border-gray-100"><td class="py-3 px-4 text-sm font-medium text-gray-900">{_e(r.get("feature"))}</td>{cells}</tr>'
        return f'''<div class="max-w-2xl mx-auto mb-10 overflow-x-auto">
            <table class="w-full"><thead><tr class="border-b-2 border-gray-100">{header}</tr></thead><tbody>{body_rows}</tbody></table>
        </div>'''

    if btype == "divider":
        style = d.get("style", "line")
        if style == "dots":
            return '<div class="text-center text-gray-300 mb-8 tracking-[1em]">• • •</div>'
        if style == "space":
            return '<div style="height:48px"></div>'
        return '<hr class="border-gray-200 mb-8 max-w-2xl mx-auto">'

    if btype == "container":
        align_class = ALIGN_CLASS.get(d.get("content_align"), "text-center")
        items_align = {"left": "items-start", "center": "items-center", "right": "items-end"}.get(d.get("content_align"), "items-center")
        try:
            min_h = int(d.get("min_height") or 0)
        except (TypeError, ValueError):
            min_h = 0
        bg_style = f'background-image:url(\'{_e(d["bg_image"])}\');background-size:cover;background-position:center;' if d.get("bg_image") else ""
        overlay = '<div class="absolute inset-0 bg-black/40"></div>' if d.get("bg_image") else ""
        text_cls = "text-white" if d.get("bg_image") else ""
        eyebrow = f'<p class="text-xs font-bold tracking-widest uppercase mb-3 opacity-70">{_e(d["eyebrow"])}</p>' if d.get("eyebrow") else ""
        body = f'<p class="text-base md:text-lg opacity-80 mt-3 max-w-xl">{_e(d["text"])}</p>' if d.get("text") else ""
        btn = ""
        if d.get("button_text"):
            nav_attr = f' data-funnel-nav="{_e(d["button_nav"])}"' if d.get("button_nav") and d["button_nav"] != "none" else ""
            href = _e(d["button_url"]) if d.get("button_url") else "#"
            btn = f'<a href="{href}"{nav_attr} class="inline-block mt-6 px-8 py-3.5 rounded-full font-bold bg-black text-white hover:opacity-90 transition-all">{_e(d["button_text"])}</a>'
        return (f'<div class="relative rounded-3xl overflow-hidden flex flex-col {items_align} justify-center {align_class} {text_cls} p-10 md:p-16" '
                f'style="{bg_style}{"min-height:" + str(min_h) + "px;" if min_h else ""}">'
                f'{overlay}<div class="relative z-10">{eyebrow}<h2 class="text-3xl md:text-4xl font-extrabold">{_e(d["heading"])}</h2>{body}{btn}</div></div>')

    if btype == "hero_split":
        media_right = d.get("media_side", "right") != "left"
        eyebrow = f'<p class="text-xs font-bold tracking-widest uppercase mb-3 text-gray-500">{_e(d["eyebrow"])}</p>' if d.get("eyebrow") else ""
        stat = f'<p class="text-sm text-gray-500 mt-4">{_e(d["stat_line"])}</p>' if d.get("stat_line") else ""
        btn = ""
        if d.get("button_text"):
            nav_attr = f' data-funnel-nav="{_e(d["button_nav"])}"' if d.get("button_nav") and d["button_nav"] != "none" else ""
            href = _e(d["button_url"]) if d.get("button_url") else "#"
            btn = f'<a href="{href}"{nav_attr} class="inline-block mt-6 px-8 py-3.5 rounded-full font-bold bg-black text-white hover:opacity-90 transition-all">{_e(d["button_text"])}</a>'
        text_col = f'''<div>
            {eyebrow}
            <h1 class="text-3xl md:text-5xl font-extrabold leading-tight mb-4">{_e(d["heading"])}</h1>
            <p class="text-lg text-gray-600 mb-2 max-w-xl">{_e(d["text"])}</p>
            {stat}{btn}
        </div>'''
        if d.get("media_type") == "video" and d.get("video_url"):
            media_col = f'<div class="aspect-video rounded-2xl overflow-hidden shadow-xl"><iframe src="{_e(d["video_url"])}" class="w-full h-full" allowfullscreen></iframe></div>'
        else:
            media_col = f'<div><img src="{_e(d["image"])}" alt="" class="rounded-2xl shadow-xl w-full h-auto object-cover"></div>'
        cols = f'{media_col}{text_col}' if not media_right else f'{text_col}{media_col}'
        return f'<div class="grid md:grid-cols-2 gap-10 md:gap-16 items-center mb-4">{cols}</div>'

    if btype == "video_section":
        media_right = d.get("media_side", "right") != "left"
        eyebrow = f'<p class="text-xs font-bold tracking-widest uppercase mb-3 text-gray-500">{_e(d["eyebrow"])}</p>' if d.get("eyebrow") else ""
        btn = f'<a href="{_e(d["button_url"]) if d.get("button_url") else "#"}" class="inline-block mt-6 px-8 py-3.5 rounded-full font-bold bg-black text-white hover:opacity-90 transition-all">{_e(d["button_text"])}</a>' if d.get("button_text") else ""
        text_col = f'''<div>{eyebrow}<h2 class="text-3xl md:text-4xl font-extrabold leading-tight mb-4">{_e(d["heading"])}</h2>
            <p class="text-lg text-gray-600 max-w-xl">{_e(d["text"])}</p>{btn}</div>'''
        if d.get("video_url"):
            media_col = f'<div class="aspect-video rounded-2xl overflow-hidden shadow-xl"><iframe src="{_e(d["video_url"])}" class="w-full h-full" allowfullscreen></iframe></div>'
        else:
            media_col = '<div class="aspect-video rounded-2xl bg-gray-100 flex items-center justify-center text-gray-400 text-sm">Add a video URL</div>'
        cols = f'{media_col}{text_col}' if not media_right else f'{text_col}{media_col}'
        return f'<div class="grid md:grid-cols-2 gap-10 md:gap-16 items-center mb-4">{cols}</div>'

    if btype == "feature_grid":
        items = d.get("items") or []
        try:
            cols = int(d.get("columns") or 4)
        except (TypeError, ValueError):
            cols = 4
        cols = min(max(cols, 1), 4)
        heading = f'<h2 class="text-2xl md:text-3xl font-extrabold text-center mb-10">{_e(d["heading"])}</h2>' if d.get("heading") else ""
        cards = "".join(
            f'''<div class="text-center">
                <div class="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                    <i data-lucide="{_e(it.get("icon") or "star")}" class="w-6 h-6"></i>
                </div>
                <h3 class="font-bold mb-2">{_e(it.get("title"))}</h3>
                <p class="text-sm text-gray-600">{_e(it.get("text"))}</p>
            </div>''' for it in items
        )
        return f'<div class="mb-6">{heading}<div class="grid md:grid-cols-{cols} gap-8">{cards}</div></div>'

    if btype == "checklist":
        items = d.get("items") or []
        color = _e(d.get("check_color") or "#111111")
        heading = f'<h3 class="text-xl font-bold mb-4">{_e(d["heading"])}</h3>' if d.get("heading") else ""
        rows = "".join(
            f'''<li class="flex items-start gap-3 mb-3">
                <i data-lucide="check" style="color:{color}" class="w-5 h-5 mt-0.5 shrink-0"></i>
                <span class="text-gray-700">{_e(it.get("text"))}</span>
            </li>''' for it in items
        )
        return f'<div class="max-w-2xl mx-auto mb-8">{heading}<ul class="list-none">{rows}</ul></div>'

    if btype == "stat_bar":
        items = d.get("items") or []
        caption = f'<p class="text-center text-xs uppercase tracking-widest text-gray-400 mb-8">{_e(d["caption"])}</p>' if d.get("caption") else ""
        stats = "".join(
            f'''<div class="text-center">
                <p class="text-3xl md:text-4xl font-extrabold">{_e(it.get("number"))}</p>
                <p class="text-sm text-gray-500 mt-1">{_e(it.get("label"))}</p>
            </div>''' for it in items
        )
        cols = min(max(len(items), 1), 5)
        return f'<div class="mb-6">{caption}<div class="grid grid-cols-2 md:grid-cols-{cols} gap-6">{stats}</div></div>'

    if btype == "announcement_bar":
        if not d.get("text"):
            return ""
        btn = f'<a href="{_e(d["button_url"]) if d.get("button_url") else "#"}" class="ml-4 px-4 py-1.5 rounded-full font-bold text-xs whitespace-nowrap" style="background:rgba(255,255,255,0.2)">{_e(d["button_text"])}</a>' if d.get("button_text") else ""
        return (f'<div class="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-center" '
                f'style="background:{_e(d.get("bg_color") or "#2D9CDB")};color:{_e(d.get("text_color") or "#ffffff")}">'
                f'<span>{_e(d["text"])}</span>{btn}</div>')

    if btype == "form":
        block_id = block.get("id") or ""
        fields = d.get("fields") or []
        heading = f'<h3 class="text-2xl font-extrabold text-center mb-6">{_e(d["heading"])}</h3>' if d.get("heading") else ""
        inputs = []
        for f in fields:
            key = _e(f.get("key") or "")
            if not key:
                continue
            label = _e(f.get("label") or f.get("key") or "")
            ftype = (f.get("field_type") or "text").strip().lower()
            if ftype not in ("text", "email", "tel", "textarea"):
                ftype = "text"
            required = str(f.get("required") or "").strip().lower() in ("yes", "true", "1")
            req_attr = " required" if required else ""
            req_mark = ' <span style="color:#EB5757">*</span>' if required else ""
            if ftype == "textarea":
                inputs.append(
                    f'<div class="mb-4 text-left"><label class="block text-sm font-medium mb-1">{label}{req_mark}</label>'
                    f'<textarea name="{key}" rows="3"{req_attr} class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-black"></textarea></div>'
                )
            else:
                inputs.append(
                    f'<div class="mb-4 text-left"><label class="block text-sm font-medium mb-1">{label}{req_mark}</label>'
                    f'<input type="{ftype}" name="{key}"{req_attr} class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-black"></div>'
                )
        submit_text = _e(d.get("submit_text") or "Submit")
        success_message = _e(d.get("success_message") or "Thanks!")
        on_success_nav = d.get("on_success_nav") or "stay"
        submit_url = f'/dashboard/funnels/leads/{int(page_id)}/submit' if page_id else ''
        form_id = f'bzn-form-{_e(block_id)}'
        script = f"""<script>
(function() {{
  var form = document.getElementById('{form_id}');
  if (!form) return;
  form.addEventListener('submit', function(e) {{
    e.preventDefault();
    var btn = form.querySelector('button[type=submit]');
    var errEl = form.querySelector('.bzn-form-error');
    var data = {{}};
    new FormData(form).forEach(function(v, k) {{ data[k] = v; }});
    if (btn) {{ btn.disabled = true; btn.textContent = 'Sending...'; }}
    if (errEl) errEl.style.display = 'none';
    fetch('{submit_url}', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ block_id: '{_e(block_id)}', data: data }})
    }}).then(function(r) {{ return r.json(); }}).then(function(res) {{
      if (res.ok) {{
        form.style.display = 'none';
        var successEl = document.getElementById('{form_id}-success');
        if (successEl) successEl.style.display = 'block';
        var nav = '{on_success_nav}';
        if (nav === 'next' && window.FUNNEL_NEXT_URL) window.location.href = window.FUNNEL_NEXT_URL;
        else if (nav === 'accept' && window.FUNNEL_ACCEPT_URL) window.location.href = window.FUNNEL_ACCEPT_URL;
      }} else {{
        if (btn) {{ btn.disabled = false; btn.textContent = '{submit_text}'; }}
        if (errEl) {{ errEl.textContent = res.error || 'Something went wrong.'; errEl.style.display = 'block'; }}
      }}
    }}).catch(function() {{
      if (btn) {{ btn.disabled = false; btn.textContent = '{submit_text}'; }}
      if (errEl) {{ errEl.textContent = 'Network error — please try again.'; errEl.style.display = 'block'; }}
    }});
  }});
}})();
</script>"""
        return (
            f'<div class="max-w-md mx-auto">{heading}'
            f'<form id="{form_id}">{"".join(inputs)}'
            f'<p class="bzn-form-error text-sm mb-3" style="display:none;color:#EB5757"></p>'
            f'<button type="submit" class="w-full py-3 rounded-full font-bold bg-black text-white hover:opacity-90 transition-all">{submit_text}</button>'
            f'</form>'
            f'<div id="{form_id}-success" style="display:none;" class="text-center py-6"><p class="text-lg font-semibold">{success_message}</p></div>'
            f'</div>{script}'
        )

    return ""


def _build_sections(blocks, page_id=None):
    """Shared section-building loop used by both render_blocks_to_html
    (full standalone document) and render_blocks_body_html (fragment
    for embedding inside another page, e.g. above a Checkout page's
    payment card). Returns (sections_list, needs_animation_js)."""
    sections = []
    blocks = blocks or []
    bg_toggle = 0
    needs_animation_js = False
    BG_CLASSES = ["bg-white", "bg-gray-50"]
    CONTAINER_WIDTHS = {"narrow": "max-w-3xl", "medium": "max-w-5xl", "wide": "max-w-6xl", "full": "max-w-none"}
    FONT_STACKS = {
        "default": "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif",
        "serif": "Georgia,'Times New Roman',serif",
        "mono": "'Courier New',monospace",
        "rounded": "'Poppins','Segoe UI',sans-serif",
    }
    FONT_SIZE = {"sm": "0.9", "default": "1", "lg": "1.125", "xl": "1.25"}
    FONT_WEIGHT = {"normal": "400", "medium": "500", "semibold": "600", "bold": "700", "extrabold": "800"}
    LINE_HEIGHT = {"tight": "1.2", "normal": "1.6", "relaxed": "1.9"}
    LETTER_SPACING = {"tight": "-0.02em", "normal": "normal", "wide": "0.02em", "widest": "0.08em"}
    ANIM_SPEED = {"fast": "0.4s", "normal": "0.7s", "slow": "1.1s"}

    for i, b in enumerate(blocks):
        html = _render_block(b, page_id=page_id)
        if not html:
            continue
        btype = b.get("type")
        design = b.get("design") or {}
        is_hero = (btype == "heading" and i <= 1)

        if btype == "spacer":
            sections.append(html)
            continue

        if btype == "announcement_bar":
            # Full-bleed bar, no section chrome/padding wrapper.
            anim = design.get("animation")
            anim_attr = f' data-bzn-anim="{_e(anim)}"' if anim and anim != "none" else ""
            if anim_attr:
                needs_animation_js = True
            sections.append(f'<div{anim_attr}>{html}</div>')
            continue

        bg = BG_CLASSES[bg_toggle % 2]
        bg_toggle += 1

        width_class = CONTAINER_WIDTHS.get(design.get("container_width"), "max-w-4xl" if is_hero else "max-w-5xl")

        # Spacing: numeric padding_y/padding_x win; fall back to legacy preset; else default.
        if design.get("padding_y"):
            try:
                py = int(design["padding_y"])
            except (TypeError, ValueError):
                py = None
        else:
            py = _LEGACY_PADDING_PRESETS.get(design.get("padding")) if design.get("padding") else None
        if py is None:
            py = 112 if is_hero else 72
        try:
            px = int(design["padding_x"]) if design.get("padding_x") else None
        except (TypeError, ValueError):
            px = None

        style_parts = [f"padding-top:{py}px;padding-bottom:{py}px;"]
        if px is not None:
            style_parts.append(f"padding-left:{px}px;padding-right:{px}px;")
        section_class = bg

        # Color: solid / gradient / none
        bg_type = design.get("bg_type")
        if bg_type == "gradient" and (design.get("gradient_from") or design.get("gradient_to")):
            angle = design.get("gradient_angle") or 135
            g_from = _e(design.get("gradient_from") or "#111111")
            g_to = _e(design.get("gradient_to") or "#333333")
            style_parts.append(f"background:linear-gradient({angle}deg,{g_from},{g_to});")
            section_class = ""
        elif bg_type == "none":
            pass
        elif design.get("bg_color"):
            style_parts.append(f"background:{_e(design['bg_color'])};")
            section_class = ""

        if design.get("text_color"):
            style_parts.append(f"color:{_e(design['text_color'])};")

        # Typography
        if design.get("font_family"):
            style_parts.append(f"font-family:{FONT_STACKS.get(design['font_family'], FONT_STACKS['default'])};")
        if design.get("font_size"):
            style_parts.append(f"font-size:{FONT_SIZE.get(design['font_size'], '1')}rem;")
        if design.get("font_weight"):
            style_parts.append(f"font-weight:{FONT_WEIGHT.get(design['font_weight'], '400')};")
        if design.get("line_height"):
            style_parts.append(f"line-height:{LINE_HEIGHT.get(design['line_height'], '1.6')};")
        if design.get("letter_spacing"):
            style_parts.append(f"letter-spacing:{LETTER_SPACING.get(design['letter_spacing'], 'normal')};")

        # Margin
        if design.get("margin_top"):
            try:
                style_parts.append(f"margin-top:{int(design['margin_top'])}px;")
            except (TypeError, ValueError):
                pass
        if design.get("margin_bottom"):
            try:
                style_parts.append(f"margin-bottom:{int(design['margin_bottom'])}px;")
            except (TypeError, ValueError):
                pass
        if design.get("border_radius"):
            try:
                style_parts.append(f"border-radius:{int(design['border_radius'])}px;overflow:hidden;")
            except (TypeError, ValueError):
                pass

        align_class = f' {ALIGN_CLASS[design["align"]]}' if design.get("align") in ALIGN_CLASS else ""

        # Animation
        anim = design.get("animation")
        anim_attr = ""
        if anim and anim != "none":
            needs_animation_js = True
            speed = ANIM_SPEED.get(design.get("animation_speed"), "0.7s")
            anim_attr = f' data-bzn-anim="{_e(anim)}" style="--bzn-anim-speed:{speed}"'

        section_style = "".join(style_parts)

        if is_hero and not design:
            sections.append(
                f'<section class="w-full bg-gradient-to-br from-gray-900 via-black to-gray-800 text-white py-20 md:py-28">'
                f'<div class="max-w-4xl mx-auto px-6">{html}</div></section>'
            )
        else:
            sections.append(
                f'<section class="w-full {section_class}{align_class}" style="{section_style}"{anim_attr}>'
                f'<div class="{width_class} mx-auto px-6">{html}</div></section>'
            )
    return sections, needs_animation_js


_ANIMATION_CSS = """
  [data-bzn-anim] { opacity: 0; }
  [data-bzn-anim].bzn-in { opacity: 1; }
  [data-bzn-anim="fade-in"] { transition: opacity var(--bzn-anim-speed, 0.7s) ease; }
  [data-bzn-anim="fade-up"] { transform: translateY(28px); transition: opacity var(--bzn-anim-speed, 0.7s) ease, transform var(--bzn-anim-speed, 0.7s) ease; }
  [data-bzn-anim="fade-up"].bzn-in { transform: translateY(0); }
  [data-bzn-anim="zoom-in"] { transform: scale(0.94); transition: opacity var(--bzn-anim-speed, 0.7s) ease, transform var(--bzn-anim-speed, 0.7s) ease; }
  [data-bzn-anim="zoom-in"].bzn-in { transform: scale(1); }
  [data-bzn-anim="slide-left"] { transform: translateX(40px); transition: opacity var(--bzn-anim-speed, 0.7s) ease, transform var(--bzn-anim-speed, 0.7s) ease; }
  [data-bzn-anim="slide-left"].bzn-in { transform: translateX(0); }
  [data-bzn-anim="slide-right"] { transform: translateX(-40px); transition: opacity var(--bzn-anim-speed, 0.7s) ease, transform var(--bzn-anim-speed, 0.7s) ease; }
  [data-bzn-anim="slide-right"].bzn-in { transform: translateX(0); }
"""

_ANIMATION_JS = """
  if ('IntersectionObserver' in window) {
    var bznIo = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('bzn-in'); bznIo.unobserve(entry.target); }
      });
    }, { threshold: 0.15 });
    document.querySelectorAll('[data-bzn-anim]').forEach(function (el) { bznIo.observe(el); });
  } else {
    document.querySelectorAll('[data-bzn-anim]').forEach(function (el) { el.classList.add('bzn-in'); });
  }
"""


def render_blocks_body_html(blocks, page_id=None):
    """Same section-building as render_blocks_to_html, but returns just
    the inner markup (sections + inline animation <style>/<script> if
    needed) with no surrounding <html>/<head>/<body> — for embedding
    inside another page's own document, e.g. prepending custom block
    content above a Checkout page's auto-generated payment card so the
    two aren't mutually exclusive anymore."""
    sections, needs_animation_js = _build_sections(blocks, page_id)
    body = "\n".join(sections)
    if not needs_animation_js:
        return body
    return (
        f"<style>{_ANIMATION_CSS}</style>{body}"
        f"<script>document.addEventListener('DOMContentLoaded', function() {{ {_ANIMATION_JS} }});</script>"
    )


def render_blocks_to_html(blocks, title="Funnel Page", page_id=None):
    """Render a page's structured blocks into a self-contained HTML
    document. This is what gets saved to FunnelPage.html_content and
    served to visitors — the blocks list stays the edit-time source of
    truth, this function is the only place that knows how to turn it
    into a page.

    Each block gets its own full-width <section> with an inner content
    column, alternating background bands between sections — this is
    what makes it read like a real landing page instead of one long
    centered column. A leading `heading` block additionally gets
    hero-band treatment: a taller, dark gradient section so the page
    opens with real visual weight instead of plain black text on white.
    """
    sections, needs_animation_js = _build_sections(blocks, page_id)
    body = "\n".join(sections)
    animation_css = _ANIMATION_CSS if needs_animation_js else ""
    animation_js = _ANIMATION_JS if needs_animation_js else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/lucide@latest"></script>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}{animation_css}</style>
</head>
<body class="bg-white text-black">
<main>
{body}
</main>
<script>
  if (window.lucide) lucide.createIcons();
  document.querySelectorAll('.funnel-countdown').forEach(function (el) {{
    var end = new Date(el.getAttribute('data-end')).getTime();
    if (!end || isNaN(end)) return;
    function tick() {{
      var diff = end - Date.now();
      if (diff <= 0) {{ el.textContent = "00:00:00"; return; }}
      var h = String(Math.floor(diff / 3600000)).padStart(2, '0');
      var m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, '0');
      var s = String(Math.floor((diff % 60000) / 1000)).padStart(2, '0');
      el.textContent = h + ':' + m + ':' + s;
    }}
    tick(); setInterval(tick, 1000);
  }});
  {animation_js}
</script>
</body>
</html>"""
