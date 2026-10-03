#!/usr/bin/env python3
"""Gera os ícones do gravador: .icns para o Mac e .ico para o Windows.

Desenho: quadrado arredondado (squircle) em verde cirúrgico, com barras
brancas de alturas diferentes — o medidor de nível que aparece na própria
tela do gravador. Lê como "gravando áudio" mesmo a 16 pixels.

A variante do celular usa o mesmo desenho em azul, para as duas se
distinguirem no Dock sem precisar ler o nome.

Desenha tudo 8x maior e reduz no fim: é assim que a borda sai lisa sem
antialiasing manual.

Uso:
    python3 tools/gerar_icones.py
"""

from __future__ import annotations

import struct
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent

# Paleta compartilhada com o manual: o verde cirúrgico é o acento de lá.
PALETAS = {
    "gravador": {
        "topo": (58, 134, 115),
        "base": (26, 74, 62),
        "glifo": (255, 255, 255),
        "ponto": (229, 72, 77),  # vermelho de "gravando", como na tela
    },
    "celular": {
        "topo": (62, 120, 168),
        "base": (26, 58, 94),
        "glifo": (255, 255, 255),
        "ponto": (229, 72, 77),
    },
}

ESCALA = 2  # desenha em 2048 e reduz para 1024
LADO = 1024

# Alturas relativas das barras do medidor, de 0 a 1. Assimétrico de propósito:
# simétrico parece gráfico de barras, assimétrico parece voz.
#
# Cinco barras e não sete: a 16 pixels, sete se fundem num borrão. Largura e
# vão são frações do lado do ícone, para escalar junto.
BARRAS = [0.42, 0.74, 1.00, 0.62, 0.34]
LARG_BARRA = 0.105
VAO = 0.055


def gradiente(lado: int, topo: tuple[int, int, int], base: tuple[int, int, int]) -> Image.Image:
    """Degradê vertical, pintado linha por linha."""
    img = Image.new("RGB", (1, lado))
    pix = img.load()
    for y in range(lado):
        t = y / max(lado - 1, 1)
        pix[0, y] = tuple(round(topo[i] + (base[i] - topo[i]) * t) for i in range(3))
    return img.resize((lado, lado), Image.NEAREST)


def desenhar(nome: str) -> Image.Image:
    """Monta o ícone no tamanho máximo, já com cantos arredondados."""
    cores = PALETAS[nome]
    lado = LADO * ESCALA

    fundo = gradiente(lado, cores["topo"], cores["base"]).convert("RGBA")

    # Máscara squircle: raio de 22,5% é a proporção que o macOS usa.
    mascara = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, lado - 1, lado - 1), radius=round(lado * 0.225), fill=255
    )

    icone = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    icone.paste(fundo, (0, 0), mascara)

    desenho = ImageDraw.Draw(icone)

    # Medidor de nível, centralizado.
    larg_barra = lado * LARG_BARRA
    vao = lado * VAO
    total = len(BARRAS) * larg_barra + (len(BARRAS) - 1) * vao
    x = (lado - total) / 2
    meio = lado * 0.52  # levemente abaixo do centro: abre espaço para o ponto
    alt_max = lado * 0.42

    for fracao in BARRAS:
        altura = alt_max * fracao
        desenho.rounded_rectangle(
            (x, meio - altura / 2, x + larg_barra, meio + altura / 2),
            radius=larg_barra / 2,
            fill=cores["glifo"],
        )
        x += larg_barra + vao

    # Ponto de gravação acima do medidor.
    raio = lado * 0.052
    cx, cy = lado / 2, lado * 0.215
    desenho.ellipse((cx - raio, cy - raio, cx + raio, cy + raio), fill=cores["ponto"])

    return icone.resize((LADO, LADO), Image.LANCZOS)


# Tipos do formato .icns que aceitam PNG embutido, com o lado correspondente.
TIPOS_ICNS = [
    (b"icp4", 16),
    (b"icp5", 32),
    (b"icp6", 64),
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024),  # 512@2x
    (b"ic11", 32),    # 16@2x
    (b"ic12", 64),    # 32@2x
    (b"ic13", 256),   # 128@2x
    (b"ic14", 512),   # 256@2x
]


def escrever_icns(base: Image.Image, destino: Path) -> None:
    """Monta um .icns na mão: cabeçalho 'icns' e uma entrada PNG por tamanho.

    Evita depender do iconutil, que só existe no macOS.
    """
    blocos = bytearray()
    for tipo, lado in TIPOS_ICNS:
        buf = BytesIO()
        base.resize((lado, lado), Image.LANCZOS).save(buf, format="PNG")
        dados = buf.getvalue()
        blocos += tipo + struct.pack(">I", len(dados) + 8) + dados

    destino.write_bytes(b"icns" + struct.pack(">I", len(blocos) + 8) + bytes(blocos))


def escrever_ico(base: Image.Image, destino: Path) -> None:
    lados = [16, 24, 32, 48, 64, 128, 256]
    base.save(destino, format="ICO", sizes=[(n, n) for n in lados])


def main() -> int:
    saida = RAIZ / "assets"
    saida.mkdir(exist_ok=True)

    for nome in PALETAS:
        icone = desenhar(nome)

        png = saida / f"{nome}.png"
        icone.save(png, format="PNG")

        icns = saida / f"{nome}.icns"
        escrever_icns(icone, icns)

        ico = saida / f"{nome}.ico"
        escrever_ico(icone, ico)

        print(f"  {nome}: {png.name}, {icns.name} ({icns.stat().st_size // 1024} KB), {ico.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
