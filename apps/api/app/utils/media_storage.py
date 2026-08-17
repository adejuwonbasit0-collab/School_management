"""
Media storage backend — local disk (default) or Cloudinary, whichever is
selected in Admin -> Settings -> Media Storage. Every upload endpoint should
go through save_upload() instead of writing file.save(...) itself, so
switching backends actually takes effect everywhere at once.
"""
import os
import uuid
from werkzeug.utils import secure_filename


def _cloudinary_configured():
    from app.utils.settings import get_setting
    return bool(get_setting("cloudinary_cloud_name") and get_setting("cloudinary_api_key") and get_setting("cloudinary_api_secret"))


def save_upload(file_storage, folder, app):
    """file_storage: a werkzeug FileStorage (request.files['file']).
    Returns (url, filename, size_bytes). Raises on failure — callers decide
    how to surface that (flash message vs JSON error)."""
    from app.utils.settings import get_setting
    backend = get_setting("media_storage_backend") or "local"
    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    filename = f"{uuid.uuid4().hex}.{ext}"

    if backend == "cloudinary" and _cloudinary_configured():
        return _save_to_cloudinary(file_storage, folder, filename)

    if backend == "cloudinary" and not _cloudinary_configured():
        # Configured to use Cloudinary but credentials are missing — fail
        # loudly rather than silently falling back and confusing the admin
        # about where their file actually went.
        raise RuntimeError("Media storage is set to Cloudinary, but the Cloud Name/API Key/API Secret aren't all filled in under Admin -> Settings -> Media Storage.")

    return _save_local(file_storage, folder, filename, app)


def _save_local(file_storage, folder, filename, app):
    upload_dir = os.path.join(app.static_folder, "uploads", folder)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file_storage.save(filepath)
    size = os.path.getsize(filepath)
    return f"/static/uploads/{folder}/{filename}", filename, size


def _save_to_cloudinary(file_storage, folder, filename):
    import cloudinary
    import cloudinary.uploader
    from app.utils.settings import get_setting

    cloudinary.config(
        cloud_name=get_setting("cloudinary_cloud_name"),
        api_key=get_setting("cloudinary_api_key"),
        api_secret=get_setting("cloudinary_api_secret"),
        secure=True,
    )
    public_id = os.path.splitext(filename)[0]
    result = cloudinary.uploader.upload(
        file_storage,
        folder=f"bazillin/{folder}",
        public_id=public_id,
        resource_type="auto",  # image, video, or raw (pdf/docx/etc) auto-detected
    )
    url = result.get("secure_url")
    size = result.get("bytes", 0)
    return url, filename, size


def delete_upload(media_file, app):
    """Best-effort delete from whichever backend the file was on. Local
    files not found are ignored (already gone); Cloudinary deletes are
    attempted by public_id derived from the stored URL."""
    if "cloudinary.com" in (media_file.url or ""):
        try:
            import cloudinary
            import cloudinary.uploader
            from app.utils.settings import get_setting
            cloudinary.config(
                cloud_name=get_setting("cloudinary_cloud_name"),
                api_key=get_setting("cloudinary_api_key"),
                api_secret=get_setting("cloudinary_api_secret"),
                secure=True,
            )
            # URL shape: .../upload/v123/bazillin/<folder>/<public_id>.<ext>
            after_upload = media_file.url.split("/upload/", 1)[-1]
            path_no_version = after_upload.split("/", 1)[-1] if after_upload.split("/", 1)[0].startswith("v") else after_upload
            public_id = os.path.splitext(path_no_version)[0]
            cloudinary.uploader.destroy(public_id)
        except Exception:
            pass  # best-effort — don't block deleting the DB record over this
    else:
        try:
            path = os.path.join(app.static_folder, "uploads", media_file.folder or "general", media_file.filename)
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
