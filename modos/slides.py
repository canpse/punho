"""Apresentação: o PDF (ou pptx/odp, via LibreOffice) vira imagens e a página /slides mostra a atual em tela cheia."""
import shutil
import subprocess
import tempfile
import re
import urllib.request
from pathlib import Path

from .base import DADOS, SAIDA, Modo, carregar, girar, salvar

PASTA = DADOS / "slides"


class Slides(Modo):
    id, nome = "slides", "Apresentação"
    # ⏭ avança, ⏯ volta um slide, ⏮ volta ao menu (padrão da Central)

    def __init__(self):
        e = carregar("slides.json", {})
        self.nome_pdf = e.get("nome_pdf")
        self.pagina = e.get("pagina", 0)
        self.preto = False
        self.na_saida = False

    def paginas(self):
        if not self.nome_pdf:
            return []
        return sorted((PASTA / self.nome_pdf).glob("p-*.png"))

    def guardar(self):
        salvar("slides.json", {"nome_pdf": self.nome_pdf, "pagina": self.pagina})

    def linha(self):
        n = len(self.paginas())
        if self.na_saida or not n:
            return SAIDA if self.na_saida else "sem PDF  ← play"
        return "■ tela preta" if self.preto else f"slide {self.pagina + 1}/{n}"

    def entrar(self, c):
        self.na_saida = False
        c.mostrar(self.linha())

    def botao(self, c, b):
        n = len(self.paginas())
        if n:
            self.pagina = max(0, min(n - 1, self.pagina + (1 if b == "proxima" else -1)))
            self.preto = False
            self.guardar()
        c.mostrar(self.linha())

    def baixar_google(self, link):
        """Link do Google Apresentações -> PDF (precisa estar "qualquer pessoa com o link")."""
        m = re.search(r"/presentation/d/([\w-]+)", link)
        if not m:
            raise ValueError("não achei o id da apresentação no link")
        tmp = Path(tempfile.mkdtemp(prefix="punho-"))
        req = urllib.request.Request(f"https://docs.google.com/presentation/d/{m.group(1)}/export/pdf",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dados = r.read()
        if not dados.startswith(b"%PDF"):
            raise PermissionError("o Google não liberou: compartilhe como 'qualquer pessoa com o link pode ver'")
        titulo = "google-" + m.group(1)[:12]
        destino = tmp / f"{titulo}.pdf"
        destino.write_bytes(dados)
        return destino

    def carregar_pdf(self, caminho):
        if str(caminho).startswith("http"):
            caminho = self.baixar_google(caminho)
        caminho = Path(caminho).expanduser()
        if not caminho.is_file():
            raise FileNotFoundError(caminho)
        nome = "".join(ch if ch.isalnum() else "-" for ch in caminho.stem)[:60]
        destino = PASTA / nome
        shutil.rmtree(destino, ignore_errors=True)
        destino.mkdir(parents=True)
        pdf = caminho
        if caminho.suffix.lower() != ".pdf":
            # pptx, odp, docx...: o LibreOffice gera um PDF numa pasta temporária
            # (o arquivo original não é tocado)
            tmp = Path(tempfile.mkdtemp(prefix="punho-"))
            subprocess.run(["soffice", f"-env:UserInstallation=file://{tmp}/perfil", "--headless",
                            "--convert-to", "pdf", "--outdir", str(tmp), str(caminho)],
                           check=True, capture_output=True, timeout=180)
            pdf = tmp / (caminho.stem + ".pdf")
            if not pdf.exists():
                raise RuntimeError("o LibreOffice não conseguiu converter o arquivo")
        subprocess.run(["pdftoppm", "-png", "-r", "110", str(pdf), str(destino / "p")], check=True)
        self.nome_pdf, self.pagina, self.preto = nome, 0, False
        self.guardar()

    def imagem_atual(self):
        p = self.paginas()
        return p[self.pagina] if p and not self.preto else None

    def estado(self):
        return {"pdf": self.nome_pdf, "pagina": self.pagina, "total": len(self.paginas()),
                "preto": self.preto}

    def api(self, c, acao, dados):
        if acao == "carregar":
            try:
                self.carregar_pdf(dados["caminho"])
            except Exception as erro:
                return {"erro": str(erro)}
        elif acao == "preto":
            self.preto = not self.preto
        elif acao == "ir":
            self.pagina = max(0, min(len(self.paginas()) - 1, int(dados["pagina"])))
            self.preto = False
            self.guardar()
        else:
            return {"erro": "acao"}
        if c.ativo is self:
            self.entrar(c)
        return {"ok": True}
