#!/usr/bin/env python3
"""Remove identificadores diretos de um texto clinico antes de qualquer uso externo.

Primeira linha de defesa, nao garantia. Nomes proprios so sao removidos se
passados explicitamente em --nomes: nenhum regex distingue "Maria" paciente de
"Maria" nome de medicacao ou de hospital.

Uso:
    python3 anonimizar.py transcricao.txt
    python3 anonimizar.py transcricao.txt --saida limpa.txt
    python3 anonimizar.py transcricao.txt --nomes "Maria Silva,Joao Souza"
    cat transcricao.txt | python3 anonimizar.py -

Saida: texto anonimizado (stdout ou --saida) + resumo do que foi removido (stderr).
Codigo 0 sempre que o processamento ocorreu; 2 em falha de uso.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Ordem importa: padroes mais especificos primeiro, para nao serem comidos
# por padroes mais gerais (CNS antes de telefone, por exemplo).
SUBSTITUICOES: list[tuple[str, re.Pattern[str], str]] = [
    ("e-mail", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), "[EMAIL]"),
    ("CPF", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    ("CNS", re.compile(r"\b[1-2]\d{2} ?\d{4} ?\d{4} ?\d{4}\b"), "[CNS]"),
    (
        "prontuário",
        re.compile(r"\b(?:prontu[áa]rio|registro|matr[íi]cula)[:\s#nº]*\d{3,}", re.IGNORECASE),
        "[PRONTUARIO]",
    ),
    ("RG", re.compile(r"\bRG[:\s]*[\d.\-]{7,}\b", re.IGNORECASE), "[RG]"),
    ("CEP", re.compile(r"\b\d{5}-?\d{3}\b"), "[CEP]"),
    (
        "endereço",
        re.compile(
            r"\b(?:rua|avenida|av\.|travessa|alameda|pra[çc]a|rodovia)\s+"
            r"[\w\sÀ-ú.]{3,40},?\s*(?:n?[ºo]?\.?\s*)?\d+[\w\s,/-]{0,20}",
            re.IGNORECASE,
        ),
        "[ENDERECO]",
    ),
    (
        "telefone",
        re.compile(r"(?<!\d)(?:\+55\s?)?\(?\d{2}\)?[\s.-]?9?\d{4}[-.\s]?\d{4}(?!\d)"),
        "[TELEFONE]",
    ),
    (
        "data de nascimento",
        re.compile(
            r"(nascimento|nasceu em|nascid[ao] em|DN)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            re.IGNORECASE,
        ),
        r"\1: [DATA_NASC]",
    ),
    ("placa", re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b"), "[PLACA]"),
]


def montar_padrao_nomes(nomes: list[str]) -> re.Pattern[str] | None:
    """Casa o nome completo e cada parte dele com >=3 letras, isolada."""
    partes: set[str] = set()
    for nome in nomes:
        nome = nome.strip()
        if not nome:
            continue
        partes.add(nome)
        for pedaco in nome.split():
            if len(pedaco) >= 3 and pedaco.lower() not in {"dos", "das", "der", "van"}:
                partes.add(pedaco)
    if not partes:
        return None
    # nomes compostos primeiro, para substituir "Maria Silva" antes de "Maria"
    alternativas = sorted(partes, key=len, reverse=True)
    return re.compile(
        r"\b(?:" + "|".join(re.escape(p) for p in alternativas) + r")\b",
        re.IGNORECASE,
    )


def anonimizar(texto: str, nomes: list[str]) -> tuple[str, Counter[str]]:
    contagem: Counter[str] = Counter()

    padrao_nomes = montar_padrao_nomes(nomes)
    if padrao_nomes is not None:
        texto, n = padrao_nomes.subn("[NOME]", texto)
        if n:
            contagem["nome"] += n

    for rotulo, padrao, troca in SUBSTITUICOES:
        texto, n = padrao.subn(troca, texto)
        if n:
            contagem[rotulo] += n

    return texto, contagem


def console_utf8() -> None:
    """Evita UnicodeEncodeError no Windows, onde a saida redirecionada usa cp1252."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str]) -> int:
    console_utf8()
    ap = argparse.ArgumentParser(
        description="Remove identificadores diretos de texto clínico (LGPD)."
    )
    ap.add_argument("arquivo", help="arquivo de entrada, ou '-' para stdin")
    ap.add_argument("--saida", type=Path, help="arquivo de saída (padrão: stdout)")
    ap.add_argument(
        "--nomes",
        default="",
        help="nomes próprios a remover, separados por vírgula "
        "(regex não detecta nomes sozinho)",
    )
    args = ap.parse_args(argv)

    if args.arquivo == "-":
        texto = sys.stdin.read()
    else:
        caminho = Path(args.arquivo)
        if not caminho.is_file():
            print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
            return 2
        texto = caminho.read_text(encoding="utf-8")

    nomes = [n for n in args.nomes.split(",") if n.strip()]
    limpo, contagem = anonimizar(texto, nomes)

    if args.saida:
        args.saida.write_text(limpo, encoding="utf-8")
        print(f"Escrito em: {args.saida}", file=sys.stderr)
    else:
        sys.stdout.write(limpo)

    if contagem:
        print("\nRemovido:", file=sys.stderr)
        for rotulo, n in sorted(contagem.items(), key=lambda kv: -kv[1]):
            print(f"  {rotulo}: {n}", file=sys.stderr)
    else:
        print("\nNenhum identificador direto encontrado.", file=sys.stderr)

    if not nomes:
        print(
            "\nAviso: nenhum nome informado em --nomes. Nomes próprios NÃO foram "
            "removidos. Revise a saída manualmente antes de qualquer uso externo.",
            file=sys.stderr,
        )
    else:
        print(
            "\nAviso: anonimização automática é primeira linha de defesa, não "
            "garantia. Revise a saída — combinação de doença rara, idade e local "
            "pode reidentificar mesmo sem nome.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
