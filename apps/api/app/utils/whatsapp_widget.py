"""Shared rendering for the WhatsApp Chat Widget product.

One canonical implementation used everywhere the widget needs to appear:
the embeddable <script> snippet, the standalone hosted page (/w/<slug>),
the dashboard live preview, and the generated WordPress plugin. Keeping
it in one place means all four surfaces stay visually and behaviorally
identical instead of drifting apart.
"""
import re
import html as _html


def sanitize_phone(raw):
    """Digits only, no leading +/spaces/dashes — what wa.me expects."""
    return re.sub(r"[^0-9]", "", raw or "")


def build_wa_url(phone, message):
    phone = sanitize_phone(phone)
    if not phone:
        return None
    url = f"https://wa.me/{phone}"
    if message:
        from urllib.parse import quote
        url += f"?text={quote(message)}"
    return url


def widget_config(widget):
    """Normalizes a UserWhatsAppWidget into a plain dict of display
    settings with sane defaults — used by every renderer below."""
    s = widget.settings or {}
    return {
        "phone": sanitize_phone(widget.phone_number),
        "business_name": _html.escape(widget.business_name or "Chat with us"),
        "welcome_message": _html.escape(widget.welcome_message or "Hi there! 👋 How can we help?"),
        "default_message": widget.default_message or "Hello, I'm interested in your services.",
        "profile_image": widget.profile_image or "",
        "position": s.get("position", "bottom-right"),
        "button_color": s.get("button_color", "#25D366"),
        "animation": s.get("animation", "pulse"),
        "show_label": s.get("show_label", True),
        "button_text": _html.escape(s.get("button_text") or "Chat with us"),
        "desktop_visible": s.get("desktop_visible", True),
        "mobile_visible": s.get("mobile_visible", True),
        "icon": s.get("icon", "whatsapp"),
    }


def render_widget_css(cfg, prefix="bzn-wa"):
    side = "right" if "right" in cfg["position"] else "left"
    other_side = "left" if side == "right" else "right"
    vpos = "bottom" if "bottom" in cfg["position"] else "top"
    anim_css = ""
    if cfg["animation"] == "pulse":
        anim_css = f"""
        @keyframes {prefix}-pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(37,211,102,0.5); }} 70% {{ box-shadow: 0 0 0 14px rgba(37,211,102,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(37,211,102,0); }} }}
        .{prefix}-btn {{ animation: {prefix}-pulse 2s infinite; }}"""
    elif cfg["animation"] == "bounce":
        anim_css = f"""
        @keyframes {prefix}-bounce {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-8px); }} }}
        .{prefix}-btn {{ animation: {prefix}-bounce 1.6s infinite; }}"""
    visibility_css = ""
    if not cfg["desktop_visible"]:
        visibility_css += f"@media (min-width: 769px) {{ .{prefix}-wrap {{ display: none !important; }} }}"
    if not cfg["mobile_visible"]:
        visibility_css += f"@media (max-width: 768px) {{ .{prefix}-wrap {{ display: none !important; }} }}"
    return f"""
    .{prefix}-wrap, .{prefix}-wrap *, .{prefix}-wrap *::before, .{prefix}-wrap *::after {{ box-sizing: border-box; }}
    .{prefix}-wrap {{ position: fixed; {vpos}: 20px; {side}: 20px; z-index: 999999; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
    .{prefix}-btn {{ display: flex; align-items: center; gap: 10px; background: {cfg['button_color']}; color: #fff; border-radius: 999px; padding: 14px; box-shadow: 0 6px 20px rgba(0,0,0,0.25); text-decoration: none; cursor: pointer; border: none; }}
    .{prefix}-btn.has-label {{ padding: 12px 20px 12px 14px; }}
    .{prefix}-label {{ font-size: 14px; font-weight: 600; white-space: nowrap; }}
    .{prefix}-icon-img {{ width: 28px; height: 28px; border-radius: 50%; overflow: hidden; flex-shrink: 0; display: block; }}
    .{prefix}-icon-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .{prefix}-bubble {{ position: absolute; {vpos}: 74px; {side}: 0; width: 260px; max-width: calc(100vw - 40px); background: #fff; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); padding: 14px; display: none; }}
    .{prefix}-wrap.open .{prefix}-bubble {{ display: block; }}
    .{prefix}-bubble-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
    .{prefix}-bubble-avatar {{ width: 32px; height: 32px; border-radius: 50%; background: {cfg['button_color']}; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 13px; overflow: hidden; flex-shrink: 0; }}
    .{prefix}-bubble-avatar img {{ width: 100%; height: 100%; object-fit: cover; }}
    .{prefix}-bubble-name {{ font-weight: 700; font-size: 13px; color: #111; }}
    .{prefix}-bubble-msg {{ font-size: 13px; color: #444; background: #f0f2f5; border-radius: 10px; padding: 8px 10px; margin-bottom: 10px; word-wrap: break-word; }}
    .{prefix}-bubble-cta {{ display: block; width: 100%; text-align: center; background: {cfg['button_color']}; color: #fff; border-radius: 8px; padding: 9px; font-size: 13px; font-weight: 600; text-decoration: none; }}
    {anim_css}
    {visibility_css}
    """


# Alternate button icons the user can pick instead of the WhatsApp glyph
# (WA_SVG below). "logo" is handled separately in render_widget_html since
# it renders an <img> from the widget's uploaded/linked profile_image
# rather than a fixed SVG shape.
ICON_LIBRARY = {
    "chat": '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "headset": '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>',
    "bell": '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
}


WA_SVG = '<svg viewBox="0 0 24 24" width="28" height="28" fill="white"><path d="M12.012 2c-5.506 0-9.989 4.478-9.99 9.984a9.96 9.96 0 0 0 1.333 4.993L2 22l5.233-1.371a9.92 9.92 0 0 0 4.777 1.372h.005c5.505 0 9.988-4.479 9.989-9.985A9.99 9.99 0 0 0 12.012 2zm5.726 14.124c-.247.697-1.206 1.293-1.66 1.343-.454.05-1.02.077-3.05-.769-2.593-1.082-4.237-3.724-4.366-3.896-.13-.171-1.053-1.401-1.053-2.67 0-1.27.666-1.894.903-2.15.237-.256.52-.32.693-.32.174 0 .348.003.5.01.16.007.375-.06.587.45.212.51.724 1.76.787 1.888.063.128.106.277.02.447-.086.17-.128.277-.256.426-.128.15-.269.336-.384.453-.128.128-.262.268-.113.524.15.255.663 1.092 1.42 1.766.977.869 1.794 1.139 2.05 1.266.256.128.405.107.554-.064.15-.17.639-.745.81-1 .17-.255.34-.213.573-.127.234.085 1.487.702 1.742.83.255.127.425.19.488.3.063.106.063.616-.184 1.313z"/></svg>'


def render_widget_html(widget, click_track_url=None, prefix="bzn-wa"):
    """Full self-contained HTML block (style + markup + tiny inline JS
    for the preview bubble toggle) — used by the standalone hosted page
    and the dashboard live preview iframe."""
    cfg = widget_config(widget)
    wa_url = build_wa_url(cfg["phone"], cfg["default_message"])
    if not wa_url:
        return "<p style='font-family:sans-serif;color:#999;padding:20px'>Add a WhatsApp number to see the widget.</p>"
    css = render_widget_css(cfg, prefix)
    avatar = f'<img src="{_html.escape(cfg["profile_image"])}" alt="">' if cfg["profile_image"] else (cfg["business_name"][:1] or "W")
    label_html = f'<span class="{prefix}-label">{cfg["button_text"]}</span>' if cfg["show_label"] else ""
    onclick_track = f"fetch('{click_track_url}', {{method:'POST'}});" if click_track_url else ""
    # Button icon: the uploaded/linked logo, a picked alternate icon, or the
    # default WhatsApp glyph — in that order of precedence. Falls back to
    # the WhatsApp glyph if "logo" is selected but no image is set, so the
    # button is never left blank.
    if cfg["icon"] == "logo" and cfg["profile_image"]:
        icon_html = f'<span class="{prefix}-icon-img"><img src="{_html.escape(cfg["profile_image"])}" alt=""></span>'
    else:
        icon_html = ICON_LIBRARY.get(cfg["icon"], WA_SVG)
    return f"""
    <style>{css}</style>
    <div class="{prefix}-wrap" id="{prefix}-wrap">
      <div class="{prefix}-bubble">
        <div class="{prefix}-bubble-header">
          <div class="{prefix}-bubble-avatar">{avatar}</div>
          <div class="{prefix}-bubble-name">{cfg['business_name']}</div>
        </div>
        <div class="{prefix}-bubble-msg">{cfg['welcome_message']}</div>
        <a class="{prefix}-bubble-cta" href="{wa_url}" target="_blank" rel="noopener" onclick="{onclick_track}">Start Chat</a>
      </div>
      <a class="{prefix}-btn {'has-label' if cfg['show_label'] else ''}" href="{wa_url}" target="_blank" rel="noopener"
         onmouseenter="document.getElementById('{prefix}-wrap').classList.add('open')"
         onmouseleave="document.getElementById('{prefix}-wrap').classList.remove('open')"
         onclick="{onclick_track}">
        {icon_html}{label_html}
      </a>
    </div>
    """


def render_embed_script(widget, base_url):
    """The copy-paste <script> snippet — injects the same widget into any
    external page via document.write-free DOM injection, plus a real
    view-tracking beacon on load and a click-tracking beacon on click."""
    slug = widget.slug
    view_url = f"{base_url}/w/{slug}/view"
    click_url = f"{base_url}/w/{slug}/click"
    html_block = render_widget_html(widget, click_track_url=click_url, prefix="bzn-wa-embed")
    # Escaping backticks alone isn't enough — this HTML lands inside a
    # JS template literal, and "${...}" in a business name/message
    # would be interpreted as a live JS expression, silently breaking
    # the whole embed with no visible error to a non-technical user.
    escaped = html_block.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return f"""<script>
(function() {{
  var d = document.createElement('div');
  d.innerHTML = `{escaped}`;
  document.body.appendChild(d);
  fetch('{view_url}', {{method:'POST'}}).catch(function(){{}});
}})();
</script>"""
