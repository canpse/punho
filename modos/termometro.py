"""Termômetro do dia: o relógio pergunta "como tá?" e a resposta vai pro Claude ler."""
import json
from datetime import datetime, timedelta

from .base import EVENTOS, SAIDA, Modo, carregar, girar, registrar, salvar

OPCOES = [("😴", "exausto"), ("😐", "morno"), ("🤔", "pensativo"), ("💪", "bem"), ("🔥", "voando")]


class Termometro(Modo):
    id, nome = "termometro", "Termômetro"

    def __init__(self):
        e = carregar("termometro.json", {})
        self.horarios = e.get("horarios", ["11:30", "20:30"])
        self.op = 2
        self.ultimo_pedido = None  # datetime
        self.ultima_resposta = None

    def guardar(self):
        salvar("termometro.json", {"horarios": self.horarios})

    def linha(self):
        if self.op == len(OPCOES):
            return SAIDA
        emoji, nome = OPCOES[self.op]
        return f"{emoji} {nome}?"

    def entrar(self, c):
        if self.op == len(OPCOES):
            self.op = 2
        c.mostrar(self.linha())

    def botao(self, c, b):
        if b == "play" and self.op == len(OPCOES):
            self.op = 2
            return c.sair_do_modo()
        if b == "play":
            emoji, nome = OPCOES[self.op]
            registrar("humor", valor=self.op + 1, nome=nome)
            self.ultima_resposta = datetime.now()
            c.mostrar(f"✅ {emoji} anotado")
            if c.interrompido_por(self):
                c.voltar(atraso=1.5)
            return
        self.op = girar(self.op, 1 if b == "proxima" else -1, len(OPCOES))
        c.mostrar(self.linha())

    def checar_horario(self, c, agora):
        """Chamado a cada minuto pela Central."""
        hm = agora.strftime("%H:%M")
        if hm not in self.horarios:
            return
        if self.ultimo_pedido and agora - self.ultimo_pedido < timedelta(minutes=5):
            return
        if self.ultima_resposta and agora - self.ultima_resposta < timedelta(hours=2):
            return
        self.ultimo_pedido = agora
        c.notificar("Como tá?", "Escolhe com anterior/próxima e confirma no play.")
        c.interromper(self)

    def historico(self, n=20):
        if not EVENTOS.exists():
            return []
        linhas = [json.loads(l) for l in EVENTOS.read_text().splitlines() if '"humor"' in l]
        return linhas[-n:][::-1]

    def estado(self):
        return {"horarios": self.horarios, "historico": self.historico()}

    def api(self, c, acao, dados):
        if acao == "horarios":
            self.horarios = [h.strip() for h in dados["texto"].split(",") if h.strip()]
            self.guardar()
            return {"ok": True}
        if acao == "perguntar":
            c.notificar("Como tá?", "Escolhe com anterior/próxima e confirma no play.")
            c.interromper(self)
            return {"ok": True}
        return {"erro": "acao"}
