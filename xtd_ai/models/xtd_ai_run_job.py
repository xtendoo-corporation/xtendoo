import logging
import threading
import time

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.modules.registry import Registry

from ..agent.errors import ProviderNotConfigured
from ..agent.loop import AgentLoop
from ..agent.prompts import load_system_prompt
from ..runner.odoo_gateway import OdooRunGateway

_logger = logging.getLogger(__name__)

CHANNEL = "root.xtd_ai"
MAX_ITERATIONS = 30
ACTIVE_STATES = ("queued", "running")
# Seconds a queued run may wait for the queue_job runner before the safety net
# runs it in a thread (e.g. Odoo was not restarted after installing queue_job, so
# its runner does not serve this database yet).
WATCHDOG_DELAY = 20
# Total time of a run: the loop ends it with its own message before the cron closes
# it as stale (token TTL + 120 s).
MAX_RUN_SECONDS = 540
# Runs the in-process fallback (thread / watchdog) may execute at once in this
# process. The fallback bypasses the queue_job channel, so it has its own limit.
MAX_FALLBACK_RUNS = 2
_fallback_slots = threading.BoundedSemaphore(MAX_FALLBACK_RUNS)


def _fallback_busy_message(env):
    return env._(
        "El servicio del agente IA está ocupado con otras peticiones. Inténtalo de "
        "nuevo en unos minutos."
    )


def _thread_main(dbname, run_id):
    """Fallback runner: own thread, own cursor (no queue_job runner available)."""
    threading.current_thread().dbname = dbname
    if not _fallback_slots.acquire(blocking=False):
        # over the limit: say so in the chat instead of leaving the run hanging
        try:
            with Registry(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env["xtd.ai.run"].browse(run_id)._xtd_ai_fail(
                    _fallback_busy_message(env)
                )
        except Exception:  # noqa: BLE001
            _logger.exception("Could not mark run %s as failed", run_id)
        return
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
    finally:
        _fallback_slots.release()


def _watchdog_main(dbname, run_id, delay):
    """Safety net for queue_job: run the agent if nobody claimed the run in time."""
    threading.current_thread().dbname = dbname
    time.sleep(delay)
    try:
        with Registry(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            run = env["xtd.ai.run"].browse(run_id).exists()
            if run and run._xtd_ai_watchdog_should_run():
                if not _fallback_slots.acquire(blocking=False):
                    _logger.warning(
                        "AI agent run %s left queued: fallback threads are at the "
                        "limit (%s)",
                        run_id,
                        MAX_FALLBACK_RUNS,
                    )
                    return
                try:
                    _watchdog_run(run, delay)
                finally:
                    _fallback_slots.release()
    except Exception:  # noqa: BLE001 - the thread must never die noisily
        _logger.exception("AI agent watchdog for run %s failed", run_id)


def _watchdog_run(run, delay):
    _logger.warning(
        "AI agent run %s not picked up by queue_job after %ss: running it in a "
        "thread (restart Odoo so the queue_job runner serves this database)",
        run.id,
        delay,
    )
    run._xtd_ai_job_run()


class XtdAiRun(models.Model):
    _inherit = "xtd.ai.run"

    agent_claimed_at = fields.Datetime(
        readonly=True,
        copy=False,
        help="When an executor (queue_job or the fallback thread) took the run. "
        "Only one executor may run it.",
    )

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
            self._xtd_ai_start_watchdog()
        else:
            self._xtd_ai_start_thread()
        return False

    def _xtd_ai_start_watchdog(self, delay=WATCHDOG_DELAY):
        dbname, run_id = self.env.cr.dbname, self.id

        def start():
            threading.Thread(
                target=_watchdog_main,
                args=(dbname, run_id, delay),
                name=f"xtd_ai_watchdog_{run_id}",
                daemon=True,
            ).start()

        self.env.cr.postcommit.add(start)

    def _xtd_ai_watchdog_should_run(self):
        """Still queued and unclaimed: nobody is executing it."""
        self.ensure_one()
        run = self.sudo()  # sudo: control record of the gateway
        if run.state != "queued" or run.agent_claimed_at:
            return False
        return not self._xtd_ai_channel_is_serving()

    def _xtd_ai_channel_is_serving(self):
        """True when queue_job is alive and merely busy: let the job wait its turn.

        A job of the channel already enqueued or started means the runner serves
        this database; the run is then waiting for channel capacity, and the
        fallback thread must not bypass it.
        """
        if "queue.job" not in self.env:
            return False
        return bool(
            self.env["queue.job"]
            .sudo()
            .search_count(
                [
                    ("channel", "=", CHANNEL),
                    ("state", "in", ("enqueued", "started")),
                ],
                limit=1,
            )
        )

    def _xtd_ai_claim(self):
        """Atomically take the run for this executor. False if another took it."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE xtd_ai_run SET agent_claimed_at = now() at time zone 'utc' "
            "WHERE id = %s AND agent_claimed_at IS NULL "
            "AND state IN ('queued', 'running') RETURNING id",
            (self.id,),
        )
        claimed = bool(self.env.cr.fetchone())
        self.invalidate_recordset(["agent_claimed_at"])
        if claimed and not tools.config["test_enable"]:
            # make the claim visible to the other executor at once (queue_job and
            # the safety net may both try): without it both could run the agent
            self.env.cr.commit()  # pylint: disable=invalid-commit
        return claimed

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
        if not run._xtd_ai_claim():
            # queue_job and the safety net may both try: only one runs it
            return _("Otra instancia ya está ejecutando esta petición.")
        reason = "respuesta no registrada"
        try:
            self._xtd_ai_job_execute()
            self.env.invalidate_all()
            still_active = run.state in ACTIVE_STATES
        except Exception as exc:  # noqa: BLE001 - nothing escapes to queue_job
            _logger.exception("AI agent run %s failed", run.id)
            self._xtd_ai_job_reset_transaction()
            still_active = True
            reason = f"error interno ({type(exc).__name__})"
        if still_active:
            # The reply could not be posted (or the loop died): always leave an
            # answer in the chat.
            run._xtd_ai_fail(
                self.env._(
                    "No he podido completar la petición. Inténtalo de nuevo en unos "
                    "minutos."
                ),
                error=reason,
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
            max_seconds=MAX_RUN_SECONDS,
        ).run()
        _logger.info(
            "AI agent run %s finished: status=%s iterations=%s tool_calls=%s",
            run.id,
            reply.status,
            reply.usage.get("iterations"),
            reply.usage.get("tool_calls"),
        )
