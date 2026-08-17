from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import current_user
from app.utils.feature_flags import require_feature
from app.models.components import UIComponent
from app.extensions import db

tools_bp = Blueprint("tools", __name__)

# Full list of Lucide icon names
ICON_NAMES = [
    "panel-left", "panel-right", "panel-top", "panel-bottom", "columns-2", "rows-2",
    "grid-2x2", "grid-3x3", "table", "table-2", "layout-dashboard", "layout-grid",
    "layout-list", "layout-template", "layout-panel-top", "layout-panel-left",
    "menu", "square-menu", "x", "circle-x", "square-x", "navigation", "navigation-2",
    "compass", "map", "map-pin", "map-pinned", "milestone", "route", "navigation-off",
    "app-window", "search", "filter", "settings", "settings-2", "sliders-horizontal",
    "square-pen", "pen", "pen-line", "pencil", "pencil-line", "trash", "trash-2",
    "delete", "copy", "clipboard", "clipboard-copy", "clipboard-check", "clipboard-list",
    "clipboard-paste", "scissors", "move", "move-diagonal", "move-diagonal-2",
    "move-horizontal", "move-vertical", "rotate-cw", "rotate-ccw", "refresh-cw",
    "refresh-ccw", "undo", "undo-2", "redo", "redo-2", "save", "save-all", "download",
    "upload", "share", "share-2", "link", "link-2", "external-link", "log-in", "log-out",
    "lock", "lock-open", "eye", "eye-off", "zoom-in", "zoom-out", "maximize", "maximize-2",
    "minimize", "minimize-2", "expand", "shrink", "fullscreen", "plus", "circle-plus",
    "square-plus", "minus", "circle-minus", "square-minus", "check", "circle-check",
    "square-check", "ban", "slash", "power", "power-off", "loader", "cloud-upload",
    "cloud-download", "database", "database-backup", "database-zap", "server", "cpu",
    "hard-drive", "hard-drive-download", "hard-drive-upload", "memory-stick", "file",
    "file-text", "file-code", "file-code-2", "file-json", "file-json-2", "file-spreadsheet",
    "file-image", "file-video", "file-audio", "file-archive", "file-plus", "file-minus",
    "file-x", "file-check", "file-search", "file-lock", "file-key", "folder", "folder-open",
    "folder-plus", "folder-minus", "folder-x", "folder-check", "folder-search", "folder-tree",
    "folder-git", "folder-git-2", "folder-cog", "folder-dot", "folder-down", "folder-up",
    "folder-symlink", "folder-lock", "folder-key", "folder-input", "folder-output",
    "archive", "archive-restore", "archive-x", "package", "package-open", "package-check",
    "package-plus", "package-minus", "package-x", "package-search", "inbox", "image",
    "image-plus", "image-minus", "image-off", "images", "camera", "camera-off", "video",
    "video-off", "film", "tv", "tv-2", "monitor", "monitor-off", "monitor-play",
    "monitor-stop", "monitor-pause", "speaker", "volume", "volume-1", "volume-2",
    "volume-x", "mic", "mic-off", "play", "pause", "circle-stop", "skip-back",
    "skip-forward", "rewind", "fast-forward", "repeat", "repeat-1", "repeat-2",
    "shuffle", "music", "music-2", "music-3", "music-4", "headphones", "radio",
    "cast", "airplay", "mail", "mail-open", "mail-check", "mail-minus", "mail-plus",
    "mail-question", "mail-search", "mail-warning", "mail-x", "message-square",
    "message-circle", "message-square-plus", "message-circle-plus", "messages-square",
    "send", "send-horizontal", "at-sign", "phone", "phone-call", "phone-off",
    "phone-incoming", "phone-outgoing", "phone-missed", "phone-forwarded",
    "arrow-up", "arrow-down", "arrow-left", "arrow-right", "arrow-up-left",
    "arrow-up-right", "arrow-down-left", "arrow-down-right", "chevron-up",
    "chevron-down", "chevron-left", "chevron-right", "chevrons-up", "chevrons-down",
    "chevrons-left", "chevrons-right", "corner-up-left", "corner-up-right",
    "corner-down-left", "corner-down-right", "corner-left-up", "corner-right-up",
    "corner-left-down", "corner-right-down", "move-up", "move-down",
    "circle-arrow-up", "circle-arrow-down", "circle-arrow-left", "circle-arrow-right",
    "star", "star-half", "star-off", "heart", "heart-crack", "heart-handshake",
    "thumbs-up", "thumbs-down", "smile", "laugh", "frown", "meh", "angry", "annoyed",
    "circle-alert", "triangle-alert", "octagon-alert", "info", "circle-help",
    "bell", "bell-off", "bell-ring", "bell-dot", "bookmark", "bookmark-plus",
    "bookmark-minus", "bookmark-check", "bookmark-x", "tag", "tags", "badge",
    "badge-check", "badge-alert", "badge-dollar-sign", "shield", "shield-check",
    "shield-alert", "shield-off", "shield-ban", "trophy", "medal", "award",
    "crown", "gem", "gift", "cake", "candy", "coffee", "beer", "wine", "pizza",
    "salad", "sandwich", "apple", "banana", "cherry", "grape", "carrot", "egg",
    "fish", "beef", "ham", "shopping-cart", "shopping-bag", "store", "wallet",
    "credit-card", "dollar-sign", "currency", "coins", "piggy-bank", "receipt",
    "ticket", "qr-code", "barcode", "scan", "scan-line", "scan-barcode", "globe",
    "globe-lock", "earth", "home", "building", "building-2", "hotel", "school",
    "hospital", "church", "castle", "landmark", "factory", "warehouse", "library",
    "tent", "trees", "tree-pine", "flower", "flower-2", "leaf", "sprout",
    "cloud", "cloud-rain", "cloud-snow", "cloud-sun", "cloud-moon", "sun",
    "moon", "sunrise", "sunset", "rainbow", "snowflake", "wind", "tornado",
    "zap", "bolt", "flame", "fire-extinguisher", "thermometer", "droplets",
    "droplet", "umbrella", "anchor", "key", "key-round", "fingerprint",
    "user", "users", "user-plus", "user-minus", "user-check", "user-x",
    "user-cog", "user-search", "circle-user", "bot", "brain", "lightbulb",
    "wand", "sparkles", "rocket", "satellite", "plane", "car", "bus",
    "train-front", "bike", "ship", "truck", "construction", "wrench",
    "hammer", "drill", "scissors-line-dashed", "ruler", "palette",
    "brush", "paint-bucket", "eraser", "glasses", "watch", "smartphone",
    "tablet", "laptop", "keyboard", "mouse", "printer", "code", "terminal",
    "git-branch", "git-commit-horizontal", "git-merge", "git-pull-request",
    "github", "gitlab", "figma"
]

# ── Public tool pages ─────────────────────────────────────────────────────

@tools_bp.route("/")
def index():
    return render_template("tools/index.html")

@tools_bp.route("/playground")
def playground():
    return render_template("tools/playground.html")

@tools_bp.route("/animations")
def animations():
    return render_template("tools/animations.html")

@tools_bp.route("/icons")
def icons():
    return render_template("tools/icons.html", icon_names=ICON_NAMES)

# ── THIS IS THE FIX ──
@tools_bp.route("/components")
@tools_bp.route("/component-library")
def components():
    # Get ALL active components – NO featured filter
    components = UIComponent.query.filter_by(active=True).order_by(UIComponent.order).all()
    categories = db.session.query(UIComponent.category).distinct().all()
    return render_template("tools/components.html",
                           components=components,
                           categories=[c[0] for c in categories],
                           count=len(components))

@tools_bp.route("/json-formatter")
def json_formatter():
    return render_template("tools/json_formatter.html")

@tools_bp.route("/base64")
def base64_tool():
    return render_template("tools/base64.html")

@tools_bp.route("/regex")
def regex_tool():
    return render_template("tools/regex.html")

@tools_bp.route("/color-picker")
def color_picker():
    return render_template("tools/color_picker.html")

@tools_bp.route("/markdown-preview")
def markdown_preview():
    return render_template("tools/markdown_preview.html")

@tools_bp.route("/css-generator")
def css_generator():
    return render_template("tools/css_generator.html")

@tools_bp.route("/code-studio")
def code_studio():
    return render_template("tools/code_studio.html")

# ── API endpoints ─────────────────────────────────────────────────────────

@tools_bp.route("/api/format-json", methods=["POST"])
def api_format_json():
    import json
    data = request.get_json(silent=True) or {}
    raw = data.get("input", "")
    try:
        parsed = json.loads(raw)
        return jsonify({"result": json.dumps(parsed, indent=2), "error": None})
    except Exception as e:
        return jsonify({"result": None, "error": str(e)})

@tools_bp.route("/api/base64", methods=["POST"])
def api_base64():
    import base64
    data = request.get_json(silent=True) or {}
    text = data.get("input", "")
    mode = data.get("mode", "encode")
    try:
        if mode == "encode":
            result = base64.b64encode(text.encode()).decode()
        else:
            result = base64.b64decode(text.encode()).decode()
        return jsonify({"result": result, "error": None})
    except Exception as e:
        return jsonify({"result": None, "error": str(e)})

@tools_bp.route("/api/regex-test", methods=["POST"])
def api_regex_test():
    import re
    data = request.get_json(silent=True) or {}
    pattern = data.get("pattern", "")
    text = data.get("text", "")
    flags_str = data.get("flags", "")
    try:
        fl = 0
        if "i" in flags_str: fl |= re.IGNORECASE
        if "m" in flags_str: fl |= re.MULTILINE
        if "s" in flags_str: fl |= re.DOTALL
        rx = re.compile(pattern, fl)
        matches = [{"match": m.group(), "start": m.start(), "end": m.end(),
                    "groups": list(m.groups())} for m in rx.finditer(text)]
        return jsonify({"matches": matches, "count": len(matches), "error": None})
    except Exception as e:
        return jsonify({"matches": [], "count": 0, "error": str(e)})

# ── Component API ──────────────────────────────────────────────────────────

@tools_bp.route("/api/component/<int:id>")
def api_component(id):
    comp = UIComponent.query.get_or_404(id)
    return jsonify({
        "id": comp.id,
        "name": comp.name,
        "category": comp.category,
        "description": comp.description,
        "html_code": comp.html_code,
        "css_code": comp.css_code or "",
        "js_code": comp.js_code or "",
        "tags": comp.tags,
        "featured": comp.featured,
        "active": comp.active,
        "order": comp.order
    })

@tools_bp.route("/api/component/<int:id>/code")
def api_component_code(id):
    comp = UIComponent.query.get_or_404(id)
    code_type = request.args.get("type", "html")
    code_map = {
        "html": comp.html_code or "",
        "css": comp.css_code or "",
        "js": comp.js_code or ""
    }
    return jsonify({"code": code_map.get(code_type, "")})







@tools_bp.route("/voice-studio")
def voice_studio():
    """Voice Studio — Text-to-Speech workspace."""
    return render_template("tools/voice_studio.html")


@tools_bp.route("/voice-studio/generate", methods=["POST"])
def voice_studio_generate():
    """Generate speech from text. Logged-in users get every generation
    saved to their history automatically (so it can be revisited/starred
    as a favorite later) — anonymous visitors can still generate, it just
    isn't saved anywhere."""
    from app.utils.tts import generate_speech
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    voice_id = data.get("voice_id", "en-US-JennyNeural")
    speed = float(data.get("speed", 1.0))
    if not text:
        return jsonify({"error": "Please enter text to convert."}), 400
    result, error = generate_speech(text, voice_id, speed=speed)
    if error:
        return jsonify({"error": error}), 500

    if current_user.is_authenticated:
        try:
            from app.models.platform import VoiceGeneration
            file_path = result["audio_url"].split("/static/", 1)[-1]
            gen = VoiceGeneration(
                user_id=current_user.id, text=text, voice_id=voice_id,
                voice_name=result.get("voice"), file_path=file_path,
                file_format="mp3", char_count=len(text),
            )
            db.session.add(gen)
            db.session.commit()
            result["generation_id"] = gen.id
        except Exception:
            db.session.rollback()  # saving history is best-effort — generation itself already succeeded

    return jsonify(result)


@tools_bp.route("/voice-studio/record", methods=["POST"])
def voice_studio_record():
    """Save a voice recording captured in-browser (MediaRecorder) to the
    user's personal 'My Voices' library — a real, named, persistent
    library entry (not just a throwaway static file), favorited by
    default. Requires login since it's a personal library.

    Note on scope: this saves the recording for playback/download/reuse
    as an audio clip — it does not clone the voice for text-to-speech.
    Turning a short recording into a synthesized voice needs a paid
    cloning provider; see ELEVENLABS_API_KEY in Admin -> Settings if
    that's wanted later."""
    import os, uuid
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in to save recordings to your voice library."}), 401
    if "audio" not in request.files:
        return jsonify({"error": "No audio received."}), 400
    file = request.files["audio"]
    if not file or not file.filename:
        return jsonify({"error": "No audio received."}), 400
    from app.utils.tts import _audio_dir
    from app.models.platform import UserVoiceSample
    ext = "webm"
    if "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1][:5]
    filename = f"recording_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(_audio_dir(), filename)
    file.save(filepath)

    name = (request.form.get("name") or "").strip() or f"Recording {datetime_now_label()}"
    sample = UserVoiceSample(
        user_id=current_user.id, name=name,
        file_path=f"generated_audio/{filename}", file_format=ext, is_favorite=True,
    )
    db.session.add(sample)
    db.session.commit()
    return jsonify({"audio_url": f"/static/generated_audio/{filename}", "mode": "recording", "sample": sample.to_dict()})


def datetime_now_label():
    from datetime import datetime
    return datetime.utcnow().strftime("%b %d, %H:%M")


@tools_bp.route("/voice-studio/voices")
def voice_studio_voices():
    """List available voices."""
    from app.utils.tts import list_voices
    voices = list_voices()
    return jsonify({"voices": voices})


@tools_bp.route("/voice-studio/my-voices")
def voice_studio_my_voices():
    """List the current user's saved recordings + favorited generations."""
    if not current_user.is_authenticated:
        return jsonify({"recordings": [], "favorites": []})
    from app.models.platform import UserVoiceSample, VoiceGeneration
    recordings = UserVoiceSample.query.filter_by(user_id=current_user.id).order_by(UserVoiceSample.created_at.desc()).all()
    favorites = VoiceGeneration.query.filter_by(user_id=current_user.id, is_favorite=True).order_by(VoiceGeneration.created_at.desc()).all()
    return jsonify({
        "recordings": [r.to_dict() for r in recordings],
        "favorites": [f.to_dict() for f in favorites],
    })


@tools_bp.route("/voice-studio/generation/<int:gen_id>/favorite", methods=["POST"])
def voice_studio_toggle_favorite(gen_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in."}), 401
    from app.models.platform import VoiceGeneration
    gen = VoiceGeneration.query.filter_by(id=gen_id, user_id=current_user.id).first()
    if not gen:
        return jsonify({"error": "Not found."}), 404
    gen.is_favorite = not gen.is_favorite
    db.session.commit()
    return jsonify({"is_favorite": bool(gen.is_favorite)})


@tools_bp.route("/voice-studio/recording/<int:sample_id>", methods=["DELETE"])
def voice_studio_delete_recording(sample_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in."}), 401
    import os
    from flask import current_app
    from app.models.platform import UserVoiceSample
    sample = UserVoiceSample.query.filter_by(id=sample_id, user_id=current_user.id).first()
    if not sample:
        return jsonify({"error": "Not found."}), 404
    filepath = os.path.join(current_app.root_path, "static", sample.file_path)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass
    db.session.delete(sample)
    db.session.commit()
    return jsonify({"deleted": True})


# ══════════════════════════════════════════════════════════════════════
#  GRAPHICS STUDIO
# ══════════════════════════════════════════════════════════════════════


