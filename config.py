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


def ip_sugerido():
    """IP do Tailscale, se tiver; senão o IP da rede local (o da rota padrão)."""
    import socket
    import subprocess
    try:
        r = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.split()[0]
    except (OSError, subprocess.SubprocessError):
        pass
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # não envia nada; só escolhe a interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def url_do_celular():
    host = HOST if HOST not in ("0.0.0.0", "127.0.0.1") else ip_sugerido()
    return f"http://{host}:{PORTA}"


def token():
    """token.txt é criado na primeira vez; o build do app embute o mesmo valor."""
    p = AQUI / "token.txt"
    if not p.exists():
        p.write_text(secrets.token_urlsafe(18) + "\n")
    return p.read_text().strip()


if __name__ == "__main__":
    import sys
    pedido = sys.argv[1] if len(sys.argv) > 1 else ""
    if pedido == "ip":
        print(ip_sugerido())
    elif pedido == "url":
        print(url_do_celular())
    elif pedido == "token":
        print(token())
    elif pedido == "link-apk":
        print(f"{url_do_celular()}/punho.apk?t={token()}")
    else:
        print(f"host={HOST} porta={PORTA} url do celular={url_do_celular()}")
