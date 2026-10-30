#!/usr/bin/env python3
"""Conjunto de referencia (golden set) del agente IA: productos, contactos y borradores.

CADA EJECUCIÓN LLAMA AL MODELO REAL (el que tenga configurado el agente, Haiku por
defecto) Y CUESTA DINERO (céntimos por caso).

Conduce las rutas del chat (/xtd_ai/chat/*) del Odoo local como los usuarios de
prueba del seed, una conversación nueva por caso, y comprueba por caso:

- ``tools_all``: herramientas que deben llamarse con éxito o quedar en tarjeta.
- ``tools_none``: herramientas que no deben ejecutarse con éxito.
- ``cards`` (exacto) o ``cards_max``: tarjetas (acciones pendientes) creadas.
- ``turns``: mensajes del usuario (por defecto 1); se informa la media.
- ``db``: pares ``[SELECT, valor esperado]`` contra la BD tras el caso.

La clave de Anthropic nunca pasa por aquí: la usa el propio Odoo (variable de
entorno del contenedor). Las contraseñas de prueba se leen del seed y no se
imprimen. Las lecturas de BD son SELECT vía ``docker compose exec db psql``.

Uso (los casos modifican la BD: úsalo siempre sobre una copia ``chk_*``):

    createdb -T ai_agent_test chk_golden   (con docker compose exec db)
    python3 run_golden.py --db chk_golden --prepare
    python3 run_golden.py --db chk_golden --yes [--only p01,c03] [--out res.json]

``--prepare`` da a ``ai_direccion`` el grupo de gestión de productos y deja la
preferencia «Confirmar acciones» desactivada (perfil Equilibrado) en esa copia.
"""
# CLI tool under scripts/, not part of the Odoo module: stdout is its interface.
# pylint: disable=print-used

import argparse
import ast
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request
from contextlib import suppress
from http.cookiejar import CookieJar

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.environ.get("XTD_AI_COMPOSE_DIR") or HERE.parents[6])
SEED = pathlib.Path(
    os.environ.get("XTD_AI_SEED") or ROOT / "scripts/ai_agent/seed_ai_agent_test.py"
)
CASES = HERE / "cases.json"
BASE = os.environ.get("XTD_AI_BASE", "http://127.0.0.1:19069")
POLL = 1.5
OK_OUTCOMES = ("ok", "pending")

PREPARE = """
group = env.ref("product.group_product_manager")
user = env["res.users"].search([("login", "=", "ai_direccion")])
user.write({"group_ids": [(4, group.id)]})
env["res.users"].search([]).write({"xtd_ai_confirm_writes": False})
env.cr.commit()
print("PREPARED", user.has_group("product.group_product_manager"))
"""


def compose(*args, stdin=None, timeout=300):
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def psql(db, sql):
    if not sql.lstrip().lower().startswith(("select", "with")):
        raise ValueError("solo SELECT")
    proc = compose("exec", "-T", "db", "psql", "-U", "odoo", "-d", db, "-At", "-c", sql)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1][:200])
    return proc.stdout.strip()


def passwords():
    for node in ast.parse(SEED.read_text()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == (
            "TEST_PASSWORDS"
        ):
            return ast.literal_eval(node.value)
    raise SystemExit("TEST_PASSWORDS no encontrado en el seed")


class Client:
    def __init__(self, db, login, password):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )
        self.call("/web/session/authenticate", db=db, login=login, password=password)

    def call(self, path, **params):
        body = json.dumps({"jsonrpc": "2.0", "method": "call", "params": params})
        request = urllib.request.Request(
            BASE + path, body.encode(), {"Content-Type": "application/json"}
        )
        for attempt in range(4):  # the dev server restarts when files change
            try:
                with self.opener.open(request, timeout=60) as response:
                    data = json.load(response)
                break
            except (OSError, ValueError):
                if attempt == 3:
                    raise
                time.sleep(15)
        if data.get("error"):
            message = (data["error"].get("data") or {}).get("message") or "error"
            raise RuntimeError(f"{path}: {message}")
        return data["result"]


def wait_reply(client, conv_id, run_id, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(POLL)
        data = client.call("/xtd_ai/chat/messages", conversation_id=conv_id)
        mine = [
            m
            for m in data.get("messages", [])
            if m.get("run_id") == run_id and m.get("role") in ("assistant", "notice")
        ]
        if mine and data.get("running_run_id") != run_id:
            return "\n".join(m.get("body") or "" for m in mine), False
    with suppress(Exception):
        client.call("/xtd_ai/chat/run/cancel", run_id=run_id)
    return "", True


def run_case(db, case, clients, pwd, timeout):
    login = case["user"]
    if login not in clients:
        clients[login] = Client(db, login, pwd[login])
    client = clients[login]
    conv = client.call("/xtd_ai/chat/open", new=True)
    conv_id = conv.get("conversation_id") or conv.get("id")
    replies, run_ids, timed_out = [], [], False
    for text in case["turns"]:
        sent = client.call("/xtd_ai/chat/send", conversation_id=conv_id, text=text)
        run_ids.append(sent["run_id"])
        reply, late = wait_reply(client, conv_id, sent["run_id"], timeout)
        replies.append(reply)
        timed_out = timed_out or late
    ids = ",".join(map(str, run_ids))
    audit = json.loads(
        psql(
            db,
            "select coalesce(json_agg(json_build_object('tool', tool_name, "
            "'outcome', outcome, 'error', error_code) order by id), '[]') "
            f"from xtd_ai_audit where run_id in ({ids}) and event='tool_call'",
        )
        or "[]"
    )
    cards = int(
        psql(db, f"select count(*) from xtd_ai_pending_action where run_id in ({ids})")
    )
    usage = json.loads(
        psql(
            db,
            "select json_build_object('cost', coalesce(sum(cost_estimate),0), "
            "'state', string_agg(state, ',')) from xtd_ai_run "
            f"where id in ({ids})",
        )
    )
    good = {a["tool"] for a in audit if a["outcome"] in OK_OUTCOMES}
    expect = case["expect"]
    fails = []
    if timed_out:
        fails.append("sin respuesta a tiempo")
    for tool in expect.get("tools_all", []):
        if tool not in good:
            fails.append(f"no llama a {tool}")
    for tool in expect.get("tools_none", []):
        if tool in good:
            fails.append(f"llama a {tool}")
    if "cards" in expect and cards != expect["cards"]:
        fails.append(f"tarjetas {cards} (esperadas {expect['cards']})")
    if "cards_max" in expect and cards > expect["cards_max"]:
        fails.append(f"tarjetas {cards} (máximo {expect['cards_max']})")
    for sql, expected in expect.get("db", []):
        got = psql(db, sql)
        if got != str(expected):
            fails.append(f"BD {got!r} != {expected!r} ({sql[:60]})")
    return {
        "id": case["id"],
        "area": case["area"],
        "ok": not fails,
        "fails": fails,
        "cards": cards,
        "turns": len(case["turns"]),
        "tools": [f"{a['tool']}:{a['outcome']}" for a in audit],
        "reply": "\n---\n".join(replies)[:1500],
        "cost": usage.get("cost"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True)
    parser.add_argument("--only", default="")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    if not args.db.startswith("chk_"):
        raise SystemExit("Los casos modifican la BD: usa una copia chk_*.")
    if args.prepare:
        proc = compose(
            "exec",
            "-T",
            "odoo",
            "odoo",
            "shell",
            "-d",
            args.db,
            "--no-http",
            stdin=PREPARE,
        )
        print(next((x for x in proc.stdout.splitlines() if "PREPARED" in x), "fallo"))
        return
    cases = json.loads(CASES.read_text())["cases"]
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if not args.yes:
        raise SystemExit(f"{len(cases)} casos con el modelo real: añade --yes.")
    pwd, clients, results = passwords(), {}, []
    for case in cases:
        try:
            result = run_case(args.db, case, clients, pwd, args.timeout)
        except Exception as exc:  # report and go on with the next case
            result = {
                "id": case["id"],
                "area": case["area"],
                "ok": False,
                "fails": [f"excepción: {exc}"],
                "turns": len(case["turns"]),
            }
        results.append(result)
        mark = "OK " if result["ok"] else "FALLO"
        print(f"{mark} {case['id']:5} {'; '.join(result['fails'])}", flush=True)
    passed = sum(r["ok"] for r in results)
    total = len(results) or 1
    print(f"\nAcierto: {passed}/{len(results)} = {100 * passed / total:.0f} %")
    for area in sorted({r["area"] for r in results}):
        rows = [r for r in results if r["area"] == area]
        print(f"  {area}: {sum(r['ok'] for r in rows)}/{len(rows)}")
    cards = sum(r.get("cards", 0) for r in results)
    turns = sum(r["turns"] for r in results)
    cost = sum(float(r.get("cost") or 0) for r in results)
    print(f"Tarjetas: {cards} · mensajes de usuario: {turns} · coste: {cost:.3f} USD")
    if args.out:
        pathlib.Path(args.out).write_text(
            json.dumps(results, ensure_ascii=False, indent=1)
        )
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
