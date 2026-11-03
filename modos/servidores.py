"""Liga e desliga os servidores que a gente inventou (lista em dados/servidores.json).

servico:  serviço de usuário do systemd (systemctl --user start/stop)
processo: script avulso; a central sobe numa sessão própria (sobrevive se a central
          reiniciar) e o estado vem da porta. Pra desligar, acha o dono da porta.
"""
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import config

from .base import DADOS, Modo, girar

LOGS = DADOS / "logs"


def porta_aberta(porta):
    for host in {"127.0.0.1", config.HOST} - {"0.0.0.0"}:
        try:
            with socket.create_connection((host, porta), timeout=0.3):
                return True
        except OSError:
            pass
    return False


def dono_da_porta(porta):
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{porta}"], capture_output=True, text=True)
    for pedaco in r.stdout.split("pid=")[1:]:
        return int(pedaco.split(",")[0])
    return None


class Servidores(Modo):
    id, nome = "servidores", "Servidores"

    def __init__(self):
        self.i = 0
        self.lista = []
        self.estados = {}   # id -> True/False
        self.mexendo = set()

    def carregar(self):
        p = DADOS / "servidores.json"  # a sua lista (fora do git); sem ela, o exemplo
        if not p.exists():
            p = DADOS / "servidores.exemplo.json"
        self.lista = json.loads(p.read_text()) if p.exists() else []
        if not self.lista:
            self.lista = [{"id": "-", "nome": "lista vazia", "tipo": "processo", "porta": 1, "cmd": ["true"],
                           "pasta": "~"}]

    def ligado(self, s):
        if s["tipo"] == "servico":
            r = subprocess.run(["systemctl", "--user", "is-active", s["unidade"]], capture_output=True, text=True)
            ativo = r.stdout.strip() == "active"
            return ativo and (porta_aberta(s["porta"]) if s.get("porta") else True)
        return porta_aberta(s["porta"])

    def atualizar_estados(self):
        self.estados = {s["id"]: self.ligado(s) for s in self.lista}

    def linha(self):
        s = self.lista[self.i]
        if s["id"] in self.mexendo:
            return f"○ {s['nome']}"
        return f"{'💚' if self.estados.get(s['id']) else '❤️'} {s['nome']}"

    def entrar(self, c):
        self.carregar()
        self.i = min(self.i, len(self.lista) - 1)
        self.atualizar_estados()
        c.mostrar(self.linha())

    def botao(self, c, b):
        if b == "proxima":
            self.i = girar(self.i, 1, len(self.lista))
            s = self.lista[self.i]
            self.estados[s["id"]] = self.ligado(s)
            c.mostrar(self.linha())
        elif b == "play":
            self.alternar(c, self.lista[self.i])

    def alternar(self, c, s):
        if s["id"] in self.mexendo:
            return
        ligar = not self.estados.get(s["id"])
        self.mexendo.add(s["id"])
        if c.ativo is self:
            c.mostrar(self.linha())
        threading.Thread(target=self._alternar, args=(c, s, ligar), daemon=True).start()

    def _alternar(self, c, s, ligar):
        erro = None
        try:
            if s["tipo"] == "servico":
                subprocess.run(["systemctl", "--user", "start" if ligar else "stop", s["unidade"]],
                               check=True, capture_output=True, timeout=30)
            elif ligar:
                LOGS.mkdir(exist_ok=True)
                log = open(LOGS / f"{s['id']}.log", "a")
                subprocess.Popen(s["cmd"], cwd=os.path.expanduser(s["pasta"]), stdout=log, stderr=log,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            else:
                pid = dono_da_porta(s["porta"])
                if pid:
                    os.kill(pid, 15)
            # espera o estado assentar (até ~8 s)
            for _ in range(16):
                time.sleep(0.5)
                if self.ligado(s) == ligar:
                    break
        except Exception as e:
            erro = str(e)
        estado = self.ligado(s)
        with c.trava:
            self.mexendo.discard(s["id"])
            self.estados[s["id"]] = estado
            if c.ativo is self and self.lista[self.i]["id"] == s["id"]:
                c.mostrar(self.linha())
            if erro or estado != ligar:
                c.notificar(f"🔥 {s['nome']}", erro or f"não {'ligou' if ligar else 'desligou'}: veja dados/logs/{s['id']}.log")
            elif ligar:
                c.notificar(f"💚 {s['nome']} ligado", s.get("url", ""))
                if s.get("abrir"):  # abre no navegador do PC
                    subprocess.Popen(["xdg-open", s["abrir"]], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)

    def estado(self):
        if not self.lista:
            self.carregar()
            self.atualizar_estados()
        return {"lista": [{"id": s["id"], "nome": s["nome"], "url": s.get("url", ""),
                           "ligado": self.estados.get(s["id"]), "mexendo": s["id"] in self.mexendo}
                          for s in self.lista]}

    def api(self, c, acao, dados):
        if acao == "alternar":
            for s in self.lista:
                if s["id"] == dados["id"]:
                    self.alternar(c, s)
                    return {"ok": True}
            return {"erro": "servidor"}
        if acao == "atualizar":
            self.carregar()
            self.atualizar_estados()
            return {"ok": True}
        return {"erro": "acao"}
