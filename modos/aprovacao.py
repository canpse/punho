"""Pedidos de permissão do Claude Code, decididos pelo pulso (ou pelo painel).

O hook (hooks/claude_hook.py) faz POST /api/pedido e fica esperando a decisão.
Quando chega um pedido, a Central interrompe o que estiver no relógio e entra aqui.
"""
import itertools
import threading
import time

from .base import SAIDA, Modo, girar

OPCOES = [("allow", "✅ aprovar"), ("deny", "🔥 negar")]


def resumo(tool, entrada):
    if tool == "Bash":
        return entrada.get("command", "")
    for k in ("file_path", "path", "url", "pattern", "description"):
        if k in entrada:
            return str(entrada[k])
    return str(entrada)[:200]


class Pedido:
    _ids = itertools.count(1)

    def __init__(self, tool, entrada, cwd):
        self.id = next(self._ids)
        self.tool = tool
        self.texto = resumo(tool, entrada)
        self.cwd = cwd
        self.criado = time.time()
        self.decisao = None
        self.evento = threading.Event()

    def decidir(self, decisao):
        self.decisao = decisao
        self.evento.set()

    def como_dict(self):
        return {"id": self.id, "tool": self.tool, "texto": self.texto, "cwd": self.cwd,
                "idade": int(time.time() - self.criado)}


class Aprovacoes(Modo):
    id, nome = "aprovacoes", "Aprovações"

    def __init__(self):
        self.pendentes = []
        self.op = 0
        self.historico = []

    def novo(self, c, tool, entrada, cwd):
        p = Pedido(tool, entrada, cwd)
        self.pendentes.append(p)
        if c.ativo is not self:
            c.interromper(self)
        elif len(self.pendentes) == 1:
            self.entrar(c)
        return p

    def entrar(self, c):
        if not self.pendentes:
            c.mostrar("✅ nada pendente")
            return
        p = self.pendentes[0]
        self.op = 0
        c.notificar(f"Claude pede: {p.tool}", f"{p.texto}\n\nem {p.cwd}")
        c.mostrar(f"{p.tool}: {p.texto}")

    def botao(self, c, b):
        if not self.pendentes:
            return c.sair_do_modo()
        if b == "play" and self.op == len(OPCOES):
            return c.sair_do_modo()  # o pedido continua pendente (painel ou terminal)
        if b == "play":
            self.decidir(c, self.pendentes[0].id, OPCOES[self.op][0])
            return
        self.op = girar(self.op, 1 if b == "proxima" else -1, len(OPCOES))
        c.mostrar(SAIDA if self.op == len(OPCOES) else OPCOES[self.op][1])

    def decidir(self, c, pid, decisao):
        for p in list(self.pendentes):
            if p.id == pid:
                p.decidir(decisao)
                self.pendentes.remove(p)
                self.historico.insert(0, {**p.como_dict(), "decisao": decisao})
                del self.historico[20:]
        if c.ativo is self:
            if self.pendentes:
                self.entrar(c)
            else:
                c.mostrar("✅ ok" if decisao == "allow" else "🔥 negado")
                c.voltar(atraso=1.5)

    def expirar(self, c, p):
        """O hook desistiu de esperar: o pedido volta pro terminal."""
        if p in self.pendentes:
            self.pendentes.remove(p)
            self.historico.insert(0, {**p.como_dict(), "decisao": "expirou"})
            if c.ativo is self:
                if self.pendentes:
                    self.entrar(c)
                else:
                    c.voltar()

    def estado(self):
        return {"pendentes": [p.como_dict() for p in self.pendentes], "historico": self.historico}

    def api(self, c, acao, dados):
        if acao == "decidir":
            self.decidir(c, int(dados["id"]), dados["decisao"])
            return {"ok": True}
        return {"erro": "acao"}
