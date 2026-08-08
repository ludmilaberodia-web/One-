# Templates de documentação clínica

Todo campo sem origem na fonte recebe `[não informado]`. Campos que dependem de
decisão do médico e não foram ditos recebem `[definir com o médico]`.

---

## 1. Anamnese completa (primeira consulta)

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
