#!/usr/bin/env python3
"""Central do punho. O celular é um terminal burro: manda os três botões e mostra a
linha. Tudo o mais mora aqui.

Celular:  POST /botao?b=anterior|proxima|play      -> {"linha", "versao"}
          GET  /espera?versao=N&notif=M             -> espera mudança (até 25 s)
Painel:   http://punho.localhost:8787               (no próprio PC, sem token)
          http://IP-DO-PC:8787/?t=TOKEN             (de outro aparelho)
Slides:   http://punho.localhost:8787/slides
Hooks:    POST /api/pedido (Claude pede permissão), POST /api/aviso

Navegação: no menu, anterior/próxima escolhem o modo e play entra.
Dentro de um modo: ⏭ próximo item, ⏯ age, ⏮ volta ao menu (na Apresentação o ⏯
volta um slide). Só toques simples.
"""
import json
import socket
import sys
import threading
import time
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modos.aprovacao import Aprovacoes
from modos.aventura import Aventura
from modos.info import Cardapio, Pendencias, Prova, Testar
from modos.metronomo import Metronomo
from modos.quiz import Quiz
from modos.rpg import Rpg
from modos.servidores import Servidores
from modos.slides import Slides
from modos.base import carregar, salvar
from modos.tela import tela
from modos.termometro import Termometro

import config

AQUI = Path(__file__).resolve().parent
TOKEN = config.token()
HOST = sys.argv[1] if len(sys.argv) > 1 else config.HOST
PORTA = config.PORTA
LOG = AQUI / "acoes.log"


class Central:
    def __init__(self):
        self.trava = threading.RLock()
        self.cond = threading.Condition(self.trava)
        self.aprovacoes = Aprovacoes()
        self.termometro = Termometro()
        self.modos = [Prova(), Cardapio(), Quiz(), Pendencias(), Servidores(), self.aprovacoes, Rpg(),
                      Metronomo(), self.termometro, Slides(), Aventura(), Testar()]
        self.por_id = {m.id: m for m in self.modos}
        self.menu_i = 0          # índice dentro de visiveis()
        self.ocultos = set(carregar("menu.json", {}).get("ocultos", []))
        self.ativo = None
        self.pilha = []          # quem estava ativo antes de uma interrupção
        self.linha = ""
        # contadores partem da hora atual: depois de reiniciar a central eles continuam
        # maiores que tudo que o celular já viu (senão ele ignora as atualizações)
        self.versao = int((time.time() - 1.7e9) * 10)  # 10 por segundo; cabe no int do Java até ~2030
        self.notifs = []         # [{"id", "titulo", "texto"}]
        self._notif_id = int((time.time() - 1.7e9) * 10)
        self._geracao = 0        # invalida voltas atrasadas antigas
        self.mostrar_menu()

    # ----- o que os modos usam -----

    def mostrar(self, linha):
        with self.cond:
            self.linha = tela(linha)
            self.versao += 1
            self.cond.notify_all()

    def notificar(self, titulo, texto):
        with self.cond:
            self._notif_id += 1
            self.notifs.append({"id": self._notif_id, "titulo": tela(titulo), "texto": texto})
            del self.notifs[:-30]
            self.versao += 1
            self.cond.notify_all()

    def interromper(self, modo):
        with self.trava:
            self._geracao += 1
            self.pilha.append(self.ativo)
            self.ativo = modo
            modo.entrar(self)

    def interrompido_por(self, modo):
        return self.ativo is modo and bool(self.pilha)

    def voltar(self, atraso=0):
        if atraso:
            g = self._geracao
            threading.Timer(atraso, self._voltar_se, args=(g,)).start()
        else:
            self._voltar()

    def _voltar_se(self, g):
        with self.trava:
            if g == self._geracao:
                self._voltar()

    def _voltar(self):
        with self.trava:
            self._geracao += 1
            self.ativo = self.pilha.pop() if self.pilha else None
            if self.ativo:
                self.ativo.entrar(self)
            else:
                self.mostrar_menu()

    def sair_do_modo(self):
        """Play no "← menu": volta pra quem foi interrompido, ou pro menu."""
        with self.trava:
            if self.pilha:
                self._voltar()
            else:
                self._geracao += 1
                if self.ativo:
                    self.ativo.sair(self)
                self.ativo = None
                self.mostrar_menu()

    # ----- menu e botões -----

    def visiveis(self):
        """Modos que aparecem no menu do relógio (escolhidos no painel)."""
        v = [m for m in self.modos if m.id not in self.ocultos]
        return v or self.modos

    def mudar_visivel(self, modo_id, visivel):
        with self.trava:
            atual = self.visiveis()[self.menu_i % len(self.visiveis())]
            if visivel:
                self.ocultos.discard(modo_id)
            elif len(self.visiveis()) > 1:
                self.ocultos.add(modo_id)
            salvar("menu.json", {"ocultos": sorted(self.ocultos)})
            v = self.visiveis()
            self.menu_i = v.index(atual) if atual in v else 0
            if self.ativo is None:
                self.mostrar_menu()

    def mostrar_menu(self):
        v = self.visiveis()
        self.menu_i %= len(v)
        self.mostrar(f"{self.menu_i + 1}. {v[self.menu_i].nome}")

    def entrar(self, modo_id):
        with self.trava:
            self._geracao += 1
            if self.ativo:
                self.ativo.sair(self)
            self.pilha = []
            self.ativo = self.por_id[modo_id]
            v = self.visiveis()
            if self.ativo in v:
                self.menu_i = v.index(self.ativo)
            self.ativo.entrar(self)

    def botao(self, b):
        if b not in ("anterior", "proxima", "play"):
            return
        with self.trava:
            with LOG.open("a") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{self.ativo.id if self.ativo else 'menu'}\t{b}\n")
            if self.ativo and b == "anterior" and not self.ativo.usa_anterior:
                self.sair_do_modo()
            elif self.ativo:
                self.ativo.botao(self, b)
            elif b == "play":
                self.entrar(self.visiveis()[self.menu_i % len(self.visiveis())].id)
            else:
                self.menu_i = (self.menu_i + (1 if b == "proxima" else -1)) % len(self.visiveis())
                self.mostrar_menu()

    def esperar(self, versao, notif, limite=25):
        with self.cond:
            self.cond.wait_for(
                lambda: self.versao > versao or (self.notifs and self.notifs[-1]["id"] > notif),
                timeout=limite)
            return {"versao": self.versao, "linha": self.linha,
                    "notifs": [n for n in self.notifs if n["id"] > notif]}

    def estado(self):
        with self.trava:
            log = LOG.read_text().splitlines()[-15:] if LOG.exists() else []
            return {
                "linha": self.linha, "versao": self.versao,
                "ativo": self.ativo.id if self.ativo else None,
                "menu": [{"id": m.id, "nome": m.nome, "visivel": m.id not in self.ocultos} for m in self.modos],
                "menu_i": self.menu_i,
                "modos": {m.id: m.estado() for m in self.modos},
                "notifs": self.notifs[-8:][::-1], "log": log[::-1],
            }

    def relogio(self):
        """Tarefas por horário (termômetro)."""
        ultimo = None
        while True:
            agora = datetime.now()
            if agora.strftime("%H:%M") != ultimo:
                ultimo = agora.strftime("%H:%M")
                with self.trava:
                    self.termometro.checar_horario(self, agora)
            time.sleep(15)


C = Central()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _enviar(self, codigo, corpo, tipo="application/json; charset=utf-8", extra=None):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode()
        elif isinstance(corpo, str):
            corpo = corpo.encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except ValueError:
            return {}

    def _autorizado(self, q):
        if self.client_address[0] in ("127.0.0.1", "::1"):
            return True  # o próprio PC (punho.localhost) não precisa de token
        if self.headers.get("X-Token") == TOKEN or q.get("t", [""])[0] == TOKEN:
            return True
        biscoito = SimpleCookie(self.headers.get("Cookie", ""))
        if "punho" in biscoito and biscoito["punho"].value == TOKEN:
            return True
        self._enviar(403, {"erro": "token"})
        return False

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if not self._autorizado(q):
            return
        biscoito = {"Set-Cookie": f"punho={TOKEN}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000"}
        if url.path == "/":
            return self._enviar(200, (AQUI / "web/painel.html").read_bytes(), "text/html; charset=utf-8", biscoito)
        if url.path == "/slides":
            return self._enviar(200, (AQUI / "web/slides.html").read_bytes(), "text/html; charset=utf-8", biscoito)
        if url.path == "/slides/img":
            img = C.por_id["slides"].imagem_atual()
            if img is None:
                return self._enviar(204, b"")
            return self._enviar(200, img.read_bytes(), "image/png")
        if url.path == "/espera":
            r = C.esperar(int(q.get("versao", ["0"])[0]), int(q.get("notif", ["0"])[0]))
            return self._enviar(200, r)
        if url.path == "/api/estado":
            return self._enviar(200, C.estado())
        if url.path == "/janelas":  # app antigo (0.x)
            return self._enviar(200, {"janelas": [{"id": "x", "titulo": "Atualize o app"}]})
        self._enviar(404, {"erro": "caminho"})

    def do_POST(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if not self._autorizado(q):
            return
        partes = url.path.strip("/").split("/")
        if url.path in ("/botao", "/api/botao"):
            C.botao(q.get("b", [""])[0])
            return self._enviar(200, {"linha": C.linha, "versao": C.versao})
        if url.path == "/api/entrar":
            C.entrar(q["id"][0])
            return self._enviar(200, {"ok": True})
        if url.path == "/api/visivel":
            d = self._corpo()
            C.mudar_visivel(d["id"], bool(d["visivel"]))
            return self._enviar(200, {"ok": True})
        if url.path == "/api/menu":
            with C.trava:
                if C.ativo:
                    C.ativo.sair(C)
                C.ativo, C.pilha = None, []
                C.mostrar_menu()
            return self._enviar(200, {"ok": True})
        if len(partes) == 4 and partes[:2] == ["api", "modo"]:
            modo = C.por_id.get(partes[2])
            if not modo:
                return self._enviar(404, {"erro": "modo"})
            with C.trava:
                r = modo.api(C, partes[3], self._corpo())
            return self._enviar(200, r)
        if url.path == "/api/pedido":
            d = self._corpo()
            with C.trava:
                p = C.aprovacoes.novo(C, d.get("tool_name", "?"), d.get("tool_input", {}), d.get("cwd", ""))
            decidido = p.evento.wait(int(d.get("espera", 110)))
            if not decidido:
                with C.trava:
                    C.aprovacoes.expirar(C, p)
            return self._enviar(200, {"decisao": p.decisao})
        if url.path == "/api/aviso":
            d = self._corpo()
            C.notificar(d.get("titulo", "Aviso"), d.get("texto", ""))
            return self._enviar(200, {"ok": True})
        if url.path == "/acao":  # app antigo (0.x)
            return self._enviar(200, {"titulo": "Atualize o app", "detalhe": ""})
        self._enviar(404, {"erro": "caminho"})

    def log_message(self, *a):
        pass


class ServidorV6(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def servir_local():
    """punho.localhost: o navegador pode ir pro 127.0.0.1 ou pro ::1, então atende os dois."""
    for classe, ende in ((ThreadingHTTPServer, "127.0.0.1"), (ServidorV6, "::1")):
        try:
            srv = classe((ende, PORTA), Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        except OSError as erro:
            print(f"não abri {ende}:{PORTA}: {erro}")


if __name__ == "__main__":
    threading.Thread(target=C.relogio, daemon=True).start()
    servir_local()
    print(f"central do punho em http://punho.localhost:{PORTA} e http://{HOST}:{PORTA}/?t=…")
    ThreadingHTTPServer((HOST, PORTA), Handler).serve_forever()
