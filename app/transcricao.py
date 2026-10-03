"""Transcricao local de audio com faster-whisper.

O audio nunca sai desta maquina. O modelo roda na CPU (ou GPU, se disponivel)
e o arquivo de audio e apagado pelo servidor assim que a transcricao termina.

Modelos, do mais rapido ao mais preciso:

    tiny    ~75 MB   rapido, erra muito termo clinico  -- nao use em consulta
    base    ~145 MB  ainda fraco para portugues medico
    small   ~500 MB  piso pratico para uso clinico     -- padrao
    medium  ~1.5 GB  bom, exige maquina com folga
    large-v3 ~3 GB   melhor, lento em CPU

Troque com a variavel de ambiente VOA_MODELO.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Callable

MODELO_PADRAO = os.environ.get("VOA_MODELO", "small")

# Termos que o Whisper erra com frequencia em portugues clinico. Alimentar o
# initial_prompt com vocabulario do dominio melhora sensivelmente o resultado.
CONTEXTO_CLINICO = (
    "Consulta médica em português do Brasil. Termos frequentes: anamnese, "
    "hipótese diagnóstica, conduta, pressão arterial, frequência cardíaca, "
    "hipertensão, diabetes mellitus, dislipidemia, hipotireoidismo, "
    "metformina, losartana, sinvastatina, enalapril, omeprazol, dipirona, "
    "levotiroxina, hidroclorotiazida, anlodipino, atenolol, insulina, "
    "miligramas, micrograma, comprimido, via oral, hemograma, creatinina, "
    "hemoglobina glicada, ultrassonografia, encaminhamento, retorno."
)

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

    segmentos, info = whisper.transcribe(
        str(caminho),
        language="pt",
        task="transcribe",
        initial_prompt=CONTEXTO_CLINICO,
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

    return "\n".join(linhas)


def _mmss(segundos: float) -> str:
    total = int(segundos)
    return f"{total // 60:02d}:{total % 60:02d}"
