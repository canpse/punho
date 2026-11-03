"""Mestre de RPG: ordem de iniciativa e dado no pulso."""
import random

from .base import SAIDA, Modo, carregar, salvar

DADOS_RPG = ["d20", "d12", "d10", "d8", "d6", "d4", "2d6"]


class Rpg(Modo):
    id, nome = "rpg", "Mestre RPG"

    def __init__(self):
        e = carregar("rpg.json", {})
        self.ordem = e.get("ordem", [["Túlio", 15], ["Julio", 12], ["Goblin", 9]])
        self.turno = e.get("turno", 0)
        self.rodada = e.get("rodada", 1)
        self.dado = e.get("dado", "d20")
        self.rolagens = []

    def guardar(self):
        salvar("rpg.json", {"ordem": self.ordem, "turno": self.turno,
                            "rodada": self.rodada, "dado": self.dado})

    def linha_turno(self):
        if not self.ordem:
            return "sem combate"
        if self.turno >= len(self.ordem):
            return SAIDA
        nome, ini = self.ordem[self.turno]
        return f"R{self.rodada} {nome} {ini}"

    def entrar(self, c):
        if self.turno >= len(self.ordem):
            self.turno = 0
        c.mostrar(self.linha_turno())

    def rolar(self):
        if self.dado == "2d6":
            r = [random.randint(1, 6) for _ in range(2)]
            return sum(r), f"2d6: {r[0]}+{r[1]}={sum(r)}"
        lados = int(self.dado[1:])
        n = random.randint(1, lados)
        marca = "⭐" if (lados == 20 and n == 20) else "🔥" if (lados == 20 and n == 1) else ""
        return n, f"{marca}{self.dado}: {n}"

    def botao(self, c, b):
        n = len(self.ordem)
        if b == "play" and (not n or self.turno >= n):
            return c.sair_do_modo()
        if b == "play":
            _, txt = self.rolar()
            quem = self.ordem[self.turno][0] if self.ordem else ""
            self.rolagens.insert(0, f"{quem}: {txt}")
            del self.rolagens[30:]
            c.mostrar(txt)
            return
        if not n:
            return
        # ⏭ passa o turno; depois do último começa a próxima rodada
        self.turno += 1
        if self.turno >= n:
            self.turno, self.rodada = 0, self.rodada + 1
        self.guardar()
        c.mostrar(self.linha_turno())

    def estado(self):
        return {"ordem": self.ordem, "turno": self.turno, "rodada": self.rodada,
                "dado": self.dado, "dados": DADOS_RPG, "rolagens": self.rolagens}

    def api(self, c, acao, dados):
        if acao == "ordem":
            ordem = []
            for linha in dados["texto"].splitlines():
                partes = linha.rsplit(None, 1)
                if not partes:
                    continue
                try:
                    ordem.append([partes[0], int(partes[1])])
                except (IndexError, ValueError):
                    ordem.append([linha.strip(), 0])
            ordem.sort(key=lambda x: -x[1])
            self.ordem, self.turno, self.rodada = ordem, 0, 1
        elif acao == "dado":
            self.dado = dados["dado"]
        else:
            return {"erro": "acao"}
        self.guardar()
        if c.ativo is self:
            self.entrar(c)
        return {"ok": True}
