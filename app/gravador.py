#!/usr/bin/env python3
"""Gravador de consulta com transcricao local.

Sobe um servidor no proprio computador. A pagina grava o audio da consulta,
envia em pedacos para ca, e ao encerrar transcreve tudo com Whisper local.
O audio e apagado assim que a transcricao existe.

Nada trafega pela internet: o servidor escuta apenas em 127.0.0.1.

Uso (Mac e Linux):
    python3 app/gravador.py
    python3 app/gravador.py --porta 9000 --modelo medium
    python3 app/gravador.py --sem-navegador

No Windows, troque `python3` por `py`:
    py app/gravador.py
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import shutil
import ssl
import sys
import threading
import uuid
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parent
ESTATICOS = RAIZ / "static"
TRABALHO = RAIZ.parent / "atendimentos"  # coberto pelo .gitignore

# Como o usuario invoca o Python nesta maquina, para as dicas no terminal.
COMANDO_PY = "py" if sys.platform == "win32" else "python3"

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

        # "gravando" -> "transcrevendo" -> "pronto" | "erro"
        # A transcricao de uma consulta longa leva minutos. Ela roda numa
        # thread e a pagina pergunta o estado de tempos em tempos, em vez de
        # segurar uma conexao aberta esperando -- que o navegador derruba.
        self.estado = "gravando"
        self.resultado: dict | None = None
        self.erro: str | None = None

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

# No modo rede o servidor fica visível para qualquer aparelho no mesmo Wi-Fi.
# O token impede que um deles use o gravador — a página só o conhece porque
# ele vem no endereço que você abriu.
TOKEN = ""


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

    def _autorizado(self) -> bool:
        """Confere o token nas rotas de API. Sem token configurado, libera."""
        if not TOKEN:
            return True
        enviado = self.headers.get("X-Token") or ""
        if not enviado:
            enviado = (parse_qs(urlparse(self.path).query).get("t") or [""])[0]
        return secrets.compare_digest(enviado, TOKEN)

    def log_message(self, formato: str, *args) -> None:
        # Silencia o log de acesso: URL de sessao nao precisa ir para o terminal.
        pass

    # ------------------------------------------------------------------- GET

    def do_GET(self) -> None:
        caminho = urlparse(self.path).path

        # Certificado da CA, para instalar no celular. Fica fora do token:
        # é chave pública, e é o que o aparelho precisa antes de confiar.
        if caminho in ("/ca.crt", "/certificado.crt"):
            import certificado

            if not certificado.CA_CRT.is_file():
                return self._erro("nenhum certificado gerado", HTTPStatus.NOT_FOUND)
            dados = certificado.CA_CRT.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-x509-ca-cert")
            self.send_header("Content-Disposition", 'attachment; filename="gravador-ca.crt"')
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            return self.wfile.write(dados)

        if caminho.startswith("/api/") and not self._autorizado():
            return self._erro("token inválido ou ausente", HTTPStatus.UNAUTHORIZED)

        # GET /api/sessao/<id>/estado — como vai a transcrição desta sessão.
        # É leitura, então é GET: a página chama isto a cada três segundos.
        partes = [p for p in caminho.split("/") if p]
        if len(partes) == 4 and partes[:2] == ["api", "sessao"] and partes[3] == "estado":
            sessao = self._sessao(partes[2])
            if sessao is None:
                # Some da memória assim que o cliente recebe o "pronto". Se a
                # página perguntar de novo, o resultado já foi entregue.
                return self._erro("sessão não encontrada", HTTPStatus.NOT_FOUND)
            return self._estado(sessao)

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
        if not self._autorizado():
            return self._erro("token inválido ou ausente", HTTPStatus.UNAUTHORIZED)
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

            if partes[3] == "estado":
                return self._estado(sessao)

        return self._erro("rota desconhecida", HTTPStatus.NOT_FOUND)

    # ---------------------------------------------------------------- DELETE

    def do_DELETE(self) -> None:
        if not self._autorizado():
            return self._erro("token inválido ou ausente", HTTPStatus.UNAUTHORIZED)
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
        """Dispara a transcricao e responde na hora.

        Transcrever meia hora de consulta leva minutos. Segurar a conexao
        aberta durante esse tempo nao funciona: o navegador desiste, a
        resposta morre num BrokenPipeError, e a tela fica girando para
        sempre -- mesmo com o arquivo ja salvo em disco. Entao o trabalho
        vai para uma thread e a pagina pergunta o estado.
        """
        with sessao.trava:
            if sessao.encerrada:
                # Reencerrar uma sessao em andamento devolve o estado atual,
                # em vez de erro: e o que acontece quando a pagina recarrega.
                return self._estado(sessao)
            sessao.encerrada = True

        if sessao.bytes_recebidos == 0:
            sessao.descartar()
            SESSOES.pop(sessao.id, None)
            return self._erro("Nenhum áudio foi gravado.")

        sessao.estado = "transcrevendo"
        threading.Thread(target=transcrever_sessao, args=(sessao,), daemon=True).start()

        return self._json({"estado": "transcrevendo", "duracao": sessao.duracao})

    def _estado(self, sessao: Sessao) -> None:
        """Onde a transcricao esta. A pagina chama isto a cada poucos segundos."""
        if sessao.estado == "pronto":
            SESSOES.pop(sessao.id, None)  # o cliente recebeu: pode sair da memoria
            return self._json({"estado": "pronto", **(sessao.resultado or {})})

        if sessao.estado == "erro":
            return self._json({"estado": "erro", "erro": sessao.erro or "falha"}, 500)

        return self._json({"estado": sessao.estado, "duracao": sessao.duracao})


def transcrever_sessao(sessao: Sessao) -> None:
    """Transcreve, salva e apaga o audio. Roda fora da requisicao.

    Chega ao fim mesmo que o navegador tenha sido fechado no meio: o arquivo
    em disco e o resultado que importa, e o caminho dele sai no terminal.
    """
    import transcricao
    import vocabulario

    duracao = sessao.duracao
    print(f"  … transcrevendo {duracao} de áudio (modelo {sessao.modelo})")

    try:
        texto = transcricao.transcrever(sessao.audio, modelo=sessao.modelo)
    except transcricao.TranscricaoIndisponivel as exc:
        # Preserva o audio: sem transcricao, ele e a unica copia do atendimento.
        sessao.encerrada = False
        sessao.estado = "erro"
        sessao.erro = (
            f"{exc}\n\nO áudio foi preservado em {sessao.audio} — "
            "resolva a instalação e encerre de novo."
        )
        print(f"  ✗ {sessao.erro}")
        return
    except Exception as exc:  # noqa: BLE001
        sessao.encerrada = False
        sessao.estado = "erro"
        sessao.erro = f"Falha na transcrição: {exc}"
        print(f"  ✗ {sessao.erro}")
        print(f"    O áudio foi preservado em {sessao.audio}")
        return

    # Termos parecidos com vocabulário de oftalmologia, mas diferentes dele.
    # Vão anexados à transcrição para virarem pendência na nota — o texto
    # acima fica como veio, sem correção automática.
    try:
        conferir = vocabulario.relatorio(texto)
    except Exception as exc:  # noqa: BLE001 — detector nunca derruba a transcrição
        print(f"  ⚠ detector de termos falhou ({exc}); transcrição segue intacta")
        conferir = ""

    destino = sessao.pasta / "transcricao.md"
    destino.write_text(
        CABECALHO_TRANSCRICAO.format(
            inicio=sessao.inicio.strftime("%d/%m/%Y %H:%M"),
            duracao=duracao,
            modelo=sessao.modelo,
        )
        + (texto or "_(nenhuma fala reconhecida)_")
        + "\n"
        + conferir,
        encoding="utf-8",
    )

    # Regra de retencao: o audio nao sobrevive a transcricao.
    sessao.audio.unlink(missing_ok=True)

    sessao.resultado = {
        "arquivo": str(destino),
        "duracao": duracao,
        "palavras": len(texto.split()),
        "previa": texto[:1200],
        "comando": (
            f'claude "Estrutura essa consulta em SOAP: @{destino.relative_to(RAIZ.parent)}"'
        ),
    }
    sessao.estado = "pronto"

    print(f"  ✓ transcrição salva — {destino}")
    print("    áudio apagado")
    print("    Se a página não mostrar, abra o arquivo acima: a transcrição está lá.")


def console_utf8() -> None:
    """Garante que acento e símbolo não quebrem a saída no terminal.

    O Windows usa cp1252 quando a saída é redirecionada para arquivo ou pipe,
    e aí um 'ç' ou um '✓' derruba o print com UnicodeEncodeError.
    """
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # fluxo substituído ou já fechado — nada a fazer


def mostrar_qr(url: str) -> bool:
    """Desenha o QR no terminal, se a biblioteca opcional estiver instalada."""
    try:
        import qrcode
    except ImportError:
        return False

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Gravador de consulta com transcrição local.")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument(
        "--modelo",
        default=None,
        help="tiny | base | small | medium | large-v3 (padrão: small)",
    )
    ap.add_argument(
        "--rede",
        action="store_true",
        help="libera o acesso pelo celular na mesma rede Wi-Fi (ativa HTTPS)",
    )
    ap.add_argument("--sem-navegador", action="store_true")
    args = ap.parse_args(argv)

    console_utf8()

    global MODELO_ATUAL, TOKEN
    sys.path.insert(0, str(RAIZ))
    import transcricao

    MODELO_ATUAL = args.modelo or transcricao.MODELO_PADRAO
    TRABALHO.mkdir(parents=True, exist_ok=True)

    contexto_tls = None
    host = "127.0.0.1"
    esquema = "http"
    ips: list[str] = []

    if args.rede:
        import certificado

        ips = certificado.detectar_ips()
        if not ips:
            print("\n  ✗ Não encontrei o endereço desta máquina na rede.")
            print("    Confirme que o computador está conectado ao Wi-Fi.\n")
            return 1

        try:
            cert, chave, novo = certificado.garantir(ips)
        except certificado.CertificadoIndisponivel as exc:
            print(f"\n  ✗ {exc}\n")
            return 1

        contexto_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto_tls.load_cert_chain(cert, chave)
        host = "0.0.0.0"  # noqa: S104 — exposição é o objetivo do modo rede
        esquema = "https"
        TOKEN = secrets.token_urlsafe(12)

        if novo:
            print("\n  Certificado gerado para:", ", ".join(ips))

    endereco_local = f"{esquema}://localhost:{args.porta}"
    if TOKEN:
        endereco_local += f"/?t={TOKEN}"

    print("\n  Gravador de consulta\n")
    print(f"  Neste computador : {endereco_local}")

    if args.rede:
        principal = f"https://{ips[0]}:{args.porta}/?t={TOKEN}"
        print(f"  No celular       : {principal}")
        print(f"  Certificado      : https://{ips[0]}:{args.porta}/ca.crt")
        if len(ips) > 1:
            print(f"  (outros IPs desta máquina: {', '.join(ips[1:])})")

    print(f"\n  Modelo de transcrição : {MODELO_ATUAL}")
    print(f"  Transcrições em       : {TRABALHO}")

    if not transcricao.disponivel():
        print("\n  ⚠ faster-whisper não instalado — a gravação funciona, mas não")
        print("    será possível transcrever. Rode: pip install -r app/requirements.txt")

    if args.rede:
        print("\n  Antes de gravar pelo celular, uma vez só:")
        print("    1. Abra o endereço do certificado no celular e instale-o")
        print("    2. iPhone: Ajustes › Geral › Sobre › Certificados Confiáveis")
        print("       e ative a confiança total")
        print("    3. Abra o endereço do gravador (ou leia o QR abaixo)")
        print("\n  O áudio trafega só pela sua rede Wi-Fi, cifrado, e é")
        print("  transcrito neste computador. Não passa pela internet.")
        print("\n  ⚠ Em Wi-Fi público ou de terceiros, prefira gravar pelo computador.")
        print("  ⚠ Neste computador o navegador vai avisar que o certificado não é")
        print(f"    conhecido — é o seu mesmo. Para gravar aqui, use '{COMANDO_PY} app/gravador.py'")
        print("    sem --rede, e o aviso não aparece.\n")
        if not mostrar_qr(principal):
            print("  (instale 'qrcode' para ver o endereço como QR: pip install qrcode)\n")
    else:
        print("\n  O áudio não sai desta máquina.")
        print(f"  Para gravar pelo celular: {COMANDO_PY} app/gravador.py --rede\n")

    print("  Ctrl+C encerra.\n")

    servidor = ThreadingHTTPServer((host, args.porta), Handler)
    if contexto_tls is not None:
        servidor.socket = contexto_tls.wrap_socket(servidor.socket, server_side=True)

    if not args.sem_navegador:
        threading.Timer(0.5, lambda: webbrowser.open(endereco_local)).start()

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
