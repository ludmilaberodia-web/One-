---
name: documentacao-clinica
description: Estrutura atendimentos médicos em documentação clínica válida — anamnese, evolução SOAP, resumo para paciente, encaminhamento — a partir de transcrição ou notas. Use sempre que houver transcrição de consulta, ditado do médico, notas de atendimento, ou pedidos como "montar prontuário", "gerar evolução", "estruturar a consulta", "resumo do atendimento". Inclui templates, regras de anonimização (LGPD) e validador automático da nota.
---

# Documentação clínica

Transformar o que aconteceu na consulta em documento clínico correto, rastreável
e pronto para o médico validar e assinar.

## Antes de tudo: o contrato

O documento que você produz é **rascunho até o médico validar**. Três regras
carregam o resto:

1. **Nada de invenção.** Sem origem na fonte, escreve-se `[não informado]`.
2. **Nada sai daqui.** Nenhum dado identificável de paciente vai para busca,
   API, web ou qualquer serviço externo — anonimize antes.
3. **Nada é definitivo.** Todo arquivo entregue termina com o bloco de validação
   assinado pelo médico.

## Passo a passo

### 1. Classifique o atendimento

A prática é **oftalmológica**. Os três primeiros cobrem o dia a dia:

| Situação | Template |
|---|---|
| Primeira consulta | **1-A** Consulta oftalmológica completa |
| Retorno / evolução | **2-A** Retorno oftalmológico (SOAP) |
| Pré-operatório de catarata ou refrativa | **7** Avaliação pré-operatória |
| Encaminhamento a outra especialidade | Carta de encaminhamento |
| Alta / fim de acompanhamento | Relatório de alta |
| Consulta fora da oftalmologia | Anamnese completa ou SOAP genéricos |

Templates completos em `references/templates.md`.

### 2. Extraia antes de redigir

Passe a fonte inteira uma vez e separe em quatro baldes, sem redigir ainda:

- **Subjetivo** — o que o paciente relata (queixa, história, sintomas,
  contexto de vida, medo).
- **Objetivo** — o que foi medido ou observado (sinais vitais, exame físico,
  resultado de exame lido em voz alta).
- **Avaliação** — o raciocínio que o médico verbalizou (hipóteses, diagnóstico,
  diferencial descartado).
- **Plano** — o que foi decidido (prescrição, exame, retorno, orientação,
  encaminhamento).

Frase que não cai em nenhum balde (conversa social, ruído, interrupção) é
descartada. Frase que cabe em dois: escolha o balde da intenção do falante.

### 2.5 Leia a tabela "Termos a conferir"

A transcrição vem com essa tabela ao final quando o detector achou palavras
parecidas com vocabulário oftalmológico. **Cada linha vira uma pendência.** A
sugestão é hipótese de software — o corpo da nota mantém o que foi dito, marcado
como inaudível. Detalhes em `references/estilo-e-terminologia.md`.

### 3. Trate as armadilhas da transcrição

- **Autocorreção**: "toma 40… 400mg" → vale 400mg, e a divergência vai em
  Pendências.
- **Homófonos clínicos**: hipo/hiper, -emia/-úria, mg/mcg, "dipirona"/"dapagliflozina"
  em áudio ruim. Se houver dúvida, cite literal e marque pendência — nunca
  escolha a mais provável em silêncio.
- **Números soltos** ("ficou em doze por oito") → normalize para `120/80 mmHg`
  apenas quando a unidade for inequívoca no contexto.
- **Negação implícita**: "sem febre" é achado registrável; silêncio sobre febre
  não é. Não transforme ausência de menção em negativa.
- **Terceiros na sala**: fala de acompanhante entra identificada ("mãe refere…").

### 4. Redija

Português clínico: terceira pessoa, pretérito para o relato, presente para
achado atual. Sem juízo de valor sobre o paciente — descreva o comportamento,
não o rotule. Abreviações apenas as consagradas (`HAS`, `DM2`, `PA`, `FC`); na
primeira ocorrência de qualquer outra, escreva por extenso.

Detalhes em `references/estilo-e-terminologia.md`.

### 5. Valide

```bash
python3 .claude/skills/documentacao-clinica/scripts/validar_nota.py nota.md
```

O validador checa seções obrigatórias, rodapé de validação, marcadores de
incerteza mal formados e padrões de dado sensível exposto. Ele **não** julga
conteúdo clínico — isso é do médico. Corrija e rode até sair limpo.

### 6. Entregue

Sempre com o bloco final:

```
---
**RASCUNHO — requer validação médica.**
Gerado por assistente de IA a partir de <fonte>. Nenhum conteúdo foi
verificado clinicamente. O médico responsável deve revisar, corrigir e assinar
antes de qualquer uso, arquivamento ou comunicação.

Médico responsável: ____________________  CRM: __________
Data/hora da validação: ____/____/______  ____:____
```

## Anonimização — quando e como

Precisa anonimizar sempre que o texto for sair do contexto local: busca na web,
consulta a PubMed, chamada de API, exemplo colado em documentação, issue de bug.

```bash
python3 .claude/skills/documentacao-clinica/scripts/anonimizar.py entrada.txt --saida saida.txt
```

Remove CPF, CNS, telefone, e-mail, CEP, datas de nascimento, RG e números de
prontuário. **Nomes próprios ele não pega sozinho** — passe-os explicitamente com
`--nomes "Maria Silva,João Souza"`. Revise a saída antes de usar: anonimização
automática é primeira linha de defesa, não garantia.

## Conformidade

Regras de LGPD, CFM 2.454/2026, retenção de áudio e limites de uso estão em
`references/seguranca-e-conformidade.md`. Leia antes de qualquer fluxo que
envolva armazenamento, envio ao paciente ou integração com prontuário
eletrônico.

## Referências

- `references/templates.md` — todos os modelos de documento
- `references/estilo-e-terminologia.md` — como escrever, o que abreviar
- `references/seguranca-e-conformidade.md` — LGPD, CFM, dados sensíveis
- `scripts/validar_nota.py` — validador estrutural
- `scripts/anonimizar.py` — remoção de identificadores diretos
