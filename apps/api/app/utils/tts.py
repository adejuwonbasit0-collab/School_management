"""
Text-to-Speech utility module.

History of this file, for whoever reads this next:
  1. Originally only returned a "use your browser's Web Speech API" config
     — nothing was ever generated server-side, so there was no real audio
     file, no real download, and only whatever "voices" the visitor's own
     browser happened to have installed.
  2. Was rebuilt on gTTS (Google Translate's public TTS endpoint) as the
     free, no-key default. That fixed "no real audio file" but NOT the
     actual ask: gTTS only exposes one synthetic voice per LANGUAGE
     (English (US), French, German, ...) — there are no distinct named
     voices, no male/female choice. Picking a "voice" was really just
     picking a language/accent. gTTS is also aggressively rate-limited by
     Google for shared/datacenter hosting IPs (PythonAnywhere included),
     which is the "generated audio has nothing in it" / "blocked with no
     explanation" symptom.

Now: edge-tts (Microsoft Edge's public neural TTS endpoint) is the
primary engine — free, no account or API key, and it exposes ~50+ real,
distinct, named neural voices (Jenny, Guy, Aria, Ryan, Sonia, Abeo,
Ezinne, ...) each tagged with an actual gender and locale, across dozens
of languages. That is what "a lot of different voices" actually needs.
gTTS is kept as an automatic silent fallback if edge-tts is ever
unreachable, so generation still works either way. ElevenLabs/Google
Cloud TTS remain available as optional premium engines if API keys are
configured in Admin -> Settings — never required.
"""
import os
import uuid
import asyncio
from datetime import datetime


# A curated, stable set of edge-tts neural voices — short names like
# "en-US-JennyNeural" have been stable in Microsoft's catalog for years.
# Each is a genuinely distinct voice (not just a language), so this list
# is what "browse a lot of voices" should have looked like from the start.
EDGE_VOICES = [
    {"id": "en-US-JennyNeural", "name": "Jenny — English (US), Woman"},
    {"id": "en-US-GuyNeural", "name": "Guy — English (US), Man"},
    {"id": "en-US-AriaNeural", "name": "Aria — English (US), Woman"},
    {"id": "en-US-DavisNeural", "name": "Davis — English (US), Man"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia — English (UK), Woman"},
    {"id": "en-GB-RyanNeural", "name": "Ryan — English (UK), Man"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha — English (Australia), Woman"},
    {"id": "en-AU-WilliamNeural", "name": "William — English (Australia), Man"},
    {"id": "en-NG-EzinneNeural", "name": "Ezinne — English (Nigeria), Woman"},
    {"id": "en-NG-AbeoNeural", "name": "Abeo — English (Nigeria), Man"},
    {"id": "en-IN-NeerjaNeural", "name": "Neerja — English (India), Woman"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat — English (India), Man"},
    {"id": "en-ZA-LeahNeural", "name": "Leah — English (South Africa), Woman"},
    {"id": "en-ZA-LukeNeural", "name": "Luke — English (South Africa), Man"},
    {"id": "fr-FR-DeniseNeural", "name": "Denise — French, Woman"},
    {"id": "fr-FR-HenriNeural", "name": "Henri — French, Man"},
    {"id": "es-ES-ElviraNeural", "name": "Elvira — Spanish, Woman"},
    {"id": "es-ES-AlvaroNeural", "name": "Alvaro — Spanish, Man"},
    {"id": "pt-BR-FranciscaNeural", "name": "Francisca — Portuguese (Brazil), Woman"},
    {"id": "pt-BR-AntonioNeural", "name": "Antonio — Portuguese (Brazil), Man"},
    {"id": "de-DE-KatjaNeural", "name": "Katja — German, Woman"},
    {"id": "de-DE-ConradNeural", "name": "Conrad — German, Man"},
    {"id": "hi-IN-SwaraNeural", "name": "Swara — Hindi, Woman"},
    {"id": "hi-IN-MadhurNeural", "name": "Madhur — Hindi, Man"},
    {"id": "ar-SA-ZariyahNeural", "name": "Zariyah — Arabic, Woman"},
    {"id": "ar-SA-HamedNeural", "name": "Hamed — Arabic, Man"},
    {"id": "sw-KE-ZuriNeural", "name": "Zuri — Swahili, Woman"},
    {"id": "sw-KE-RafikiNeural", "name": "Rafiki — Swahili, Man"},
    {"id": "ja-JP-NanamiNeural", "name": "Nanami — Japanese, Woman"},
    {"id": "ja-JP-KeitaNeural", "name": "Keita — Japanese, Man"},
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao — Chinese, Woman"},
    {"id": "zh-CN-YunxiNeural", "name": "Yunxi — Chinese, Man"},
]

# gTTS fallback only needs a language/accent, used silently if edge-tts fails.
GTTS_FALLBACK = {"lang": "en", "tld": "com"}


def list_voices():
    """Real, selectable, named voices — free, no API key needed."""
    voices = [{"id": v["id"], "name": v["name"], "provider": "edge", "free": True} for v in EDGE_VOICES]

    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if elevenlabs_key:
        voices.extend(_list_elevenlabs_voices(elevenlabs_key))
    google_tts_key = os.environ.get("GOOGLE_TTS_API_KEY", "")
    if google_tts_key:
        voices.append({
            "id": "google", "name": "Google Cloud TTS (Premium, 50+ languages)",
            "provider": "google", "free": False,
        })
    return voices


def _list_elevenlabs_voices(api_key):
    import requests
    try:
        resp = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": api_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException:
        return [{"id": "elevenlabs", "name": "ElevenLabs (Premium AI voices)", "provider": "elevenlabs", "free": False}]

    out = []
    for v in data.get("voices", []):
        labels = v.get("labels", {}) or {}
        gender = (labels.get("gender") or "").title()
        age = (labels.get("age") or "").title()
        accent = (labels.get("accent") or "").title()
        descriptor = " · ".join(x for x in [gender, age, accent] if x)
        out.append({
            "id": f"elevenlabs:{v['voice_id']}", "name": f"{v.get('name', 'Voice')}" + (f" — {descriptor}" if descriptor else ""),
            "provider": "elevenlabs", "free": False,
        })
    return out or [{"id": "elevenlabs", "name": "ElevenLabs (Premium AI voices)", "provider": "elevenlabs", "free": False}]


def _audio_dir():
    from flask import current_app
    d = os.path.join(current_app.root_path, "static", "generated_audio")
    os.makedirs(d, exist_ok=True)
    return d


def generate_speech(text, voice_id="en-US-JennyNeural", speed=1.0, pitch=1.0):
    """Generates a REAL audio file and returns a URL the browser can play
    or download directly. Returns (result_dict, error_string)."""
    text = (text or "").strip()
    if not text:
        return None, "No text provided."
    if len(text) > 5000:
        return None, "Text too long. Maximum 5000 characters."

    if voice_id == "elevenlabs" or voice_id.startswith("elevenlabs:"):
        eleven_voice_id = voice_id.split(":", 1)[1] if ":" in voice_id else "21m00Tcm4TlvDq8ikWAM"
        return _generate_elevenlabs(text, eleven_voice_id)
    if voice_id == "google":
        return _generate_google_tts(text)

    voice_meta = next((v for v in EDGE_VOICES if v["id"] == voice_id), EDGE_VOICES[0])

    # Primary: edge-tts — free, no key, real distinct named voices.
    result, error = _generate_edge_tts(text, voice_meta, speed)
    if result:
        return result, None

    # Automatic fallback: gTTS, silently, so generation still works even
    # if edge-tts's endpoint is unreachable from this server right now.
    fallback_result, fallback_error = _generate_gtts(text, speed)
    if fallback_result:
        fallback_result["voice"] = f"{voice_meta['name']} (fallback voice used — primary engine unreachable)"
        return fallback_result, None

    return None, (
        f"Couldn't generate speech: the primary voice service failed ({error}), and the backup "
        f"service also failed ({fallback_error}). Both free services can occasionally be blocked from "
        "this server's hosting IP. Try again in a bit, or add an ELEVENLABS_API_KEY or GOOGLE_TTS_API_KEY "
        "in Admin → Settings for generation that isn't affected by this."
    )


def _system_proxy():
    """PythonAnywhere (and similar hosts) route all outbound internet
    through a mandatory proxy and set the standard *_proxy env vars for
    it. `requests` (used by gTTS) picks these up automatically, which is
    why gTTS could still reach Google. `edge-tts` talks to Microsoft's
    endpoint directly over aiohttp and does NOT read these env vars on
    its own — without passing the proxy through explicitly, it can't
    reach the internet at all on a proxied host, which is what produced
    'Cannot connect to host speech.platform.bing.com:443'."""
    return (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or None)


def _generate_edge_tts(text, voice_meta, speed=1.0):
    try:
        import edge_tts
    except ImportError:
        return None, "edge-tts isn't installed on the server — run `pip install edge-tts`."

    # edge-tts expects rate as a signed percentage string, e.g. "+20%".
    pct = int(round((speed - 1.0) * 100))
    rate = f"{'+' if pct >= 0 else ''}{pct}%"

    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(_audio_dir(), filename)
    proxy = _system_proxy()

    async def _run():
        communicate = edge_tts.Communicate(text, voice_meta["id"], rate=rate, proxy=proxy, connect_timeout=8)
        await communicate.save(filepath)

    try:
        try:
            asyncio.run(_run())
        except RuntimeError:
            # Already inside an event loop (rare under some WSGI setups) —
            # fall back to a fresh loop.
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run())
            finally:
                loop.close()
    except Exception as e:
        _cleanup_failed_file(filepath)
        return None, str(e)

    if not os.path.exists(filepath) or os.path.getsize(filepath) < 500:
        _cleanup_failed_file(filepath)
        return None, "service returned no audio"

    return {
        "mode": "audio_file",
        "audio_url": f"/static/generated_audio/{filename}",
        "voice": voice_meta["name"],
        "text": text,
        "created_at": datetime.utcnow().isoformat(),
    }, None


def _generate_gtts(text, speed=1.0):
    try:
        from gtts import gTTS
    except ImportError:
        return None, "gTTS not installed"

    slow = speed < 0.85
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(_audio_dir(), filename)
    try:
        tts = gTTS(text=text, lang=GTTS_FALLBACK["lang"], tld=GTTS_FALLBACK["tld"], slow=slow)
        tts.save(filepath)
    except Exception as e:
        _cleanup_failed_file(filepath)
        return None, str(e)

    if not os.path.exists(filepath) or os.path.getsize(filepath) < 500:
        _cleanup_failed_file(filepath)
        return None, "service returned no audio"

    return {
        "mode": "audio_file",
        "audio_url": f"/static/generated_audio/{filename}",
        "voice": "English (fallback)",
        "text": text,
        "created_at": datetime.utcnow().isoformat(),
    }, None


def _cleanup_failed_file(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass


def _generate_elevenlabs(text, voice_id="21m00Tcm4TlvDq8ikWAM"):
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        return None, "ElevenLabs isn't configured — add ELEVENLABS_API_KEY, or pick a free voice instead."
    import requests
    try:
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_monolingual_v1"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"ElevenLabs error: {e}"
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(_audio_dir(), filename)
    with open(filepath, "wb") as f:
        f.write(resp.content)
    if os.path.getsize(filepath) < 500:
        _cleanup_failed_file(filepath)
        return None, "ElevenLabs returned an empty response — check your API key and voice ID, then try again."
    return {"mode": "audio_file", "audio_url": f"/static/generated_audio/{filename}", "voice": "ElevenLabs", "text": text}, None


def _generate_google_tts(text):
    api_key = os.environ.get("GOOGLE_TTS_API_KEY", "")
    if not api_key:
        return None, "Google Cloud TTS isn't configured — add GOOGLE_TTS_API_KEY, or pick a free voice instead."
    import requests, base64
    try:
        resp = requests.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}",
            json={
                "input": {"text": text},
                "voice": {"languageCode": "en-US", "ssmlGender": "NEUTRAL"},
                "audioConfig": {"audioEncoding": "MP3"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        audio_content = resp.json().get("audioContent")
    except requests.exceptions.RequestException as e:
        return None, f"Google TTS error: {e}"
    if not audio_content:
        return None, "Google TTS returned no audio."
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(_audio_dir(), filename)
    with open(filepath, "wb") as f:
        f.write(base64.b64decode(audio_content))
    if os.path.getsize(filepath) < 500:
        _cleanup_failed_file(filepath)
        return None, "Google Cloud TTS returned an empty response — check your API key, then try again."
    return {"mode": "audio_file", "audio_url": f"/static/generated_audio/{filename}", "voice": "Google TTS", "text": text}, None
