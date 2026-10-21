from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from odoo.tests import tagged
from odoo.tools.misc import Callbacks

from odoo.addons.queue_job.tests.common import trap_jobs
from odoo.addons.xtd_ai_gateway.tests.common import XtdAiCase

from ..agent.errors import ProviderError, ProviderNotConfigured
from ..models import xtd_ai_run as run_module
from ..providers.fake import FakeProvider, text_response, tool_response

CONFIG = "xtd.ai.agent.config"


@tagged("post_install", "-at_install")
class TestAgentJob(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run(text="busca a Azure")

    def use_provider(self, script):
        provider = FakeProvider(script)
        patcher = patch.object(
            self.registry[CONFIG], "_xtd_ai_build_provider", lambda *a, **k: provider
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return provider

    def messages(self, role=None):
        domain = [("run_id", "=", self.run.id)]
        if role:
            domain.append(("role", "=", role))
        return self.env["xtd.ai.message"].sudo().search(domain, order="id")

    def job(self):
        return self.run.with_user(self.user)._xtd_ai_job_run()

    # -- happy paths -------------------------------------------------------
    def test_end_to_end_with_real_tools(self):
        partner = self.env["res.partner"].create({"name": "Azure Interior Test"})
        provider = self.use_provider(
            [
                tool_response(("get_user_context", {})),
                tool_response(("search_partners", {"query": "Azure Interior Test"})),
                text_response("Encontré a Azure Interior Test."),
            ]
        )
        self.job()
        self.assertEqual(self.run.state, "done")
        self.assertEqual(len(provider.requests), 3)
        reply = self.messages("assistant")
        self.assertEqual(reply.body, "Encontré a Azure Interior Test.")
        audits = self.audits(self.run, event="tool_call")
        self.assertEqual(
            audits.mapped("tool_name"), ["get_user_context", "search_partners"]
        )
        self.assertEqual(set(audits.mapped("outcome")), {"ok"})
        self.assertEqual(set(audits.mapped("user_id")), {self.user})
        self.assertEqual(self.run.tool_calls, 2)
        self.assertEqual(self.run.iterations, 3)
        self.assertEqual(self.run.provider, "fake")
        self.assertEqual(self.run.input_tokens, 30)
        self.assertTrue(partner)
        # the first user turn carries the context from xtd_ai/history
        self.assertIn("Usuario:", provider.requests[0].messages[0].text)

    def test_tools_run_as_the_user_without_sudo(self):
        self.use_provider(
            [
                tool_response(("get_user_context", {})),
                text_response("ok"),
            ]
        )
        self.job()
        result = self.messages("assistant")
        self.assertTrue(result)
        audit = self.audits(self.run, tool_name="get_user_context")
        self.assertEqual(audit.user_id, self.user)

    def test_pending_confirmation_flow(self):
        self.set_confirm(self.user, True)
        self.use_provider(
            [
                tool_response(("create_contact", {"name": "Contacto Pendiente SL"})),
                text_response("Revisa la tarjeta de confirmación."),
            ]
        )
        self.job()
        self.assertEqual(self.run.state, "done")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .search([("run_id", "=", self.run.id)])
        )
        self.assertEqual(len(action), 1)
        self.assertEqual(action.state, "pending")
        self.assertEqual(action.message_id, self.messages("assistant"))
        self.assertFalse(
            self.env["res.partner"].search([("name", "=", "Contacto Pendiente SL")])
        )

    def test_attachment_reaches_the_provider(self):
        self.run.state = "done"
        self.run.conversation_id.sudo().run_ids.write({"state": "done"})
        attachment = self.upload(self.user)
        run, _t = (
            self.env["xtd.ai.conversation"]
            .with_user(self.user)
            ._xtd_ai_start_run("mira esto", attachment_ids=[attachment.id])
        )
        self.run = run.sudo()
        provider = self.use_provider([text_response("visto")])
        self.job()
        last = provider.requests[0].messages[-1]
        self.assertEqual([a.id for a in last.attachments], [attachment.id])
        self.assertTrue(self.audits(self.run, event="attachment_read"))

    # -- control ------------------------------------------------------------
    def test_cancel_stops_the_loop(self):
        run = self.run

        def cancel(request):
            run.with_user(self.user).action_cancel()
            return tool_response(("get_user_context", {}))

        provider = self.use_provider([cancel, text_response("nunca")])
        self.job()
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(self.run.state, "cancelled")
        self.assertFalse(self.messages("assistant"))
        self.assertFalse(self.audits(self.run, tool_name="get_user_context"))

    def test_cancel_between_iterations(self):
        run = self.run

        def cancel(request):
            run.with_user(self.user).action_cancel()
            return text_response("nunca llega")

        provider = self.use_provider(
            [tool_response(("get_user_context", {})), cancel, text_response("x")]
        )
        self.job()
        self.assertEqual(self.run.state, "cancelled")
        self.assertLessEqual(len(provider.requests), 2)
        self.assertFalse(self.messages("assistant"))

    def test_iteration_cap_of_30(self):
        provider = self.use_provider(
            [tool_response(("get_user_context", {})) for _i in range(40)]
        )
        self.job()
        self.assertEqual(len(provider.requests), 30)
        self.assertEqual(self.run.state, "done")
        self.assertIn("límite", self.messages("assistant").body)

    def test_finished_run_is_not_rerun(self):
        provider = self.use_provider([text_response("x")])
        self.run.state = "done"
        self.job()
        self.assertEqual(provider.requests, [])

    # -- failures -----------------------------------------------------------
    def test_provider_failure_fails_run_with_spanish_message(self):
        self.use_provider([ProviderError("anthropic http 500 request_id=x")])
        self.job()  # must not raise
        self.assertEqual(self.run.state, "failed")
        self.assertTrue(self.run.error)
        body = self.messages().mapped("body")[-1]
        self.assertIn("No he podido", body)
        self.assertNotIn("anthropic", body)

    def test_unexpected_exception_never_escapes(self):
        patcher = patch.object(
            self.registry[CONFIG],
            "_xtd_ai_build_provider",
            side_effect=RuntimeError("boom sk-ant-secret"),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.job()
        self.assertEqual(self.run.state, "failed")
        notices = self.messages("notice")
        self.assertTrue(notices)
        self.assertNotIn("sk-ant", notices[-1].body)

    def test_provider_not_configured(self):
        patcher = patch.object(
            self.registry[CONFIG],
            "_xtd_ai_build_provider",
            side_effect=ProviderNotConfigured("no key"),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            self.job()
        self.assertEqual(self.run.state, "failed")
        self.assertIn("Ajustes", self.messages("notice")[-1].body)

    def test_revalidation_failure_mid_run_closes_the_run(self):
        user = self.user

        def deactivate(request):
            user.sudo().active = False
            return tool_response(("get_user_context", {}))

        self.use_provider([deactivate, text_response("x")])
        self.run.sudo().with_user(1)._xtd_ai_job_run()
        self.assertEqual(self.run.state, "failed")
        self.assertTrue(self.messages("notice"))

    # -- scheduling ---------------------------------------------------------
    def test_queue_job_path(self):
        run = self.run.with_user(self.user)
        with (
            patch.object(
                self.registry[CONFIG], "_xtd_ai_jobrunner_active", lambda *a: True
            ),
            patch.object(
                self.registry[CONFIG], "_xtd_ai_config_error", lambda *a: False
            ),
            trap_jobs() as trap,
        ):
            self.assertFalse(run._xtd_ai_schedule())
            trap.assert_jobs_count(1)
            trap.assert_enqueued_job(
                run._xtd_ai_job_run,
                properties={"channel": "root.xtd_ai", "max_retries": 1},
            )
        function = self.env["queue.job.function"].search(
            [("name", "=", "<xtd.ai.run>._xtd_ai_job_run")]
        )
        self.assertEqual(function.channel, "root.xtd_ai")
        self.assertTrue(function.allow_commit)

    def test_fallback_thread_path(self):
        run = self.run.with_user(self.user)
        added = []
        with (
            patch.object(
                self.registry[CONFIG], "_xtd_ai_jobrunner_active", lambda *a: False
            ),
            patch.object(
                self.registry[CONFIG], "_xtd_ai_config_error", lambda *a: False
            ),
            patch.object(Callbacks, "add", lambda cbs, f: added.append(f)),
            trap_jobs() as trap,
        ):
            self.assertFalse(run._xtd_ai_schedule())
            trap.assert_jobs_count(0)
        self.assertEqual(len(added), 1)
        with patch.object(run_module.threading, "Thread") as thread:
            added[0]()
        self.assertEqual(thread.call_args.kwargs["target"], run_module._thread_main)
        self.assertEqual(
            thread.call_args.kwargs["args"], (self.env.cr.dbname, self.run.id)
        )
        thread.return_value.start.assert_called_once()

    def test_queue_job_path_arms_the_watchdog(self):
        run = self.run.with_user(self.user)
        added = []
        with (
            patch.object(
                self.registry[CONFIG], "_xtd_ai_jobrunner_active", lambda *a: True
            ),
            patch.object(
                self.registry[CONFIG], "_xtd_ai_config_error", lambda *a: False
            ),
            patch.object(Callbacks, "add", lambda cbs, f: added.append(f)),
            trap_jobs() as trap,
        ):
            self.assertFalse(run._xtd_ai_schedule())
            trap.assert_jobs_count(1)
        self.assertEqual(len(added), 1)  # the watchdog, after the commit
        with patch.object(run_module.threading, "Thread") as thread:
            added[0]()
        self.assertEqual(thread.call_args.kwargs["target"], run_module._watchdog_main)
        self.assertEqual(
            thread.call_args.kwargs["args"],
            (self.env.cr.dbname, self.run.id, run_module.WATCHDOG_DELAY),
        )

    def test_only_one_executor_runs_it(self):
        provider = self.use_provider([text_response("una vez")])
        self.assertTrue(self.run._xtd_ai_claim())
        self.assertFalse(self.run._xtd_ai_claim())  # the second executor loses
        # a run already claimed by another executor is left alone
        self.job()
        self.assertEqual(len(provider.requests), 0)
        self.assertFalse(self.messages("assistant"))

    def test_job_claims_before_running(self):
        provider = self.use_provider([text_response("hecho")])
        self.job()
        self.assertTrue(self.run.agent_claimed_at)
        self.assertEqual(len(provider.requests), 1)
        self.assertFalse(self.run._xtd_ai_claim())

    def test_watchdog_runs_an_unclaimed_queued_run(self):
        provider = self.use_provider([text_response("rescatada")])
        self.assertTrue(self.run._xtd_ai_watchdog_should_run())
        registry = MagicMock()
        registry.return_value.cursor.return_value = nullcontext(self.env.cr)
        with (
            patch.object(run_module, "Registry", registry),
            patch.object(run_module.time, "sleep") as sleep,
        ):
            run_module._watchdog_main(self.env.cr.dbname, self.run.id, 20)
        sleep.assert_called_once_with(20)
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(self.messages("assistant").body, "rescatada")

    def test_watchdog_leaves_a_claimed_run_alone(self):
        provider = self.use_provider([text_response("no")])
        self.assertTrue(self.run._xtd_ai_claim())  # queue_job got it first
        self.assertFalse(self.run._xtd_ai_watchdog_should_run())
        registry = MagicMock()
        registry.return_value.cursor.return_value = nullcontext(self.env.cr)
        with (
            patch.object(run_module, "Registry", registry),
            patch.object(run_module.time, "sleep"),
        ):
            run_module._watchdog_main(self.env.cr.dbname, self.run.id, 0)
        self.assertEqual(len(provider.requests), 0)

    def test_thread_main_runs_with_its_own_cursor(self):
        provider = self.use_provider([text_response("desde el hilo")])
        registry = MagicMock()
        registry.return_value.cursor.return_value = nullcontext(self.env.cr)
        with patch.object(run_module, "Registry", registry):
            run_module._thread_main(self.env.cr.dbname, self.run.id)
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(self.run.state, "done")
        self.assertEqual(self.messages("assistant").body, "desde el hilo")

    def test_schedule_without_key_returns_notice(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            self.env["ir.config_parameter"].sudo().set_param(
                "xtd_ai_agent.anthropic_api_key", False
            )
            error = self.run.with_user(self.user)._xtd_ai_schedule()
        self.assertIn("Ajustes → Agente IA", error)
