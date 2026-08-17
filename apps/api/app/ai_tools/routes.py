from flask import Blueprint, render_template, request, jsonify, current_app, Response, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.utils.feature_flags import require_feature
import ipaddress, socket, uuid, os, io
from urllib.parse import urlparse
import requests as _requests
from werkzeug.utils import secure_filename

ai_bp = Blueprint("ai", __name__)

SYSTEM_PROMPTS = {
    "chat":        "You are a helpful AI assistant for Bazillin Studio. Help developers with code, architecture, and technical questions.",
    "code_review": "You are an expert code reviewer. Analyse for bugs, security issues, performance, and style. Return: Issues, Suggestions, Positives.",
    "readme":      "You are a technical writer. Generate a complete professional README.md with all standard sections.",
    "sql":         "You are a SQL expert. Convert natural language to SQL. State dialect. Format cleanly. Explain in one line.",
    "api_design":  "You are a REST API architect. Design a clean REST API. Return: endpoints, schemas, methods, status codes, auth notes.",
    "debug":       "You are a debugging expert. Give: 1) Root cause 2) Exact fix with code 3) How to prevent.",
    "explain":     "You are a technical educator. Explain clearly with analogies and examples at intermediate level.",
    "refactor":    "You are a senior engineer. Refactor the code. Show before/after. Explain each change.",
    "blog_writer": "You are a professional technical writer. Write a complete, engaging, SEO-optimised blog post. Include intro, body with subheadings, and conclusion. Use Markdown.",
    "email_writer":"You are a professional email writer. Write clear, concise, professional emails from the bullet points provided.",
    "prompt_eng":  "You are an expert prompt engineer. Analyse and rewrite the prompt to be clearer, more specific, and more effective for AI systems.",
    "code_explain":"You are a patient technical educator. Explain exactly what this code does, line by line, in simple terms.",
    "test_writer": "You are a senior QA engineer. Write comprehensive unit tests. Cover happy path, edge cases, and error cases.",
    "commit_writer":"You are an expert at writing git commit messages following Conventional Commits. Given a diff or description of changes, write a concise, well-formatted commit message (type(scope): summary, then body bullet points if needed).",
    "docstring":  "You are an expert technical writer. Given a function or class, write a complete, idiomatic docstring/comment block in the appropriate style for the language (e.g. Google-style for Python, JSDoc for JavaScript). Return only the documented code.",
}

def _resolve_ai_provider():
    """DB settings take priority over .env (same pattern as the
    Background Remover key) — lets the admin manage keys from the
    dashboard without redeploying. Falls back to whichever provider
    actually has a key configured if no preference is set.
    Priority order defaults to Groq -> OpenRouter -> Gemini -> Anthropic -> OpenAI."""
    from app.utils.settings import get_setting
    groq_key = get_setting("groq_api_key") or current_app.config.get("GROQ_API_KEY", "")
    openrouter_key = get_setting("openrouter_api_key") or current_app.config.get("OPENROUTER_API_KEY", "")
    gemini_key = get_setting("gemini_api_key") or current_app.config.get("GEMINI_API_KEY", "")
    anthropic_key = get_setting("anthropic_api_key") or current_app.config.get("ANTHROPIC_API_KEY", "")
    openai_key = get_setting("openai_api_key") or current_app.config.get("OPENAI_API_KEY", "")
    preferred = get_setting("preferred_ai_provider") or ""
    keys = {"groq": groq_key, "openrouter": openrouter_key, "gemini": gemini_key,
            "anthropic": anthropic_key, "openai": openai_key}
    if preferred and keys.get(preferred):
        return preferred, keys[preferred]
    for name in ("groq", "openrouter", "gemini", "anthropic", "openai"):
        if keys.get(name):
            return name, keys[name]
    return None, None


def _classify_ai_error(provider, exc):
    """Best-effort classification so the admin log/notice says something
    useful instead of a raw stack trace. Not exhaustive — different SDKs
    raise different exception shapes, so this only pattern-matches on the
    stringified error, which is what's actually available across providers.

    Order matters here: a 413/rate_limit_exceeded "request too large"
    error is checked FIRST, before the generic billing/quota catch-all,
    because Groq's actual wording for that case ("exceeded... quota) on
    tokens per minute (TPM)") trips the word "quota" even though the real
    problem is request size, not billing — that mislabeling previously
    sent people to check their payment method for what was actually a
    too-many-tokens-in-one-request problem."""
    msg = str(exc)
    lowered = msg.lower()
    if "413" in msg or "rate_limit_exceeded" in lowered or "too large" in lowered or "context_length" in lowered or "reduce the length" in lowered or "reduce your" in lowered:
        return f"{provider}: request too large for this model's per-request/rate limit — try a shorter message, or ask your admin to trim the AI conversation history / switch AI model. ({msg})"
    if "402" in msg or "payment" in lowered or "billing" in lowered or "insufficient" in lowered:
        return f"{provider}: billing/quota issue (likely account restriction, expired trial, or exceeded quota) — {msg}"
    if "401" in msg or "403" in msg or ("invalid" in lowered and "key" in lowered) or "unauthorized" in lowered:
        return f"{provider}: authentication issue (likely invalid or revoked API key) — {msg}"
    if "429" in msg or "rate limit" in lowered:
        return f"{provider}: rate limited — {msg}"
    if "timeout" in lowered or "connection" in lowered:
        return f"{provider}: network/connectivity issue — {msg}"
    return f"{provider}: {msg}"


def _get_provider_models(provider):
    """Returns an ordered list of models to try for a given provider, starting
    with the user's configured model (if any), followed by resilient adaptive fallbacks."""
    from app.utils.settings import get_setting

    if provider == "groq":
        # Free & Ultra-Fast Groq tier with adaptive fallbacks if decommissioned/rate-limited
        primary = get_setting("groq_model") or "llama-3.1-8b-instant"
        fallbacks = [
            primary,
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
        ]
    elif provider == "openrouter":
        # OpenRouter Active Free Tier with 100% free endpoints
        primary = get_setting("openrouter_model") or "meta-llama/llama-3.1-8b-instruct:free"
        fallbacks = [
            primary,
            "meta-llama/llama-3.1-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "qwen/qwen-2.5-72b-instruct:free",
            "openrouter/auto",
            "meta-llama/llama-3.3-70b-instruct:free",
        ]
    elif provider == "gemini":
        # Google Gemini fast REST fallback tier
        primary = get_setting("gemini_model") or "gemini-2.5-flash"
        fallbacks = [
            primary,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
    elif provider == "anthropic":
        primary = get_setting("anthropic_model") or "claude-sonnet-5"
        fallbacks = [primary, "claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-4-8"]
    elif provider == "openai":
        primary = get_setting("openai_model") or "gpt-4o"
        fallbacks = [primary, "gpt-4o", "gpt-4o-mini", "o3-mini"]
    else:
        fallbacks = [get_setting(f"{provider}_model") or "default"]

    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for m in fallbacks:
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def _call_ai_single(provider, api_key, system_prompt, messages, max_tokens=2048, temperature=None):
    """Calls exactly one provider with adaptive model-level fallbacks.
    Returns (text, error)."""
    models_to_try = _get_provider_models(provider)
    last_err = None

    if provider == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            for model in models_to_try:
                try:
                    kwargs = dict(model=model, max_tokens=max_tokens, system=system_prompt, messages=messages)
                    if temperature is not None:
                        kwargs["temperature"] = max(0.0, min(1.0, temperature))
                    msg = client.messages.create(**kwargs)
                    return msg.content[0].text, None
                except Exception as model_err:
                    last_err = model_err
                    continue
        except Exception as e:
            return None, _classify_ai_error(provider, e)
        return None, _classify_ai_error(provider, last_err or "Unknown Anthropic error")

    elif provider == "gemini":
        # Plain REST call — no extra SDK dependency.
        import requests as _requests
        contents = [{"role": "user", "parts": [{"text": system_prompt}]},
                    {"role": "model", "parts": [{"text": "Understood."}]}]
        for m in messages:
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        gen_config = {"maxOutputTokens": max_tokens}
        if temperature is not None:
            gen_config["temperature"] = max(0.0, min(1.0, temperature))

        for model in models_to_try:
            try:
                resp = _requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                    json={"contents": contents, "generationConfig": gen_config}, timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text, None
            except Exception as model_err:
                last_err = model_err
                continue
        return None, _classify_ai_error(provider, last_err or "Gemini REST error")

    elif provider in ("openai", "groq", "openrouter"):
        try:
            import openai
            base_urls = {
                "groq": "https://api.groq.com/openai/v1",
                "openrouter": "https://openrouter.ai/api/v1",
            }
            client_kwargs = {"api_key": api_key}
            if provider in base_urls:
                client_kwargs["base_url"] = base_urls[provider]
            
            # OpenRouter requires HTTP-Referer and X-Title headers for ranking and compliance
            if provider == "openrouter":
                client_kwargs["default_headers"] = {
                    "HTTP-Referer": "https://bazillin.com",
                    "X-Title": "Bazillin Studio",
                }

            client = openai.OpenAI(**client_kwargs)
            chat_messages = [{"role": "system", "content": system_prompt}] + messages
            temp = None
            if temperature is not None:
                temp = max(0.0, min(2.0, temperature * 2))

            for model in models_to_try:
                try:
                    kwargs = dict(model=model, max_tokens=max_tokens, messages=chat_messages)
                    if temp is not None:
                        kwargs["temperature"] = temp
                    resp = client.chat.completions.create(**kwargs)
                    text = resp.choices[0].message.content
                    if text is not None:
                        return text, None
                except Exception as model_err:
                    last_err = model_err
                    # Auto-fallback to next model in provider list
                    continue
        except Exception as e:
            return None, _classify_ai_error(provider, e)
        return None, _classify_ai_error(provider, last_err or f"{provider} completion failed")

    else:
        return None, f"Unknown AI provider: {provider}"


def _configured_providers_in_order():
    """Ordered list of (provider, api_key) for every provider that actually
    has a key set, preferred provider first.
    Default order: Groq -> OpenRouter -> Gemini -> Anthropic -> OpenAI."""
    from app.utils.settings import get_setting
    groq_key = get_setting("groq_api_key") or current_app.config.get("GROQ_API_KEY", "")
    openrouter_key = get_setting("openrouter_api_key") or current_app.config.get("OPENROUTER_API_KEY", "")
    gemini_key = get_setting("gemini_api_key") or current_app.config.get("GEMINI_API_KEY", "")
    anthropic_key = get_setting("anthropic_api_key") or current_app.config.get("ANTHROPIC_API_KEY", "")
    openai_key = get_setting("openai_api_key") or current_app.config.get("OPENAI_API_KEY", "")
    keys = {"groq": groq_key, "openrouter": openrouter_key, "gemini": gemini_key,
            "anthropic": anthropic_key, "openai": openai_key}
    preferred = get_setting("preferred_ai_provider") or ""
    order = []
    if preferred and keys.get(preferred):
        order.append(preferred)
    for name in ("groq", "openrouter", "gemini", "anthropic", "openai"):
        if name not in order and keys.get(name):
            order.append(name)
    return [(name, keys[name]) for name in order]


def _record_ai_failover(note):
    """Logs a provider failure to the same rotating file the rest of the
    app's errors go to (see app/__init__.py), and to a small in-DB setting
    so it can be surfaced on System Health without tailing a log file.
    Best-effort only — a failure here should never break the actual AI
    call it's reporting on."""
    try:
        current_app.logger.warning("AI provider failover: %s", note)
    except Exception:
        pass
    try:
        from app.utils.settings import set_setting
        import datetime
        set_setting("last_ai_failover", f"{datetime.datetime.utcnow().isoformat()}Z — {note}")
    except Exception:
        pass


def _call_ai(system_prompt, messages, max_tokens=2048, temperature=None):
    """Tries the preferred/first-configured provider; on failure, logs the
    reason and automatically retries the next configured provider in order
    (this is the actual failover — previously a broken preferred provider
    just returned its error straight to the user with no fallback attempt).
    Only returns an error once every configured provider has been tried."""
    providers = _configured_providers_in_order()
    if not providers:
        return None, "AI not configured — set an Anthropic, Gemini, OpenAI, Groq, or OpenRouter API key in Admin -> Settings -> AI Providers"

    errors = []
    for i, (provider, api_key) in enumerate(providers):
        text, err = _call_ai_single(provider, api_key, system_prompt, messages, max_tokens, temperature)
        if text is not None:
            if i > 0:
                _record_ai_failover(
                    f"{providers[0][0]} failed ({errors[0]}); succeeded on fallback provider '{provider}'."
                )
            if current_user.is_authenticated:
                from app.utils.credits import deduct_credits
                deduct_credits(current_user.id, 1, type="usage", reason="AI generation")
            return text, None
        errors.append(err)

    # every configured provider failed
    combined = " | ".join(errors)
    _record_ai_failover(f"All configured providers failed: {combined}")
    return None, combined

@ai_bp.route("/")
@require_feature("ai_tools_enabled")
def index():
    credits = current_user.credits if current_user.is_authenticated else 0
    return render_template("ai_tools/index.html", credits=credits)

@ai_bp.route("/chat")
@require_feature("ai_tools_enabled")
def chat_page():
    return render_template("ai_tools/chat.html")

@ai_bp.route("/code-review")
@require_feature("ai_tools_enabled")
def code_review_page():
    return render_template("ai_tools/code_review.html")

@ai_bp.route("/readme-gen")
@require_feature("ai_tools_enabled")
def readme_gen_page():
    return render_template("ai_tools/readme_gen.html")

@ai_bp.route("/sql-gen")
@require_feature("ai_tools_enabled")
def sql_gen_page():
    return render_template("ai_tools/sql_gen.html")

@ai_bp.route("/api-design")
@require_feature("ai_tools_enabled")
def api_design_page():
    return render_template("ai_tools/api_design.html")

@ai_bp.route("/debugger")
@require_feature("ai_tools_enabled")
def debugger_page():
    return render_template("ai_tools/debugger.html")

@ai_bp.route("/bg-remove")
def bg_remove():
    return render_template("ai_tools/bg_remove.html")

@ai_bp.route("/img-compress")
def img_compress():
    return render_template("ai_tools/img_compress.html")

@ai_bp.route("/img-convert")
def img_convert():
    return render_template("ai_tools/img_convert.html")

@ai_bp.route("/csv-analyzer")
def csv_analyzer():
    return render_template("ai_tools/csv_analyzer.html")

@ai_bp.route("/text-utils")
def text_utils():
    return render_template("ai_tools/text_utils.html")

@ai_bp.route("/password-gen")
def password_gen():
    return render_template("ai_tools/password_gen.html")

@ai_bp.route("/timestamp")
def timestamp():
    return render_template("ai_tools/timestamp.html")

@ai_bp.route("/number-base")
def number_base():
    return render_template("ai_tools/number_base.html")

@ai_bp.route("/url-encode")
def url_encode():
    return render_template("ai_tools/url_encode.html")

@ai_bp.route("/diff-checker")
def diff_checker():
    return render_template("ai_tools/diff_checker.html")

@ai_bp.route("/blog-writer")
@require_feature("ai_tools_enabled")
def blog_writer_page():
    return render_template("ai_tools/blog_writer.html")

@ai_bp.route("/email-writer")
@require_feature("ai_tools_enabled")
def email_writer_page():
    return render_template("ai_tools/email_writer.html")

@ai_bp.route("/prompt-engineer")
@require_feature("ai_tools_enabled")
def prompt_eng_page():
    return render_template("ai_tools/prompt_eng.html")

@ai_bp.route("/code-explain")
@require_feature("ai_tools_enabled")
def code_explain_page():
    return render_template("ai_tools/code_explain.html")

@ai_bp.route("/test-writer")
@require_feature("ai_tools_enabled")
def test_writer_page():
    return render_template("ai_tools/test_writer.html")

@ai_bp.route('/s/<code>')
def redirect_short(code):
    from app.models.core import ShortenedUrl
    short = ShortenedUrl.query.filter_by(code=code).first_or_404()
    short.clicks += 1
    db.session.commit()
    return redirect(short.original)

# ── File to URL (upload) ──
@ai_bp.route("/file-to-url", methods=['GET', 'POST'])
@require_feature("ai_tools_enabled")
def file_to_url():
    from app.models import MediaFile
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Please select a file', 'danger')
            return redirect(url_for('ai.file_to_url'))
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        filename = f"{uuid.uuid4().hex}.{ext}"
        folder = 'uploads'
        upload_dir = os.path.join(current_app.static_folder, folder)
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        mf = MediaFile(
            filename=filename,
            original_name=secure_filename(file.filename),
            file_type='image' if ext in ('png','jpg','jpeg','gif','webp') else 'document',
            mime_type=file.content_type or '',
            size=os.path.getsize(filepath),
            url=f'/static/{folder}/{filename}',
            folder=folder,
            uploaded_by=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(mf)
        db.session.commit()
        return render_template('ai_tools/file_to_url.html',
                               file_url=mf.url,
                               original_name=mf.original_name,
                               file_size=mf.size)
    return render_template('ai_tools/file_to_url.html')

# ── URL to File (download from URL) ──
@ai_bp.route("/url-to-file", methods=['GET', 'POST'])
@require_feature("ai_tools_enabled")
def url_to_file():
    if request.method == 'POST':
        import time
        url = request.form.get('url')
        if not url:
            flash('URL is required', 'danger')
            return redirect(url_for('ai.url_to_file'))
        safe, reason = _is_safe_url(url)
        if not safe:
            flash(reason, 'danger')
            return redirect(url_for('ai.url_to_file'))
        HARD_DEADLINE_SECONDS = 25
        started = time.monotonic()
        try:
            resp = _requests.get(url, stream=True, timeout=(10, 15), headers={"User-Agent": "BazillinStudio-URLFetcher/1.0"})
            resp.raise_for_status()
            chunks, total = [], 0
            for chunk in resp.iter_content(chunk_size=65536):
                if time.monotonic() - started > HARD_DEADLINE_SECONDS:
                    resp.close()
                    flash(f'That file is taking too long to download (over {HARD_DEADLINE_SECONDS}s) — the source may be slow or the file too large.', 'danger')
                    return redirect(url_for('ai.url_to_file'))
                total += len(chunk)
                if total > MAX_FETCH_BYTES:
                    resp.close()
                    flash('File exceeds the 50 MB limit.', 'danger')
                    return redirect(url_for('ai.url_to_file'))
                chunks.append(chunk)
            filename = url.split('/')[-1].split('?')[0] or 'download'
            return send_file(
                io.BytesIO(b"".join(chunks)),
                as_attachment=True,
                download_name=filename,
                mimetype=resp.headers.get('content-type', 'application/octet-stream')
            )
        except _requests.exceptions.Timeout:
            flash('The source took too long to respond. Try again or use a different link.', 'danger')
            return redirect(url_for('ai.url_to_file'))
        except Exception as e:
            flash(f'Failed to fetch file: {str(e)}', 'danger')
            return redirect(url_for('ai.url_to_file'))
    return render_template('ai_tools/url_to_file.html')

# ── Background Removal V2 (AI-quality, requires a remove.bg API key —
#    configurable in Admin -> Settings -> Background Remover, or via
#    REMOVEBG_API_KEY in .env as a fallback if the admin setting is blank) ──
def _removebg_api_key():
    from app.utils.settings import get_setting
    return get_setting("removebg_api_key") or current_app.config.get('REMOVEBG_API_KEY')


@ai_bp.route('/bg-remove-v2', methods=['POST'])
@login_required
def bg_remove_v2():
    api_key = _removebg_api_key()
    if not api_key:
        return jsonify({
            'error': 'AI background removal isn\'t configured yet. '
                     'An admin needs to set a remove.bg API key in Admin -> Settings -> Background Remover. '
                     'The free in-browser tool above still works without any setup.'
        }), 503

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    try:
        from app.utils.settings import get_setting
        size = get_setting("removebg_size") or "auto"
        resp = _requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': (file.filename, file.stream, file.mimetype)},
            data={'size': size},
            headers={'X-Api-Key': api_key},
            timeout=30,
        )
        if resp.status_code != 200:
            try:
                detail = resp.json().get('errors', [{}])[0].get('title', 'Unknown error')
            except Exception:
                detail = resp.text[:200]
            return jsonify({'error': f'Background removal failed: {detail}'}), 502
        return send_file(io.BytesIO(resp.content), mimetype='image/png',
                          as_attachment=False, download_name='removed_bg.png')
    except _requests.RequestException as e:
        return jsonify({'error': f'Could not reach the background removal service: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/api/bg-remove-status')
def bg_remove_status():
    """Lets the frontend know whether the AI-quality path is available."""
    return jsonify({'ai_available': bool(_removebg_api_key())})

# ── API endpoints ──
@ai_bp.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining. Contact admin."}), 402
    data = request.get_json(silent=True) or {}
    tool = data.get("tool", "chat")
    messages = data.get("messages", [])
    system = SYSTEM_PROMPTS.get(tool, SYSTEM_PROMPTS["chat"])
    text, err = _call_ai(system, messages)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

@ai_bp.route("/api/code-review", methods=["POST"])
@login_required
def api_code_review():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining."}), 402
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    lang = data.get("language", "")
    messages = [{"role": "user", "content": f"Review this {lang} code:\n\n```{lang}\n{code}\n```"}]
    text, err = _call_ai(SYSTEM_PROMPTS["code_review"], messages, max_tokens=3000)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

@ai_bp.route("/api/readme", methods=["POST"])
@login_required
def api_readme():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining."}), 402
    data = request.get_json(silent=True) or {}
    info = data.get("project_info", "")
    messages = [{"role": "user", "content": f"Generate a README for:\n\n{info}"}]
    text, err = _call_ai(SYSTEM_PROMPTS["readme"], messages, max_tokens=4000)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

@ai_bp.route("/api/sql", methods=["POST"])
@login_required
def api_sql():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining."}), 402
    data = request.get_json(silent=True) or {}
    prompt = f"Dialect: {data.get('dialect','PostgreSQL')}\nSchema:\n{data.get('schema','')}\nRequest: {data.get('description','')}"
    text, err = _call_ai(SYSTEM_PROMPTS["sql"], [{"role":"user","content":prompt}], max_tokens=2000)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

@ai_bp.route("/api/api-design", methods=["POST"])
@login_required
def api_api_design():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining."}), 402
    data = request.get_json(silent=True) or {}
    messages = [{"role":"user","content":f"Design a REST API for:\n\n{data.get('requirements','')}"}]
    text, err = _call_ai(SYSTEM_PROMPTS["api_design"], messages, max_tokens=3000)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

@ai_bp.route("/api/debug", methods=["POST"])
@login_required
def api_debug():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining."}), 402
    data = request.get_json(silent=True) or {}
    messages = [{"role":"user","content":f"Error:\n{data.get('error','')}\n\nCode:\n```\n{data.get('code','')}\n```"}]
    text, err = _call_ai(SYSTEM_PROMPTS["debug"], messages, max_tokens=3000)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

@ai_bp.route("/api/generic", methods=["POST"])
@login_required
def api_generic():
    if current_user.credits <= 0:
        return jsonify({"error": "No credits remaining."}), 402
    data = request.get_json(silent=True) or {}
    tool = data.get("tool", "chat")
    content = data.get("content", "")
    system = SYSTEM_PROMPTS.get(tool, SYSTEM_PROMPTS["chat"])
    text, err = _call_ai(system, [{"role":"user","content":content}], max_tokens=3000)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"response": text, "credits_left": current_user.credits})

MAX_FETCH_BYTES = 50 * 1024 * 1024
# The tool's own UI promises "video, image, document" — but this only
# allowed application/pdf as a "document" type, so any real-world direct
# link to a .docx/.xlsx/.zip/.csv/.txt file (all common "document" links)
# was rejected with a confusing "only downloads media files" error. That
# mismatch between what the tool advertises and what it actually accepts
# is almost certainly what "still not working" reports were hitting.
ALLOWED_FETCH_TYPES = (
    "video/", "image/", "audio/",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument",  # .docx/.xlsx/.pptx
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/zip", "application/x-zip-compressed",
    "application/x-rar-compressed", "application/vnd.rar",
    "application/x-7z-compressed",
    "text/plain", "text/csv",
    "application/json",
    "application/octet-stream",
)

def _is_safe_url(url: str) -> tuple:
    """Returns (ok: bool, reason: str) — separate DNS failures from
    actual security blocks so the error message is honest about which
    happened, instead of lumping 'domain doesn't exist' and 'points to
    a private IP' into one confusing message."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "URL must start with http:// or https://"
        host = parsed.hostname
        if not host:
            return False, "Could not parse a hostname from that URL."
    except Exception:
        return False, "That doesn't look like a valid URL."
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, f"Could not resolve '{host}' — check the domain is spelled correctly."
    except Exception as e:
        return False, f"Could not resolve host: {e}"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, "That address points to a private/internal network and can't be fetched."
    return True, ""

@ai_bp.route("/api/url-fetch", methods=["POST"])
@login_required
def api_url_fetch():
    import time
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided."}), 400
    safe, reason = _is_safe_url(url)
    if not safe:
        return jsonify({"error": reason}), 400
    HARD_DEADLINE_SECONDS = 25
    started = time.monotonic()
    try:
        # (connect_timeout, read_timeout) — read_timeout bounds each individual
        # socket read, so a server that goes silent mid-response fails fast
        # instead of hanging. The elapsed-time check below additionally caps
        # the *total* download time for slow-but-steady connections.
        resp = _requests.get(url, stream=True, timeout=(10, 15), headers={"User-Agent": "BazillinStudio-URLFetcher/1.0"})
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        if not any(content_type.startswith(t) for t in ALLOWED_FETCH_TYPES):
            hint = " That looks like a webpage, not a direct file link — right-click the actual file/image and copy its direct link instead." if content_type.startswith("text/html") else ""
            return jsonify({"error": f"This tool only downloads media and document files (image/video/audio/PDF/Word/Excel/zip/etc.), and that URL returned '{content_type}'.{hint}"}), 415
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if time.monotonic() - started > HARD_DEADLINE_SECONDS:
                resp.close()
                return jsonify({"error": f"That file is taking too long to download (over {HARD_DEADLINE_SECONDS}s) — the source may be slow or the file too large. Try a smaller file or a different host."}), 504
            total += len(chunk)
            if total > MAX_FETCH_BYTES:
                resp.close()
                return jsonify({"error": "File exceeds the 50 MB limit."}), 413
            chunks.append(chunk)
        return Response(b"".join(chunks), mimetype=content_type)
    except _requests.exceptions.Timeout:
        return jsonify({"error": "The source took too long to respond. Try again or use a different link."}), 504
    except _requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not fetch URL: {str(e)}"}), 502
