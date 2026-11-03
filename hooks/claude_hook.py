#!/usr/bin/env python3
"""Hook do Claude Code -> punho.

PermissionRequest: manda o pedido pro relógio e espera a decisão (até ~110 s).
                   Sem resposta (ou central fora do ar): não decide nada e o
                   pedido segue normal no terminal.
UserPromptSubmit:  anota a hora em que a tarefa começou.
Stop:              se a tarefa levou 3 min ou mais, vibra "terminou" no pulso.

Nunca pode atrapalhar o Claude: qualquer erro -> sai em silêncio.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

PUNHO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PUNHO))
import config  # noqa: E402

URL = f"http://127.0.0.1:{config.PORTA}"  # pelo próprio PC: não precisa de token
MARCAS = Path("/tmp/punho-hook")
MINIMO_AVISO = 180  # segundos


def post(caminho, dados, espera):
    req = urllib.request.Request(
        URL + caminho, data=json.dumps(dados).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Token": (PUNHO / "token.txt").read_text().strip()})
    with urllib.request.urlopen(req, timeout=espera) as r:
        return json.loads(r.read())


def main():
    if os.environ.get("PUNHO_INTERNO"):
        return
    entrada = json.load(sys.stdin)
    evento = entrada.get("hook_event_name")
    sessao = entrada.get("session_id", "x")
    projeto = Path(entrada.get("cwd", "")).name or "?"

    if evento == "PermissionRequest":
        r = post("/api/pedido", {"tool_name": entrada.get("tool_name"), "tool_input": entrada.get("tool_input", {}),
                                 "cwd": entrada.get("cwd", ""), "espera": 110}, espera=120)
        decisao = r.get("decisao")
        if decisao in ("allow", "deny"):
            d = {"behavior": decisao}
            if decisao == "deny":
                d["message"] = "Negado pelo Lucas no relógio."
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": d}}))

    elif evento == "UserPromptSubmit":
        MARCAS.mkdir(exist_ok=True)
        (MARCAS / sessao).write_text(str(time.time()))

    elif evento == "Stop":
        marca = MARCAS / sessao
        if not marca.exists():
            return
        inicio = float(marca.read_text())
        marca.unlink()
        duracao = time.time() - inicio
        if duracao < MINIMO_AVISO:
            return
        texto = (entrada.get("last_assistant_message") or "")[:300]
        post("/api/aviso", {"titulo": f"✅ {projeto} terminou", "texto": f"{int(duracao // 60)} min\n\n{texto}"},
             espera=3)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
