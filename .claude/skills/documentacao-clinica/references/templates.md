# Templates de documentação clínica

Todo campo sem origem na fonte recebe `[não informado]`. Campos que dependem de
decisão do médico e não foram ditos recebem `[definir com o médico]`.

A prática é **oftalmológica**: os templates 1-A, 2-A e 7 são os de uso diário.
Os genéricos abaixo deles ficam para o que não couber.

---

## 1-A. Consulta oftalmológica completa (primeira consulta)

```markdown
# Consulta oftalmológica — <dd/mm/aaaa>

**Paciente:** <iniciais>   **Idade:** <n> anos   **Sexo:** <>
**Profissão:** <>   **Modalidade:** presencial | telemedicina

## Queixa principal
<frase do paciente, entre aspas quando possível> — há <tempo>.

## História da doença atual
<início, evolução, uni ou bilateral, fatores de melhora/piora, sintomas
associados — dor, fotofobia, halos, moscas volantes, flashes, secreção,
lacrimejamento, ardor. Tratamentos já tentados e resposta.>

## Antecedentes oftalmológicos
- Uso de correção: <óculos / lente de contato / nenhum> — desde <>
- Cirurgias oculares:
- Trauma ocular:
- Oclusão ou tratamento de ambliopia na infância:
- Última consulta oftalmológica:

## Antecedentes gerais
- Comorbidades: <atenção a diabetes, hipertensão, doença autoimune, tireoide>
- Medicações em uso: <nome — dose — via — frequência>
- Alergias:
- Tabagismo:

## História familiar oftalmológica
<glaucoma, ceratocone, DMRI, descolamento de retina, catarata precoce,
estrabismo, cegueira na família.>

## Acuidade visual

| | Sem correção | Com correção | Para perto |
|---|---|---|---|
| **OD** | | | |
| **OE** | | | |

## Refração

| | Esférico | Cilíndrico | Eixo | Adição |
|---|---|---|---|---|
| **Óculos em uso** OD | | | | |
| **Óculos em uso** OE | | | | |
| **Refração atual** OD | | | | |
| **Refração atual** OE | | | | |

## Biomicroscopia

| | OD | OE |
|---|---|---|
| Pálpebras e cílios | | |
| Conjuntiva | | |
| Córnea | | |
| Câmara anterior | | |
| Íris e pupila | | |
| Cristalino | | |

## Pressão intraocular
OD <> mmHg · OE <> mmHg — <método> às <hh:mm>

## Fundoscopia

| | OD | OE |
|---|---|---|
| Meios | | |
| Papila (escavação) | | |
| Mácula | | |
| Vasos | | |
| Periferia | | |

## Exames complementares apresentados
| Exame | Data | Olho | Resultado |
|---|---|---|---|

## Hipóteses diagnósticas
1. <hipótese> — <olho> — CID-10 <código, apenas se dito pelo médico>

## Conduta
- Prescrição: <princípio ativo — concentração — olho — frequência — duração>
- Exames solicitados:
- Orientações:
- Retorno:
- Encaminhamentos:

## Pendências de validação
- [ ] <trecho incerto, contradição, termo suspeito da transcrição>
```

---

## 2-A. Retorno oftalmológico (SOAP)

```markdown
# Retorno — <dd/mm/aaaa>

**Paciente:** <identificador>   **Última consulta:** <dd/mm/aaaa>

## S — Subjetivo
<evolução desde a última consulta, adesão ao colírio, efeitos adversos
— ardor, hiperemia, sabor amargo —, novas queixas visuais.>

## O — Objetivo
- Acuidade visual: OD <> · OE <> (com correção)
- Pressão intraocular: OD <> mmHg · OE <> mmHg às <hh:mm>
- Biomicroscopia dirigida:
- Fundoscopia dirigida:
- Exames desde a última consulta:

## A — Avaliação
<interpretação verbalizada pelo médico: controlado / não controlado,
progressão, resposta ao tratamento.>

## P — Plano
- Manter / ajustar / suspender colírio:
- Novos exames:
- Orientações:
- Retorno:

## Pendências de validação
- [ ]
```

---

## 7. Avaliação pré-operatória (catarata ou refrativa)

```markdown
# Avaliação pré-operatória — <procedimento> — <dd/mm/aaaa>

**Paciente:** <identificador>   **Olho a operar:** <OD | OE | AO>
**Motivação do paciente:** <queixa funcional, expectativa declarada>

## Refração e acuidade
<tabela como no template 1-A.>

## Exames pré-operatórios
| Exame | Data | OD | OE |
|---|---|---|---|
| Ceratometria | | | |
| Biometria / comprimento axial | | | |
| Paquimetria | | | |
| Topografia / Pentacam | | | |
| Contagem endotelial | | | |
| OCT de mácula | | | |

## Achados relevantes ao planejamento
<astigmatismo corneano, olho seco, distrofia, suspeita de ceratocone,
pseudoexfoliação, pupila, câmara rasa, alteração macular.>

## Lente ou técnica planejada
<LIO: modelo, poder, tipo — monofocal, tórica, multifocal | técnica refrativa>
<cálculo e fórmula usada, se verbalizados.>

## Expectativa alinhada com o paciente
<o que foi explicado sobre resultado esperado, necessidade de óculos para
perto, halos, tempo de recuperação.>

## Riscos explicados
<registrar o que foi efetivamente dito na consulta.>

## Pendências de validação
- [ ]
```

---

## 1. Anamnese completa (primeira consulta) — genérico

```markdown
# Anamnese — <especialidade>

**Paciente:** <iniciais ou identificador>   **Idade:** <n> anos   **Sexo:** <>
**Data do atendimento:** <dd/mm/aaaa>   **Modalidade:** presencial | telemedicina

## Queixa principal
<frase do paciente, entre aspas quando possível> — há <tempo>.

## História da doença atual
<narrativa cronológica: início, evolução, fatores de melhora/piora, sintomas
associados, tratamentos já tentados e resposta.>

## História patológica pregressa
- Comorbidades:
- Cirurgias:
- Internações:
- Alergias:
- Medicações em uso: <nome — dose — via — frequência>

## História familiar
## História social e hábitos
Tabagismo / etilismo / atividade física / ocupação / suporte familiar / sono.

## Revisão de sistemas
<apenas os sistemas efetivamente perguntados.>

## Exame físico
- Sinais vitais: PA <> mmHg | FC <> bpm | FR <> irpm | Tax <> °C | SatO2 <> % | Peso <> kg | Altura <> m | IMC <>
- Geral:
- Segmentar: <apenas o examinado.>

## Exames complementares apresentados
| Exame | Data | Resultado |
|---|---|---|

## Hipóteses diagnósticas
1. <hipótese> — CID-10 <código, apenas se dito pelo médico>

## Conduta
- Prescrição:
- Exames solicitados:
- Orientações:
- Retorno:
- Encaminhamentos:

## Pendências de validação
- [ ] <trecho incerto, contradição ou dado ilegível>
```

---

## 2. Evolução SOAP (retorno)

```markdown
# Evolução — <dd/mm/aaaa>

**Paciente:** <identificador>   **Consulta nº:** <> (última em <dd/mm/aaaa>)

## S — Subjetivo
<relato do paciente desde a última consulta: evolução dos sintomas, adesão ao
tratamento, efeitos adversos, novas queixas.>

## O — Objetivo
- Sinais vitais:
- Exame físico dirigido:
- Exames desde a última consulta:

## A — Avaliação
<interpretação verbalizada pelo médico: quadro controlado/não controlado,
mudança de hipótese, resposta ao tratamento.>

## P — Plano
- Manter / ajustar / suspender:
- Novos exames:
- Orientações:
- Retorno:

## Pendências de validação
- [ ]
```

---

## 3. SOAP enxuto (consulta rápida / pronto atendimento)

```markdown
# Atendimento — <dd/mm/aaaa hh:mm>

**S:** <queixa e história em até 4 linhas>
**O:** <vitais + achados relevantes>
**A:** <hipótese principal>
**P:** <conduta imediata + destino: alta, observação, internação, retorno>

**Sinais de alarme orientados:** <o que traz o paciente de volta>

## Pendências de validação
- [ ]
```

---

## 4. Carta de encaminhamento

```markdown
# Encaminhamento para <especialidade>

**De:** Dr(a). <nome> — CRM <>
**Para:** <especialidade / serviço>
**Data:** <dd/mm/aaaa>

Prezado(a) colega,

Encaminho <identificação mínima do paciente>, <idade> anos, para avaliação de
<motivo objetivo>.

**Resumo do caso:** <história relevante, condensada.>
**Comorbidades e medicações em uso:** <>
**Exames já realizados:** <com datas e resultados.>
**Hipótese diagnóstica:** <>
**Motivo específico do encaminhamento:** <a pergunta que se quer respondida.>

Permaneço à disposição.
```

---

## 5. Relatório de alta / fim de acompanhamento

```markdown
# Relatório de alta — <dd/mm/aaaa>

**Período de acompanhamento:** <dd/mm/aaaa> a <dd/mm/aaaa>
**Diagnóstico(s):** <>
**Resumo da evolução:** <>
**Tratamento realizado:** <>
**Situação na alta:** <>
**Orientações e seguimento:** <>
**Medicações mantidas:** <nome — dose — via — frequência — duração>
```

---

## 6. Resumo para o paciente

Linguagem de 6ª série, segunda pessoa, frases curtas. Sem CID, sem sigla, sem
termo técnico não explicado.

```markdown
# O que conversamos hoje — <dd/mm/aaaa>

## O que está acontecendo
<explicação em 3-4 frases.>

## O que você vai fazer
| O quê | Como | Quando |
|---|---|---|

## Seus remédios
| Remédio | Para quê | Quanto | Quando |
|---|---|---|---|

## Quando procurar ajuda agora
- <sinal de alarme concreto>

## Seu retorno
<data ou "a combinar"> — traga: <exames, cartão, lista de remédios>
```

---

## Bloco de validação (obrigatório em todos)

```markdown
---
**RASCUNHO — requer validação médica.**
Gerado por assistente de IA a partir de <fonte>. Nenhum conteúdo foi verificado
clinicamente. O médico responsável deve revisar, corrigir e assinar antes de
qualquer uso, arquivamento ou comunicação.

Médico responsável: ____________________  CRM: __________
Data/hora da validação: ____/____/______  ____:____
```
