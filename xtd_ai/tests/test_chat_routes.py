import json
import os
from unittest.mock import MagicMock, patch

from odoo import http
from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user
from odoo.tools.misc import Callbacks

from ..controllers import chat as chat_main
from .common import make_pdf

AI_GROUPS = "base.group_user,xtd_ai.group_xtd_ai_user"
SERVICE_URL = "http://ai_service:8000"
SERVICE_KEY = "test-service-key-0123456789abcdef0123456789abcdef"


@tagged("post_install", "-at_install")
class TestChatRoutes(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        patcher = patch.dict(
            os.environ,
            {"XTD_AI_SERVICE_URL": SERVICE_URL, "XTD_AI_SERVICE_KEY": SERVICE_KEY},
        )
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.u1 = new_test_user(
            cls.env, "chat_u1", groups=AI_GROUPS + ",base.group_partner_manager"
        )
        cls.u2 = new_test_user(cls.env, "chat_u2", groups=AI_GROUPS)
        cls.plain = new_test_user(cls.env, "chat_plain", groups="base.group_user")

    # -- helpers ---------------------------------------------------------
    def login(self, user):
        self.authenticate(user.login, user.login + "x" * (8 - len(user.login)))

    def rpc(self, route, **params):
        return self.url_open(
            route,
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": params}),
            headers={"Content-Type": "application/json"},
        ).json()

    def ok(self, route, **params):
        data = self.rpc(route, **params)
        self.assertNotIn("error", data, data)
        return data["result"]

    def capture_postcommit(self):
        """Record the callbacks registered on cursors (TestCursor never runs them)."""
        captured = []
        original = Callbacks.add

        def add(callbacks, func):
            if "XtdAiChatController" in func.__qualname__:
                captured.append(func)
            return original(callbacks, func)

        patcher = patch.object(Callbacks, "add", add)
        patcher.start()
        self.addCleanup(patcher.stop)
        return captured

    def make_action(self, user, **vals):
        conversation = self.env["xtd.ai.conversation"].with_user(user)._xtd_ai_open()
        run, _token = conversation._xtd_ai_start_run("hola")
        run.sudo()._xtd_ai_finish("done")
        values = {
            "run_id": run.id,
            "conversation_id": conversation.id,
            "user_id": user.id,
            "tool_name": "create_contact",
            "arguments": {"name": "Chat Test SL"},
            "preview": {
                "summary": "Crear contacto «Chat Test SL»",
                "lines": [{"field": "name", "value": "Chat Test SL"}],
            },
            "cids": [user.company_id.id],
        }
        values.update(vals)
        return self.env["xtd.ai.pending_action"].sudo().create(values)

    # -- access ----------------------------------------------------------
    def test_requires_login(self):
        response = self.url_open(
            "/xtd_ai/chat/open",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": {}}),
            headers={"Content-Type": "application/json"},
        )
        self.assertNotIn("result", response.text)

    def test_requires_ai_group(self):
        self.login(self.plain)
        for route, params in (
            ("/xtd_ai/chat/open", {}),
            ("/xtd_ai/chat/conversations", {}),
            ("/xtd_ai/chat/settings", {}),
            ("/xtd_ai/chat/send", {"text": "hola"}),
        ):
            data = self.rpc(route, **params)
            self.assertIn("error", data, route)
            self.assertIn("agente IA", json.dumps(data["error"]), route)

    # -- send / service call -----------------------------------------------
    def test_send_calls_service_only_after_commit(self):
        captured = self.capture_postcommit()
        self.login(self.u1)
        with patch.object(chat_main.requests, "post") as post:
            post.return_value = MagicMock(status_code=202)
            res = self.ok("/xtd_ai/chat/send", text="¿Qué clientes tengo?")
            self.assertEqual(res["state"], "queued")
            post.assert_not_called()  # nothing before the commit
            self.assertEqual(len(captured), 1)
            run = self.env["xtd.ai.run"].sudo().browse(res["run_id"])
            self.assertEqual(run.state, "queued")
            captured[0]()  # the post-commit hook
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], SERVICE_URL + "/v1/runs")
        self.assertEqual(kwargs["timeout"], 5)
        self.assertEqual(kwargs["headers"], {"X-XTD-AI-Service-Key": SERVICE_KEY})
        body = kwargs["json"]
        self.assertEqual(set(body), {"run_id", "conversation_id", "db", "token"})
        self.assertEqual(body["run_id"], run.id)
        self.assertEqual(body["conversation_id"], run.conversation_id.id)
        self.assertEqual(body["db"], self.env.cr.dbname)
        self.assertTrue(body["token"].startswith("xtdai1."))
        self.assertEqual(run.sudo().state, "queued")  # accepted: stays queued

    def test_send_uses_active_companies_of_switcher(self):
        from ..tools.token import parse_token

        main = self.env.company
        other = self.env["res.company"].create({"name": "Chat second company"})
        foreign = self.env["res.company"].create({"name": "Chat foreign company"})
        self.u1.write({"company_ids": [(4, other.id)]})
        captured = self.capture_postcommit()
        self.login(self.u1)
        secret = self.env["xtd.ai.token"].sudo()._xtd_ai_secret()

        def sent_cids(company_ids):
            with patch.object(chat_main.requests, "post") as post:
                post.return_value = MagicMock(status_code=202)
                res = self.ok("/xtd_ai/chat/send", text="hola", company_ids=company_ids)
                captured.pop()()
                payload, _reason = parse_token(
                    secret, post.call_args.kwargs["json"]["token"]
                )
            self.env["xtd.ai.run"].sudo().browse(res["run_id"]).write({"state": "done"})
            return payload["cids"]

        # order kept (first = current company); foreign and bogus ids dropped
        self.assertEqual(
            sent_cids([other.id, main.id, foreign.id, 999999]), [other.id, main.id]
        )
        # nothing valid → the user's default company
        self.assertEqual(sent_cids([foreign.id]), [self.u1.company_id.id])
        self.assertEqual(sent_cids(None), [self.u1.company_id.id])

    def test_service_failure_fails_run_with_notice(self):
        captured = self.capture_postcommit()
        self.login(self.u1)
        with patch.object(chat_main.requests, "post", side_effect=OSError("boom")):
            res = self.ok("/xtd_ai/chat/send", text="hola")
            captured[0]()
        run = self.env["xtd.ai.run"].sudo().browse(res["run_id"])
        run.invalidate_recordset()
        self.assertEqual(run.state, "failed")
        notice = (
            self.env["xtd.ai.message"]
            .sudo()
            .search([("run_id", "=", run.id), ("role", "=", "notice")])
        )
        self.assertEqual(len(notice), 1)
        self.assertIn("servicio del agente IA", notice.body)
        self.assertNotIn("xtdai1", notice.body)

    def test_service_rejection_fails_run(self):
        captured = self.capture_postcommit()
        self.login(self.u1)
        with patch.object(
            chat_main.requests, "post", return_value=MagicMock(status_code=401)
        ):
            res = self.ok("/xtd_ai/chat/send", text="hola")
            captured[0]()
        run = self.env["xtd.ai.run"].sudo().browse(res["run_id"])
        run.invalidate_recordset()
        self.assertEqual(run.state, "failed")

    def test_missing_env_fails_run(self):
        captured = self.capture_postcommit()
        self.login(self.u1)
        with (
            patch.dict(os.environ, {}, clear=False) as env,
            patch.object(chat_main.requests, "post") as post,
        ):
            env.pop("XTD_AI_SERVICE_URL", None)
            env.pop("ANTHROPIC_API_KEY", None)
            res = self.ok("/xtd_ai/chat/send", text="hola")
        post.assert_not_called()
        self.assertEqual(captured, [])
        self.assertEqual(res["state"], "failed")
        notice = (
            self.env["xtd.ai.message"]
            .sudo()
            .search([("run_id", "=", res["run_id"]), ("role", "=", "notice")])
        )
        # integrated mode without a possible provider: points to the settings
        self.assertIn("Ajustes → Agente IA", notice.body)

    def test_external_mode_without_service_key_fails_run(self):
        self.login(self.u1)
        with (
            patch.dict(os.environ, {}, clear=False) as env,
            patch.object(chat_main.requests, "post") as post,
        ):
            env.pop("XTD_AI_SERVICE_KEY", None)
            res = self.ok("/xtd_ai/chat/send", text="hola")
        post.assert_not_called()
        self.assertEqual(res["state"], "failed")
        notice = (
            self.env["xtd.ai.message"]
            .sudo()
            .search([("run_id", "=", res["run_id"]), ("role", "=", "notice")])
        )
        self.assertIn("XTD_AI_SERVICE_KEY", notice.body)

    def test_second_send_while_running_is_refused(self):
        self.capture_postcommit()
        self.login(self.u1)
        res = self.ok("/xtd_ai/chat/send", text="primero")
        data = self.rpc("/xtd_ai/chat/send", text="segundo")
        self.assertIn("error", data)
        self.assertIn("en curso", json.dumps(data["error"], ensure_ascii=False))
        conversation = (
            self.env["xtd.ai.run"].sudo().browse(res["run_id"]).conversation_id
        )
        self.assertEqual(
            len(conversation.message_ids.filtered(lambda m: m.role == "user")), 1
        )
        # after cancelling it can send again
        self.ok("/xtd_ai/chat/run/cancel", run_id=res["run_id"])
        self.ok("/xtd_ai/chat/send", text="tercero")

    # -- isolation -----------------------------------------------------------
    def test_other_user_cannot_touch_conversation_or_actions(self):
        self.capture_postcommit()
        self.login(self.u1)
        res = self.ok("/xtd_ai/chat/send", text="mío")
        action = self.make_action(self.u2)
        run1 = res["run_id"]
        conv1 = res["conversation_id"]
        self.login(self.u2)
        for route, params in (
            ("/xtd_ai/chat/messages", {"conversation_id": conv1}),
            ("/xtd_ai/chat/send", {"text": "intruso", "conversation_id": conv1}),
            ("/xtd_ai/chat/run/cancel", {"run_id": run1}),
        ):
            self.assertIn("error", self.rpc(route, **params), route)
        self.assertEqual(self.env["xtd.ai.run"].sudo().browse(run1).state, "queued")
        # u1 cannot confirm or cancel u2's pending action
        self.login(self.u1)
        for route in ("/xtd_ai/chat/pending/confirm", "/xtd_ai/chat/pending/cancel"):
            self.assertIn("error", self.rpc(route, action_id=action.id), route)
        self.assertEqual(action.state, "pending")

    # -- pending actions -----------------------------------------------------
    def test_confirm_and_cancel_pending_action(self):
        action = self.make_action(self.u1)
        action2 = self.make_action(self.u1)
        self.login(self.u1)
        res = self.ok("/xtd_ai/chat/pending/confirm", action_id=action.id)
        self.assertEqual(res["state"], "confirmed")
        self.assertEqual(res["action"]["result"]["model"], "res.partner")
        partner_id = res["action"]["result"]["id"]
        self.assertEqual(
            res["action"]["result"]["url"], f"/odoo/res.partner/{partner_id}"
        )
        self.assertEqual(res["action"]["title"], "Crear contacto")
        self.assertIn(
            "error", self.rpc("/xtd_ai/chat/pending/confirm", action_id=action.id)
        )
        res = self.ok("/xtd_ai/chat/pending/cancel", action_id=action2.id)
        self.assertEqual(res["state"], "cancelled")
        self.assertEqual(action2.state, "cancelled")

    def test_messages_payload_and_record_links(self):
        action = self.make_action(self.u1)
        partner = self.env["res.partner"].create({"name": "Cliente Enlace"})
        message = (
            self.env["xtd.ai.message"]
            .sudo()
            .create(
                {
                    "conversation_id": action.conversation_id.id,
                    "role": "assistant",
                    "body": "Listo **hecho** https://evil.example",
                    "run_id": action.run_id.id,
                    "record_refs": [
                        {
                            "model": "res.partner",
                            "id": partner.id,
                            "name": "Cliente Enlace",
                            "created": True,
                        },
                        {"model": "res.partner'; drop", "id": 1, "name": "x"},
                        {"model": "res.partner", "id": "7", "name": "x"},
                        {"model": "res.partner", "id": -3, "name": "x"},
                        "junk",
                    ],
                }
            )
        )
        action.message_id = message
        self.login(self.u1)
        res = self.ok(
            "/xtd_ai/chat/messages", conversation_id=action.conversation_id.id
        )
        payload = next(m for m in res["messages"] if m["id"] == message.id)
        self.assertEqual(payload["role"], "assistant")
        self.assertEqual(payload["body"], "Listo **hecho** https://evil.example")
        self.assertEqual(payload["run_state"], "done")
        self.assertEqual(
            [r["url"] for r in payload["record_refs"]],
            [f"/odoo/res.partner/{partner.id}"],
        )
        card = payload["pending_actions"][0]
        self.assertEqual(card["id"], action.id)
        self.assertEqual(card["state"], "pending")
        self.assertEqual(card["summary"], "Crear contacto «Chat Test SL»")
        self.assertEqual(card["lines"], [{"field": "name", "value": "Chat Test SL"}])
        self.assertTrue(card["expires_at"])
        self.assertFalse(res["running_run_id"])

    def test_open_fresh_from_icon(self):
        """The navbar icon starts a new conversation unless there is nothing to lose."""
        conversations = self.env["xtd.ai.conversation"]
        self.login(self.u1)
        # empty open conversation: reused, no banner
        first = self.ok("/xtd_ai/chat/open")
        again = self.ok("/xtd_ai/chat/open", fresh=True)
        self.assertEqual(again["conversation_id"], first["conversation_id"])
        self.assertFalse(again["auto_started"])
        # with messages and nothing in progress: closed, new one, banner to the old one
        conv = conversations.browse(first["conversation_id"])
        run, _token = conv.with_user(self.u1)._xtd_ai_start_run("hola")
        run.sudo()._xtd_ai_finish("done")
        fresh = self.ok("/xtd_ai/chat/open", fresh=True)
        self.assertNotEqual(fresh["conversation_id"], conv.id)
        self.assertEqual(conv.state, "closed")
        self.assertTrue(fresh["auto_started"])
        self.assertEqual(fresh["previous_conversation_id"], conv.id)
        # a pending action that can still be confirmed keeps the conversation open
        action = self.make_action(self.u1)
        kept = self.ok("/xtd_ai/chat/open", fresh=True)
        self.assertEqual(kept["conversation_id"], action.conversation_id.id)
        self.assertEqual(action.conversation_id.state, "open")
        # once resolved, the icon starts a new one again
        action.sudo().write({"state": "cancelled"})
        after = self.ok("/xtd_ai/chat/open", fresh=True)
        self.assertNotEqual(after["conversation_id"], action.conversation_id.id)

    def test_open_fresh_keeps_running_answer(self):
        self.login(self.u1)
        first = self.ok("/xtd_ai/chat/open")
        conv = self.env["xtd.ai.conversation"].browse(first["conversation_id"])
        conv.with_user(self.u1)._xtd_ai_start_run("hola")  # queued: still in progress
        kept = self.ok("/xtd_ai/chat/open", fresh=True)
        self.assertEqual(kept["conversation_id"], conv.id)
        self.assertEqual(conv.state, "open")

    def test_open_new_conversation(self):
        self.login(self.u1)
        first = self.ok("/xtd_ai/chat/open")
        again = self.ok("/xtd_ai/chat/open")
        self.assertEqual(first["conversation_id"], again["conversation_id"])
        new = self.ok("/xtd_ai/chat/open", new=True)
        self.assertNotEqual(new["conversation_id"], first["conversation_id"])
        self.assertEqual(
            self.env["xtd.ai.conversation"].browse(first["conversation_id"]).state,
            "closed",
        )
        listing = self.ok("/xtd_ai/chat/conversations")
        # the closed one is empty (nothing to read): only the current one is listed
        self.assertEqual({c["id"] for c in listing}, {new["conversation_id"]})

    # -- read-only history ---------------------------------------------------
    def closed_conversation_with_messages(self, user, text="primera pregunta"):
        self.login(user)
        res = self.ok("/xtd_ai/chat/send", text=text)
        run = self.env["xtd.ai.run"].sudo().browse(res["run_id"])
        run._xtd_ai_finish("done")
        self.env["xtd.ai.message"].sudo().create(
            {
                "conversation_id": res["conversation_id"],
                "role": "assistant",
                "body": "respuesta",
                "run_id": run.id,
            }
        )
        self.ok("/xtd_ai/chat/open", new=True)
        return res["conversation_id"]

    def test_closed_conversation_cannot_be_sent_to(self):
        self.capture_postcommit()
        conv_id = self.closed_conversation_with_messages(self.u1)
        data = self.rpc("/xtd_ai/chat/send", text="reanudar", conversation_id=conv_id)
        self.assertIn("error", data)
        self.assertIn("cerrada", json.dumps(data, ensure_ascii=False))
        conversation = self.env["xtd.ai.conversation"].sudo().browse(conv_id)
        self.assertEqual(conversation.state, "closed")
        self.assertFalse(conversation.run_ids.filtered(lambda r: r.state == "queued"))
        self.assertFalse(
            conversation.message_ids.filtered(lambda m: m.body == "reanudar")
        )

    def test_history_lists_only_own_conversations(self):
        self.capture_postcommit()
        mine = self.closed_conversation_with_messages(
            self.u1, "pregunta de u1 " + "x" * 100
        )
        theirs = self.closed_conversation_with_messages(self.u2, "pregunta de u2")
        self.login(self.u1)
        listing = self.ok("/xtd_ai/chat/conversations")
        ids = {c["id"] for c in listing}
        self.assertIn(mine, ids)
        self.assertNotIn(theirs, ids)
        item = next(c for c in listing if c["id"] == mine)
        self.assertEqual(item["state"], "closed")
        self.assertTrue(item["name"].startswith("pregunta de u1"))
        self.assertLessEqual(len(item["name"]), 60)
        self.assertEqual(item["message_count"], 2)
        self.assertTrue(item["date"])

    def test_closed_conversation_messages_readable_but_not_actionable(self):
        conv_id = self.closed_conversation_with_messages(self.u1)
        action = self.make_action(self.u1)
        action.message_id = (
            self.env["xtd.ai.message"]
            .sudo()
            .create(
                {
                    "conversation_id": action.conversation_id.id,
                    "role": "assistant",
                    "body": "propuesta",
                    "run_id": action.run_id.id,
                }
            )
        )
        self.login(self.u1)
        res = self.ok(
            "/xtd_ai/chat/messages", conversation_id=action.conversation_id.id
        )
        live = [a for m in res["messages"] for a in m["pending_actions"]]
        self.assertTrue(live and all(a["actionable"] for a in live))
        action.conversation_id.sudo().action_close()
        res = self.ok("/xtd_ai/chat/messages", conversation_id=conv_id)
        self.assertEqual(res["state"], "closed")
        self.assertEqual([m["role"] for m in res["messages"]], ["user", "assistant"])
        res = self.ok(
            "/xtd_ai/chat/messages", conversation_id=action.conversation_id.id
        )
        cards = [a for m in res["messages"] for a in m["pending_actions"]]
        self.assertTrue(cards)
        for card in cards:
            self.assertFalse(card["actionable"])
        # other user cannot read it
        self.login(self.u2)
        self.assertIn(
            "error", self.rpc("/xtd_ai/chat/messages", conversation_id=conv_id)
        )

    def test_confirm_and_cancel_refused_on_closed_conversation(self):
        action = self.make_action(self.u1)
        self.login(self.u1)
        action.conversation_id.sudo().action_close()
        for route in ("/xtd_ai/chat/pending/confirm", "/xtd_ai/chat/pending/cancel"):
            data = self.rpc(route, action_id=action.id)
            self.assertIn("error", data, route)
            self.assertIn("cerrada", json.dumps(data, ensure_ascii=False))
        self.assertEqual(action.state, "pending")
        self.assertFalse(
            self.env["res.partner"].sudo().search([("name", "=", "Chat Test SL")])
        )

    # -- settings ------------------------------------------------------------
    def test_settings_toggle_and_forced(self):
        self.login(self.u1)
        res = self.ok("/xtd_ai/chat/settings", confirm_writes=False)
        self.assertEqual(res, {"forced": False, "confirm_writes": False})
        self.assertFalse(self.u1.xtd_ai_confirm_writes)
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.force_confirmation", "True"
        )
        res = self.ok("/xtd_ai/chat/settings", confirm_writes=False)
        self.assertEqual(res, {"forced": True, "confirm_writes": True})
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.force_confirmation", "False"
        )
        res = self.ok("/xtd_ai/chat/settings", confirm_writes=True)
        self.assertEqual(res["confirm_writes"], True)

    # -- attachments (CONTRACT §14) ----------------------------------------
    PDF = make_pdf()
    PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

    def upload(self, name, data, conversation_id=None, csrf=True, ctype=None):
        fields = {}
        if csrf:
            fields["csrf_token"] = http.Request.csrf_token(self)
        if conversation_id is not None:
            fields["conversation_id"] = str(conversation_id)
        response = self.url_open(
            "/xtd_ai/chat/upload",
            data=fields,
            files={"ufile": (name, data, ctype or "application/octet-stream")},
        )
        return response

    def test_upload_pdf_and_png(self):
        self.login(self.u1)
        conv = self.ok("/xtd_ai/chat/open")["conversation_id"]
        res = self.upload("factura.pdf", self.PDF, conv)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["name"], "factura.pdf")
        self.assertEqual(data["mimetype"], "application/pdf")
        self.assertEqual(data["size"], len(self.PDF))
        attachment = self.env["ir.attachment"].browse(data["attachment_id"])
        self.assertEqual(attachment.res_model, "xtd.ai.conversation")
        self.assertEqual(attachment.res_id, conv)
        self.assertEqual(attachment.create_uid, self.u1)
        # without conversation_id: the open conversation of the user
        res = self.upload("foto.png", self.PNG)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["mimetype"], "image/png")

    def test_upload_rejects_bad_type_size_and_csrf(self):
        self.login(self.u1)
        conv = self.ok("/xtd_ai/chat/open")["conversation_id"]
        before = self.env["ir.attachment"].search_count([])
        # a text file renamed .pdf: the real content is checked, not the name
        res = self.upload("falso.pdf", b"hola mundo", conv, ctype="application/pdf")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Tipo de fichero no admitido", res.json()["error"])
        # extension that does not match the content
        res = self.upload("falso.png", self.PDF, conv)
        self.assertEqual(res.status_code, 400)
        res = self.upload("macro.exe", b"MZ" + b"\x00" * 10, conv)
        self.assertEqual(res.status_code, 400)
        big = self.PDF + b"0" * (chat_main.UPLOAD_MAX_BYTES + 1)
        res = self.upload("grande.pdf", big, conv)
        self.assertEqual(res.status_code, 400)
        self.assertIn("10 MB", res.json()["error"])
        res = self.upload("vacio.pdf", b"", conv)
        self.assertEqual(res.status_code, 400)
        res = self.upload("sin_csrf.pdf", self.PDF, conv, csrf=False)
        self.assertNotEqual(res.status_code, 200)
        self.assertEqual(self.env["ir.attachment"].search_count([]), before)

    def test_upload_requires_login_and_ai_group(self):
        res = self.upload("a.pdf", self.PDF, csrf=False)
        self.assertNotEqual(res.status_code, 200)
        self.login(self.plain)
        res = self.upload("a.pdf", self.PDF)
        self.assertEqual(res.status_code, 403, res.text)
        self.assertIn("agente IA", res.json()["error"])

    def test_upload_ownership_and_closed_conversation(self):
        self.login(self.u2)
        other = self.ok("/xtd_ai/chat/open")["conversation_id"]
        closed = self.closed_conversation_with_messages(self.u1)
        res = self.upload("a.pdf", self.PDF, other)  # u1 uploads to u2's conversation
        self.assertEqual(res.status_code, 403, res.text)
        self.assertIn("no es tuya", res.json()["error"])
        res = self.upload("a.pdf", self.PDF, closed)
        self.assertEqual(res.status_code, 400)
        self.assertIn("solo de lectura", res.json()["error"])
        self.assertFalse(
            self.env["ir.attachment"].search_count(
                [("res_model", "=", "xtd.ai.conversation"), ("res_id", "=", other)]
            )
        )

    def test_send_with_attachments_and_messages_payload(self):
        self.login(self.u1)
        conv = self.ok("/xtd_ai/chat/open")["conversation_id"]
        att = self.upload("factura.pdf", self.PDF, conv).json()["attachment_id"]
        # text may be empty when there are attachments
        res = self.ok(
            "/xtd_ai/chat/send", text="", conversation_id=conv, attachment_ids=[att]
        )
        self.assertEqual(res["state"], "queued")
        data = self.ok("/xtd_ai/chat/messages", conversation_id=conv)
        user_msg = [m for m in data["messages"] if m["role"] == "user"][0]
        self.assertEqual(
            user_msg["attachments"],
            [
                {
                    "id": att,
                    "name": "factura.pdf",
                    "mimetype": "application/pdf",
                    "size": len(self.PDF),
                    "url": f"/web/content/{att}?download=true",
                }
            ],
        )
        # the history title falls back to the attachment name
        listing = self.ok("/xtd_ai/chat/conversations")
        self.assertEqual(listing[0]["name"], "factura.pdf")
        self.assertEqual(listing[0]["preview"], "Adjunto")

    def test_send_rejects_foreign_or_invalid_attachments(self):
        self.login(self.u2)
        conv2 = self.ok("/xtd_ai/chat/open")["conversation_id"]
        foreign = self.upload("a.pdf", self.PDF, conv2).json()["attachment_id"]
        self.login(self.u1)
        conv = self.ok("/xtd_ai/chat/open")["conversation_id"]
        for ids in ([foreign], ["x"], [True], [1] * 1 + list(range(100, 106))):
            data = self.rpc(
                "/xtd_ai/chat/send",
                text="hola",
                conversation_id=conv,
                attachment_ids=ids,
            )
            self.assertIn("error", data, ids)
        self.assertFalse(
            self.env["xtd.ai.run"].sudo().search([("conversation_id", "=", conv)])
        )

    # -- chips and "new conversation" notice --------------------------------
    def test_suggestions_depend_on_role(self):
        seller = new_test_user(
            self.env,
            "chat_seller",
            groups=AI_GROUPS + ",sales_team.group_sale_salesman",
        )
        self.login(seller)
        chips = self.ok("/xtd_ai/chat/open")["suggestions"]
        keys = [c["key"] for c in chips]
        self.assertIn("search_sale_orders", keys)
        self.assertLessEqual(len(chips), 4)
        for chip in chips:
            self.assertTrue(chip["text"])
            self.assertEqual(set(chip), {"key", "text", "send", "attach"})
        self.login(self.u2)  # AI user without sales/accounting groups
        keys2 = [c["key"] for c in self.ok("/xtd_ai/chat/open")["suggestions"]]
        self.assertNotIn("search_sale_orders", keys2)
        self.assertNotIn("search_invoices", keys2)
        self.assertTrue(keys2)  # always at least the generic chip

    def test_auto_started_conversation_links_previous(self):
        self.login(self.u1)
        first = self.ok("/xtd_ai/chat/open")
        self.assertFalse(first["auto_started"])  # nothing to look back at
        previous = self.closed_conversation_with_messages(self.u1)
        # closed_conversation_with_messages ended with an explicit "new"
        again = self.ok("/xtd_ai/chat/open")
        self.assertFalse(again["auto_started"])  # the open one already existed
        # the open conversation is closed elsewhere (idle close): reopening is automatic
        self.env["xtd.ai.conversation"].sudo().browse(
            again["conversation_id"]
        ).action_close()
        auto = self.ok("/xtd_ai/chat/open")
        self.assertTrue(auto["auto_started"])
        self.assertEqual(auto["previous_conversation_id"], previous)
        explicit = self.ok("/xtd_ai/chat/open", new=True)
        self.assertFalse(explicit["auto_started"])
        self.assertFalse(explicit["previous_conversation_id"])

    def test_history_preview_and_title(self):
        conv = self.closed_conversation_with_messages(self.u1, text="Facturas de marzo")
        listing = {c["id"]: c for c in self.ok("/xtd_ai/chat/conversations")}
        self.assertEqual(listing[conv]["name"], "Facturas de marzo")
        self.assertEqual(listing[conv]["preview"], "respuesta")


@tagged("post_install", "-at_install")
class TestPreviewLines(HttpCase):
    """Preview lines of any tool become readable ``{field, value}`` rows."""

    def test_document_line_is_rendered(self):
        line = {
            "product": {
                "untrusted_text": "Caja Tornillos Inox 500u",
                "truncated": False,
            },
            "description": {
                "untrusted_text": "Caja Tornillos Inox 500u",
                "truncated": False,
            },
            "quantity": 10.0,
            "price_unit": {"amount": 18.0, "currency": "EUR"},
            "taxes": ["21% B"],
            "subtotal": {"amount": 180.0, "currency": "EUR"},
        }
        row = chat_main.XtdAiChatController._preview_line(line)
        self.assertEqual(row["field"], "Caja Tornillos Inox 500u")
        self.assertEqual(row["value"], "10 × 18.00 EUR = 180.00 EUR [21% B]")

    def test_generic_field_value_line_passes_through(self):
        row = chat_main.XtdAiChatController._preview_line(
            {
                "field": "Cliente",
                "value": {"untrusted_text": "Acme", "truncated": False},
            }
        )
        self.assertEqual(row, {"field": "Cliente", "value": "Acme"})

    def test_unknown_structure_is_not_empty(self):
        row = chat_main.XtdAiChatController._preview_line(
            {"name": "Contacto duplicado", "email": "a@example.com"}
        )
        self.assertEqual(row["field"], "Contacto duplicado")
        self.assertIn("a@example.com", row["value"])
