import json
from datetime import datetime
from pathlib import Path

import config

AQUI = Path(__file__).resolve().parent.parent
DADOS = AQUI / "dados"
DADOS.mkdir(exist_ok=True)
ASSISTENTE = config.ASSISTENTE  # opcional: pasta com pendencias.json / estudos.json
# eventos de um botão (humor, quiz, estudo escolhido): um assistente de IA pode ler depois
EVENTOS = (ASSISTENTE / "punho-eventos.jsonl") if ASSISTENTE else (DADOS / "eventos.jsonl")


def ler_assistente(nome):
    """Lista vinda da pasta do assistente; sem pasta ou sem arquivo, lista vazia."""
    if not ASSISTENTE or not (ASSISTENTE / nome).exists():
        return []
    return json.loads((ASSISTENTE / nome).read_text())


def registrar(tipo, **dados):
    """Guarda um evento pro Claude ler depois (humor, estudo escolhido, quiz...)."""
    linha = {"quando": datetime.now().isoformat(timespec="seconds"), "tipo": tipo, **dados}
    with EVENTOS.open("a") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def carregar(nome, padrao):
    p = DADOS / nome
    if p.exists():
        return json.loads(p.read_text())
    return padrao


def salvar(nome, dados):
    (DADOS / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=1))


SAIDA = "← menu"


def girar(i, passo, n):
    """Anda numa roda de n itens (a saída agora é o botão ⏮, cuidado pela Central)."""
    return (i + passo) % n


class Modo:
    """Um "cartucho": dá significado aos três botões.

    c é a Central: c.mostrar(linha), c.notificar(titulo, texto), c.sair_do_modo().
    Cada modo tem na sua roda uma posição SAIDA; play nela chama c.sair_do_modo().
    """
    id = ""
    nome = ""
    usa_anterior = False  # True: o modo trata o ⏮ (senão a Central usa ⏮ pra voltar ao menu)

    def entrar(self, c):
        c.mostrar(self.nome)

    def botao(self, c, b):
        pass

    def sair(self, c):
        pass

    def estado(self):
        return {}

    def api(self, c, acao, dados):
        return {"erro": "sem api"}
