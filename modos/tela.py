"""O que cabe na única linha da tela de Música do Redmi Watch 5 Active.

Mapa de 02/11/2026 (fotos do Lucas): o que não está em EMOJIS/SIMBOLOS vira
retângulo. Réguas: cabem 16 dígitos, 9 emojis, 9 quadradinhos. Regra dele: o
texto NUNCA pode rolar.
"""
EMOJIS = set("🔴✅⭐🔥👍😐😴🤔💪💚💙💛⚡😀") | {"❤️", "☀️"}
SIMBOLOS = set("←→↑↓↖↗○◎●█▓▄■□▲▼①②③")
LARGOS = SIMBOLOS - set("←→↑↓↖↗")  # medem como emoji
LARGURA = 16  # unidade = largura de um dígito


def _pedacos(texto):
    out = []
    for c in texto:
        if c == "️" and out:
            out[-1] += c
        else:
            out.append(c)
    return out


def peso(g):
    if g in EMOJIS or g in LARGOS:
        return 1.75
    if g == " ":
        return 0.6
    if g.isupper() or g in "mwMW@%":
        return 1.25
    return 1.0


def existe(g):
    return g in EMOJIS or g in SIMBOLOS or ord(g[0]) < 0x2000


def tela(texto):
    """Só glifos que o relógio tem, cortado pra caber sem rolar."""
    texto = " ".join(str(texto).split())
    ok, usado = "", 0.0
    for g in _pedacos(texto):
        if not existe(g):
            continue
        if g == " " and ok.endswith(" "):
            continue
        w = peso(g)
        if usado + w > LARGURA - 0.5:
            return ok.rstrip() + "."
        ok, usado = ok + g, usado + w
    return ok


def barra(feito, total, n=5):
    cheio = round(n * feito / total) if total else 0
    return "■" * cheio + "□" * (n - cheio)


def coracao(dias):
    return "❤️" if dias <= 2 else "💛" if dias <= 7 else "💚"
