# Estilo e terminologia

## Voz e tempo

- Terceira pessoa: "Refere dor…" e não "Você refere dor…" nem "Eu observei…".
- Pretérito para o relato ("refere que iniciou há 3 dias"), presente para o
  achado atual ("apresenta edema em membros inferiores").
- Sem juízo de valor. Descreva o observável:
  - ✗ "paciente não aderente" → ✓ "refere ter interrompido a medicação há 2
    semanas por conta própria"
  - ✗ "paciente ansioso e difícil" → ✓ "chora durante a consulta; interrompe a
    anamnese repetidamente"
  - ✗ "obeso mórbido" → ✓ "IMC 41 kg/m²"

## Fala do paciente

Cite literal quando a formulação importa (dor, sintoma psíquico, evento
sentinela): `Refere "uma dor que aperta e sobe pro braço".` Parafraseie quando a
fala é longa e sem carga diagnóstica.

Fala de acompanhante entra identificada: `Mãe refere que…`. Nunca funda os dois
relatos.

## Notação oftalmológica

A prática é oftalmológica. Estas convenções valem antes das gerais.

**Olhos.** `OD` (direito), `OE` (esquerdo), `AO` (ambos). Toda medida carrega o
olho. Se a fonte não disser de qual olho é um valor, **não distribua**: escreva
`[não informado]` no olho faltante e abra pendência. Acuidade sem olho é
acuidade inútil.

**Acuidade visual.** Longe em Snellen (`20/20`, `20/40`), perto em Jaeger
(`J1`, `J3`). Sempre diga se é com ou sem correção: `AV c/c OD 20/20`.

**Refração.** Formato fixo, nesta ordem:

```
OD −2,00 −0,75 × 180°   adição +1,75
OE −1,75 −0,50 × 005°
```

Esférico e cilíndrico em **dioptrias**, eixo em **graus de 0 a 180**. O eixo
leva `°`, nunca `mm`. Transcrição que trouxer "milímetros" num eixo ou num grau
está errada — registre o valor e abra pendência, não converta por conta própria.

**Pressão intraocular.** `PIO OD 16 mmHg · OE 15 mmHg às 12h`. O horário importa
em glaucoma; se foi dito, registre.

**Escavação.** Relação escavação/disco em decimal: `E/D 0,3`.

**Colírios.** Princípio ativo — concentração — olho — frequência — duração:

```
Latanoprosta 0,005% — OE — 1 gota à noite — uso contínuo
Moxifloxacino 0,5% — AO — 1 gota 4x/dia — 7 dias
```

Nome comercial só quando o médico o usou e a marca importa. Nesse caso:
`princípio ativo (Nome®)`. Lubrificante é o caso em que a marca costuma importar
na prática — registre a que foi dita.

**Termos a conferir.** A transcrição vem com uma tabela "Termos a conferir" ao
final quando o detector achou palavras parecidas com vocabulário oftalmológico.
**Cada linha dessa tabela vira uma pendência na nota.** Nunca adote a sugestão
como se fosse o que foi dito — ela é uma hipótese do detector, não do médico.

## Abreviações

**Livres em oftalmologia:** OD, OE, AO, AV, PIO, E/D, LIO, DMRI, PRK, LASIK,
OCT, BUT, GPAA, c/c (com correção), s/c (sem correção).

**Livres em geral:** HAS, DM1, DM2, DPOC, IAM, AVC, ICC, IRC, PA, FC, FR, Tax,
SatO2, IMC, HDA, HPP, MMII, MMSS, VO, IM, EV, SC, SN, ACM, CID-10.

**Escreva por extenso na primeira ocorrência** qualquer outra sigla, com a
abreviação entre parênteses: `insuficiência cardíaca com fração de ejeção
reduzida (ICFEr)`.

**Nunca abrevie** (risco de erro grave de medicação): unidade → escreva
`unidades`, nunca `U`; microgramas → `mcg`, nunca `µg` ou `ug`; zero à esquerda
sempre (`0,5 mg`), zero à direita nunca (`5 mg`, não `5,0 mg`).

## Medicações

Formato fixo: **princípio ativo — dose — via — frequência — duração**.

```
Losartana potássica — 50 mg — VO — 12/12h — uso contínuo
Amoxicilina + clavulanato — 875/125 mg — VO — 12/12h — 7 dias
```

Nome comercial só quando o médico o usou e a troca importa (medicamentos de
janela terapêutica estreita, biológicos). Nesse caso: `princípio ativo
(Nome®)`.

## Números e unidades

| Medida | Formato |
|---|---|
| Pressão arterial | `120/80 mmHg` |
| Frequência cardíaca | `72 bpm` |
| Frequência respiratória | `16 irpm` |
| Temperatura | `36,8 °C` |
| Saturação | `SatO2 97% em ar ambiente` |
| Peso / altura | `78 kg` / `1,72 m` |
| Glicemia | `142 mg/dL` |
| Tempo de sintoma | `há 3 dias`, `há 2 meses` — nunca "recentemente" |

Vírgula decimal (padrão pt-BR). Converta a fala ("doze por oito") só quando a
unidade for inequívoca no contexto; caso contrário cite literal e marque
pendência.

## Marcadores de incerteza

Use exatamente estes três — o validador reconhece só eles:

- `[não informado]` — o dado não apareceu na fonte.
- `[definir com o médico]` — depende de decisão que não foi verbalizada.
- `[inaudível: "trecho aproximado"]` — a fonte estava ininteligível.

Todo marcador usado gera uma linha correspondente em **Pendências de validação**.

## CID-10

Só registre código CID quando o médico enunciou o código ou o diagnóstico
nominal fechado. Nunca derive código a partir de sintomas.

## O que não entra no prontuário

Conversa social, opinião sobre o paciente, dados de terceiros ouvidos por acaso,
comentário sobre outros profissionais, ruído da transcrição, e qualquer
especulação diagnóstica que o médico não tenha verbalizado.
