"""Shared rendering for the AI Chatbot / WhatsApp Bot floating chat
widget — the little bubble + expandable chat panel that businesses embed
on their own site. Mirrors app/utils/whatsapp_widget.py's structure (one
canonical config + CSS + HTML builder used by every surface) so the
embed script, the standalone hosted page, and the dashboard preview all
stay visually identical instead of drifting apart — which is exactly
what was missing before: the bubble was a fixed, hardcoded shape/color/
icon with zero per-bot configuration.
"""
import html as _html

ICON_LIBRARY = {
    "chat": '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>',
    "bot": '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>',
    "headset": '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/></svg>',
    "message-circle": '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
    "sparkles": '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8L4 11l6.1 2.2L12 19l1.9-5.8L20 11l-6.1-2.2z"/></svg>',
}
DEFAULT_ICON = ICON_LIBRARY["chat"]


def widget_config(bot):
    """Normalizes a UserChatbot into a plain dict of display settings
    with sane defaults — same field names/shape as
    whatsapp_widget.widget_config so the two stay consistent for anyone
    who's configured one and moves to the other."""
    s = bot.widget_settings or {}
    return {
        "name": _html.escape(bot.name or "Chat with us"),
        "greeting": _html.escape(bot.greeting or "Hi! How can I help you today?"),
        "logo_url": bot.logo_url or "",
        "position": s.get("position", "bottom-right"),
        "button_color": s.get("button_color", "#1DB954"),
        "animation": s.get("animation", "none"),
        "show_label": s.get("show_label", False),
        "button_text": _html.escape(s.get("button_text") or "Chat with us"),
        "desktop_visible": s.get("desktop_visible", True),
        "mobile_visible": s.get("mobile_visible", True),
        "icon": s.get("icon", "chat"),
        "show_branding": s.get("show_branding", True),
    }


def render_widget_css(cfg, prefix="bzn-cb"):
    side = "right" if "right" in cfg["position"] else "left"
    vpos = "bottom" if "bottom" in cfg["position"] else "top"
    panel_vpos = "bottom: 90px;" if vpos == "bottom" else "top: 90px;"
    anim_css = ""
    if cfg["animation"] == "pulse":
        anim_css = f"""
        @keyframes {prefix}-pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0.25); }} 70% {{ box-shadow: 0 0 0 14px rgba(0,0,0,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }} }}
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
    .{prefix}-btn {{ display: flex; align-items: center; gap: 10px; background: {cfg['button_color']}; color: #fff; border-radius: 999px; padding: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.3); cursor: pointer; border: none; }}
    .{prefix}-btn.has-label {{ padding: 14px 22px 14px 16px; }}
    .{prefix}-label {{ font-size: 14px; font-weight: 600; white-space: nowrap; }}
    .{prefix}-icon-img {{ width: 26px; height: 26px; border-radius: 50%; overflow: hidden; flex-shrink: 0; display: block; }}
    .{prefix}-icon-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .{prefix}-panel {{ position: absolute; {panel_vpos} {side}: 0; width: 380px; max-width: calc(100vw - 40px); height: 540px; max-height: calc(100vh - 140px); border-radius: 16px; box-shadow: 0 12px 40px rgba(0,0,0,0.3); overflow: hidden; display: none; background: #0a0a0a; border: 1px solid rgba(255,255,255,0.08); }}
    .{prefix}-wrap.open .{prefix}-panel {{ display: block; }}
    .{prefix}-panel iframe {{ width: 100%; height: 100%; border: none; }}
    {anim_css}
    {visibility_css}
    """


def render_bubble_html(cfg, embed_url, prefix="bzn-cb"):
    """Full self-contained HTML block for the floating bubble + toggle
    panel — used by the embed script, the standalone hosted page, and
    the dashboard live preview alike. Deliberately markup+CSS only, no
    inline <script> — a <script> tag set via innerHTML never executes,
    so the toggle click handler is wired up separately by whichever
    surface renders this (see render_embed_script below), in a real
    script context that actually runs."""
    css = render_widget_css(cfg, prefix)
    if cfg["icon"] == "logo" and cfg["logo_url"]:
        icon_html = f'<span class="{prefix}-icon-img"><img src="{_html.escape(cfg["logo_url"])}" alt=""></span>'
    else:
        icon_html = ICON_LIBRARY.get(cfg["icon"], DEFAULT_ICON)
    label_html = f'<span class="{prefix}-label">{cfg["button_text"]}</span>' if cfg["show_label"] else ""
    return f"""
    <style>{css}</style>
    <div class="{prefix}-wrap" id="{prefix}-wrap">
      <div class="{prefix}-panel"><iframe src="{embed_url}"></iframe></div>
      <button type="button" class="{prefix}-btn {'has-label' if cfg['show_label'] else ''}" id="{prefix}-toggle" aria-label="Open chat">
        {icon_html}{label_html}
      </button>
    </div>
    """


def render_embed_script(bot, base_url):
    """The copy-paste <script> snippet — injects the bubble markup via
    innerHTML (same DOM-injection approach as
    whatsapp_widget.render_embed_script) and wires the toggle click
    handler in this OUTER, genuinely-executing script — not inside the
    injected HTML, where a <script> tag would silently never run."""
    embed_url = f"{base_url.rstrip('/')}/dashboard/chatbot/embed/{bot.id}"
    cfg = widget_config(bot)
    prefix = f"bzn-cb-{bot.id}"
    html_block = render_bubble_html(cfg, embed_url, prefix=prefix)
    escaped = html_block.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return f"""<script>
(function() {{
  var d = document.createElement('div');
  d.innerHTML = `{escaped}`;
  document.body.appendChild(d);
  var wrap = document.getElementById('{prefix}-wrap');
  var btn = document.getElementById('{prefix}-toggle');
  if (btn && wrap) {{
    btn.addEventListener('click', function() {{ wrap.classList.toggle('open'); }});
  }}
}})();
</script>"""
