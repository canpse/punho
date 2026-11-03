"""Metrônomo na caixa de som do PC. Um fluxo contínuo pro pw-cat (tempo exato,
sem abrir processo a cada batida)."""
import math
import struct
import subprocess
import threading

from .base import SAIDA, Modo, carregar, girar, salvar

TAXA = 44100


def clique(freq, dur=0.03, vol=0.6):
    n = int(TAXA * dur)
    amostras = (int(32767 * vol * math.sin(2 * math.pi * freq * i / TAXA) * (1 - i / n)) for i in range(n))
    return struct.pack(f"<{n}h", *amostras)


FORTE = clique(1600)
FRACO = clique(1000, vol=0.45)


class Metronomo(Modo):
    id, nome = "metronomo", "Metrônomo"

    def __init__(self):
        e = carregar("metronomo.json", {})
        self.bpm = e.get("bpm", 80)
        self.compasso = e.get("compasso", 4)
        self.tocando = False
        self.pos = 0
        self._fio = None
        self._proc = None

    def guardar(self):
        salvar("metronomo.json", {"bpm": self.bpm, "compasso": self.compasso})

    # roda: 0 tocar/parar, 1 mais rápido, 2 mais lento, 3 "← menu"
    def linha(self):
        return [f"{'●' if self.tocando else '○'} {self.bpm} bpm", f"↑ {self.bpm} bpm",
                f"↓ {self.bpm} bpm", SAIDA][self.pos]

    def entrar(self, c):
        self.pos = 0
        c.mostrar(self.linha())

    def botao(self, c, b):
        if b != "play":
            self.pos = girar(self.pos, 1 if b == "proxima" else -1, 3)
        elif self.pos == 0:
            self.parar() if self.tocando else self.tocar()
        elif self.pos in (1, 2):
            self.bpm = max(30, min(240, self.bpm + (5 if self.pos == 1 else -5)))
            self.guardar()
        else:
            self.pos = 0
            return c.sair_do_modo()  # continua tocando se estiver tocando
        c.mostrar(self.linha())

    def tocar(self):
        self.tocando = True
        self._proc = subprocess.Popen(
            ["pw-cat", "--playback", "--raw", "--rate", str(TAXA), "--channels", "1", "--format", "s16", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._fio = threading.Thread(target=self._laco, args=(self._proc,), daemon=True)
        self._fio.start()

    def _laco(self, proc):
        batida = 0
        try:
            while self.tocando and proc.poll() is None:
                som = FORTE if batida % self.compasso == 0 else FRACO
                total = int(TAXA * 60 / self.bpm) * 2  # bytes (s16)
                proc.stdin.write(som + b"\x00" * max(0, total - len(som)))
                proc.stdin.flush()
                batida += 1
        except (BrokenPipeError, ValueError):
            pass

    def parar(self):
        self.tocando = False
        if self._proc:
            self._proc.terminate()
            self._proc = None

    def estado(self):
        return {"bpm": self.bpm, "compasso": self.compasso, "tocando": self.tocando}

    def api(self, c, acao, dados):
        if acao == "config":
            self.bpm = max(30, min(240, int(dados.get("bpm", self.bpm))))
            self.compasso = max(1, min(12, int(dados.get("compasso", self.compasso))))
            self.guardar()
        elif acao == "alternar":
            self.parar() if self.tocando else self.tocar()
        else:
            return {"erro": "acao"}
        if c.ativo is self:
            self.entrar(c)
        return {"ok": True}
