"""Configuração local (config.json, fora do git). Tudo tem padrão sensato.

{
  "host": "0.0.0.0",        IP onde o celular encontra o PC (LAN ou Tailscale); 0.0.0.0 = todas
  "porta": 8787,
  "assistente": null         pasta opcional com pendencias.json / estudos.json (modos Prova,
                             Cardápio, Pendências) e onde os eventos (humor, quiz) são gravados
}
"""
import json
import secrets
from pathlib import Path

AQUI = Path(__file__).resolve().parent
_PADRAO = {"host": "0.0.0.0", "porta": 8787, "assistente": None}


def _ler():
    p = AQUI / "config.json"
    dados = dict(_PADRAO)
    if p.exists():
        dados.update(json.loads(p.read_text()))
    return dados


CONFIG = _ler()
HOST = CONFIG["host"]
PORTA = int(CONFIG["porta"])
ASSISTENTE = Path(CONFIG["assistente"]).expanduser() if CONFIG.get("assistente") else None


def token():
    """token.txt é criado na primeira vez; o build do app embute o mesmo valor."""
    p = AQUI / "token.txt"
    if not p.exists():
        p.write_text(secrets.token_urlsafe(18) + "\n")
    return p.read_text().strip()
