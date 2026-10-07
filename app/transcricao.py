"""Transcricao local de audio com faster-whisper.

O audio nunca sai desta maquina. O modelo roda na CPU (ou GPU, se disponivel)
e o arquivo de audio e apagado pelo servidor assim que a transcricao termina.

Modelos, do mais rapido ao mais preciso:

    tiny    ~75 MB   rapido, erra muito termo clinico  -- nao use em consulta
    base    ~145 MB  ainda fraco para portugues medico
    small   ~500 MB  erra nome de colirio e eixo em oftalmologia
    medium  ~1.5 GB  padrao: o piso pratico para consulta oftalmologica
    large-v3 ~3 GB   melhor, lento em CPU

Troque com a variavel de ambiente VOA_MODELO ou com --modelo.

O vocabulario de oftalmologia vive em vocabulario.py e entra aqui por dois
caminhos: como hotwords dentro do motor, e como deteccao de termos suspeitos
depois -- que marca, nunca corrige.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vocabulario  # noqa: E402

# Medium e nao small: em consulta de oftalmologia o small erra nome de colirio,
# eixo e estrutura a ponto de a nota virar um formulario de pendencias. Medido
# em atendimento real.
MODELO_PADRAO = os.environ.get("VOA_MODELO", "medium")

_modelo = None
_modelo_carregado: str | None = None


class TranscricaoIndisponivel(RuntimeError):
    """faster-whisper nao esta instalado ou o modelo nao pode ser carregado."""


def disponivel() -> bool:
    """Diz se o faster-whisper esta instalado, sem pagar o preco de importa-lo.

    Importar de verdade puxa ctranslate2, onnxruntime e tokenizers -- de 5 a 30
    segundos na primeira execucao, com o terminal mudo e o navegador sem abrir.
    find_spec so procura o modulo no disco: instantaneo.
    """
    return importlib.util.find_spec("faster_whisper") is not None


def carregar_modelo(nome: str = MODELO_PADRAO):
    """Carrega o modelo uma vez e mantem em memoria entre atendimentos."""
    global _modelo, _modelo_carregado

    if _modelo is not None and _modelo_carregado == nome:
        return _modelo

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscricaoIndisponivel(
            "faster-whisper não está instalado. Rode:\n"
            "    pip install -r app/requirements.txt"
        ) from exc

    # int8 cabe em qualquer maquina moderna e e ~4x mais rapido que float32
    # na CPU, com perda de qualidade irrelevante para fala.
    try:
        _modelo = WhisperModel(nome, device="auto", compute_type="int8")
    except Exception as exc:
        raise TranscricaoIndisponivel(
            f"Não consegui carregar o modelo '{nome}': {exc}\n"
            "Na primeira execução o modelo é baixado — confirme a conexão."
        ) from exc

    _modelo_carregado = nome
    return _modelo


def transcrever(
    caminho: Path,
    *,
    modelo: str = MODELO_PADRAO,
    progresso: Callable[[float], None] | None = None,
) -> str:
    """Transcreve o arquivo e devolve o texto com marcacao de tempo por trecho.

    `progresso` recebe a fracao concluida (0.0 a 1.0) quando a duracao do
    audio e conhecida.
    """
    if not caminho.is_file() or caminho.stat().st_size == 0:
        raise TranscricaoIndisponivel(f"Áudio vazio ou inexistente: {caminho}")

    whisper = carregar_modelo(modelo)

    # O BLAS do macOS (Accelerate) deixa marcadores de excecao de ponto
    # flutuante ligados depois de uma multiplicacao de matrizes, e o numpy os
    # reporta como "divide by zero / overflow / invalid value in matmul" ao
    # montar o espectrograma. Matmul nao divide: o aviso e do backend, nao da
    # conta. Silenciar aqui evita encher o terminal de alarme falso durante
    # meia hora de transcricao.
    #
    # Isto nao substitui conferir o resultado: se a transcricao sair vazia ou
    # sem sentido, o problema e numerico de verdade e o silencio atrapalha --
    # por isso o aviso abaixo quando nao sai texto nenhum.
    with _silenciar_ponto_flutuante():
        return _transcrever(whisper, caminho, progresso)


def _silenciar_ponto_flutuante():
    try:
        import numpy as np

        return np.errstate(divide="ignore", over="ignore", invalid="ignore")
    except ImportError:  # pragma: no cover
        from contextlib import nullcontext

        return nullcontext()


def _transcrever(whisper, caminho: Path, progresso) -> str:
    segmentos, info = whisper.transcribe(
        str(caminho),
        language="pt",
        task="transcribe",
        # hotwords e nao initial_prompt: e o parametro feito para enviesar o
        # reconhecimento a termos especificos, e com condition_on_previous_text
        # desligado ele e reaplicado a cada janela de 30s, nao so na primeira.
        # Orcamento de ~220 tokens, truncado em silencio -- por isso a lista em
        # vocabulario.py e curta de proposito.
        hotwords=vocabulario.hotwords(),
        # VAD corta silencio: consulta tem muita pausa, e silencio e onde o
        # Whisper alucina frase inteira.
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 700},
        beam_size=5,
        condition_on_previous_text=False,  # evita propagar erro por todo o audio
    )

    duracao = getattr(info, "duration", 0) or 0
    linhas: list[str] = []

    for seg in segmentos:
        texto = seg.text.strip()
        if not texto:
            continue
        linhas.append(f"[{_mmss(seg.start)}] {texto}")
        if progresso and duracao:
            progresso(min(seg.end / duracao, 1.0))

    if progresso:
        progresso(1.0)

    if not linhas:
        # Audio com fala mas transcricao vazia costuma ser erro numerico real,
        # e nao silencio -- o VAD teria cortado silencio antes de chegar aqui.
        print(
            "  ⚠ Nenhuma fala foi reconhecida. Se havia áudio, pode ser problema "
            "numérico do backend — tente outro modelo com --modelo small."
        )

    return "\n".join(linhas)


def _mmss(segundos: float) -> str:
    total = int(segundos)
    return f"{total // 60:02d}:{total % 60:02d}"
