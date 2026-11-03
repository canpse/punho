"""Aventura de uma linha: o Claude narra (claude -p), a cena vai pra notificação,
a linha mostra as escolhas."""
import json
import os
import re
import subprocess
import threading

from .base import ASSISTENTE, SAIDA, Modo, carregar, girar, salvar


def _trecho(rel, n=1800):
    try:
        return (ASSISTENTE / rel).read_text()[:n] if ASSISTENTE else ""
    except OSError:
        return ""


MUNDOS = {
    "tulios": lambda: "Mundo de Julio e Tulio (comédia visual, absurdo contado com cara séria):\n"
                      + _trecho("tulios/mundo.md"),
    "griffin": lambda: "Mundo do jogo Griffin: ficção científica, 'Star Citizen com gráficos de RimWorld', "
                       "naves-mãe com NPCs vivendo dentro, naves dentro de naves, contratos de caça "
                       "(como a caça ao pirata Dente-Torto), tripulações, trajes, combate a pé e de nave.",
    "livre": lambda: "Fantasia livre, tom leve e esperto.",
}

PROMPT = """Você narra uma aventura interativa jogada num relógio minúsculo.
{mundo}

História até agora:
{historia}

Escreva a PRÓXIMA cena. Responda SÓ com JSON, sem markdown:
{{"cena": "até 260 caracteres, em português, segunda pessoa, viva e concreta",
  "opcoes": ["2 ou 3 escolhas", "cada uma com no MÁXIMO 11 caracteres", "sem emoji"]}}
Se a história chegou a um fim natural, use "opcoes": ["recomeçar"]."""


class Aventura(Modo):
    id, nome = "aventura", "Aventura"

    def __init__(self):
        e = carregar("aventura.json", {})
        self.mundo = e.get("mundo", "tulios")
        self.historia = e.get("historia", [])  # [{"cena", "escolha"}]
        self.opcoes = e.get("opcoes", [])
        self.op = 0
        self.pensando = False
        self.erro = None

    def guardar(self):
        salvar("aventura.json", {"mundo": self.mundo, "historia": self.historia, "opcoes": self.opcoes})

    def entrar(self, c):
        if self.pensando:
            c.mostrar("… pensando")
        elif not self.opcoes:
            self.gerar(c)
        else:
            c.notificar("Aventura", self.historia[-1]["cena"])
            self.op = 0
            self.mostrar_opcao(c)

    def mostrar_opcao(self, c):
        c.mostrar(SAIDA if self.op == len(self.opcoes) else f"→ {self.opcoes[self.op]}")

    def botao(self, c, b):
        if self.pensando or not self.opcoes:
            if b == "play":
                c.sair_do_modo()  # pode sair enquanto pensa; a cena chega como notificação
            return
        if b == "play" and self.op == len(self.opcoes):
            self.op = 0
            return c.sair_do_modo()
        if b == "play":
            escolha = self.opcoes[self.op]
            if escolha == "recomeçar":
                self.historia = []
            else:
                self.historia[-1]["escolha"] = escolha
            self.gerar(c)
            return
        self.op = girar(self.op, 1 if b == "proxima" else -1, len(self.opcoes))
        self.mostrar_opcao(c)

    def gerar(self, c):
        self.pensando = True
        self.erro = None
        c.mostrar("… pensando")
        threading.Thread(target=self._gerar, args=(c,), daemon=True).start()

    def _gerar(self, c):
        hist = "\n".join(f"- {h['cena']} (escolheu: {h.get('escolha', '?')})" for h in self.historia[-8:]) \
            or "(começo da aventura)"
        prompt = PROMPT.format(mundo=MUNDOS.get(self.mundo, MUNDOS["livre"])(), historia=hist)
        try:
            env = {**os.environ, "PUNHO_INTERNO": "1"}  # o hook do punho ignora esta sessão
            r = subprocess.run(["claude", "-p", "--model", "haiku", prompt], capture_output=True,
                               text=True, timeout=120, env=env, cwd="/tmp")
            m = re.search(r"\{.*\}", r.stdout, re.S)
            dados = json.loads(m.group(0))
            cena = dados["cena"].strip()
            opcoes = [o.strip()[:14] for o in dados["opcoes"] if o.strip()][:3] or ["seguir"]
        except Exception as erro:
            with c.trava:
                self.pensando = False
                self.erro = repr(erro)
                self.opcoes = self.opcoes or ["tentar de novo"]
                if not self.historia:
                    self.historia = [{"cena": "(falhou ao gerar)"}]
                if c.ativo is self:
                    c.mostrar("🔥 falhou, play")
            return
        with c.trava:
            self.historia.append({"cena": cena})
            self.opcoes, self.op, self.pensando = opcoes, 0, False
            self.guardar()
            c.notificar("Aventura", cena)
            if c.ativo is self:
                self.mostrar_opcao(c)

    def estado(self):
        return {"mundo": self.mundo, "mundos": list(MUNDOS), "historia": self.historia[-12:],
                "opcoes": self.opcoes, "pensando": self.pensando, "erro": self.erro}

    def api(self, c, acao, dados):
        if acao == "mundo":
            self.mundo = dados["mundo"]
            self.historia, self.opcoes = [], []
            self.guardar()
            if c.ativo is self:
                self.gerar(c)
            return {"ok": True}
        if acao == "recomecar":
            self.historia, self.opcoes = [], []
            self.guardar()
            if c.ativo is self:
                self.gerar(c)
            return {"ok": True}
        return {"erro": "acao"}
