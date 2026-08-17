"""
Browser-native AI tool routes — no API key needed.
These mostly just render templates; the logic is all client-side JS.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from flask_login import current_user, login_required
from app.utils.feature_flags import require_feature
import requests

ai_browser_bp = Blueprint("ai_browser", __name__)

@ai_browser_bp.route("/background-remover")
def background_remover():
    return render_template("ai_tools/background_remover.html")

@ai_browser_bp.route("/image-compress")
def image_compress():
    return redirect(url_for("ai.img_compress"))

@ai_browser_bp.route("/image-resize")
def image_resize():
    return render_template("ai_tools/image_resize.html")

@ai_browser_bp.route("/pdf-to-text")
def pdf_to_text():
    return render_template("ai_tools/pdf_to_text.html")

@ai_browser_bp.route("/pdf-merge")
def pdf_merge():
    return render_template("ai_tools/pdf_merge.html")

@ai_browser_bp.route("/pdf-editor")
def pdf_editor():
    return render_template("ai_tools/pdf_editor.html")

@ai_browser_bp.route("/pdf-converter")
def pdf_converter():
    return render_template("ai_tools/pdf_converter.html")

# ── Document & Media Converters ───────────────────────────────────────────
@ai_browser_bp.route("/image-to-text")
def image_to_text_page():
    return render_template("tools/image_to_text.html")

@ai_browser_bp.route("/api/image-to-text", methods=["POST"])
def api_image_to_text():
    from app.tools.converter_tools import image_to_text_engine
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No image file provided."}), 400
    img_bytes = file.read()
    res = image_to_text_engine(img_bytes, file.filename)
    return jsonify(res)

@ai_browser_bp.route("/image-to-word")
def image_to_word_page():
    return render_template("tools/image_to_word.html")

@ai_browser_bp.route("/api/image-to-word", methods=["POST"])
def api_image_to_word():
    from flask import Response
    from app.tools.converter_tools import image_to_word_engine
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No image file provided."}), 400
    try:
        docx_bytes = image_to_word_engine(file.read(), file.filename)
    except Exception as e:
        current_app.logger.exception("image_to_word failed")
        return jsonify({"error": f"Couldn't convert this image: {e}"}), 500
    filename = (file.filename.rsplit(".", 1)[0] if "." in file.filename else "Document") + ".doc"
    return Response(docx_bytes, mimetype="application/msword",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@ai_browser_bp.route("/pdf-to-word")
def pdf_to_word_page():
    return render_template("tools/pdf_to_word.html")

@ai_browser_bp.route("/api/pdf-to-word", methods=["POST"])
def api_pdf_to_word():
    from flask import Response
    from app.tools.converter_tools import pdf_to_word_engine
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No PDF file provided."}), 400
    try:
        docx_bytes = pdf_to_word_engine(file.read())
    except Exception as e:
        current_app.logger.exception("pdf_to_word failed")
        return jsonify({"error": f"Couldn't convert this PDF: {e}"}), 500
    filename = (file.filename.rsplit(".", 1)[0] if "." in file.filename else "Converted") + ".docx"
    return Response(docx_bytes, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@ai_browser_bp.route("/word-to-pdf")
def word_to_pdf_page():
    return render_template("tools/word_to_pdf.html")

@ai_browser_bp.route("/api/word-to-pdf", methods=["POST"])
def api_word_to_pdf():
    from flask import Response, flash
    from app.tools.converter_tools import word_to_pdf_engine
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No Word document provided.", "danger")
        return redirect(url_for("ai_browser.word_to_pdf_page"))
    try:
        pdf_bytes = word_to_pdf_engine(file.read())
    except ValueError as e:
        # Known, explained failure (legacy .doc, corrupt file, etc.)
        flash(str(e), "danger")
        return redirect(url_for("ai_browser.word_to_pdf_page"))
    except Exception as e:
        current_app.logger.exception("word_to_pdf failed")
        flash(f"Couldn't convert this file: {e}", "danger")
        return redirect(url_for("ai_browser.word_to_pdf_page"))
    filename = (file.filename.rsplit(".", 1)[0] if "." in file.filename else "Converted") + ".pdf"
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@ai_browser_bp.route("/social-downloader")
def social_downloader_page():
    return render_template("tools/social_downloader.html")

@ai_browser_bp.route("/api/social-download", methods=["POST"])
def api_social_download():
    from app.tools.converter_tools import social_media_download_engine
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "No social media URL provided."}), 400
    try:
        res = social_media_download_engine(url)
    except Exception as e:
        current_app.logger.exception("social_media_download failed")
        return jsonify({"error": f"Couldn't fetch this media: {e}"}), 500
    return jsonify(res)

@ai_browser_bp.route("/webpage-to-pdf")
def url_to_file_page():
    return render_template("tools/url_to_file.html")

@ai_browser_bp.route("/api/webpage-to-pdf", methods=["POST"])
def api_url_to_file():
    from flask import Response
    from app.tools.converter_tools import url_to_file_engine
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    output_format = data.get("format", "pdf")
    if not url:
        return jsonify({"error": "No URL provided."}), 400
    try:
        file_bytes = url_to_file_engine(url, output_format)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Couldn't fetch that URL: {e}"}), 502
    except Exception as e:
        current_app.logger.exception("webpage_to_pdf failed")
        return jsonify({"error": f"Couldn't convert that page: {e}"}), 500
    mime = "application/pdf" if output_format == "pdf" else "text/html"
    ext = "pdf" if output_format == "pdf" else "html"
    return Response(file_bytes, mimetype=mime,
                    headers={"Content-Disposition": f"attachment; filename=webpage_export.{ext}"})

@ai_browser_bp.route("/upload-to-url")
@login_required
def upload_to_url_page():
    return render_template("ai_tools/upload_to_url.html")

@ai_browser_bp.route("/api/upload-to-url", methods=["POST"])
@login_required
def api_upload_to_url():
    import os, uuid
    from werkzeug.utils import secure_filename
    from app.models.content import MediaFile
    from app.extensions import db

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400

    MAX_BYTES = 25 * 1024 * 1024  # 25 MB cap for user uploads
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_BYTES:
        return jsonify({"error": "File exceeds the 25 MB limit."}), 413

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    blocked_ext = {"exe", "bat", "sh", "cmd", "msi", "php", "py", "js"}
    if ext in blocked_ext:
        return jsonify({"error": f".{ext} files are not allowed for security reasons."}), 415

    filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    upload_dir = os.path.join(current_app.static_folder, "uploads", "user-uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    file_type = ("image" if ext in {"png","jpg","jpeg","gif","webp","svg"} else
                 "video" if ext in {"mp4","webm","mov"} else
                 "audio" if ext in {"mp3","wav","ogg"} else
                 "document" if ext in {"pdf","docx","doc","txt","csv","xlsx"} else "other")

    mf = MediaFile(filename=filename, original_name=secure_filename(file.filename),
                   file_type=file_type, mime_type=file.content_type or "",
                   size=os.path.getsize(filepath),
                   url=f"/static/uploads/user-uploads/{filename}",
                   folder="user-uploads", uploaded_by=current_user.id)
    db.session.add(mf)
    db.session.commit()

    full_url = request.host_url.rstrip("/") + mf.url
    return jsonify({"success": True, "url": full_url, "filename": mf.original_name,
                     "size": mf.size, "type": mf.file_type})

@ai_browser_bp.route("/url-downloader")
def url_downloader():
    return render_template("ai_tools/url_downloader.html")

@ai_browser_bp.route("/url-shortener")
def url_shortener_page():
    return render_template("ai_tools/url_shortener.html")

@ai_browser_bp.route("/api/shorten", methods=["POST"])
def api_shorten():
    from app.shorturl.routes import generate_code
    from app.models.platform import ShortUrl
    from app.extensions import db
    from urllib.parse import urlparse

    data = request.get_json(silent=True) or {}
    target = (data.get("url") or "").strip()
    if not target:
        return jsonify({"error": "Please provide a URL."}), 400
    parsed = urlparse(target)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({"error": "Please provide a valid http(s) URL."}), 400

    code = generate_code()
    link = ShortUrl(code=code, target_url=target,
                    user_id=current_user.id if current_user.is_authenticated else None)
    db.session.add(link)
    db.session.commit()
    short_url = request.host_url.rstrip("/") + url_for("shorturl.resolve", code=code)
    return jsonify({"success": True, "short_url": short_url, "code": code, "id": link.id})

@ai_browser_bp.route("/api/my-links")
@login_required
def api_my_links():
    from app.models.platform import ShortUrl
    links = ShortUrl.query.filter_by(user_id=current_user.id).order_by(ShortUrl.created_at.desc()).limit(50).all()
    return jsonify({"links": [
        {"id": l.id, "code": l.code, "target_url": l.target_url,
         "short_url": request.host_url.rstrip("/") + url_for("shorturl.resolve", code=l.code),
         "click_count": l.click_count, "created_at": l.created_at.strftime("%Y-%m-%d %H:%M")}
        for l in links
    ]})

@ai_browser_bp.route("/api/shorten/<int:link_id>/delete", methods=["POST"])
@login_required
def api_delete_short_link(link_id):
    from app.models.platform import ShortUrl
    from app.extensions import db
    link = ShortUrl.query.get_or_404(link_id)
    if link.user_id != current_user.id:
        return jsonify({"error": "Not authorized."}), 403
    db.session.delete(link)
    db.session.commit()
    return jsonify({"success": True})

@ai_browser_bp.route("/hash-generator")
def hash_generator():
    return render_template("ai_tools/hash_generator.html")

@ai_browser_bp.route("/uuid-generator")
def uuid_generator():
    return render_template("ai_tools/uuid_generator.html")

@ai_browser_bp.route("/qr-generator")
def qr_generator():
    return render_template("ai_tools/qr_generator.html")

@ai_browser_bp.route("/word-counter")
def word_counter():
    return render_template("ai_tools/word_counter.html")

@ai_browser_bp.route("/lorem-ipsum")
def lorem_ipsum():
    return render_template("ai_tools/lorem_ipsum.html")

@ai_browser_bp.route("/password-generator")
def password_generator():
    return redirect(url_for("ai.password_gen"))

@ai_browser_bp.route("/timestamp-converter")
def timestamp_converter():
    return redirect(url_for("ai.timestamp"))

@ai_browser_bp.route("/minifier")
def minifier():
    return render_template("ai_tools/minifier.html")

# ── Claude AI tools ──────────────────────────────────────────────────────

@ai_browser_bp.route("/explainer")
def explainer_page():
    return redirect(url_for("ai.code_explain_page"))

@ai_browser_bp.route("/refactor")
@require_feature("ai_tools_enabled")
def refactor_page():
    return render_template("ai_tools/refactor.html")

@ai_browser_bp.route("/ai-regex")
def ai_regex_page():
    return render_template("ai_tools/ai_regex.html")

@ai_browser_bp.route("/commit-writer")
@require_feature("ai_tools_enabled")
def commit_writer_page():
    return render_template("ai_tools/commit_writer.html")

@ai_browser_bp.route("/docstring")
@require_feature("ai_tools_enabled")
def docstring_page():
    return render_template("ai_tools/docstring.html")


# ── Client-side-only tool pages (no backend logic needed) ──────────────────

@ai_browser_bp.route("/jwt-decoder")
def jwt_decoder_page():
    return render_template("ai_tools/jwt_decoder.html")

@ai_browser_bp.route("/json-diff")
def json_diff_page():
    return render_template("ai_tools/json_diff.html")

@ai_browser_bp.route("/gradient-generator")
def gradient_generator_page():
    return render_template("ai_tools/gradient_tailwind.html")

@ai_browser_bp.route("/meta-tags")
def meta_tags_page():
    return render_template("ai_tools/meta_tags.html")

@ai_browser_bp.route("/sql-formatter")
def sql_formatter_page():
    return render_template("ai_tools/sql_formatter.html")

@ai_browser_bp.route("/api-tester")
def api_tester_page():
    return render_template("ai_tools/api_tester.html")


# ── Real network diagnostic tools (genuine protocol clients, no API key) ───

@ai_browser_bp.route("/dns-lookup")
def dns_lookup_page():
    return render_template("ai_tools/dns_lookup.html")

@ai_browser_bp.route("/api/dns-lookup", methods=["POST"])
def api_dns_lookup():
    import socket
    domain = (request.get_json(silent=True) or {}).get("domain", "").strip().lower()
    domain = domain.replace("http://", "").replace("https://", "").split("/")[0]
    if not domain:
        return jsonify({"error": "Enter a domain name."}), 400
    try:
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(domain)
    except socket.gaierror as e:
        return jsonify({"error": f"Could not resolve '{domain}': {e}"}), 502
    reverse = []
    for ip in ip_addresses:
        try:
            rev_host, _, _ = socket.gethostbyaddr(ip)
            reverse.append({"ip": ip, "reverse": rev_host})
        except Exception:
            reverse.append({"ip": ip, "reverse": None})
    return jsonify({"hostname": hostname, "aliases": aliases, "addresses": reverse})


@ai_browser_bp.route("/ssl-checker")
def ssl_checker_page():
    return render_template("ai_tools/ssl_checker.html")

@ai_browser_bp.route("/api/ssl-checker", methods=["POST"])
def api_ssl_checker():
    import ssl, socket
    from datetime import datetime as dt
    domain = (request.get_json(silent=True) or {}).get("domain", "").strip().lower()
    domain = domain.replace("http://", "").replace("https://", "").split("/")[0]
    if not domain:
        return jsonify({"error": "Enter a domain name."}), 400
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
    except Exception as e:
        return jsonify({"error": f"Could not connect: {e}"}), 502

    def fmt_name(tup):
        return ", ".join(f"{k}={v}" for entry in tup for k, v in entry)

    not_before = dt.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
    not_after = dt.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days_left = (not_after - dt.utcnow()).days
    return jsonify({
        "subject": fmt_name(cert.get("subject", [])),
        "issuer": fmt_name(cert.get("issuer", [])),
        "valid_from": not_before.strftime("%Y-%m-%d"),
        "valid_until": not_after.strftime("%Y-%m-%d"),
        "days_remaining": days_left,
        "is_expired": days_left < 0,
        "san": cert.get("subjectAltName", []),
    })


@ai_browser_bp.route("/whois-lookup")
def whois_lookup_page():
    return render_template("ai_tools/whois_lookup.html")

@ai_browser_bp.route("/api/whois-lookup", methods=["POST"])
def api_whois_lookup():
    import socket

    domain = (request.get_json(silent=True) or {}).get("domain", "").strip().lower()
    domain = domain.replace("http://", "").replace("https://", "").split("/")[0]
    if not domain or "." not in domain:
        return jsonify({"error": "Enter a valid domain name."}), 400

    tld_servers = {
        "com": "whois.verisign-grs.com", "net": "whois.verisign-grs.com",
        "org": "whois.pir.org", "io": "whois.nic.io", "dev": "whois.nic.google",
        "app": "whois.nic.google", "co": "whois.nic.co", "info": "whois.afilias.net",
        "biz": "whois.nic.biz", "me": "whois.nic.me", "ai": "whois.nic.ai",
        "xyz": "whois.nic.xyz", "tech": "whois.nic.tech",
    }
    tld = domain.rsplit(".", 1)[-1]
    server = tld_servers.get(tld, "whois.iana.org")

    def query(host, query_domain, timeout=8):
        with socket.create_connection((host, 43), timeout=timeout) as sock:
            sock.sendall((query_domain + "\r\n").encode())
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks).decode(errors="replace")

    try:
        raw = query(server, domain)
        # Follow referral for thin registries (e.g. .com via Verisign points to the actual registrar)
        for line in raw.splitlines():
            if line.lower().startswith("registrar whois server:"):
                referral = line.split(":", 1)[1].strip()
                if referral and referral != server:
                    try:
                        raw = query(referral, domain)
                    except Exception:
                        pass
                break
    except Exception as e:
        return jsonify({"error": f"WHOIS query failed: {e}"}), 502

    return jsonify({"raw": raw, "server_queried": server})


# ── Audio Tools ─────────────────────────────────────────────────────────────

@ai_browser_bp.route("/audio-meta")
def audio_meta():
    return render_template("ai_tools/audio_meta.html")


# ── Video Tools ─────────────────────────────────────────────────────────────

@ai_browser_bp.route("/mov-to-mp4")
def mov_to_mp4_page():
    return render_template("tools/mov_to_mp4.html")

@ai_browser_bp.route("/api/mov-to-mp4", methods=["POST"])
def api_mov_to_mp4():
    from flask import Response
    from app.tools.converter_tools import mov_to_mp4_engine
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No video file provided."}), 400
    try:
        mp4_bytes = mov_to_mp4_engine(file.read())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("mov_to_mp4 failed")
        return jsonify({"error": f"Couldn't convert this video: {e}"}), 500
    filename = (file.filename.rsplit(".", 1)[0] if "." in file.filename else "Converted") + ".mp4"
    return Response(mp4_bytes, mimetype="video/mp4",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@ai_browser_bp.route("/video-compressor")
def video_compressor_page():
    return render_template("tools/video_compressor.html")

@ai_browser_bp.route("/api/video-compressor", methods=["POST"])
def api_video_compressor():
    from flask import Response
    from app.tools.converter_tools import video_compress_engine
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No video file provided."}), 400
    quality = request.form.get("quality", "balanced")
    try:
        original_size = file.stream.seek(0, 2) or 0
        file.stream.seek(0)
        compressed_bytes = video_compress_engine(file.read(), filename=file.filename, target_quality=quality)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("video_compressor failed")
        return jsonify({"error": f"Couldn't compress this video: {e}"}), 500
    filename = (file.filename.rsplit(".", 1)[0] if "." in file.filename else "Compressed") + "_compressed.mp4"
    resp = Response(compressed_bytes, mimetype="video/mp4",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
    resp.headers["X-Original-Size"] = str(original_size)
    resp.headers["X-Compressed-Size"] = str(len(compressed_bytes))
    return resp