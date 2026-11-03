"""Modos de consulta: próxima prova, cardápio de estudo, pendências, teste."""
from datetime import datetime

from .base import SAIDA, Modo, girar, ler_assistente, registrar
from .tela import coracao

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
TEMPO = {"curto": "5m", "medio": "25m", "longo": "1h"}


class Lista(Modo):
    """anterior/próxima passeiam pelos itens; play manda o texto inteiro pro pulso."""

    def __init__(self):
        self.i = 0
        self.itens = []  # (linha, titulo_notif, texto_notif)

    def carregar(self):
        return []

    def entrar(self, c):
        self.itens = self.carregar() or [("vazio", "", "")]
        self.i = min(self.i, len(self.itens) - 1)
        self.mostrar(c)

    def mostrar(self, c):
        c.mostrar(SAIDA if self.i == len(self.itens) else self.itens[self.i][0])

    def botao(self, c, b):
        if b == "play" and self.i == len(self.itens):
            self.i = 0
            c.sair_do_modo()
            return
        if b == "play":
            linha, titulo, texto = self.itens[self.i]
            if texto:
                c.notificar(titulo, texto)
            self.ao_play(c)
            return
        self.i = girar(self.i, 1 if b == "proxima" else -1, len(self.itens))
        self.mostrar(c)

    def ao_play(self, c):
        pass


class Prova(Lista):
    id, nome = "prova", "Próxima prova"

    def carregar(self):
        agora = datetime.now().astimezone()
        itens = []
        provas = [p for p in ler_assistente("pendencias.json") if p.get("tipo") == "prova"]
        datadas = sorted((datetime.fromisoformat(p["prazo"]), p) for p in provas if p.get("prazo"))
        for d, p in datadas:
            if d < agora:
                continue
            dias = (d.date() - agora.date()).days
            quando = "hoje" if dias == 0 else f"{dias}d"
            itens.append((f"{coracao(dias)}{quando} {p['materia']}", p["materia"],
                          f"{DIAS[d.weekday()]} {d:%d/%m %H:%M}\n\n{p['titulo']}"))
        for p in provas:
            if not p.get("prazo"):
                itens.append((f"? {p['materia']}", p["materia"], p["titulo"]))
        return itens


class Cardapio(Lista):
    id, nome = "cardapio", "Cardápio"

    def carregar(self):
        return [(f"⭐{TEMPO.get(e.get('tamanho'), '')} {e.get('materia', '')}", e.get("materia", ""),
                 f"{e['titulo']}\n\nPor quê: {e['porque']}")
                for e in ler_assistente("estudos.json")]

    def ao_play(self, c):
        registrar("estudo_escolhido", item=self.itens[self.i][2].split("\n")[0])


class Pendencias(Lista):
    id, nome = "pendencias", "Pendências"

    def carregar(self):
        p = ler_assistente("pendencias.json")
        return [(f"{i + 1}/{len(p)} {x['materia']}", x["materia"], x["titulo"]) for i, x in enumerate(p)]


class Testar(Modo):
    id, nome = "testar", "Testar"

    def __init__(self):
        self.i = 0

    def entrar(self, c):
        self.i = 0
        c.mostrar(f"✅ {datetime.now():%H:%M:%S}")

    def botao(self, c, b):
        if b != "play":
            self.i = girar(self.i, 1 if b == "proxima" else -1, 1)
        elif self.i == 1:
            self.i = 0
            return c.sair_do_modo()
        c.mostrar(SAIDA if self.i == 1 else f"✅ {b} {datetime.now():%H:%M:%S}")
