#!/usr/bin/env python3
"""Valida a estrutura de uma nota clinica gerada pelo assistente.

Checa o que da para checar mecanicamente: secoes obrigatorias do template,
bloco de validacao medica, marcadores de incerteza bem formados, coerencia
entre marcadores e pendencias, e vazamento de identificadores diretos.

NAO julga conteudo clinico -- isso e do medico.

Uso:
    python3 validar_nota.py nota.md
    python3 validar_nota.py nota.md --template soap
    python3 validar_nota.py nota.md --sem-pii   # pula a checagem de identificadores

Saida: relatorio no stdout. Codigo 0 = limpo, 1 = erros, 2 = falha de uso.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------
# Templates: secoes exigidas (comparadas sem acento, minusculas)
# --------------------------------------------------------------------------

TEMPLATES: dict[str, list[str]] = {
    "oftalmo": [
        "queixa principal",
        "acuidade visual",
        "biomicroscopia",
        "pressao intraocular",
        "fundoscopia",
        "hipoteses diagnosticas",
        "conduta",
        "pendencias de validacao",
    ],
    "oftalmo-retorno": [
        "subjetivo",
        "objetivo",
        "avaliacao",
        "plano",
        "acuidade visual",
        "pressao intraocular",
        "pendencias de validacao",
    ],
    "pre-operatorio": [
        "exames pre-operatorios",
        "lente ou tecnica planejada",
        "expectativa alinhada com o paciente",
        "riscos explicados",
        "pendencias de validacao",
    ],
    "anamnese": [
        "queixa principal",
        "historia da doenca atual",
        "historia patologica pregressa",
        "exame fisico",
        "hipoteses diagnosticas",
        "conduta",
        "pendencias de validacao",
    ],
    "soap": [
        "subjetivo",
        "objetivo",
        "avaliacao",
        "plano",
        "pendencias de validacao",
    ],
    "soap-enxuto": [
        "pendencias de validacao",
    ],
    "encaminhamento": [
        "resumo do caso",
        "hipotese diagnostica",
        "motivo especifico do encaminhamento",
    ],
    "alta": [
        "resumo da evolucao",
        "tratamento realizado",
        "situacao na alta",
        "orientacoes e seguimento",
    ],
    "paciente": [
        "o que esta acontecendo",
        "o que voce vai fazer",
        "quando procurar ajuda agora",
    ],
}

MARCADORES_VALIDOS = {"[nao informado]", "[definir com o medico]"}
MARCADOR_INAUDIVEL = re.compile(r"\[inaudivel: \".+?\"\]")

# Marcadores parecidos mas errados -- pegam o caso de o agente inventar variante.
MARCADOR_QUALQUER = re.compile(r"\[[^\[\]\n]{2,60}\]")
MARCADOR_IGNORAR = re.compile(
    r"^\[(x| |\s*)\]$"  # checkbox de markdown
    r"|^\[\^?\d+\]$"  # nota de rodape / referencia
    r"|^\[.*\]\(.*\)$"  # link markdown (nunca casa: MARCADOR_QUALQUER exclui parenteses do alvo)
)

# Placeholders do proprio template que devem ter sido preenchidos.
PLACEHOLDERS_TEMPLATE = re.compile(r"<[a-zà-ú][^<>\n]{2,60}>", re.IGNORECASE)

# --------------------------------------------------------------------------
# Identificadores diretos (LGPD) -- heuristicas, nao garantia
# --------------------------------------------------------------------------

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CPF", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("CNS (cartao SUS)", re.compile(r"\b[1-2]\d{2} ?\d{4} ?\d{4} ?\d{4}\b")),
    ("telefone", re.compile(r"(?<!\d)(?:\+55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)")),
    ("e-mail", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    ("CEP", re.compile(r"\b\d{5}-\d{3}\b")),
    ("RG", re.compile(r"\bRG[:\s]*[\d.\-]{7,}", re.IGNORECASE)),
    (
        "endereco",
        re.compile(
            r"\b(?:rua|avenida|av\.|travessa|alameda|praca)\s+[A-ZÀ-Ú][\w\s]{3,40},?\s*n?º?\s*\d+",
            re.IGNORECASE,
        ),
    ),
]

# Datas completas fora de contexto clinico legitimo (atendimento, retorno, exame).
DATA_COMPLETA = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
CONTEXTO_DATA_OK = re.compile(
    r"(atendimento|consulta|retorno|exame|evolucao|evolução|alta|validacao|validação"
    r"|data|periodo|período|desde|em|realizado|solicitado|ultima|última)",
    re.IGNORECASE,
)
NASCIMENTO = re.compile(r"(nascimento|nasceu|nascid[ao]|DN)[:\s]", re.IGNORECASE)

BLOCO_VALIDACAO = [
    "rascunho",
    "requer validacao medica",
    "medico responsavel",
    "crm",
]

# Eixo de refracao em milimetros: erro de transcricao visto em atendimento real
# ("mais 1mm em 25mm"). Eixo e grau, de 0 a 180.
EIXO_EM_MM = re.compile(r"[×x]\s*\d{1,3}\s*mm\b", re.IGNORECASE)
GRAU_EM_MM = re.compile(r"[+-]\s?\d+[.,]?\d*\s?mm\b")

DOSE_SUSPEITA = re.compile(r"\b\d+[.,]0\s?(mg|g|ml|mcg|ui)\b", re.IGNORECASE)
UNIDADE_ABREVIADA = re.compile(r"(?<![\w])(\d+\s?U\b|µg|(?<![m])ug\b)")
ZERO_AUSENTE = re.compile(r"(?<![\d,.])\,\d+\s?(mg|g|ml|mcg)\b", re.IGNORECASE)


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def detectar_template(corpo_norm: str) -> str:
    """Escolhe o template cujas secoes obrigatorias mais aparecem no texto."""
    melhor, melhor_score = "soap", -1.0
    for nome, secoes in TEMPLATES.items():
        achadas = sum(1 for s in secoes if s in corpo_norm)
        score = achadas / len(secoes)
        # desempate: template mais especifico (mais secoes) ganha
        if score > melhor_score or (score == melhor_score and len(secoes) > len(TEMPLATES[melhor])):
            melhor, melhor_score = nome, score
    return melhor


class Relatorio:
    def __init__(self) -> None:
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def erro(self, msg: str) -> None:
        self.erros.append(msg)

    def aviso(self, msg: str) -> None:
        self.avisos.append(msg)

    def imprimir(self, arquivo: Path, template: str) -> int:
        print(f"Validando: {arquivo}")
        print(f"Template detectado: {template}\n")

        if self.erros:
            print(f"ERROS ({len(self.erros)}) — corrija antes de entregar:")
            for e in self.erros:
                print(f"  ✗ {e}")
            print()

        if self.avisos:
            print(f"AVISOS ({len(self.avisos)}) — confirme com o médico:")
            for a in self.avisos:
                print(f"  ! {a}")
            print()

        if not self.erros and not self.avisos:
            print("Nota limpa. Segue como RASCUNHO até a validação médica.")
        elif not self.erros:
            print("Sem erros estruturais. Revise os avisos acima.")

        return 1 if self.erros else 0


def checar_secoes(corpo_norm: str, template: str, rel: Relatorio) -> None:
    for secao in TEMPLATES[template]:
        if secao not in corpo_norm:
            rel.erro(f"Seção obrigatória ausente: '{secao}'")


def checar_bloco_validacao(corpo_norm: str, template: str, rel: Relatorio) -> None:
    if template == "paciente":
        return  # resumo do paciente nao carrega o bloco de assinatura
    faltando = [t for t in BLOCO_VALIDACAO if t not in corpo_norm]
    if faltando:
        rel.erro(
            "Bloco de validação médica incompleto ou ausente "
            f"(faltam: {', '.join(faltando)}). Ver SKILL.md, passo 6."
        )


def checar_marcadores(corpo: str, rel: Relatorio) -> set[str]:
    """Verifica marcadores de incerteza e devolve os encontrados."""
    encontrados: set[str] = set()
    for bruto in MARCADOR_QUALQUER.findall(corpo):
        if MARCADOR_IGNORAR.match(bruto.strip()):
            continue
        norm = sem_acento(bruto)
        if norm in MARCADORES_VALIDOS:
            encontrados.add(norm)
        elif MARCADOR_INAUDIVEL.match(norm):
            encontrados.add("[inaudivel]")
        else:
            rel.erro(
                f"Marcador de incerteza inválido: {bruto} — use apenas "
                "[não informado], [definir com o médico] ou "
                '[inaudível: "trecho"]. Ver estilo-e-terminologia.md.'
            )
    return encontrados


def checar_pendencias(corpo: str, corpo_norm: str, marcadores: set[str], rel: Relatorio) -> None:
    if "pendencias de validacao" not in corpo_norm:
        return
    trecho = corpo_norm.split("pendencias de validacao", 1)[1]
    # corta no bloco de validacao, se houver
    trecho = trecho.split("rascunho", 1)[0]
    itens = [l for l in trecho.splitlines() if l.strip().startswith(("- [", "* [", "- ", "* "))]
    preenchidos = [i for i in itens if len(i.strip().lstrip("-*[ ]x")) > 3]
    if marcadores and not preenchidos:
        rel.erro(
            f"Há {len(marcadores)} tipo(s) de marcador de incerteza no texto, "
            "mas 'Pendências de validação' está vazia. Todo marcador gera uma pendência."
        )


def checar_placeholders(corpo: str, rel: Relatorio) -> None:
    achados = {p for p in PLACEHOLDERS_TEMPLATE.findall(corpo)}
    if achados:
        amostra = ", ".join(sorted(achados)[:5])
        rel.erro(
            f"Placeholders do template não preenchidos ({len(achados)}): {amostra}"
            + (" …" if len(achados) > 5 else "")
        )


def checar_pii(corpo: str, rel: Relatorio) -> None:
    for nome, padrao in PII_PATTERNS:
        achados = padrao.findall(corpo)
        if achados:
            rel.erro(
                f"Identificador direto exposto ({nome}): {len(achados)} ocorrência(s). "
                "Rode scripts/anonimizar.py antes de qualquer uso externo."
            )

    for linha in corpo.splitlines():
        if NASCIMENTO.search(linha) and DATA_COMPLETA.search(linha):
            rel.erro(
                "Data de nascimento completa registrada — prefira a idade em anos. "
                f"Linha: {linha.strip()[:70]}"
            )
        elif DATA_COMPLETA.search(linha) and not CONTEXTO_DATA_OK.search(linha):
            rel.aviso(
                "Data completa sem contexto clínico claro — confirme que não é "
                f"identificador. Linha: {linha.strip()[:70]}"
            )


def checar_oftalmo(corpo: str, rel: Relatorio) -> None:
    """Erros de notação oftalmológica que a transcrição costuma introduzir."""
    if EIXO_EM_MM.search(corpo):
        rel.erro(
            "Eixo de refração registrado em milímetros. Eixo é grau, de 0 a 180 — "
            "a transcrição trocou a unidade. Registre como veio e abra pendência; "
            "não converta por conta própria."
        )
    if GRAU_EM_MM.search(corpo):
        rel.erro(
            "Grau esférico ou cilíndrico em milímetros. A unidade é dioptria. "
            "Mesma origem: erro de transcrição, vira pendência."
        )


def checar_medicacao(corpo: str, rel: Relatorio) -> None:
    if DOSE_SUSPEITA.search(corpo):
        rel.aviso(
            "Dose com zero à direita (ex.: '5,0 mg') — risco de leitura como "
            "'50 mg'. Escreva sem a casa decimal."
        )
    if UNIDADE_ABREVIADA.search(corpo):
        rel.erro(
            "Unidade abreviada de risco ('U', 'µg', 'ug'). Escreva 'unidades' e 'mcg'."
        )
    if ZERO_AUSENTE.search(corpo):
        rel.erro("Dose sem zero à esquerda (ex.: ',5 mg'). Escreva '0,5 mg'.")


def console_utf8() -> None:
    """Evita UnicodeEncodeError no Windows, onde a saida redirecionada usa cp1252."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str]) -> int:
    console_utf8()
    ap = argparse.ArgumentParser(description="Valida a estrutura de uma nota clínica.")
    ap.add_argument("arquivo", type=Path, help="arquivo .md da nota")
    ap.add_argument(
        "--template",
        choices=sorted(TEMPLATES),
        help="força um template em vez de detectar",
    )
    ap.add_argument(
        "--sem-pii",
        action="store_true",
        help="pula a checagem de identificadores diretos",
    )
    args = ap.parse_args(argv)

    if not args.arquivo.is_file():
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 2

    corpo = args.arquivo.read_text(encoding="utf-8")
    if not corpo.strip():
        print(f"Arquivo vazio: {args.arquivo}", file=sys.stderr)
        return 2

    corpo_norm = sem_acento(corpo)
    template = args.template or detectar_template(corpo_norm)

    rel = Relatorio()
    checar_secoes(corpo_norm, template, rel)
    checar_bloco_validacao(corpo_norm, template, rel)
    marcadores = checar_marcadores(corpo, rel)
    checar_pendencias(corpo, corpo_norm, marcadores, rel)
    checar_placeholders(corpo, rel)
    checar_oftalmo(corpo, rel)
    checar_medicacao(corpo, rel)
    if not args.sem_pii:
        checar_pii(corpo, rel)

    return rel.imprimir(args.arquivo, template)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
