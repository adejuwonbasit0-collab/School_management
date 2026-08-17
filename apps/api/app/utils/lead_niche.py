"""Classifies a CRM lead's industry/niche from whatever real text is on
their record (name, company, notes) using the site's own already-configured
AI provider — no new external service needed for this one, unlike Bloom/
video/search which genuinely require a separate account."""


def detect_niche(lead):
    """Returns (niche_string, error) — exactly one is None."""
    from app.ai_tools.routes import _call_ai

    context_parts = []
    if lead.company:
        context_parts.append(f"Company: {lead.company}")
    if lead.notes:
        context_parts.append(f"Notes: {lead.notes}")
    if lead.name:
        context_parts.append(f"Contact name: {lead.name}")
    context_parts.append(f"Email domain: {lead.email.split('@')[-1] if '@' in lead.email else lead.email}")

    if len(context_parts) <= 1:
        return None, ("Not enough information on this lead to detect a niche — "
                       "add a company name or some notes first.")

    system_prompt = (
        "Based ONLY on the real information about a business lead that the user gives you, respond with "
        "their most likely industry/niche as 2-4 words (e.g. \"e-commerce fashion\", "
        "\"local restaurant\", \"SaaS / software\", \"real estate agency\"). "
        "If you genuinely can't tell, respond with exactly: unknown. No other text."
    )
    user_message = "\n".join(context_parts)
    text, err = _call_ai(system_prompt, [{"role": "user", "content": user_message}], max_tokens=30)
    if err:
        return None, f"Couldn't detect niche: {err}"
    niche = (text or "").strip().strip(".").lower()
    if not niche or niche == "unknown":
        return None, "Couldn't confidently determine a niche from the information available on this lead."
    return niche[:128], None
