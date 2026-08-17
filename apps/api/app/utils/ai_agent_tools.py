"""
The bounded set of real actions the AI Console (and later, an AI Agent
workflow node) is allowed to take on the site. This is deliberately a
short, explicit allow-list — not "let the model run arbitrary code" —
because an LLM performing unrestricted actions on a real business site
is a genuine safety problem, not just an engineering one. Each tool
below wraps something the admin could already do by hand; the AI just
does the clicking.

Every tool function takes `user` (the current_user performing the
request, for attribution) plus its own arguments, and returns a short
plain-English string describing what happened — that string gets fed
back to the model so it can tell the person what it did.
"""

TOOL_SCHEMAS = [
    {
        "name": "create_blog_draft",
        "description": "Create a new blog post as an UNPUBLISHED draft (never publishes automatically — a human reviews and publishes it from Admin -> Blog Posts).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The blog post's title"},
                "content": {"type": "string", "description": "The full post content (plain text or simple HTML)"},
                "excerpt": {"type": "string", "description": "A one or two sentence summary (optional)"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "create_portfolio_project",
        "description": "Creates a project as a DRAFT for the admin to review before it's published to the portfolio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Project title"},
                "description": {"type": "string", "description": "Project description"},
                "client_name": {"type": "string", "description": "Client name, if any (optional)"},
                "tech_stack": {"type": "array", "items": {"type": "string"}, "description": "Technologies used, e.g. ['Django','React'] (optional)"},
                "live_url": {"type": "string", "description": "Live site URL, if any (optional)"},
            },
            "required": ["title", "description"],
        },
    },
    {
        "name": "create_todo",
        "description": "Add a task to the admin's personal To-Do board.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The task description"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "send_test_email",
        "description": "Send a real email right now via the site's configured SMTP settings. Use only when explicitly asked to send/test an email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string"},
                "body_html": {"type": "string", "description": "Email body as simple HTML"},
            },
            "required": ["to", "subject", "body_html"],
        },
    },
    {
        "name": "create_automation_workflow",
        "description": "Creates an INACTIVE automation workflow shell (trigger + steps) for a human to review and activate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "trigger_type": {"type": "string", "enum": [
                    "hire_request_submitted", "newsletter_subscribed", "job_application_submitted",
                    "channel_message_received", "meeting_scheduled", "manual",
                ]},
                "active": {"type": "boolean", "description": "Defaults to true"},
                "action_type": {"type": "string", "description": "Optional action type (send_email, notify_admin, send_channel_reply, etc.)"},
                "action_config": {"type": "object", "description": "Optional parameters for the action"}
            },
            "required": ["name", "trigger_type"],
        },
    },
    {
        "name": "create_site_popup",
        "description": "Create a website popup shown to visitors — starts INACTIVE so a human can review it in Admin -> Site Popups before turning it on.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Internal label, not shown to visitors"},
                "headline": {"type": "string", "description": "Shown to visitors"},
                "body_html": {"type": "string"},
                "trigger_type": {"type": "string", "enum": ["delay", "exit_intent", "scroll"]},
                "trigger_value": {"type": "integer", "description": "Seconds for delay, % for scroll"},
            },
            "required": ["title", "headline"],
        },
    },
    {
        "name": "get_site_stats",
        "description": "Looks up live site stats (visitors, revenue, leads, etc.) for a given period.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_lead",
        "description": "Add a new prospect to the CRM sales pipeline (Leads). Use when told about a new prospect/lead to track, not for existing clients.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "company": {"type": "string", "description": "Optional"},
                "niche": {"type": "string", "description": "Their industry/niche, optional"},
                "notes": {"type": "string", "description": "Any context worth recording, optional"},
            },
            "required": ["email"],
        },
    },
    {
        "name": "update_lead_stage",
        "description": "Moves a lead to a different pipeline stage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "The lead's email — used to find them"},
                "deal_stage": {"type": "string", "enum": ["new", "qualified", "proposal", "won", "lost"]},
                "note": {"type": "string", "description": "Optional note to append to the lead's record"},
            },
            "required": ["email"],
        },
    },
    {
        "name": "get_project_summary",
        "description": "Looks up the status, budget, and timeline of a specific client project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_title": {"type": "string", "description": "Full or partial project title to search for"},
            },
            "required": ["project_title"],
        },
    },
    {
        "name": "schedule_meeting",
        "description": "Schedules a meeting/call and adds it to the calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_title": {"type": "string", "description": "Full or partial project title to find the project"},
                "title": {"type": "string", "description": "What the meeting is about"},
                "scheduled_at": {"type": "string", "description": "ISO 8601 datetime, e.g. 2026-08-01T15:00:00"},
                "duration_minutes": {"type": "integer", "description": "Defaults to 30 if not given"},
                "location": {"type": "string", "description": "A video call link, phone number, or address — optional"},
            },
            "required": ["project_title", "title", "scheduled_at"],
        },
    },
    {
        "name": "delegate_to_agent",
        "description": "Hands a task off to another named Agent (one hop only, no chains) when this task fits that agent's role better than your own.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "The other agent's name"},
                "message": {"type": "string", "description": "What to ask or hand off to them"},
            },
            "required": ["agent_name", "message"],
        },
    },
    {
        "name": "generate_report",
        "description": "Generates a PDF/data report (e.g. revenue, leads, projects) for a given date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "report_type": {"type": "string", "enum": ["revenue", "pipeline", "projects"]},
            },
            "required": ["report_type"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "Searches the site's own knowledge base articles/docs for an answer before falling back to general knowledge — always check this first for questions about how this specific platform/business works.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for, e.g. 'website packages' or 'hotel projects'"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_inactive_customers",
        "description": "Lists customers with no recent activity/orders, for re-engagement outreach.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Quiet threshold in days — defaults to 60 if not given"},
            },
        },
    },
    {
        "name": "create_faq_draft",
        "description": "Adds a new FAQ entry, created INACTIVE so an admin reviews and activates it before it appears on the site.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"},
                "category": {"type": "string", "description": "Optional, defaults to 'General'"},
            },
            "required": ["question", "answer"],
        },
    },
    {
        "name": "update_project_status",
        "description": "Updates a real client project's status and/or progress percentage. Look the project up by title (or part of it).",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_title": {"type": "string"},
                "status": {"type": "string", "enum": ["planning", "in_progress", "review", "completed", "on_hold"]},
                "progress_pct": {"type": "integer", "description": "0-100"},
            },
            "required": ["project_title"],
        },
    },
    {
        "name": "create_testimonial_draft",
        "description": "Creates a testimonial as a DRAFT for the admin to review before it goes live.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "company": {"type": "string"},
                "content": {"type": "string", "description": "The actual testimonial text"},
                "rating": {"type": "integer", "description": "1-5, defaults to 5"},
            },
            "required": ["name", "content"],
        },
    },
    {
        "name": "create_auto_reply_rule",
        "description": "Creates an auto-reply rule for a messaging channel (keyword -> response).",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_label": {"type": "string", "description": "The channel's admin-facing name (e.g. 'Support WhatsApp') — used to find it"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Words/phrases that trigger this rule"},
                "reply": {"type": "string", "description": "The reply to send when triggered"},
                "match": {"type": "string", "enum": ["contains", "exact"], "description": "Defaults to 'contains'"},
            },
            "required": ["channel_label", "keywords", "reply"],
        },
    },
    {
        "name": "get_achievement_summary",
        "description": "Looks up the site owner's real achievement/portfolio stats (projects done, clients, years active) to ground claims in facts instead of guessing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["today", "week", "month"], "description": "Defaults to 'week'"},
            },
        },
    },
    {
        "name": "search_web",
        "description": "Searches the web for current information not in the site's own data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "detect_lead_niche",
        "description": "Classifies a lead's industry/niche from their message, for routing/tagging.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "The lead's email — used to find them"},
            },
            "required": ["email"],
        },
    },
    {
        "name": "generate_video_ai",
        "description": "Generates a short AI video from a text prompt and attaches it to the given content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Description of the video to generate"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "send_whatsapp_message",
        "description": "Sends a WhatsApp message via the connected number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient phone number in E.164 format, e.g. +15551234567"},
                "body": {"type": "string", "description": "The message to send"},
            },
            "required": ["to", "body"],
        },
    },
    {
        "name": "get_portfolio_content_summary",
        "description": "Reads the current About/skills/experience/services/projects/partners so you know what's already on the site before adding more (avoids duplicates, matches existing voice/stack).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_profile",
        "description": "Updates the site owner's About/Profile section directly (live immediately — it's their own bio). Only pass fields to change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "title": {"type": "string", "description": "Headline role, e.g. 'Full-Stack Developer'"},
                "subtitle": {"type": "string", "description": "Short tagline shown under the title"},
                "bio": {"type": "string", "description": "Short bio (hero section)"},
                "about": {"type": "string", "description": "Longer About-page text"},
                "twitter": {"type": "string"}, "github": {"type": "string"},
                "linkedin": {"type": "string"}, "instagram": {"type": "string"},
                "resume_url": {"type": "string"},
            },
        },
    },
    {
        "name": "add_skill",
        "description": "Adds one skill to the Skills section, live immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "category": {"type": "string", "description": "e.g. 'Backend', 'Frontend', 'DevOps' (optional)"},
                "level": {"type": "string", "description": "e.g. 'Advanced', 'Intermediate' (optional)"},
                "percentage": {"type": "integer", "description": "0-100 proficiency bar value (optional)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_experience",
        "description": "Adds one work-experience entry to the Experience timeline, live immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "role": {"type": "string"},
                "description": {"type": "string"},
                "start_date": {"type": "string", "description": "e.g. '2023' or 'Jan 2023'"},
                "end_date": {"type": "string", "description": "e.g. '2024' — omit if current"},
                "current": {"type": "boolean", "description": "True if this is the person's current role"},
            },
            "required": ["company", "role"],
        },
    },
    {
        "name": "add_service",
        "description": "Adds one offered service to the Services section, active and live immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "price": {"type": "string", "description": "e.g. 'From $500' (optional)"},
                "features": {"type": "array", "items": {"type": "string"}, "description": "Bullet list of what's included (optional)"},
            },
            "required": ["title", "description"],
        },
    },
    {
        "name": "add_partner",
        "description": "Adds a real partner/client logo to the homepage 'Trusted by' strip, live immediately. Only use a logo URL the person actually gave you — never invent one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "logo_url": {"type": "string"},
                "website": {"type": "string"},
            },
            "required": ["name", "logo_url"],
        },
    },
    {
        "name": "connect_telegram_bot",
        "description": "Connects a Telegram bot with a @BotFather token — saves it, registers the webhook, verifies it's live.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bot_token": {"type": "string"},
                "label": {"type": "string", "description": "Admin-facing name, e.g. 'Portfolio Bot' (optional)"},
            },
            "required": ["bot_token"],
        },
    },
    {
        "name": "connect_whatsapp_business",
        "description": "Connects a WhatsApp Business number via Meta Cloud API (needs Phone Number ID + Access Token from the person's Meta app). Saves and verifies the credentials.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_number_id": {"type": "string"},
                "access_token": {"type": "string"},
                "app_secret": {"type": "string", "description": "optional"},
                "label": {"type": "string", "description": "optional"},
            },
            "required": ["phone_number_id", "access_token"],
        },
    },
    {
        "name": "connect_linkedin_account",
        "description": "Connects a LinkedIn account for posting using an access token the person already has. Saves and verifies it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "access_token": {"type": "string"},
                "label": {"type": "string", "description": "optional"},
            },
            "required": ["access_token"],
        },
    },
    {
        "name": "set_tiktok_developer_keys",
        "description": "Saves the person's TikTok Client Key/Secret. TikTok still needs one manual OAuth click to finish (Admin -> Social Channels -> Connect TikTok) — no API can skip that.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_key": {"type": "string"},
                "client_secret": {"type": "string"},
            },
            "required": ["client_key", "client_secret"],
        },
    },
]


def _tool_schemas_for_openai(tool_schemas):
    """Anthropic's `input_schema` is already plain JSON Schema, so it drops
    straight into OpenAI's `parameters` field — same schema, different
    envelope. This shape is what OpenAI, Groq, and OpenRouter all expect
    (Groq/OpenRouter both expose an OpenAI-compatible tools API)."""
    return [{"type": "function", "function": {
        "name": t["name"], "description": t["description"], "parameters": t["input_schema"],
    }} for t in tool_schemas]


def _tool_schemas_for_gemini(tool_schemas):
    """Gemini's function_declarations use the same JSON-Schema-shaped
    `parameters` field as OpenAI's."""
    return [{"function_declarations": [
        {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}
        for t in tool_schemas
    ]}]


def _run_agent_turn_openai_compatible(provider, api_key, system_prompt, history, user, max_tokens, temperature, tool_schemas, _depth):
    """Real tool-calling for OpenAI, Groq, and OpenRouter — they all speak
    the same OpenAI-compatible chat-completions + tools API, just with a
    different base_url/model (same pattern _call_ai_single already uses
    for plain, non-agentic calls)."""
    import json as _json
    import openai as _openai
    from app.ai_tools.routes import _get_provider_models, _classify_ai_error

    base_urls = {"groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
    models_to_try = _get_provider_models(provider)
    client_kwargs = {"api_key": api_key}
    if provider in base_urls:
        client_kwargs["base_url"] = base_urls[provider]
    if provider == "openrouter":
        client_kwargs["default_headers"] = {
            "HTTP-Referer": "https://bazillin.com",
            "X-Title": "Bazillin Studio",
        }
    client = _openai.OpenAI(**client_kwargs)

    chat_messages = [{"role": "system", "content": system_prompt}] + list(history)
    actions_taken = []
    openai_tools = _tool_schemas_for_openai(tool_schemas)
    temp = 0.7 if temperature is None else max(0.0, min(2.0, temperature * 2))

    current_model = models_to_try[0]
    model_idx = 0

    for _ in range(5):
        resp = None
        while model_idx < len(models_to_try):
            current_model = models_to_try[model_idx]
            try:
                kwargs = {
                    "model": current_model,
                    "max_tokens": max_tokens,
                    "temperature": temp,
                    "messages": chat_messages,
                }
                if tool_schemas:
                    kwargs["tools"] = openai_tools
                    kwargs["tool_choice"] = "auto"
                resp = client.chat.completions.create(**kwargs)
                break
            except Exception as e:
                # If rate-limited or model unavailable/decommissioned, try next model in tier
                if model_idx + 1 < len(models_to_try):
                    model_idx += 1
                    continue
                return None, actions_taken, _classify_ai_error(provider, e)

        if not resp:
            return None, actions_taken, f"{provider}: No active model responded"

        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content or "", actions_taken, None

        chat_messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [{
                "id": tc.id, "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            } for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                tool_input = _json.loads(tc.function.arguments or "{}")
            except ValueError:
                tool_input = {}
            if allowed_tools_check(name, tool_schemas):
                try:
                    result = execute_tool(name, tool_input, user, _depth=_depth)
                except Exception as e:
                    result = f"Tool '{name}' failed: {e}"
            else:
                result = f"Tool '{name}' is not permitted for this agent."
            actions_taken.append(result)
            chat_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "I took several actions but hit the per-turn action limit — check what happened below.", actions_taken, None


def _run_agent_turn_gemini(api_key, system_prompt, history, user, max_tokens, temperature, tool_schemas, _depth):
    """Real tool-calling for Gemini via its REST API (no extra SDK
    dependency, matching the plain-call Gemini branch in _call_ai_single)."""
    import json as _json
    import time
    import requests as _requests
    from app.ai_tools.routes import _get_provider_models, _classify_ai_error

    models_to_try = _get_provider_models("gemini")
    contents = [{"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "model", "parts": [{"text": "Understood."}]}]
    for m in history:
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    gemini_tools = _tool_schemas_for_gemini(tool_schemas)
    gen_config = {"maxOutputTokens": max_tokens}
    if temperature is not None:
        gen_config["temperature"] = max(0.0, min(1.0, temperature))

    actions_taken = []
    model_idx = 0

    for _ in range(5):
        resp = None
        while model_idx < len(models_to_try):
            current_model = models_to_try[model_idx]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
            payload = {"contents": contents, "generationConfig": gen_config}
            if tool_schemas:
                payload["tools"] = gemini_tools
            try:
                resp = _requests.post(url, json=payload, timeout=30)
                if resp.status_code == 429 and model_idx + 1 < len(models_to_try):
                    model_idx += 1
                    continue
                resp.raise_for_status()
                break
            except Exception as e:
                if model_idx + 1 < len(models_to_try):
                    model_idx += 1
                    continue
                return None, actions_taken, _classify_ai_error("gemini", e)
        try:
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
        except Exception as e:
            from app.ai_tools.routes import _classify_ai_error
            return None, actions_taken, _classify_ai_error("gemini", e)

        function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not function_calls:
            text = "".join(p.get("text", "") for p in parts)
            return text, actions_taken, None

        contents.append({"role": "model", "parts": parts})
        response_parts = []
        for fc in function_calls:
            name = fc.get("name")
            tool_input = fc.get("args") or {}
            if allowed_tools_check(name, tool_schemas):
                try:
                    result = execute_tool(name, tool_input, user, _depth=_depth)
                except Exception as e:
                    result = f"Tool '{name}' failed: {e}"
            else:
                result = f"Tool '{name}' is not permitted for this agent."
            actions_taken.append(result)
            response_parts.append({"functionResponse": {"name": name, "response": {"result": result}}})
        contents.append({"role": "user", "parts": response_parts})

    return "I took several actions but hit the per-turn action limit — check what happened below.", actions_taken, None


def allowed_tools_check(name, tool_schemas):
    """tool_schemas here is already pre-filtered to the caller's
    allowed_tools (see run_agent_turn below), so this just confirms the
    model didn't somehow name a tool outside that filtered set."""
    return name in {t["name"] for t in tool_schemas}


def trim_history_for_agent(history, max_messages=14, max_chars=6000):
    """Keeps only the most recent messages (both a message-count cap and a
    total-character cap, whichever bites first) before a turn is sent to
    the model. Every provider call sends the FULL thread history on every
    single message — with no cap, a long-running AI Console/Agent thread
    keeps growing until a request is too large for the provider's limits
    (this is exactly what caused Groq's `rate_limit_exceeded` / 413 "Request
    too large" errors: Groq's free tier caps llama-3.3-70b-versatile at
    6,000 tokens per request, and an old thread plus ~30 tool schemas blows
    past that fast). Trimming from the front (oldest first) is safe here
    because each AIConsole/Agent turn re-states enough site context via
    the system prompt's live snapshot — older chat turns aren't load-
    bearing the way they'd be in a document-analysis context."""
    trimmed = history[-max_messages:] if len(history) > max_messages else list(history)
    total = sum(len(m.get("content") or "") for m in trimmed)
    while total > max_chars and len(trimmed) > 1:
        total -= len(trimmed[0].get("content") or "")
        trimmed = trimmed[1:]
    return trimmed


def run_agent_turn(system_prompt, history, user, max_tokens=2000, _depth=0,
                    allowed_tools=None, model_name=None, temperature=None):
    """Runs one turn with real tool-calling: the model can call any of
    TOOL_SCHEMAS, each call actually executes via execute_tool(), and the
    result gets fed back so the model can use it or call another tool
    (capped at 5 tool calls per turn so a confused model can't loop
    forever). Returns (final_text, actions_taken, error).

    _depth tracks agent-to-agent delegation hops (see delegate_to_agent in
    execute_tool) so a delegation loop (A asks B asks A asks B...) can't
    recurse forever — capped at one hop deep.

    `allowed_tools`: optional list of tool names this specific caller is
    scoped to (an Agent's `tools_permissions`). Falsy/empty means "no
    restriction configured" — every tool is available, matching prior
    behavior for every agent that existed before this could be configured.
    A non-empty list is enforced TWICE: the model is never even shown the
    tools outside its allow-list (so it can't be talked into asking for
    one), and execute_tool() independently refuses to run anything not on
    the list, so a stale/forged tool_use block can't bypass the scoping.

    `model_name`/`temperature`: optional per-agent overrides.

    Tool-calling is wired up for Anthropic, OpenAI, Groq, and OpenRouter
    (all four support real actions — create drafts, send messages, etc.),
    and for Gemini via its REST function-calling API. Whichever provider
    is active in Admin -> Settings -> AI Providers is used automatically.
    """
    from app.ai_tools.routes import _resolve_ai_provider
    from app.utils.settings import get_setting

    provider, api_key = _resolve_ai_provider()
    if not provider:
        return None, [], "AI not configured — set a provider in Admin -> Settings -> AI Providers"

    # Cap history size before it ever reaches a provider call — see
    # trim_history_for_agent's docstring for why this exists.
    history = trim_history_for_agent(history)

    tool_schemas = TOOL_SCHEMAS
    if allowed_tools:
        allowed_set = set(allowed_tools)
        tool_schemas = [t for t in TOOL_SCHEMAS if t["name"] in allowed_set]

    if provider in ("openai", "groq", "openrouter"):
        return _run_agent_turn_openai_compatible(provider, api_key, system_prompt, history, user, max_tokens, temperature, tool_schemas, _depth)

    if provider == "gemini":
        return _run_agent_turn_gemini(api_key, system_prompt, history, user, max_tokens, temperature, tool_schemas, _depth)

    try:
        import anthropic
        model = model_name or get_setting("anthropic_model") or "claude-sonnet-5"
        temp = 0.7 if temperature is None else float(temperature)
        client = anthropic.Anthropic(api_key=api_key)
        messages = list(history)
        actions_taken = []

        for _ in range(5):
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temp,
                "system": system_prompt,
                "messages": messages,
            }
            if tool_schemas:
                kwargs["tools"] = tool_schemas
            resp = client.messages.create(**kwargs)
            if resp.stop_reason != "tool_use":
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                return final_text, actions_taken, None

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                if allowed_tools and block.name not in set(allowed_tools):
                    # Shouldn't happen since the model was never shown this
                    # tool, but enforced again here so scoping can't be
                    # bypassed by a malformed/forged tool_use block.
                    result = (f"Tool '{block.name}' is not permitted for this agent — "
                              f"its allowed tools are: {', '.join(allowed_tools)}.")
                else:
                    try:
                        result = execute_tool(block.name, block.input, user, _depth=_depth)
                    except Exception as e:
                        result = f"Tool '{block.name}' failed: {e}"
                actions_taken.append(result)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})

        return "I took several actions but hit the per-turn action limit — check what happened below.", actions_taken, None
    except Exception as e:
        return None, [], str(e)


def execute_tool(name, tool_input, user, _depth=0):
    """Actually performs one tool call named in TOOL_SCHEMAS. This function
    was previously missing entirely (its body existed but with no `def`
    line, so it silently threw NameError on every call, caught by the
    try/except in run_agent_turn and reported back to the model as
    "Tool 'x' failed: name 'execute_tool' is not defined" — meaning every
    single AI Console tool call has been failing since this was written).
    """
    from app.extensions import db

    if name == "create_blog_draft":
        from app.models.content import BlogPost
        import re
        title = tool_input["title"]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        base_slug, n = slug, 1
        while BlogPost.query.filter_by(slug=slug).first():
            n += 1
            slug = f"{base_slug}-{n}"
        post = BlogPost(title=title, slug=slug, content=tool_input["content"],
                         excerpt=tool_input.get("excerpt", ""), author_id=user.id, published=False)
        db.session.add(post)
        db.session.commit()
        return f'Created blog draft "{title}" (unpublished) — review it in Admin -> Blog Posts.'

    if name == "create_portfolio_project":
        from app.models.content import Project
        import re
        title = tool_input["title"]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        base_slug, n = slug, 1
        while Project.query.filter_by(slug=slug).first():
            n += 1
            slug = f"{base_slug}-{n}"
        project = Project(
            title=title, slug=slug, description=tool_input["description"],
            client_name=tool_input.get("client_name", ""),
            tech_stack=tool_input.get("tech_stack") or [],
            live_url=tool_input.get("live_url", ""), featured=False,
        )
        db.session.add(project)
        db.session.commit()
        return f'Added portfolio project "{title}" (not featured) — review and feature it in Admin -> Portfolio.'

    if name == "create_todo":
        from app.models.platform import TodoItem
        todo = TodoItem(user_id=user.id, title=tool_input["title"])
        db.session.add(todo)
        db.session.commit()
        return f'Added to-do: "{tool_input["title"]}"'

    if name == "send_test_email":
        from app.utils.email import send_email
        ok = send_email(tool_input["to"], tool_input["subject"], tool_input["body_html"])
        return (f'Sent email to {tool_input["to"]}.' if ok else
                f'Email to {tool_input["to"]} failed — check SMTP settings in Admin -> Settings -> Email.')

    if name == "create_automation_workflow":
        from app.models.platform import AutomationWorkflow
        active = tool_input.get("active", True)
        actions = []
        if tool_input.get("action_type"):
            actions.append({
                "type": tool_input["action_type"],
                "config": tool_input.get("action_config", {})
            })
        wf = AutomationWorkflow(
            name=tool_input["name"],
            trigger_type=tool_input["trigger_type"],
            actions=actions,
            active=active
        )
        db.session.add(wf)
        db.session.commit()
        return (f'Created active workflow "{tool_input["name"]}" (ID: {wf.id}) — '
                f'visible and live in Admin -> Automation Center.')

    if name == "create_site_popup":
        from app.models.core import SitePopup
        popup = SitePopup(
            title=tool_input["title"], headline=tool_input["headline"],
            body_html=tool_input.get("body_html", ""),
            trigger_type=tool_input.get("trigger_type", "delay"),
            trigger_value=tool_input.get("trigger_value", 5),
            active=False,
        )
        db.session.add(popup)
        db.session.commit()
        return f'Created popup "{tool_input["title"]}" (inactive) — review and activate it in Admin -> Site Popups.'

    if name == "get_site_stats":
        from datetime import datetime, timedelta
        from app.models.platform import ProjectRequest, SupportTicket
        from app.models.core import NewsletterSubscriber
        week_ago = datetime.utcnow() - timedelta(days=7)
        return (
            f"New Hire-Me requests: {ProjectRequest.query.filter_by(status='new').count()}. "
            f"Quoted proposals awaiting a decision: {ProjectRequest.query.filter_by(status='quoted').count()}. "
            f"Newsletter signups (last 7 days): {NewsletterSubscriber.query.filter(NewsletterSubscriber.created_at >= week_ago).count()}. "
            f"Open support tickets: {SupportTicket.query.filter(SupportTicket.status != 'closed').count()}."
        )

    if name == "create_lead":
        from app.models.platform import Lead
        email = tool_input["email"].strip().lower()
        existing = Lead.query.filter_by(email=email).first()
        if existing:
            return f"A lead with email {email} already exists (stage: {existing.deal_stage}) — use update_lead_stage instead."
        lead = Lead(
            name=tool_input.get("name", "").strip() or None, email=email,
            company=tool_input.get("company", "").strip() or None,
            niche=tool_input.get("niche", "").strip() or None,
            notes=tool_input.get("notes", "").strip() or None,
            source="AI Agent", status="new", deal_stage="new",
        )
        lead.ensure_token()
        db.session.add(lead)
        db.session.commit()
        return f"Added {email} to the CRM pipeline (stage: new) — see Admin -> CRM."

    if name == "update_lead_stage":
        from app.models.platform import Lead
        email = tool_input["email"].strip().lower()
        lead = Lead.query.filter_by(email=email).first()
        if not lead:
            return f"No lead found with email {email} — use create_lead first if this is a new prospect."
        changes = []
        new_stage = tool_input.get("deal_stage")
        if new_stage:
            lead.deal_stage = new_stage
            changes.append(f"stage -> {new_stage}")
        note = tool_input.get("note", "").strip()
        if note:
            lead.notes = (lead.notes + "\n" if lead.notes else "") + f"[AI Agent] {note}"
            changes.append("note added")
        if not changes:
            return f"No changes given for {email} — provide a deal_stage and/or a note."
        db.session.commit()
        return f"Updated {email}: {', '.join(changes)}."

    if name == "get_project_summary":
        from app.models.platform import ClientProject
        title_query = tool_input["project_title"].strip()
        matches = ClientProject.query.filter(ClientProject.title.ilike(f"%{title_query}%")).limit(5).all()
        if not matches:
            return f'No project found matching "{title_query}".'
        if len(matches) > 1:
            names = ", ".join(f'"{p.title}"' for p in matches)
            return f'Multiple projects match "{title_query}": {names}. Ask which one, or be more specific.'
        p = matches[0]
        total_invoiced = sum(float(i.amount) for i in p.invoices)
        total_paid = sum(float(i.amount_paid or 0) for i in p.invoices)
        milestone_summary = ", ".join(f"{m.title} ({m.status})" for m in p.milestones) or "none set"
        return (
            f'"{p.title}" — status: {p.status}, progress: {p.progress_pct}%, '
            f"due: {p.due_date or 'not set'}. "
            f"Milestones: {milestone_summary}. "
            f"Invoiced {total_invoiced:.2f}, paid {total_paid:.2f} of that."
        )

    if name == "schedule_meeting":
        from datetime import datetime as dt
        from app.models.platform import ClientProject, ProjectMeeting
        from app.utils.automation import trigger as automation_trigger
        from app.utils.email import send_email

        title_query = tool_input["project_title"].strip()
        matches = ClientProject.query.filter(ClientProject.title.ilike(f"%{title_query}%")).limit(5).all()
        if not matches:
            return f'No project found matching "{title_query}" — can\'t schedule a meeting without a real project.'
        if len(matches) > 1:
            names = ", ".join(f'"{p.title}"' for p in matches)
            return f'Multiple projects match "{title_query}": {names}. Ask which one, or be more specific.'
        proj = matches[0]

        try:
            scheduled_at = dt.fromisoformat(tool_input["scheduled_at"])
        except ValueError:
            return f'"{tool_input["scheduled_at"]}" isn\'t a valid date/time — use ISO format like 2026-08-01T15:00:00.'

        meeting = ProjectMeeting(
            project_id=proj.id, title=tool_input["title"], scheduled_at=scheduled_at,
            duration_minutes=tool_input.get("duration_minutes") or 30,
            location=tool_input.get("location", "").strip() or None,
            created_by_id=user.id,
        )
        db.session.add(meeting)
        db.session.commit()

        automation_trigger("meeting_scheduled", {
            "project": proj.title, "client": proj.client.name if proj.client else "",
            "title": meeting.title, "scheduled_at": scheduled_at.isoformat(), "location": meeting.location or "",
        })

        if proj.client and proj.client.email:
            send_email(
                to=proj.client.email,
                subject=f"Meeting scheduled: {meeting.title}",
                body_html=f"<p>A meeting has been scheduled on <strong>{proj.title}</strong>:</p>"
                          f"<p><strong>{meeting.title}</strong><br>{scheduled_at.strftime('%A, %B %d %Y at %I:%M %p')} "
                          f"({meeting.duration_minutes} min)</p>"
                          f"{'<p>Where: ' + meeting.location + '</p>' if meeting.location else ''}",
            )
        return (f'Scheduled "{meeting.title}" on "{proj.title}" for '
                f'{scheduled_at.strftime("%A, %B %d %Y at %I:%M %p")} — client notified by email.')

    if name == "delegate_to_agent":
        if _depth >= 1:
            return "Can't delegate further — already one hop deep (delegation is capped at a single hop to avoid loops)."
        from app.models.core import Agent, AgentMessage
        target_name = tool_input["agent_name"].strip()
        target = Agent.query.filter(Agent.name.ilike(target_name)).first()
        if not target:
            return f'No agent named "{target_name}" found.'
        if not target.active:
            return f'Agent "{target.name}" is paused — can\'t delegate to them right now.'

        message = tool_input["message"]
        db.session.add(AgentMessage(agent_id=target.id, role="user", content=f"[Delegated from another agent] {message}"))
        db.session.commit()
        target_history = [{"role": m.role, "content": m.content} for m in target.messages]
        target_system = (
            f"You are {target.name}" + (f", the {target.role}" if target.role else "")
            + f". Your instructions: {target.instructions}\n\n"
            "Another AI agent just delegated a task/question to you. Respond helpfully and directly — "
            "your reply goes straight back to them, not to a live chat."
        )
        text, _, err = run_agent_turn(
            target_system, target_history, user, max_tokens=1000, _depth=_depth + 1,
            allowed_tools=target.tools_permissions or None,
            model_name=target.model_name, temperature=target.temperature)
        if err:
            return f'Delegation to "{target.name}" failed: {err}'
        db.session.add(AgentMessage(agent_id=target.id, role="assistant", content=text or ""))
        db.session.commit()
        return f'{target.name} replied: {text}'

    if name == "generate_report":
        report_type = tool_input["report_type"]
        from datetime import datetime as dt
        month_start = dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if report_type == "revenue":
            from app.models.platform import Invoice
            invoices = Invoice.query.filter(Invoice.created_at >= month_start).all()
            by_currency = {}
            for inv in invoices:
                cur = inv.currency or "USD"
                by_currency.setdefault(cur, {"invoiced": 0.0, "paid": 0.0})
                by_currency[cur]["invoiced"] += float(inv.amount)
                by_currency[cur]["paid"] += float(inv.amount_paid or 0)
            if not by_currency:
                return "No invoices created this month yet."
            lines = [f"{cur}: invoiced {v['invoiced']:.2f}, paid {v['paid']:.2f}" for cur, v in by_currency.items()]
            return "Revenue this month — " + "; ".join(lines)

        if report_type == "pipeline":
            from app.models.platform import Lead
            stages = ["new", "qualified", "proposal", "won", "lost"]
            counts = {s: Lead.query.filter_by(deal_stage=s).count() for s in stages}
            return "CRM pipeline — " + ", ".join(f"{s}: {c}" for s, c in counts.items())

        if report_type == "projects":
            from app.models.platform import ClientProject
            active = ClientProject.query.filter(ClientProject.status.in_(["planning", "in_progress", "review"])).all()
            if not active:
                return "No active projects right now."
            lines = [f'"{p.title}" — {p.status}, {p.progress_pct}%' for p in active]
            return f"{len(active)} active project(s): " + "; ".join(lines)

        return f"Unknown report_type: {report_type}"

    if name == "search_knowledge_base":
        from app.utils.knowledge import search_knowledge_base, format_knowledge_results
        results = search_knowledge_base(tool_input["query"])
        return format_knowledge_results(results)

    if name == "list_inactive_customers":
        from datetime import datetime, timedelta
        from app.models.user import User, Role
        from app.models.platform import ClientProject
        from app.admin.routes import _client_last_activity

        days_threshold = tool_input.get("days") or 60
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        client_role = Role.query.filter_by(name="client").first()
        if not client_role:
            return "No client role configured — can't look up clients."
        clients = User.query.filter_by(role_id=client_role.id).all()

        results = []
        for c in clients:
            last_activity, source = _client_last_activity(c.id)
            if last_activity is None or last_activity >= cutoff:
                continue
            latest_project = ClientProject.query.filter_by(client_id=c.id).order_by(ClientProject.created_at.desc()).first()
            if latest_project and latest_project.status == "completed":
                continue
            days_quiet = (datetime.utcnow() - last_activity).days
            results.append(f"{c.name or c.email} — {days_quiet}d quiet (last: {source})")

        if not results:
            return f"No clients have gone quiet for {days_threshold}+ days on an unfinished project."
        return f"{len(results)} inactive client(s): " + "; ".join(results)

    if name == "create_faq_draft":
        from app.models.platform import FAQItem
        faq = FAQItem(
            question=tool_input["question"].strip(), answer=tool_input["answer"].strip(),
            category=(tool_input.get("category") or "General").strip(), active=False,
        )
        db.session.add(faq)
        db.session.commit()
        return f'Created FAQ draft "{faq.question}" — inactive, review and activate it in Admin -> FAQs.'

    if name == "update_project_status":
        from app.models.platform import ClientProject
        title_query = tool_input["project_title"].strip()
        matches = ClientProject.query.filter(ClientProject.title.ilike(f"%{title_query}%")).limit(5).all()
        if not matches:
            return f'No project found matching "{title_query}".'
        if len(matches) > 1:
            names = ", ".join(f'"{p.title}"' for p in matches)
            return f'Multiple projects match "{title_query}": {names}. Ask which one, or be more specific.'
        proj = matches[0]
        changes = []
        if tool_input.get("status"):
            proj.status = tool_input["status"]
            changes.append(f"status -> {proj.status}")
        if tool_input.get("progress_pct") is not None:
            proj.progress_pct = max(0, min(100, int(tool_input["progress_pct"])))
            changes.append(f"progress -> {proj.progress_pct}%")
        if not changes:
            return f'No changes given for "{proj.title}" — provide a status and/or progress_pct.'
        db.session.commit()
        return f'Updated "{proj.title}": {", ".join(changes)}.'

    if name == "create_testimonial_draft":
        from app.models.content import Testimonial
        rating = tool_input.get("rating") or 5
        testimonial = Testimonial(
            name=tool_input["name"].strip(), company=(tool_input.get("company") or "").strip() or None,
            content=tool_input["content"].strip(), rating=max(1, min(5, int(rating))), approved=False,
        )
        db.session.add(testimonial)
        db.session.commit()
        return f'Created testimonial draft from "{testimonial.name}" — unapproved, review it in Admin -> Testimonials.'

    if name == "create_auto_reply_rule":
        from app.models.platform import SocialChannel
        channel = SocialChannel.query.filter(SocialChannel.label.ilike(f'%{tool_input["channel_label"]}%')).first()
        if not channel:
            return f'No channel found matching "{tool_input["channel_label"]}".'
        rules = list(channel.auto_reply_rules or [])
        rules.append({
            "match": tool_input.get("match") or "contains",
            "keywords": tool_input["keywords"],
            "reply": tool_input["reply"],
            "show_products": False,
            "product_search": "",
        })
        channel.auto_reply_rules = rules
        db.session.commit()
        return f'Added an auto-reply rule to "{channel.label}" for keywords: {", ".join(tool_input["keywords"])}.'

    if name == "get_achievement_summary":
        from app.utils.achievements import get_achievement_summary
        period = tool_input.get("period") or "week"
        return get_achievement_summary(period)

    if name == "search_web":
        from app.utils.web_search import search_web
        result, err = search_web(tool_input["query"])
        return err or result

    if name == "detect_lead_niche":
        from app.models.platform import Lead
        from app.utils.lead_niche import detect_niche
        lead = Lead.query.filter_by(email=tool_input["email"].strip().lower()).first()
        if not lead:
            return f'No lead found with email {tool_input["email"]}.'
        niche, err = detect_niche(lead)
        if err:
            return err
        lead.niche = niche
        db.session.commit()
        return f'Detected niche for {lead.name or lead.email}: "{niche}" — saved on the lead record.'

    if name == "generate_video_ai":
        from app.utils.video_ai import generate_video
        result, err = generate_video(tool_input["prompt"])
        return err or f"Video AI returned: {result}"

    if name == "send_whatsapp_message":
        from app.utils.twilio_integration import send_whatsapp_message
        ok, err = send_whatsapp_message(tool_input["to"], tool_input["body"])
        return err if err else f'WhatsApp message sent to {tool_input["to"]}.'

    if name == "get_portfolio_content_summary":
        from app.models.content import Profile, Skill, Experience, Service, Project, Partner
        profile = Profile.query.first()
        skills = Skill.query.order_by(Skill.order).all()
        experience = Experience.query.order_by(Experience.order).all()
        services = Service.query.order_by(Service.order).all()
        projects = Project.query.order_by(Project.order).limit(10).all()
        partners = Partner.query.all()
        lines = []
        if profile:
            lines.append(f"Profile: name={profile.full_name!r}, title={profile.title!r}, "
                          f"subtitle={profile.subtitle!r}, bio={(profile.bio or '')[:200]!r}, "
                          f"about={(profile.about or '')[:300]!r}")
        else:
            lines.append("Profile: not set up yet.")
        lines.append("Skills: " + (", ".join(s.name for s in skills) or "none yet"))
        lines.append("Experience: " + ("; ".join(f"{e.role} at {e.company}" for e in experience) or "none yet"))
        lines.append("Services: " + (", ".join(s.title for s in services) or "none yet"))
        lines.append("Projects (up to 10): " + ("; ".join(p.title for p in projects) or "none yet"))
        lines.append("Partners: " + (", ".join(p.name for p in partners) or "none yet"))
        return "\n".join(lines)

    if name == "update_profile":
        from app.models.content import Profile
        profile = Profile.query.first()
        if not profile:
            profile = Profile(user_id=user.id)
            db.session.add(profile)
        changed = []
        for field in ("full_name", "title", "subtitle", "bio", "about",
                      "twitter", "github", "linkedin", "instagram", "resume_url"):
            if field in tool_input and tool_input[field] is not None:
                setattr(profile, field, tool_input[field])
                changed.append(field)
        if not changed:
            return "No profile fields given to update."
        db.session.commit()
        return f"Updated profile fields: {', '.join(changed)} — live on the site now."

    if name == "add_skill":
        from app.models.content import Skill
        skill = Skill(
            name=tool_input["name"], category=tool_input.get("category"),
            level=tool_input.get("level"), percentage=tool_input.get("percentage", 0),
        )
        db.session.add(skill)
        db.session.commit()
        return f'Added skill "{skill.name}" — live on the site now.'

    if name == "add_experience":
        from app.models.content import Experience
        exp = Experience(
            company=tool_input["company"], role=tool_input["role"],
            description=tool_input.get("description"),
            start_date=tool_input.get("start_date"), end_date=tool_input.get("end_date"),
            current=bool(tool_input.get("current", False)),
        )
        db.session.add(exp)
        db.session.commit()
        return f'Added experience "{exp.role} at {exp.company}" — live on the site now.'

    if name == "add_service":
        from app.models.content import Service
        svc = Service(
            title=tool_input["title"], description=tool_input.get("description"),
            price=tool_input.get("price"), features=tool_input.get("features") or [],
            active=True,
        )
        db.session.add(svc)
        db.session.commit()
        return f'Added service "{svc.title}" — active and live on the site now.'

    if name == "add_partner":
        from app.models.content import Partner
        partner = Partner(
            name=tool_input["name"], logo_url=tool_input["logo_url"],
            website=tool_input.get("website"), active=True,
        )
        db.session.add(partner)
        db.session.commit()
        return f'Added partner "{partner.name}" to the "Trusted by" strip — live on the site now.'

    if name == "connect_telegram_bot":
        from app.models.platform import SocialChannel
        from app.utils.social_bots import test_telegram_connection, register_telegram_webhook
        from flask import url_for
        bot_token = tool_input["bot_token"].strip()
        channel = SocialChannel(platform="telegram", label=tool_input.get("label", "Telegram Bot"),
                                 credentials={"bot_token": bot_token})
        channel.ensure_secret()
        db.session.add(channel)
        db.session.flush()
        try:
            bot_info = test_telegram_connection(bot_token)
            webhook_url = url_for("social.telegram_webhook", secret=channel.webhook_secret, _external=True)
            register_telegram_webhook(bot_token, webhook_url)
            channel.connected = True
            db.session.commit()
            return f'Connected Telegram bot @{bot_info.get("username")} — it\'s live and receiving messages.'
        except Exception as e:
            channel.connected = False
            channel.connection_error = str(e)
            db.session.commit()
            return f"Saved the bot token, but the connection check failed: {e}"

    if name == "connect_whatsapp_business":
        from app.models.platform import SocialChannel
        from app.utils.social_bots import test_whatsapp_connection
        import secrets as _secrets
        phone_number_id = tool_input["phone_number_id"].strip()
        access_token = tool_input["access_token"].strip()
        verify_token = _secrets.token_urlsafe(16)
        channel = SocialChannel(platform="whatsapp", label=tool_input.get("label", "WhatsApp"), credentials={
            "phone_number_id": phone_number_id, "access_token": access_token,
            "verify_token": verify_token, "app_secret": tool_input.get("app_secret", ""),
        })
        channel.ensure_secret()
        db.session.add(channel)
        try:
            test_whatsapp_connection(phone_number_id, access_token)
            channel.connected = True
            db.session.commit()
            return ("WhatsApp credentials verified and saved. One manual step left: open Admin -> "
                    "Social Channels, copy the Webhook URL and Verify Token shown there, and paste them "
                    "into your Meta App's WhatsApp -> Configuration page — Meta requires that click, no API can do it.")
        except Exception as e:
            channel.connected = False
            channel.connection_error = str(e)
            db.session.commit()
            return f"Saved, but the credential check failed: {e}"

    if name == "connect_linkedin_account":
        from app.models.platform import SocialChannel
        from app.utils.social_bots import test_linkedin_connection
        access_token = tool_input["access_token"].strip()
        channel = SocialChannel(platform="linkedin", label=tool_input.get("label", "LinkedIn"),
                                 credentials={"access_token": access_token})
        channel.ensure_secret()
        db.session.add(channel)
        try:
            profile_info = test_linkedin_connection(access_token)
            channel.connected = True
            channel.credentials["person_urn"] = f"urn:li:person:{profile_info.get('id')}"
            db.session.commit()
            return f'Connected LinkedIn profile "{profile_info.get("name")}" — live now.'
        except Exception as e:
            channel.connected = False
            channel.connection_error = str(e)
            db.session.commit()
            return f"Saved, but the credential check failed: {e}"

    if name == "set_tiktok_developer_keys":
        from app.utils.settings import set_setting
        set_setting("tiktok_client_key", tool_input["client_key"].strip())
        set_setting("tiktok_client_secret", tool_input["client_secret"].strip())
        return ("Saved your TikTok Client Key/Secret. TikTok requires one manual click to finish: "
                "open Admin -> Social Channels and click 'Connect TikTok' — that opens TikTok's own "
                "login screen, which no API call is allowed to bypass.")

    return f"Unknown tool: {name}"
