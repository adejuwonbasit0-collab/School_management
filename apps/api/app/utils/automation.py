"""
Automation Center Graph Engine — n8n/Zapier-style graph nodes and edge routing,
fully integrated into the Flask app.

This engine executes both:
1. Linear workflows (backwards compatibility)
2. Graph workflows (nodes and links)

Supports Logic nodes, Database nodes, API nodes, File nodes, and AI nodes.
Runs synchronously in-request with safety limits to avoid blocking workers.
"""
import time
import json
import re
import csv
import io
import sqlalchemy as sa
from datetime import datetime
import requests
from flask import current_app
from app.extensions import db

TRIGGERS = {
    "hire_request_submitted":   "New Hire-Me Request",
    "newsletter_subscribed":    "New Newsletter Subscriber",
    "job_application_submitted": "New Job Application",
    "channel_message_received": "Social Channel Message Received (WhatsApp/Telegram/Facebook)",
    "meeting_scheduled":        "Customer Meeting Scheduled",
    "manual":                   "Manual / Webhook Only",
    "schedule":                 "Scheduled (runs on an interval)",
    "user_registered":          "User Registered",
    "user_logged_in":           "User Logged In",
    "user_logged_out":          "User Logged Out",
    "payment_received":         "Payment Received",
    "payment_failed":           "Payment Failed",
}

ACTION_TYPES = {
    "send_email": "Send Email",
    "webhook":    "Call Webhook (Zapier / n8n / Slack / Discord / anything)",
    "notify_admin": "Create Admin Notification",
    "send_channel_reply": "Send WhatsApp/Telegram/Facebook Message",
    "voice_reply": "Send Voice Reply (text→speech, Telegram)",
    "post_to_linkedin": "Post update to LinkedIn",
    "append_google_sheet": "Append Row to Google Sheet",
    "ai_agent": "Run AI Agent",
    "condition": "If / Else Condition",
    "switch": "Switch / Router",
    "delay": "Wait / Sleep / Delay",
    "variables": "Set Context Variables",
    "math": "Math Operations",
    "json_data": "JSON Parse / Stringify",
    "csv_data": "CSV Parse / Stringify",
    "db_query": "Database CRUD Query",
    "api_request": "REST API Request",
    "file_manage": "File Manage (Zip/Resize/Crop)",
    "ai_node": "Run AI Model (Claude/OpenAI/Gemini)",
}

CONDITION_OPERATORS = {
    "eq": "equals",
    "neq": "does not equal",
    "contains": "contains",
    "not_contains": "does not contain",
    "gt": "is greater than (numeric)",
    "lt": "is less than (numeric)",
}


def convert_n8n_to_internal_graph(n8n_data: dict) -> dict:
    """Converts a standard n8n exported workflow JSON object into our internal graph representation."""
    name = n8n_data.get("name", "Imported n8n Workflow")
    nodes = n8n_data.get("nodes", [])
    connections = n8n_data.get("connections", {})
    
    internal_nodes = []
    internal_links = []
    canvas_positions = {}
    trigger_type = "manual"
    trigger_config = {}
    
    for i, node in enumerate(nodes):
        node_name = node.get("name", f"Node_{i}")
        node_id = str(node.get("id", f"node_{i}"))
        n8n_type = str(node.get("type", ""))
        params = node.get("parameters", {})
        pos = node.get("position", [200 + i * 180, 200])
        canvas_positions[node_id] = {"x": pos[0], "y": pos[1]}
        
        if "trigger" in n8n_type.lower() or "webhook" in n8n_type.lower() or n8n_type.endswith(".manualTrigger"):
            if "webhook" in n8n_type.lower():
                trigger_type = "manual"
                trigger_config = {"webhook_path": params.get("path", "")}
            elif "cron" in n8n_type.lower() or "schedule" in n8n_type.lower():
                trigger_type = "manual"
                trigger_config = {"schedule": params.get("rule", {})}
            internal_nodes.append({
                "id": node_id,
                "name": node_name,
                "type": "trigger",
                "config": trigger_config,
                "n8n_type": n8n_type,
            })
        else:
            internal_type = "api_request"
            if "httprequest" in n8n_type.lower() or "webhook" in n8n_type.lower():
                internal_type = "api_request"
            elif "email" in n8n_type.lower():
                internal_type = "send_email"
            elif "if" in n8n_type.lower():
                internal_type = "condition"
            elif "openai" in n8n_type.lower() or "anthropic" in n8n_type.lower() or "ai" in n8n_type.lower():
                internal_type = "ai_node"
            elif "code" in n8n_type.lower() or "function" in n8n_type.lower():
                internal_type = "variables"
            elif "sheet" in n8n_type.lower():
                internal_type = "append_google_sheet"
            
            internal_nodes.append({
                "id": node_id,
                "name": node_name,
                "type": internal_type,
                "config": params,
                "n8n_type": n8n_type,
            })
            
    for source_node_name, conn_data in connections.items():
        src_node = next((n for n in internal_nodes if n["name"] == source_node_name), None)
        if not src_node:
            continue
        main_conns = conn_data.get("main", [])
        for output_index, branch in enumerate(main_conns):
            for target_info in branch:
                target_node_name = target_info.get("node")
                tgt_node = next((n for n in internal_nodes if n["name"] == target_node_name), None)
                if tgt_node:
                    internal_links.append({
                        "source": src_node["id"],
                        "target": tgt_node["id"],
                        "sourceHandle": "main" if output_index == 0 else f"out_{output_index}",
                        "targetHandle": "in"
                    })
                    
    return {
        "name": name,
        "trigger_type": trigger_type,
        "trigger_config": trigger_config,
        "actions": {
            "nodes": internal_nodes,
            "links": internal_links
        },
        "canvas_positions": canvas_positions
    }


def convert_internal_graph_to_n8n(wf) -> dict:
    """Converts internal graph workflow to standard n8n JSON format for export."""
    actions = wf.actions or {}
    nodes = actions.get("nodes", []) if isinstance(actions, dict) else []
    links = actions.get("links", []) if isinstance(actions, dict) else []
    positions = wf.canvas_positions or {}
    
    n8n_nodes = []
    n8n_connections = {}
    
    id_to_name = {}
    for node in nodes:
        nid = str(node.get("id", ""))
        nname = node.get("name", f"Node {nid}")
        id_to_name[nid] = nname
        pos = positions.get(nid, {"x": 200, "y": 200})
        ntype = node.get("type", "api_request")
        
        n8n_type = node.get("n8n_type")
        if not n8n_type:
            if ntype == "trigger": n8n_type = "n8n-nodes-base.manualTrigger"
            elif ntype == "send_email": n8n_type = "n8n-nodes-base.emailSend"
            elif ntype == "api_request": n8n_type = "n8n-nodes-base.httpRequest"
            elif ntype == "condition": n8n_type = "n8n-nodes-base.if"
            elif ntype == "ai_node" or ntype == "ai_agent": n8n_type = "n8n-nodes-base.openAi"
            else: n8n_type = "n8n-nodes-base.httpRequest"
            
        n8n_nodes.append({
            "id": nid,
            "name": nname,
            "type": n8n_type,
            "typeVersion": 1,
            "position": [pos.get("x", 200), pos.get("y", 200)],
            "parameters": node.get("config", {})
        })
        
    for link in links:
        src_id = str(link.get("source", ""))
        tgt_id = str(link.get("target", ""))
        src_name = id_to_name.get(src_id)
        tgt_name = id_to_name.get(tgt_id)
        if src_name and tgt_name:
            if src_name not in n8n_connections:
                n8n_connections[src_name] = {"main": [[]]}
            n8n_connections[src_name]["main"][0].append({
                "node": tgt_name,
                "type": "main",
                "index": 0
            })
            
    return {
        "name": wf.name,
        "nodes": n8n_nodes,
        "connections": n8n_connections,
        "active": wf.active
    }


def _evaluate_condition(cfg: dict, context: dict) -> bool:
    field = cfg.get("field", "")
    operator = cfg.get("operator", "eq")
    expected = cfg.get("value", "")
    actual = _resolve_context_value(field, context)
    actual_str = "" if actual is None else str(actual)
    expected_str = "" if expected is None else str(expected)
    if operator == "eq":
        return actual_str.strip().lower() == expected_str.strip().lower()
    if operator == "neq":
        return actual_str.strip().lower() != expected_str.strip().lower()
    if operator == "contains":
        return expected_str.strip().lower() in actual_str.lower()
    if operator == "not_contains":
        return expected_str.strip().lower() not in actual_str.lower()
    if operator in ("gt", "lt"):
        try:
            a, b = float(actual_str), float(expected_str)
        except (TypeError, ValueError):
            return False
        return a > b if operator == "gt" else a < b
    return False


def _resolve_context_value(key_path: str, context: dict):
    """Resolves nested paths like 'node_1.output.name' or 'email' from context."""
    if not key_path:
        return None
    parts = key_path.split(".")
    curr = context
    for p in parts:
        if isinstance(curr, dict):
            curr = curr.get(p)
        elif hasattr(curr, p):
            curr = getattr(curr, p)
        else:
            return None
    return curr


def _render(template: str, context: dict) -> str:
    """Substitutes {{var}} or {{node_id.output}} syntax."""
    if not template or not isinstance(template, str):
        return template
    out = template
    matches = re.findall(r"\{\{([^}]+)\}\}", out)
    for match in matches:
        key = match.strip()
        val = _resolve_context_value(key, context)
        out = out.replace("{{" + match + "}}", str(val) if val is not None else "")
    return out


class GraphExecutor:
    """Executes a workflow represented as a directed graph of nodes and connections."""
    def __init__(self, workflow_id, graph_data, trigger_context):
        self.workflow_id = workflow_id
        self.nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
        self.connections = graph_data.get("connections", [])
        self.context = dict(trigger_context or {})
        self.log_lines = []
        self.visited = set()
        
        # Execution metrics
        self.api_calls = 0
        self.webhook_calls = 0
        self.ai_tokens = 0
        self.nodes_run = 0

    def get_outgoing_connections(self, node_id, from_pin=None):
        out = []
        for c in self.connections:
            if c.get("fromId") == node_id:
                if from_pin is None or c.get("fromPin") == from_pin:
                    out.append(c)
        return out

    def run(self):
        # Find trigger node
        trigger_node = None
        for n in self.nodes.values():
            if n.get("type") == "trigger" or n.get("id") == "trigger":
                trigger_node = n
                break
        if not trigger_node:
            self.log_lines.append("ERROR: No trigger node found in workflow.")
            return "failed"

        self.log_lines.append(f"Starting graph execution for trigger node: {trigger_node.get('id')}")
        self.visited.add(trigger_node["id"])
        self.nodes_run += 1
        
        # Run outgoing connections from trigger
        for conn in self.get_outgoing_connections(trigger_node["id"]):
            self.execute_node(conn["toId"], conn.get("toPin"))

        success_count = sum(1 for line in self.log_lines if "SUCCESS" in line)
        failed_count = sum(1 for line in self.log_lines if "FAILED" in line)
        if failed_count > 0:
            return "partial" if success_count > 0 else "failed"
        return "success"

    def execute_node(self, node_id, input_pin=None):
        if node_id in self.visited:
            # Prevent infinite loops in request execution
            if len(self.visited) > 15:
                self.log_lines.append(f"Loop limit reached at node: {node_id}")
                return
        
        node = self.nodes.get(node_id)
        if not node:
            return

        self.visited.add(node_id)
        self.nodes_run += 1
        kind = node.get("type")
        cfg = node.get("config", {}) or {}

        if cfg.get("disabled"):
            self.log_lines.append(f"SKIPPED [{kind}] {node_id} — node is disabled")
            # Still walk downstream from this node's "out" pin, same as a
            # no-op passthrough, so a disabled node in the middle of a
            # chain doesn't silently break everything after it.
            for conn in self.get_outgoing_connections(node_id, "out"):
                self.execute_node(conn["toId"], conn.get("toPin"))
            return

        self.log_lines.append(f"Executing node {node_id} [{kind}]")
        
        # Execute node logic
        next_pin = "out"
        node_result = None
        try:
            next_pin, node_result = self._run_node_logic(kind, cfg)
            self.log_lines.append(f"SUCCESS [{kind}] {node_id}")
        except Exception as e:
            self.log_lines.append(f"FAILED [{kind}] {node_id}: {e}")
            # Halt branch on failure
            return

        # Store node output in context
        self.context[node_id] = {"output": node_result}

        # Follow connections from this node based on the output pin
        for conn in self.get_outgoing_connections(node_id, next_pin):
            self.execute_node(conn["toId"], conn.get("toPin"))

    def _run_node_logic(self, kind, cfg):
        # 1. Standard Logic Actions (reuse existing if possible)
        if kind == "send_email":
            from app.utils.email import send_email
            to = _render(cfg.get("to", ""), self.context)
            if to == "admin" or not to:
                from app.utils.settings import get_setting
                to = get_setting("admin_notification_email") or current_app.config.get("MAIL_DEFAULT_SENDER") or ""
            if not to:
                raise ValueError("No recipient resolved for send_email action")
            subject = _render(cfg.get("subject", "Automation notification"), self.context)
            body = _render(cfg.get("body", ""), self.context)
            from_name = _render(cfg.get("from_name", ""), self.context).strip() or None
            reply_to = _render(cfg.get("reply_to", ""), self.context).strip() or None
            ok = send_email(to=to, subject=subject, body_html=body, from_name=from_name, reply_to=reply_to)
            if not ok:
                raise RuntimeError(f"send_email failed for {to}")
            return "out", f"Emailed {to}: {subject}"

        if kind == "webhook":
            self.webhook_calls += 1
            url = cfg.get("url")
            if not url:
                raise ValueError("webhook action missing url")
            resp = requests.post(url, json=self.context, timeout=8)
            if resp.status_code >= 400:
                raise RuntimeError(f"Webhook {url} returned {resp.status_code}")
            return "out", f"Webhook POST {url} -> {resp.status_code}"

        if kind == "notify_admin":
            from app.models.user import User
            from app.models.core import Notification
            message = _render(cfg.get("message", "Automation triggered"), self.context)
            admins = User.query.join(User.role).filter_by(name="admin").all()
            for admin in admins:
                db.session.add(Notification(user_id=admin.id, type="automation",
                                             title="Automation", body=message, read=False))
            db.session.commit()
            return "out", f"Notified {len(admins)} admin(s): {message}"

        if kind == "send_channel_reply":
            from app.models.platform import SocialChannel
            channel_id = cfg.get("channel_id")
            channel = SocialChannel.query.get(channel_id) if channel_id else None
            if not channel:
                raise ValueError("send_channel_reply action has no valid channel_id configured")
            to = _render(cfg.get("to", "") or "{{contact}}", self.context)
            if not to or to == "None":
                raise ValueError("send_channel_reply could not resolve recipient")
            message = _render(cfg.get("message", ""), self.context)
            from app.utils.social_bots import send_reply
            send_reply(channel, to, message)
            return "out", f"Sent {channel.platform} message to {to}"

        if kind == "voice_reply":
            # Real text-to-speech reply: renders the message template,
            # generates an actual audio file through the same TTS engine
            # the site's own AI Voice tool uses (app/utils/tts.py — real
            # edge-tts/gTTS/ElevenLabs calls, not a canned sample), then
            # delivers it as a real voice message. Telegram only for now
            # (sendAudio, multipart upload) — WhatsApp/Facebook voice
            # delivery need their own per-platform media-upload work,
            # which isn't built yet, so this fails loudly on those
            # platforms instead of silently sending nothing.
            from app.models.platform import SocialChannel
            channel_id = cfg.get("channel_id")
            channel = SocialChannel.query.get(channel_id) if channel_id else None
            if not channel:
                raise ValueError("voice_reply action has no valid channel_id configured")
            if channel.platform != "telegram":
                raise ValueError(
                    f"voice_reply only supports Telegram right now (channel is {channel.platform}). "
                    "WhatsApp/Facebook voice delivery isn't built yet."
                )
            to = _render(cfg.get("to", "") or "{{contact}}", self.context)
            if not to or to == "None":
                raise ValueError("voice_reply could not resolve recipient")
            message = _render(cfg.get("message", ""), self.context)
            if not message.strip():
                raise ValueError("voice_reply has no message text to speak")
            from app.utils.tts import generate_speech, _audio_dir
            import os as _os
            voice_id = cfg.get("voice_id") or "en-US-JennyNeural"
            result, error = generate_speech(message, voice_id=voice_id)
            if not result:
                raise RuntimeError(f"Text-to-speech generation failed: {error}")
            filename = result["audio_url"].rsplit("/", 1)[-1]
            filepath = _os.path.join(_audio_dir(), filename)
            from app.utils.social_bots import send_telegram_audio
            send_telegram_audio(channel, to, filepath, caption=cfg.get("caption") or None)
            self.ai_tokens += 0  # TTS isn't a token-metered LLM call; explicit no-op, not an omission
            return "out", f"Sent voice reply ({result['voice']}) to {to}"

        if kind == "post_to_linkedin":
            from app.models.platform import SocialChannel
            channel_id = cfg.get("channel_id")
            channel = SocialChannel.query.get(channel_id) if channel_id else None
            if not channel:
                raise ValueError("post_to_linkedin action has no valid channel_id configured")
            message = _render(cfg.get("message", ""), self.context)
            from app.utils.social_bots import post_to_linkedin
            post_to_linkedin(channel, message)
            return "out", f"Posted to LinkedIn channel {channel.label}"

        if kind == "append_google_sheet":
            from app.utils.settings import get_setting
            from app.utils.google_sheets import append_row, append_row_with_token, get_oauth_access_token
            spreadsheet_id = (cfg.get("spreadsheet_id") or "").strip()
            sheet_range = (cfg.get("sheet_range") or "Sheet1!A:Z").strip() or "Sheet1!A:Z"
            raw_values = cfg.get("values", "")
            columns = [_render(v.strip(), self.context) for v in raw_values.split("|")] if raw_values else []
            if not columns:
                raise ValueError("append_google_sheet action has no values configured")
            channel_id = cfg.get("channel_id")
            if channel_id:
                from app.models.platform import SocialChannel
                channel = SocialChannel.query.get(int(channel_id))
                if not channel or channel.platform != "google_sheets":
                    raise ValueError("Selected Google Sheets connection no longer exists")
                client_id = get_setting("google_oauth_client_id")
                client_secret = get_setting("google_oauth_client_secret")
                token = get_oauth_access_token(channel.credentials.get("refresh_token"), client_id, client_secret)
                append_row_with_token(token, spreadsheet_id, sheet_range, columns)
            else:
                sa_json = get_setting("google_service_account_json")
                append_row(sa_json, spreadsheet_id, sheet_range, columns)
            return "out", f"Appended row to Google Sheet {spreadsheet_id}"

        if kind == "ai_agent":
            from app.models.core import Agent, AgentMessage
            from app.models.user import User
            from app.utils.ai_agent_tools import run_agent_turn

            agent_id = cfg.get("agent_id")
            agent = Agent.query.get(int(agent_id)) if agent_id else None
            if not agent:
                raise ValueError("ai_agent action has no valid agent selected")
            if not agent.active:
                raise ValueError(f'Agent "{agent.name}" is paused')
            prompt = _render(cfg.get("message", ""), self.context)
            actor = User.query.get(agent.created_by) if agent.created_by else None
            if not actor:
                actor = User.query.join(User.role).filter_by(name="admin").first()
            if not actor:
                raise ValueError("No admin user exists to attribute actions")
            db.session.add(AgentMessage(agent_id=agent.id, role="user", content=f"[Automation trigger] {prompt}"))
            db.session.commit()
            history = [{"role": m.role, "content": m.content} for m in agent.messages]
            system = (
                f"You are {agent.name}" + (f", the {agent.role}" if agent.role else "")
                + f". Your instructions: {agent.instructions}\n\n"
                "You were just triggered automatically by a workflow. "
                "Keep your response short."
            )
            text, actions_taken, err = run_agent_turn(
                system, history, actor, max_tokens=1200,
                allowed_tools=agent.tools_permissions or None,
                model_name=agent.model_name, temperature=agent.temperature)
            if err:
                raise RuntimeError(f'Agent "{agent.name}" failed: {err}')
            full_response = text or ""
            if actions_taken:
                full_response = (full_response + "\n\n" if full_response else "") + "\n".join(f"🔧 {a}" for a in actions_taken)
            db.session.add(AgentMessage(agent_id=agent.id, role="assistant", content=full_response))
            db.session.commit()
            return "out", full_response

        # 2. Logic Nodes
        if kind == "condition":
            branch_taken = _evaluate_condition(cfg, self.context)
            return ("true" if branch_taken else "false"), branch_taken

        if kind == "switch":
            val = str(_resolve_context_value(cfg.get("field", ""), self.context)).strip().lower()
            cases = cfg.get("cases", [])
            for idx, case in enumerate(cases):
                if str(case).strip().lower() == val:
                    return f"output-{idx}", val
            return "default", val

        if kind == "delay":
            secs = min(5, max(1, int(cfg.get("seconds", 1))))
            time.sleep(secs)
            return "out", f"Delayed for {secs} seconds"

        if kind == "variables":
            var_name = cfg.get("var_name", "variable")
            var_value = _render(cfg.get("var_value", ""), self.context)
            self.context[var_name] = var_value
            return "out", var_value

        if kind == "math":
            expr = _render(cfg.get("expression", ""), self.context)
            # Safe basic evaluation of digits and math operators only
            clean_expr = re.sub(r"[^0-9.+\-*/() ]", "", expr)
            try:
                res = eval(clean_expr) if clean_expr else 0
            except:
                res = 0
            return "out", res

        # 3. Data Nodes
        if kind == "json_data":
            mode = cfg.get("mode", "parse")
            raw = cfg.get("data", "")
            if mode == "parse":
                parsed = json.loads(_render(raw, self.context))
                return "out", parsed
            else:
                stringified = json.dumps(_resolve_context_value(raw, self.context))
                return "out", stringified

        if kind == "csv_data":
            mode = cfg.get("mode", "parse")
            raw = _render(cfg.get("data", ""), self.context)
            if mode == "parse":
                f = io.StringIO(raw)
                reader = csv.DictReader(f)
                return "out", list(reader)
            else:
                data_list = _resolve_context_value(cfg.get("data", ""), self.context) or []
                if not isinstance(data_list, list):
                    data_list = [data_list]
                f = io.StringIO()
                if data_list:
                    writer = csv.DictWriter(f, fieldnames=data_list[0].keys())
                    writer.writeheader()
                    writer.writerows(data_list)
                return "out", f.getvalue()

        # 4. Database Nodes
        if kind == "db_query":
            query = _render(cfg.get("query", ""), self.context).strip()
            # A workflow node that runs arbitrary raw SQL against the
            # production database is a serious risk on its own — doubly so
            # since workflows can be IMPORTED from external n8n JSON
            # (convert_n8n_to_internal_graph above), which means a pasted-in
            # workflow file could otherwise run UPDATE/DELETE/DROP with zero
            # review. This was also crashing outright before (sqlalchemy
            # wasn't imported in this file at all), so it had never actually
            # been run successfully either way.
            #
            # This now only permits SELECT, and only against tables this
            # app actually owns (blocks sqlite_master, information_schema,
            # pg_* etc.) — reject anything else instead of silently
            # "helping" by trying to run it anyway. If you genuinely need a
            # workflow to write to the DB, use one of the specific actions
            # above (append_google_sheet, notify_admin, etc.) which are
            # scoped to one safe operation each, or ask me to add a new
            # narrowly-scoped write action for the exact thing you need.
            first_word = query.strip().split(None, 1)[0].lower() if query.strip() else ""
            if first_word != "select":
                raise ValueError(
                    "db_query only allows read-only SELECT statements — "
                    "write/DDL queries (INSERT/UPDATE/DELETE/DROP/ALTER/etc.) "
                    "are blocked here for safety. Use a specific action node "
                    "for writes instead."
                )
            if re.search(r"\b(pg_|information_schema|sqlite_master|sqlite_temp_master)\b", query, re.I):
                raise ValueError("db_query cannot access database metadata tables.")
            stmt = sa.text(query)
            params = cfg.get("params", {})
            rendered_params = {k: _render(v, self.context) for k, v in params.items()}
            result = db.session.execute(stmt, rendered_params)
            rows = [dict(row) for row in result.mappings().all()][:200]
            return "out", rows

        # 5. REST API Node
        if kind == "api_request":
            self.api_calls += 1
            method = cfg.get("method", "GET").upper()
            url = _render(cfg.get("url", ""), self.context)
            headers = cfg.get("headers", {})
            headers = {k: _render(v, self.context) for k, v in headers.items()}

            # If this node was configured to use a saved Connection, resolve
            # + decrypt it now and let it overwrite whatever placeholder
            # auth header the node started with (e.g. the catalog preset's
            # "Bearer YOUR_SLACK_BOT_TOKEN"). A missing/disabled credential
            # fails loudly here rather than silently sending an
            # unauthenticated request with stale placeholder text.
            credential_id = cfg.get("credential_id")
            if credential_id:
                from app.models.platform import AutomationCredential
                from app.utils.credential_providers import build_auth_header
                cred = AutomationCredential.query.get(credential_id)
                if not cred or not cred.active:
                    raise RuntimeError(
                        f"This node references a saved connection (id={credential_id}) "
                        "that no longer exists or has been disabled. Open the node and "
                        "pick a connection again."
                    )
                secret = cred.get_secret()
                if cred.provider == "google_gemini":
                    # Google's Generative Language API takes the key as a
                    # ?key= query param, not an Authorization header — the
                    # generic build_auth_header() correctly returns
                    # (None, None) for this (there IS no header), but that
                    # meant the credential was silently never applied at
                    # all here, so a configured Gemini connection would
                    # send a real, completely unauthenticated request and
                    # fail with a confusing 400 instead of using the key.
                    token = secret.get("token", "")
                    sep = "&" if "?" in url else "?"
                    url = f"{url}{sep}key={token}"
                else:
                    header_name, header_value = build_auth_header(cred.provider, secret)
                    if header_name and header_value:
                        headers[header_name] = header_value

            body_type = cfg.get("body_type", "json")
            body_raw = _render(cfg.get("body", ""), self.context)
            
            req_kwargs = {"headers": headers, "timeout": 10}
            if method in ("POST", "PUT", "PATCH"):
                if body_type == "json" and body_raw:
                    req_kwargs["json"] = json.loads(body_raw)
                elif body_raw:
                    req_kwargs["data"] = body_raw

            res = requests.request(method, url, **req_kwargs)
            res_content = res.text
            try:
                res_content = res.json()
            except:
                pass
            if res.status_code >= 400:
                raise RuntimeError(f"API returned status {res.status_code}: {res.text}")
            return "out", {"status": res.status_code, "body": res_content}

        # 6. File Node
        if kind == "file_manage":
            import os
            import zipfile
            from PIL import Image  # was "from Pillow import Image" — Pillow is
            # the pip package name, but the importable module is PIL. That
            # typo meant this node crashed with ModuleNotFoundError on every
            # single run before, regardless of config.
            op_type = cfg.get("operation", "zip")

            # Workflow-configured paths are restricted to one dedicated
            # folder rather than any absolute path on the server — letting
            # a workflow config (especially one imported from external n8n
            # JSON) read/write arbitrary filesystem paths is a real risk,
            # and nothing about this feature needs paths outside the app's
            # own storage.
            safe_root = os.path.join(current_app.instance_path, "automation_files")
            os.makedirs(safe_root, exist_ok=True)

            def _safe_path(raw):
                raw = (raw or "").strip().lstrip("/")
                full = os.path.realpath(os.path.join(safe_root, raw))
                if not full.startswith(os.path.realpath(safe_root) + os.sep) and full != os.path.realpath(safe_root):
                    raise ValueError(f"'{raw}' resolves outside the allowed automation_files folder.")
                return full

            file_path = _safe_path(_render(cfg.get("file_path", ""), self.context))
            dest_path = _safe_path(_render(cfg.get("dest_path", ""), self.context))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            if op_type == "zip":
                with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    if os.path.isdir(file_path):
                        for root, _, files in os.walk(file_path):
                            for file in files:
                                zipf.write(os.path.join(root, file),
                                           os.path.relpath(os.path.join(root, file), os.path.join(file_path, '..')))
                    else:
                        zipf.write(file_path, os.path.basename(file_path))
                return "out", f"Zipped file to {dest_path}"

            if op_type == "resize":
                width = int(cfg.get("width", 200))
                height = int(cfg.get("height", 200))
                with Image.open(file_path) as img:
                    img.thumbnail((width, height))
                    img.save(dest_path)
                return "out", f"Resized image saved to {dest_path}"

            if op_type == "crop":
                x, y = int(cfg.get("x", 0)), int(cfg.get("y", 0))
                width = int(cfg.get("width", 200))
                height = int(cfg.get("height", 200))
                with Image.open(file_path) as img:
                    img.crop((x, y, x + width, y + height)).save(dest_path)
                return "out", f"Cropped image saved to {dest_path}"

            raise ValueError(f"Unsupported file operation: {op_type}")

        # 7. AI Node
        if kind == "ai_node":
            # cfg.get("provider") used to be collected in the node's UI and
            # then silently ignored — _call_ai() auto-picks whichever
            # provider is configured/preferred admin-wide with its own
            # failover order, with no way to force a specific one, so
            # picking "Gemini" here did nothing and the call could still
            # run on Anthropic (or whatever else). Now actually honored:
            # an explicit provider goes straight to that one provider via
            # _call_ai_single(), using the exact same configured-key
            # lookup _call_ai() itself uses — fails clearly if that
            # provider has no key set, instead of silently substituting
            # a different one. No provider chosen keeps the old
            # auto-pick-with-failover behavior.
            from app.ai_tools.routes import _call_ai, _call_ai_single, _configured_providers_in_order
            provider = (cfg.get("provider") or "").strip()
            prompt = _render(cfg.get("prompt", ""), self.context)
            system = _render(cfg.get("system_prompt", ""), self.context)
            messages = [{"role": "user", "content": prompt}]

            if provider:
                configured = dict(_configured_providers_in_order())
                api_key = configured.get(provider)
                if not api_key:
                    raise ValueError(
                        f"ai_node is set to provider '{provider}' but no API key is configured for it "
                        "(Admin -> Settings -> AI Providers). Either add that key or clear the provider "
                        "field to use whichever provider is configured."
                    )
                text, err = _call_ai_single(provider, api_key, system, messages, max_tokens=1000)
            else:
                text, err = _call_ai(system, messages, max_tokens=1000)
            if err:
                raise RuntimeError(f"AI Node Generation failed: {err}")

            self.ai_tokens += len(prompt.split()) + len(text.split())
            return "out", text.strip()

        raise ValueError(f"Unknown node type: {kind}")


# ── Sequential Legacy Engine ────────────────────────────────────────────────
def _run_action(action: dict, context: dict) -> str:
    """Runs one action, returns a short log line."""
    kind = action.get("type")
    cfg = action.get("config", {})

    if kind == "send_email":
        from flask import current_app
        from app.utils.email import send_email
        to = _render(cfg.get("to", ""), context)
        if to == "admin" or not to:
            from app.utils.settings import get_setting
            to = get_setting("admin_notification_email") or current_app.config.get("MAIL_DEFAULT_SENDER") or ""
        if not to:
            raise ValueError("No recipient resolved for send_email action")
        subject = _render(cfg.get("subject", "Automation notification"), context)
        body = _render(cfg.get("body", ""), context)
        from_name = _render(cfg.get("from_name", ""), context).strip() or None
        reply_to = _render(cfg.get("reply_to", ""), context).strip() or None
        ok = send_email(to=to, subject=subject, body_html=body, from_name=from_name, reply_to=reply_to)
        if not ok:
            raise RuntimeError(f"send_email failed for {to}")
        return f"Emailed {to}: {subject}"

    if kind == "webhook":
        url = cfg.get("url")
        if not url:
            raise ValueError("webhook action missing url")
        resp = requests.post(url, json=context, timeout=8)
        if resp.status_code >= 400:
            raise RuntimeError(f"Webhook {url} returned {resp.status_code}")
        return f"Webhook POST {url} -> {resp.status_code}"

    if kind == "notify_admin":
        from app.models.user import User
        from app.models.core import Notification
        message = _render(cfg.get("message", "Automation triggered"), context)
        admins = User.query.join(User.role).filter_by(name="admin").all()
        for admin in admins:
            db.session.add(Notification(user_id=admin.id, type="automation",
                                         title="Automation", body=message, read=False))
        db.session.commit()
        return f"Notified {len(admins)} admin(s): {message}"

    if kind == "send_channel_reply":
        from app.models.platform import SocialChannel
        channel_id = cfg.get("channel_id")
        channel = SocialChannel.query.get(channel_id) if channel_id else None
        if not channel:
            raise ValueError("send_channel_reply action has no valid channel_id configured")
        to = _render(cfg.get("to", "") or "{{contact}}", context)
        if not to or to == "None":
            raise ValueError("send_channel_reply recipient unresolved")
        message = _render(cfg.get("message", ""), context)
        from app.utils.social_bots import send_reply
        send_reply(channel, to, message)
        return f"Sent {channel.platform} message to {to}"

    if kind == "post_to_linkedin":
        from app.models.platform import SocialChannel
        channel_id = cfg.get("channel_id")
        channel = SocialChannel.query.get(channel_id) if channel_id else None
        if not channel:
            raise ValueError("post_to_linkedin action has no valid channel_id configured")
        message = _render(cfg.get("message", ""), context)
        from app.utils.social_bots import post_to_linkedin
        post_to_linkedin(channel, message)
        return f"Posted to LinkedIn channel {channel.label}"

    if kind == "append_google_sheet":
        from app.utils.settings import get_setting
        from app.utils.google_sheets import append_row, append_row_with_token, get_oauth_access_token
        spreadsheet_id = (cfg.get("spreadsheet_id") or "").strip()
        sheet_range = (cfg.get("sheet_range") or "Sheet1!A:Z").strip() or "Sheet1!A:Z"
        raw_values = cfg.get("values", "")
        columns = [_render(v.strip(), context) for v in raw_values.split("|")] if raw_values else []
        if not columns:
            raise ValueError("append_google_sheet action has no values configured")

        channel_id = cfg.get("channel_id")
        if channel_id:
            from app.models.platform import SocialChannel
            channel = SocialChannel.query.get(int(channel_id))
            if not channel or channel.platform != "google_sheets":
                raise ValueError("Selected Google Sheets connection no longer exists")
            client_id = get_setting("google_oauth_client_id")
            client_secret = get_setting("google_oauth_client_secret")
            token = get_oauth_access_token(channel.credentials.get("refresh_token"), client_id, client_secret)
            append_row_with_token(token, spreadsheet_id, sheet_range, columns)
        else:
            sa_json = get_setting("google_service_account_json")
            append_row(sa_json, spreadsheet_id, sheet_range, columns)
        return f"Appended row to Google Sheet {spreadsheet_id}"

    if kind == "ai_agent":
        from app.models.core import Agent, AgentMessage
        from app.models.user import User
        from app.utils.ai_agent_tools import run_agent_turn

        agent_id = cfg.get("agent_id")
        agent = Agent.query.get(int(agent_id)) if agent_id else None
        if not agent:
            raise ValueError("ai_agent action has no valid agent selected")
        if not agent.active:
            raise ValueError(f'Agent "{agent.name}" is paused')

        prompt = _render(cfg.get("message", ""), context)
        actor = User.query.get(agent.created_by) if agent.created_by else None
        if not actor:
            actor = User.query.join(User.role).filter_by(name="admin").first()
        if not actor:
            raise ValueError("No admin user exists to attribute actions")

        db.session.add(AgentMessage(agent_id=agent.id, role="user", content=f"[Automation trigger] {prompt}"))
        db.session.commit()

        history = [{"role": m.role, "content": m.content} for m in agent.messages]
        system = (
            f"You are {agent.name}" + (f", the {agent.role}" if agent.role else "")
            + f". Your instructions: {agent.instructions}\n\n"
            "You were just triggered automatically by a workflow."
        )
        text, actions_taken, err = run_agent_turn(
            system, history, actor, max_tokens=1200,
            allowed_tools=agent.tools_permissions or None,
            model_name=agent.model_name, temperature=agent.temperature)
        if err:
            raise RuntimeError(f'Agent "{agent.name}" failed: {err}')

        full_response = text or ""
        if actions_taken:
            full_response = (full_response + "\n\n" if full_response else "") + "\n".join(f"🔧 {a}" for a in actions_taken)
        db.session.add(AgentMessage(agent_id=agent.id, role="assistant", content=full_response))
        db.session.commit()
        return f'Agent "{agent.name}" ran: {full_response[:160]}'

    raise ValueError(f"Unknown action type: {kind}")


def _run_action_list(actions: list, context: dict, log_lines: list) -> tuple:
    fail_count = 0
    total_count = 0
    for action in (actions or []):
        kind = action.get("type")
        cfg = action.get("config", {}) or {}
        if kind == "condition":
            branch_taken = _evaluate_condition(cfg, context)
            log_lines.append(
                f"Condition [{cfg.get('field')} {cfg.get('operator')} {cfg.get('value')}] "
                f"-> {'TRUE' if branch_taken else 'FALSE'}"
            )
            branch_actions = cfg.get("if_true" if branch_taken else "if_false") or []
            f, t = _run_action_list(branch_actions, context, log_lines)
            fail_count += f
            total_count += t
            continue
        total_count += 1
        try:
            log_lines.append(_run_action(action, context))
        except Exception as e:
            fail_count += 1
            log_lines.append(f"FAILED [{kind}]: {e}")
    return fail_count, total_count


def _run_workflow_and_log(wf, context: dict):
    """Runs ONE workflow (graph or legacy) and writes its AutomationRun.
    Extracted out of _execute_trigger's loop body so a scheduled workflow
    (run_scheduled_workflow, below) can execute a single specific
    workflow directly instead of going through trigger_type broadcast
    matching — which doesn't make sense for schedules, since two
    different scheduled workflows can have two different intervals and
    firing one must never fire the other early."""
    status = "success"
    log_output = ""
    metrics_data = {}
    start_time = time.time()

    if isinstance(wf.actions, dict) and ("nodes" in wf.actions or "connections" in wf.actions):
        executor = GraphExecutor(wf.id, wf.actions, context)
        status = executor.run()
        log_output = "\n".join(executor.log_lines)
        duration = int((time.time() - start_time) * 1000)
        metrics_data = {
            "execution_time_ms": duration,
            "api_calls_count": executor.api_calls,
            "webhook_requests_count": executor.webhook_calls,
            "ai_tokens_used": executor.ai_tokens,
            "nodes_run_count": executor.nodes_run,
        }
    else:
        log_lines = []
        fail_count, total_count = _run_action_list(wf.actions or [], context, log_lines)
        if total_count == 0 or fail_count == 0:
            status = "success"
        elif fail_count == total_count:
            status = "failed"
        else:
            status = "partial"
        log_output = "\n".join(log_lines)
        duration = int((time.time() - start_time) * 1000)
        metrics_data = {
            "execution_time_ms": duration,
            "nodes_run_count": total_count,
        }

    wf.run_count = (wf.run_count or 0) + 1
    wf.last_run_at = datetime.utcnow()

    from app.models.platform import AutomationRun
    run_log = AutomationRun(
        workflow_id=wf.id,
        status=status,
        trigger_data=context,
        log=log_output,
        metrics=metrics_data,
        created_at=datetime.utcnow()
    )
    db.session.add(run_log)
    db.session.commit()


def run_scheduled_workflow(workflow_id: int):
    """Runs exactly one workflow, for the scheduler (job_queue.py's
    _scheduler_loop) — never call this from a request handler; the
    scheduler already runs on the background worker thread inside its
    own app_context(), same as _execute_trigger()."""
    try:
        from app.models.platform import AutomationWorkflow
        wf = AutomationWorkflow.query.get(workflow_id)
        # Re-check active here, not just when the scheduler decided this
        # workflow was due — it could have been disabled in the seconds
        # between the scheduler tick queuing this job and the worker
        # thread actually picking it up.
        if not wf or not wf.active or wf.trigger_type != "schedule":
            return
        _run_workflow_and_log(wf, {"scheduled_at": datetime.utcnow().isoformat()})
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Scheduled workflow run failed for workflow_id=%s", workflow_id)


def trigger(event_type: str, context: dict):
    """Public entry point every real event in the app calls (payment
    received, form submitted, etc.). Just enqueues the job and returns
    immediately — see app/utils/job_queue.py for what actually runs it
    and this file's docstring there for the honest scope/limits of that
    queue. The real logic lives in _execute_trigger() below, unchanged
    from before except for the rename."""
    from app.utils.job_queue import enqueue
    enqueue(event_type, context)


def _execute_trigger(event_type: str, context: dict):
    """Fires all active workflows registered to event_type. Handles both graph and legacy schemas.
    Runs on the background worker thread (see job_queue.py), inside its
    own app_context() — never call this directly from a request handler;
    call trigger() instead."""
    try:
        from app.models.platform import AutomationWorkflow

        workflows = AutomationWorkflow.query.filter_by(
            trigger_type=event_type, active=True
        ).all()
        
        for wf in workflows:
            cfg = wf.trigger_config or {}
            # Match optional exact trigger filters
            if cfg and any(str(context.get(k)) != str(v) for k, v in cfg.items() if v not in (None, "")):
                continue
            _run_workflow_and_log(wf, context)

    except Exception:
        import logging
        logging.getLogger(__name__).exception("Automation trigger failed for event %s", event_type)

