"""Lightweight knowledge retrieval across real site content.

This is NOT the full 'Knowledge Ingestion Engine + vector index' from the
master prompt — no embeddings, no vector DB, no continuous sync pipeline,
no PDF/Word/image/video ingestion. It's a plain keyword (ILIKE) search
across the content tables that already exist, used the same way an
embedding-based retriever would be used: called BEFORE generation so an AI
answer is grounded in real records instead of invented ones. That's the
part of "never hallucinate — retrieve real information first" that's
actually implemented here; true semantic/hybrid search is a separate,
much bigger project.
"""


def search_knowledge_base(query, limit=5):
    """Searches Services, Portfolio Projects, published Blog posts, active
    FAQs, Products (if the commerce module has any), and saved
    ScrapedSiteItems (results from the website importer, kept around for
    reuse instead of vanishing after one look) for `query` by simple
    substring match on their title/description-ish fields. Returns
    a list of dicts: {type, title, detail, url}. Empty list means no
    match — callers should say plainly that nothing was found, never
    invent a result to fill the gap."""
    from app.extensions import db
    from app.models.content import Service, Project, BlogPost
    from app.models.platform import FAQItem

    q = (query or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    results = []

    for s in Service.query.filter(
        Service.active == True,
        db.or_(Service.title.ilike(like), Service.description.ilike(like)),
    ).limit(limit).all():
        results.append({
            "type": "service", "title": s.title,
            "detail": (s.description or "")[:200] + (f" — {s.price}" if s.price else ""),
            "url": "/services",
        })

    for p in Project.query.filter(
        db.or_(Project.title.ilike(like), Project.description.ilike(like)),
    ).limit(limit).all():
        results.append({
            "type": "project", "title": p.title,
            "detail": (p.description or "")[:200],
            "url": f"/portfolio/{p.slug}" if p.slug else "/portfolio",
        })

    for bp in BlogPost.query.filter(
        BlogPost.published == True,
        db.or_(BlogPost.title.ilike(like), BlogPost.excerpt.ilike(like)),
    ).limit(limit).all():
        results.append({
            "type": "blog_post", "title": bp.title,
            "detail": (bp.excerpt or "")[:200],
            "url": f"/blog/{bp.slug}" if bp.slug else "/blog",
        })

    for f in FAQItem.query.filter(
        FAQItem.active == True,
        db.or_(FAQItem.question.ilike(like), FAQItem.answer.ilike(like)),
    ).limit(limit).all():
        results.append({
            "type": "faq", "title": f.question,
            "detail": (f.answer or "")[:300],
            "url": "/faq",
        })

    try:
        from app.models.commerce import Product
        for pr in Product.query.filter(
            Product.status == "active",
            db.or_(Product.title.ilike(like), Product.description.ilike(like)),
        ).limit(limit).all():
            price = f"{pr.sale_price or pr.price} {pr.currency or ''}".strip()
            results.append({
                "type": "product", "title": pr.title,
                "detail": (pr.description or "")[:200] + f" — {price}",
                "url": f"/marketplace/{pr.slug}" if pr.slug else "/marketplace",
            })
    except Exception:
        pass  # commerce module optional in some deployments

    from app.models.platform import ScrapedSiteItem
    for sc in ScrapedSiteItem.query.filter(
        db.or_(ScrapedSiteItem.name.ilike(like), ScrapedSiteItem.description.ilike(like)),
    ).order_by(ScrapedSiteItem.created_at.desc()).limit(limit).all():
        detail = (sc.description or "")[:150]
        if sc.price:
            detail += f" — {sc.price}"
        results.append({
            "type": f"scraped_{sc.kind or 'item'}", "title": sc.name or "Untitled",
            "detail": detail, "url": sc.link or sc.source_url,
        })

    return results[:limit]


def format_knowledge_results(results):
    """Turns search_knowledge_base's output into plain text suitable for
    dropping into an AI prompt or a tool result."""
    if not results:
        return "No matching records found in the knowledge base."
    lines = []
    for r in results:
        lines.append(f"[{r['type']}] {r['title']} — {r['detail']} (link: {r['url']})")
    return "\n".join(lines)


def extract_text_from_upload(file_storage):
    """Extract readable text from an uploaded knowledge document.
    Supports PDF, DOCX, and TXT — the exact formats Doc 9 §5 asks for
    (CSV is treated as plain text). Returns (text, error).
    """
    filename = (file_storage.filename or "").lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    try:
        if ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(file_storage)
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        elif ext == "docx":
            import docx
            document = docx.Document(file_storage)
            text = "\n\n".join(p.text for p in document.paragraphs if p.text.strip())
        elif ext in ("txt", "csv"):
            raw = file_storage.read()
            text = raw.decode("utf-8", errors="replace")
        else:
            return None, "Unsupported file type — please upload a PDF, DOCX, TXT, or CSV file."
    except Exception as e:
        return None, f"Couldn't read that file: {e}"

    text = text.strip()
    if not text:
        return None, "That file loaded but had no readable text in it."
    return text[:20000], None  # cap per-document text so one huge file can't dominate every prompt


def fetch_url_text(url):
    """Fetch a business's website page and extract its readable text for
    the chatbot's Knowledge Base. Reuses the exact same fetch/extraction
    path already used and hardened for Content Studio's site scanner
    (SSRF guard via _is_safe_url, timeout, content-type check) instead of
    a second hand-rolled HTTP fetch. Returns (title, text, error)."""
    import requests
    from app.ai_tools.routes import _is_safe_url
    from app.admin.routes import _extract_page_text

    norm_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
    safe, reason = _is_safe_url(norm_url)
    if not safe:
        return None, None, reason

    try:
        resp = requests.get(norm_url, timeout=(10, 15), headers={"User-Agent": "BazillinStudio-KnowledgeBase/1.0"})
        resp.raise_for_status()
        if "text/html" not in resp.headers.get("Content-Type", ""):
            return None, None, "That URL didn't return a webpage."
    except requests.exceptions.Timeout:
        return None, None, "That site took too long to respond."
    except requests.exceptions.RequestException as e:
        return None, None, f"Could not fetch that URL: {e}"

    extracted = _extract_page_text(resp.text, norm_url)
    if not extracted["body_text"] and not extracted["title"]:
        return None, None, "That page loaded but had no readable text on it."
    return extracted["title"] or norm_url, extracted["body_text"][:20000], None

def search_bot_knowledge(faqs, knowledge_text, query, limit=5, sources=None):
    """Per-bot knowledge retrieval — DISTINCT from search_knowledge_base()
    above, which searches the *platform's own* site content (services,
    portfolio, blog). This searches the *business owner's* knowledge for
    THEIR chatbot: the FAQs and manual info they typed into the Knowledge
    Base panel on the WhatsApp Bot / AI Chatbot builder. Same keyword
    (substring) approach — no embeddings/vector DB — for the same reason:
    a real, working retrieval step that grounds the AI in what the owner
    actually told it, instead of nothing being checked at all before
    generating a reply (which was the previous behavior — `ai_instructions`
    was the only input, with no way to add FAQs or business info).

    faqs: list of {"question": "..", "answer": "..", "category": ".."}
    knowledge_text: freeform manual text (About Us, policies, pricing, etc)
    Returns list of {"type", "title", "detail"} — never invents an answer
    when nothing matches, callers should say so explicitly.
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    # Naive keyword match: exact substring first (catches short/precise
    # queries), then per-word overlap for longer natural-language
    # questions like "do you deliver to my area?" that won't be a
    # verbatim substring of a stored FAQ but clearly relate to it.
    # Common stopwords are filtered out of the word-overlap pass so
    # "do"/"you"/"the" etc don't match nearly everything.
    _stopwords = {
        "the", "you", "your", "are", "and", "for", "with", "that", "this",
        "have", "has", "what", "when", "where", "how", "can", "does", "do",
        "did", "will", "would", "could", "should", "about", "there", "their",
        "them", "then", "than", "from", "into", "just", "like", "some",
        "any", "not", "yes", "please", "hello", "hey", "hii", "get", "got",
    }
    words = [w for w in q.split() if len(w) >= 3 and w not in _stopwords]
    def _matches(text):
        text = (text or "").lower()
        if not text:
            return False
        if q in text:
            return True
        return any(w in text for w in words)

    results = []

    for f in (faqs or []):
        question = (f.get("question") or "").strip()
        answer = (f.get("answer") or "").strip()
        if not question or not answer:
            continue
        if _matches(question) or _matches(answer):
            results.append({"type": "faq", "title": question, "detail": answer})

    # Manual info is freeform text — search it paragraph by paragraph so a
    # match returns a focused snippet instead of the whole block.
    for para in (knowledge_text or "").split("\n\n"):
        para = para.strip()
        if para and _matches(para):
            results.append({"type": "info", "title": "Business info", "detail": para[:500]})

    # Ingested website pages / uploaded documents — same paragraph-level
    # search so a hit returns a focused snippet, not the whole document.
    for src in (sources or []):
        title = src.get("title") or src.get("source") or "Document"
        for para in (src.get("text") or "").split("\n\n"):
            para = para.strip()
            if para and _matches(para):
                results.append({"type": src.get("type", "source"), "title": title, "detail": para[:500]})
                break  # one snippet per source is enough context

    return results[:limit]


def format_bot_knowledge(results):
    """Text form of search_bot_knowledge() output, ready to drop into an
    AI system prompt as grounding context."""
    if not results:
        return ""
    lines = ["Relevant information from the business's own knowledge base (use this when it answers the question; do not contradict it):"]
    for r in results:
        lines.append(f"- {r['title']}: {r['detail']}")
    return "\n".join(lines)


def generate_bot_reply(base_instructions, faqs, knowledge_text, message, unknown_reply=None, sources=None, charge_user_id=None):
    """The one shared reply-generation path for a business's own chatbot
    (WhatsApp Bot or AI Chatbot) — used identically by the live public
    reply endpoint AND both builders' test panels, so a test preview
    behaves exactly like the real thing instead of two separately
    hand-rolled AI calls drifting apart. Grounds the answer in the
    owner's FAQs/manual info/ingested sources before generating, and
    tells the AI to say so plainly rather than invent an answer when
    nothing matches — Doc 9's "never fabricate prices/products, say when
    info is unavailable" rule.

    charge_user_id: if given, deducts one AI-reply credit from that
    user's balance (the bot OWNER, never the visitor) before calling the
    AI provider — Doc 9 §20-22's credit metering. On insufficient
    credits, returns the platform's real unavailable-message immediately
    without spending an actual AI API call. Omit this for internal/free
    paths that shouldn't be metered (none currently — every real reply
    surface passes it).

    Returns (reply_text, error_or_None).
    """
    from app.ai_tools.routes import _call_ai

    if charge_user_id is not None:
        from app.utils.credits import charge_ai_reply
        ok, charge_err = charge_ai_reply(charge_user_id)
        if not ok:
            return charge_err, None  # a clear, real reply — not a Python error — this is the AI Chatbot Exhausted state (Doc 9 §22)

    knowledge_hits = search_bot_knowledge(faqs, knowledge_text, message, limit=5, sources=sources)
    context = format_bot_knowledge(knowledge_hits)
    fallback = unknown_reply or "Sorry, I don't have that information yet. I'll pass this on to the business owner."

    system = (base_instructions or "You are a helpful customer support assistant.").strip()
    system += (
        "\n\nOnly answer using the knowledge base context below and general courteous conversation. "
        "Never invent prices, products, availability, or policies that aren't given to you. "
        f"If the answer isn't in the context, say: \"{fallback}\""
    )
    if context:
        system += "\n\n" + context
    else:
        system += "\n\nNo matching knowledge base entry was found for this question — say so plainly rather than guessing."

    reply, err = _call_ai(system, [{"role": "user", "content": message}], max_tokens=500, temperature=0.6)
    if err or not reply:
        return None, err or "No response generated."
    return reply, None
