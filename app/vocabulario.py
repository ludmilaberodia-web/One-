"""Vocabulario de oftalmologia para a transcricao.

Duas listas com funcoes diferentes:

HOTWORDS  vai para dentro do motor de transcricao e enviesa o reconhecimento.
          O orcamento e de ~220 tokens, truncado sem aviso -- cerca de 60
          palavras. Entra so o que e dito em quase toda consulta E que o
          motor erra. Lista longa aqui nao ajuda: atrapalha.

TERMOS    fica fora do motor, sem limite de tamanho, e serve ao detector de
          termos suspeitos: palavras que chegaram parecidas com um termo
          conhecido mas nao iguais.

O detector **nunca** troca palavra. Ele marca para o medico conferir. Trocar
em silencio e exatamente o erro que este projeto existe para evitar: uma dose
ou um colirio trocado sem ninguem perceber.

Para acrescentar os seus proprios termos sem mexer em codigo, crie o arquivo
`vocabulario-local.txt` na raiz do projeto, um termo por linha. Ele nao vai
para o controle de versao.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOCAL = RAIZ / "vocabulario-local.txt"

# ---------------------------------------------------------------------------
# O que vai para o motor. Cabe ~60 palavras: escolha, nao catalogo.
# ---------------------------------------------------------------------------

HOTWORDS = (
    "acuidade visual, biomicroscopia, fundoscopia, tonometria, refração, "
    "dioptrias, esférico, cilíndrico, eixo, adição, presbiopia, miopia, "
    "hipermetropia, astigmatismo, catarata, glaucoma, ceratocone, "
    "olho seco, conjuntiva, córnea, câmara anterior, cristalino, mácula, "
    "papila, escavação, retina, nervo óptico, pressão intraocular, "
    "Pentacam, topografia, paquimetria, OCT, campimetria, gonioscopia, "
    "Systane, Hyabak, Lacrifilm, Optive, Refresh, latanoprosta, timolol, "
    "dorzolamida, brimonidina, moxifloxacino, prednisolona, olopatadina, "
    "facoemulsificação, PRK, LASIK, crosslinking, lente intraocular, "
    "olho direito, olho esquerdo, ambos os olhos"
)

# ---------------------------------------------------------------------------
# Catalogo completo, para deteccao. Pode crescer a vontade.
# ---------------------------------------------------------------------------

EXAMES = """
acuidade visual, refração, refratometria, autorrefração, biomicroscopia,
fundoscopia, oftalmoscopia, tonometria, paquimetria, gonioscopia,
ceratometria, topografia, tomografia de córnea, Pentacam, OCT,
tomografia de coerência óptica, campimetria, campo visual, retinografia,
angiofluoresceinografia, ecobiometria, biometria, microscopia especular,
teste de Schirmer, tempo de ruptura do filme lacrimal, BUT, cover test,
teste de Ishihara, mapeamento de retina, ultrassonografia ocular,
aberrometria, pupilometria, meibografia, Belin Ambrósio
"""

ESTRUTURAS = """
conjuntiva, esclera, córnea, epitélio corneano, estroma, endotélio, limbo,
câmara anterior, ângulo iridocorneano, íris, pupila, cristalino, cápsula
posterior, zônula, corpo ciliar, vítreo, retina, mácula, fóvea, papila,
disco óptico, escavação, nervo óptico, coroide, pálpebra, menisco lacrimal,
glândulas de Meibomius, ponto lacrimal, saco lacrimal, músculo reto medial,
músculo reto lateral, filme lacrimal
"""

DIAGNOSTICOS = """
presbiopia, miopia, hipermetropia, astigmatismo, anisometropia, ambliopia,
estrabismo, esotropia, exotropia, catarata, catarata nuclear, catarata
cortical, catarata subcapsular, glaucoma, glaucoma primário de ângulo
aberto, glaucoma de ângulo fechado, hipertensão ocular, ceratocone,
degeneração marginal pelúcida, olho seco, disfunção de glândulas de
Meibomius, blefarite, pterígio, pinguécula, conjuntivite, ceratite,
úlcera de córnea, uveíte, irite, episclerite, esclerite, calázio, hordéolo,
degeneração macular relacionada à idade, DMRI, retinopatia diabética,
edema macular, oclusão de veia central, descolamento de retina, rasgadura
retiniana, membrana epirretiniana, buraco macular, neurite óptica,
retinose pigmentar, ptose palpebral, entrópio, ectrópio, dacriocistite,
opacificação de cápsula posterior, distrofia de Fuchs, olho vermelho
"""

CIRURGIAS = """
facectomia, facoemulsificação, extração extracapsular, lente intraocular,
LIO, LIO multifocal, LIO tórica, LIO monofocal, lente fácica, PRK, LASIK,
SMILE, crosslinking, anel intraestromal, ceratoplastia, transplante de
córnea, DSAEK, DMEK, trabeculectomia, implante de drenagem, iridotomia,
SLT, trabeculoplastia, vitrectomia, retinopexia, capsulotomia,
YAG laser, fotocoagulação, panfotocoagulação, injeção intravítrea,
antiangiogênico, blefaroplastia, dacriocistorrinostomia
"""

MEDICAMENTOS = """
Systane, Hyabak, Lacrifilm, Optive, Refresh, Fresh Tears, Lacrima,
Hylo Comod, Artelac, Genteal, Ecofilm, Trehalose, ciclosporina, Restasis,
Ikervis, soro autólogo, lágrima artificial, cloridrato de dorzolamida,
timolol, maleato de timolol, brimonidina, latanoprosta, bimatoprosta,
travoprosta, tafluprosta, brinzolamida, acetazolamida, Cosopt, Combigan,
Azorga, DuoTrav, Xalatan, Lumigan, Travatan, Alphagan, Trusopt,
moxifloxacino, Vigamox, tobramicina, ciprofloxacino, ofloxacino,
gatifloxacino, azitromicina, prednisolona, Pred Fort, dexametasona,
fluormetolona, loteprednol, Maxitrol, Tobradex, ketorolaco, nepafenaco,
bromfenaco, Acular, Nevanac, olopatadina, Patanol, cetotifeno, epinastina,
azelastina, Lastacaft, aciclovir, ganciclovir, natamicina, anfotericina,
atropina, tropicamida, fenilefrina, ciclopentolato, proparacaína,
colírio anestésico, bevacizumabe, ranibizumabe, aflibercepte, Avastin,
Lucentis, Eylia
"""

NOTACAO = """
olho direito, olho esquerdo, ambos os olhos, acuidade visual sem correção,
acuidade visual com correção, visão para perto, visão para longe,
dioptrias, grau esférico, grau cilíndrico, eixo, adição, equivalente
esférico, pressão intraocular, milímetros de mercúrio, relação escavação
disco, sem correção, com correção, fundo de olho, meios transparentes,
reflexo pupilar, fotomotor, consensual
"""


def _limpar(bloco: str) -> list[str]:
    return [t.strip() for t in bloco.replace("\n", " ").split(",") if t.strip()]


TERMOS: list[str] = (
    _limpar(EXAMES)
    + _limpar(ESTRUTURAS)
    + _limpar(DIAGNOSTICOS)
    + _limpar(CIRURGIAS)
    + _limpar(MEDICAMENTOS)
    + _limpar(NOTACAO)
)

# ---------------------------------------------------------------------------
# Confusoes ja observadas em atendimento real. Cada uma entrou aqui porque
# aconteceu, nao porque parecia provavel.
# ---------------------------------------------------------------------------

CONFUSOES = {
    "cistaneo": "Systane",
    "sistaneo": "Systane",
    "cistane": "Systane",
    "iabac": "Hyabak",
    "hiabac": "Hyabak",
    "iabaque": "Hyabak",
    "capila": "papila",
    "capilar fisiologica": "papila fisiológica",
    "facica": "fácica",
    "lacrifim": "Lacrifilm",
    "pentacan": "Pentacam",
    "pentaca": "Pentacam",
    "optive": "Optive",
    "cross linking": "crosslinking",
    "lasic": "LASIK",
    "perecer": "PRK",
    "pe erre ka": "PRK",
}

# Palavras comuns que nao devem ser comparadas com o catalogo.
IGNORAR = {
    "paciente", "consulta", "retorno", "exame", "exames", "olhos", "olho",
    "direito", "esquerdo", "ambos", "queixa", "refere", "relata", "nega",
    "usando", "usar", "usa", "sobre", "porque", "quando", "depois", "antes",
    "muito", "pouco", "melhor", "pior", "mesmo", "ainda", "agora", "então",
    "também", "apenas", "cada", "todos", "todas", "outro", "outra", "pode",
    "fazer", "fazendo", "vamos", "vai", "tem", "está", "estão", "seria",
}

PALAVRA = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]{3,}")


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def carregar_locais() -> list[str]:
    """Termos que a médica acrescentou em vocabulario-local.txt."""
    if not LOCAL.is_file():
        return []
    linhas = LOCAL.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in linhas if l.strip() and not l.lstrip().startswith("#")]


def hotwords() -> str:
    """O que vai para o motor, com os termos locais na frente.

    Na frente de propósito: se o truncamento cortar, corta o genérico e
    preserva o que esta médica de fato usa.
    """
    locais = carregar_locais()
    if not locais:
        return HOTWORDS
    return ", ".join(locais) + ", " + HOTWORDS


def catalogo() -> list[str]:
    return TERMOS + carregar_locais()


def suspeitos(texto: str, corte: float = 0.78) -> list[tuple[str, str]]:
    """Palavras parecidas com um termo do catálogo, mas diferentes dele.

    Devolve pares (como veio, termo provável), sem repetição e na ordem em
    que aparecem. Nada é trocado no texto — isso é decisão do médico.
    """
    catalogo_termos = catalogo()
    # Só termos de uma palavra entram na comparação difusa; os compostos
    # ("câmara anterior") não casam contra palavra solta.
    simples = {sem_acento(t): t for t in catalogo_termos if " " not in t}
    conhecidos = set(simples)

    achados: list[tuple[str, str]] = []
    # Guarda a palavra como ela chegou, não o termo sugerido: é o que impede a
    # busca difusa de reencontrar o que a lista de confusões já apontou.
    vistos: set[str] = set()

    texto_norm = sem_acento(texto)
    # Da mais longa para a mais curta: "cistaneo" precisa ganhar de "cistane",
    # senão as duas entradas disparam no mesmo trecho.
    for expressao in sorted(CONFUSOES, key=len, reverse=True):
        if expressao not in texto_norm:
            continue
        if any(expressao in ja for ja in vistos):
            continue
        achados.append((expressao, CONFUSOES[expressao]))
        vistos.add(expressao)

    for bruto in PALAVRA.findall(texto):
        chave = sem_acento(bruto)
        if chave in conhecidos or chave in IGNORAR or chave in vistos:
            continue
        # Uma confusão de várias palavras já cobriu esta? ("capilar fisiologica")
        if any(chave in expressao.split() for expressao in vistos):
            continue
        perto = difflib.get_close_matches(chave, conhecidos, n=1, cutoff=corte)
        if perto:
            achados.append((bruto, simples[perto[0]]))
            vistos.add(chave)

    return achados


def relatorio(texto: str) -> str:
    """Bloco em markdown para anexar à transcrição. Vazio se não houver nada."""
    achados = suspeitos(texto)
    if not achados:
        return ""

    linhas = [
        "",
        "---",
        "",
        "## Termos a conferir",
        "",
        "Palavras que chegaram parecidas com um termo de oftalmologia, mas não",
        "iguais. **Nada foi corrigido** — confira no áudio da sua memória ou",
        "refaça a pergunta ao paciente. Cada uma destas vira pendência na nota.",
        "",
        "| Como veio | Pode ser |",
        "|---|---|",
    ]
    linhas += [f"| `{veio}` | {provavel} |" for veio, provavel in achados]
    linhas.append("")
    return "\n".join(linhas)
