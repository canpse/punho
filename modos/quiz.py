"""Flashcards: a pergunta vai pra notificação, a linha mostra as alternativas."""
import json
import random

from .base import DADOS, SAIDA, Modo, girar, registrar
from .tela import barra

LETRAS = "ABCD"


class Quiz(Modo):
    id, nome = "quiz", "Flashcards"

    def __init__(self, arquivo="paradigmas"):
        self.arquivo = arquivo
        self.fila = []
        self.atual = None
        self.op = 0
        self.respondida = False
        self.acertos = 0
        self.feitas = 0
        self.erros = {}  # tópico -> vezes

    def _perguntas(self):
        return json.loads((DADOS / "quiz" / f"{self.arquivo}.json").read_text())

    def entrar(self, c):
        if self.atual is None:
            self.proxima(c)
        else:
            self.mostrar_opcao(c)

    def proxima(self, c):
        if not self.fila:
            self.fila = self._perguntas()
            random.shuffle(self.fila)
        self.atual = self.fila.pop()
        self.op = 0
        self.respondida = False
        c.notificar(f"Q{self.feitas + 1}", self.atual["texto"])
        self.mostrar_opcao(c)

    def mostrar_opcao(self, c):
        if self.op == len(self.atual["opcoes"]):
            return c.mostrar(SAIDA)
        c.mostrar(f"{LETRAS[self.op]}) {self.atual['opcoes'][self.op]}")

    def botao(self, c, b):
        if self.respondida:
            self.proxima(c)
            return
        n = len(self.atual["opcoes"])
        if b == "play" and self.op == n:
            self.op = 0
            return c.sair_do_modo()
        if b == "play":
            self.responder(c)
            return
        self.op = girar(self.op, 1 if b == "proxima" else -1, n)
        self.mostrar_opcao(c)

    def responder(self, c):
        self.respondida = True
        self.feitas += 1
        certa = self.atual["certa"]
        ok = self.op == certa
        if ok:
            self.acertos += 1
            c.mostrar(f"✅ {barra(self.acertos, self.feitas)}")
        else:
            t = self.atual["topico"]
            self.erros[t] = self.erros.get(t, 0) + 1
            c.mostrar(f"🔥 era {LETRAS[certa]} {self.atual['opcoes'][certa]}")
        c.notificar("✅ certo" if ok else "🔥 errou", self.atual["explica"])
        registrar("quiz", arquivo=self.arquivo, topico=self.atual["topico"], acertou=ok)

    def estado(self):
        return {"acertos": self.acertos, "feitas": self.feitas, "erros": self.erros,
                "pergunta": self.atual["texto"] if self.atual else None}

    def api(self, c, acao, dados):
        if acao == "zerar":
            self.__init__(self.arquivo)
            return {"ok": True}
        return {"erro": "acao"}
