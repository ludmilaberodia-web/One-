#!/usr/bin/env python3
"""Gravador de consulta com transcricao local.

Sobe um servidor no proprio computador. A pagina grava o audio da consulta,
envia em pedacos para ca, e ao encerrar transcreve tudo com Whisper local.
O audio e apagado assim que a transcricao existe.

Nada trafega pela internet: o servidor escuta apenas em 127.0.0.1.

Uso:
    python3 app/gravador.py
    python3 app/gravador.py --porta 9000 --modelo medium
    python3 app/gravador.py --sem-navegador
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import threading
import uuid
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent
ESTATICOS = RAIZ / "static"
TRABALHO = RAIZ.parent / "atendimentos"  # coberto pelo .gitignore

# Limite por pedaco de audio (10s de opus a 32 kbps ~ 40 KB; 8 MB e folga enorme).
MAX_PEDACO = 8 * 1024 * 1024
ID_VALIDO = re.compile(r"^[0-9a-f]{32}$")

TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}

CABECALHO_TRANSCRICAO = """\
# Transcrição de atendimento — {inicio}

> DADO SENSÍVEL (LGPD, art. 5º, II). Transcrição bruta, não revisada.
> Áudio original já foi apagado. Apague este arquivo assim que a nota clínica
> validada estiver arquivada no prontuário eletrônico.
> Duração da gravação: {duracao}. Modelo: {modelo}.

---

"""


class Sessao:
    """Uma gravação em andamento."""

    def __init__(self, modelo: str) -> None:
        self.id = uuid.uuid4().hex
        self.inicio = datetime.now()
        self.modelo = modelo
        self.pasta = TRABALHO / self.inicio.strftime("%Y-%m-%d_%H-%M-%S")
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.audio = self.pasta / "audio.webm"
        self.bytes_recebidos = 0
        self.encerrada = False
        self.trava = threading.Lock()

    def anexar(self, dados: bytes) -> None:
        with self.trava:
            if self.encerrada:
                raise ValueError("sessão já encerrada")
            with self.audio.open("ab") as fh:
                fh.write(dados)
            self.bytes_recebidos += len(dados)

    @property
    def duracao(self) -> str:
        total = int((datetime.now() - self.inicio).total_seconds())
        return f"{total // 60:02d}:{total % 60:02d}"

    def descartar(self) -> None:
        with self.trava:
            self.encerrada = True
        shutil.rmtree(self.pasta, ignore_errors=True)


SESSOES: dict[str, Sessao] = {}
MODELO_ATUAL = "small"


class Handler(BaseHTTPRequestHandler):
    server_version = "GravadorConsulta"

    # ------------------------------------------------------------------ util

    def _json(self, dados: dict, status: int = 200) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _erro(self, mensagem: str, status: int = 400) -> None:
        self._json({"erro": mensagem}, status)

    def _corpo(self) -> bytes:
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > MAX_PEDACO:
            raise ValueError("pedaço de áudio grande demais")
        return self.rfile.read(tamanho) if tamanho else b""

    def _sessao(self, sid: str) -> Sessao | None:
        if not ID_VALIDO.match(sid or ""):
            return None
        return SESSOES.get(sid)

    def log_message(self, formato: str, *args) -> None:
        # Silencia o log de acesso: URL de sessao nao precisa ir para o terminal.
        pass

    # ------------------------------------------------------------------- GET

    def do_GET(self) -> None:
        caminho = urlparse(self.path).path

        if caminho == "/api/estado":
            import transcricao

            return self._json(
                {
                    "transcricaoDisponivel": transcricao.disponivel(),
                    "modelo": MODELO_ATUAL,
                    "pastaTrabalho": str(TRABALHO),
                }
            )

        alvo = "index.html" if caminho == "/" else caminho.lstrip("/")
        arquivo = (ESTATICOS / alvo).resolve()

        # Bloqueia travessia de caminho.
        if not str(arquivo).startswith(str(ESTATICOS.resolve())) or not arquivo.is_file():
            return self._erro("não encontrado", HTTPStatus.NOT_FOUND)

        dados = arquivo.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", TIPOS.get(arquivo.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    # ------------------------------------------------------------------ POST

    def do_POST(self) -> None:
        caminho = urlparse(self.path).path
        partes = [p for p in caminho.split("/") if p]

        # POST /api/sessao
        if partes == ["api", "sessao"]:
            try:
                pedido = json.loads(self._corpo() or b"{}")
            except (ValueError, json.JSONDecodeError) as exc:
                return self._erro(str(exc))

            if not pedido.get("consentimento"):
                return self._erro(
                    "Gravação exige consentimento registrado do paciente.", 403
                )

            sessao = Sessao(MODELO_ATUAL)
            SESSOES[sessao.id] = sessao
            print(f"  ● gravação iniciada — {sessao.pasta.name}")
            return self._json({"id": sessao.id, "inicio": sessao.inicio.isoformat()})

        # POST /api/sessao/<id>/audio  |  /encerrar
        if len(partes) == 4 and partes[:2] == ["api", "sessao"]:
            sessao = self._sessao(partes[2])
            if sessao is None:
                return self._erro("sessão não encontrada", HTTPStatus.NOT_FOUND)

            if partes[3] == "audio":
                try:
                    dados = self._corpo()
                    if dados:
                        sessao.anexar(dados)
                except ValueError as exc:
                    return self._erro(str(exc))
                return self._json({"bytes": sessao.bytes_recebidos})

            if partes[3] == "encerrar":
                return self._encerrar(sessao)

        return self._erro("rota desconhecida", HTTPStatus.NOT_FOUND)

    # ---------------------------------------------------------------- DELETE

    def do_DELETE(self) -> None:
        partes = [p for p in urlparse(self.path).path.split("/") if p]
        if len(partes) == 3 and partes[:2] == ["api", "sessao"]:
            sessao = self._sessao(partes[2])
            if sessao is None:
                return self._erro("sessão não encontrada", HTTPStatus.NOT_FOUND)
            sessao.descartar()
            SESSOES.pop(sessao.id, None)
            print("  ○ gravação descartada — áudio apagado")
            return self._json({"descartada": True})
        return self._erro("rota desconhecida", HTTPStatus.NOT_FOUND)

    # ------------------------------------------------------------ encerrar

    def _encerrar(self, sessao: Sessao) -> None:
        import transcricao

        with sessao.trava:
            if sessao.encerrada:
                return self._erro("sessão já encerrada")
            sessao.encerrada = True

        if sessao.bytes_recebidos == 0:
            sessao.descartar()
            SESSOES.pop(sessao.id, None)
            return self._erro("Nenhum áudio foi gravado.")

        duracao = sessao.duracao
        print(f"  … transcrevendo {duracao} de áudio (modelo {sessao.modelo})")

        try:
            texto = transcricao.transcrever(sessao.audio, modelo=sessao.modelo)
        except transcricao.TranscricaoIndisponivel as exc:
            # Preserva o audio: sem transcricao, ele e a unica copia do atendimento.
            sessao.encerrada = False
            return self._erro(
                f"{exc}\n\nO áudio foi preservado em {sessao.audio} — "
                "resolva a instalação e encerre de novo.",
                503,
            )
        except Exception as exc:  # noqa: BLE001
            sessao.encerrada = False
            return self._erro(f"Falha na transcrição: {exc}", 500)

        destino = sessao.pasta / "transcricao.md"
        destino.write_text(
            CABECALHO_TRANSCRICAO.format(
                inicio=sessao.inicio.strftime("%d/%m/%Y %H:%M"),
                duracao=duracao,
                modelo=sessao.modelo,
            )
            + (texto or "_(nenhuma fala reconhecida)_")
            + "\n",
            encoding="utf-8",
        )

        # Regra de retencao: o audio nao sobrevive a transcricao.
        sessao.audio.unlink(missing_ok=True)
        SESSOES.pop(sessao.id, None)

        print(f"  ✓ transcrição salva — {destino}")
        print("    áudio apagado")

        return self._json(
            {
                "arquivo": str(destino),
                "duracao": duracao,
                "palavras": len(texto.split()),
                "previa": texto[:1200],
                "comando": (
                    f'claude "Estrutura essa consulta em SOAP: @{destino.relative_to(RAIZ.parent)}"'
                ),
            }
        )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Gravador de consulta com transcrição local.")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument(
        "--modelo",
        default=None,
        help="tiny | base | small | medium | large-v3 (padrão: small)",
    )
    ap.add_argument("--sem-navegador", action="store_true")
    args = ap.parse_args(argv)

    global MODELO_ATUAL
    sys.path.insert(0, str(RAIZ))
    import transcricao

    MODELO_ATUAL = args.modelo or transcricao.MODELO_PADRAO
    TRABALHO.mkdir(parents=True, exist_ok=True)

    endereco = f"http://localhost:{args.porta}"

    print("\n  Gravador de consulta")
    print(f"  {endereco}\n")
    print(f"  Modelo de transcrição : {MODELO_ATUAL}")
    print(f"  Transcrições em       : {TRABALHO}")
    if not transcricao.disponivel():
        print("\n  ⚠ faster-whisper não instalado — a gravação funciona, mas não")
        print("    será possível transcrever. Rode: pip install -r app/requirements.txt")
    print("\n  O áudio não sai desta máquina. Ctrl+C encerra.\n")

    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), Handler)

    if not args.sem_navegador:
        threading.Timer(0.5, lambda: webbrowser.open(endereco)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n  Encerrando.")
        for sessao in list(SESSOES.values()):
            if sessao.bytes_recebidos and not sessao.encerrada:
                print(f"  ⚠ gravação não encerrada preservada em {sessao.audio}")
        servidor.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
