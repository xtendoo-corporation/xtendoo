import logging
import threading

from odoo import SUPERUSER_ID, _, api, models, tools
from odoo.modules.registry import Registry

from ..agent.errors import ProviderNotConfigured
from ..agent.loop import AgentLoop
from ..agent.prompts import load_system_prompt
from ..runner.odoo_gateway import OdooRunGateway

_logger = logging.getLogger(__name__)

CHANNEL = "root.xtd_ai"
MAX_ITERATIONS = 30
ACTIVE_STATES = ("queued", "running")


def _thread_main(dbname, run_id):
    """Fallback runner: own thread, own cursor (no queue_job runner available)."""
    threading.current_thread().dbname = dbname
    try:
        with Registry(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["xtd.ai.run"].browse(run_id)._xtd_ai_job_run()
    except Exception:  # noqa: BLE001 - the thread must never die noisily
        _logger.exception("AI agent thread for run %s failed", run_id)
        try:
            with Registry(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env["xtd.ai.run"].browse(run_id)._xtd_ai_fail(
                    env._("La ejecución del agente IA ha fallado inesperadamente.")
                )
        except Exception:  # noqa: BLE001
            _logger.exception("Could not mark run %s as failed", run_id)


class XtdAiRun(models.Model):
    _inherit = "xtd.ai.run"

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    def _xtd_ai_schedule(self):
        """Start the in-process agent for this run (called by the chat route).

        With the queue_job runner active, the job is created in the current
        transaction (no race with the run). Otherwise a thread starts after the
        commit.

        :returns: a Spanish error message when the agent cannot run, else False.
        """
        self.ensure_one()
        config = self.env["xtd.ai.agent.config"]
        error = config._xtd_ai_config_error()
        if error:
            return error
        if config._xtd_ai_jobrunner_active():
            self.with_delay(
                channel=CHANNEL,
                max_retries=1,
                description=self.env._("Agente IA: ejecución %(run)s", run=self.id),
            )._xtd_ai_job_run()
        else:
            self._xtd_ai_start_thread()
        return False

    def _xtd_ai_start_thread(self):
        dbname, run_id = self.env.cr.dbname, self.id

        def start():
            threading.Thread(
                target=_thread_main,
                args=(dbname, run_id),
                name=f"xtd_ai_run_{run_id}",
                daemon=True,
            ).start()

        self.env.cr.postcommit.add(start)

    # ------------------------------------------------------------------
    # Execution (job or thread entry point)
    # ------------------------------------------------------------------
    def _xtd_ai_job_run(self):
        """Run the agent loop for this run. Never raises for a normal failure.

        Failures of the provider or of Odoo end the run with a ``failed`` reply
        (a retry would repeat paid calls).
        """
        self.ensure_one()
        run = self.sudo()  # sudo: control record of the gateway
        if run.state not in ACTIVE_STATES:
            return _("La ejecución ya había terminado (%s).", run.state)
        try:
            self._xtd_ai_job_execute()
            self.env.invalidate_all()
            still_active = run.state in ACTIVE_STATES
        except Exception:  # noqa: BLE001 - nothing escapes to queue_job
            _logger.exception("AI agent run %s failed", run.id)
            self._xtd_ai_job_reset_transaction()
            still_active = True
        if still_active:
            # The reply could not be posted (or the loop died): always leave an
            # answer in the chat.
            run._xtd_ai_fail(
                self.env._(
                    "No he podido completar la petición. Inténtalo de nuevo en unos "
                    "minutos."
                )
            )
        return run.state

    def _xtd_ai_job_reset_transaction(self):
        """Drop a broken transaction (outside tests) so the run can be failed."""
        if tools.config["test_enable"]:
            return
        try:
            self.env.cr.rollback()
        except Exception:  # noqa: BLE001
            _logger.exception("Rollback failed")
        self.env.invalidate_all()

    def _xtd_ai_job_execute(self):
        run = self.sudo()  # sudo: control record of the gateway
        config = self.env["xtd.ai.agent.config"]
        try:
            provider = config._xtd_ai_build_provider()
        except ProviderNotConfigured:
            run._xtd_ai_fail(
                config._xtd_ai_config_error() or _("Proveedor no configurado.")
            )
            return
        max_bytes = self.env["xtd.ai.conversation"]._xtd_ai_attachment_limits()[0]
        gateway = OdooRunGateway(self.env, run)
        reply = AgentLoop(
            provider,
            gateway,
            load_system_prompt(),
            max_iterations=MAX_ITERATIONS,
            prices=config._xtd_ai_prices(),
            post_retry_delay=0.0,
            run_id=run.id,
            max_attachment_bytes=max_bytes,
        ).run()
        _logger.info(
            "AI agent run %s finished: status=%s iterations=%s tool_calls=%s",
            run.id,
            reply.status,
            reply.usage.get("iterations"),
            reply.usage.get("tool_calls"),
        )
