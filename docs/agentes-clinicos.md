# Agentes clínicos

Suíte de agentes de IA para apoio ao atendimento médico: documentação clínica,
consulta a evidência científica e acompanhamento de pacientes. Inspirada no
modelo de assistentes clínicos como o da Voa Health.

O princípio que atravessa tudo: **o agente executa, o médico decide**. Nenhum
documento gerado aqui tem valor clínico antes da revisão e assinatura do médico
responsável.

## Os três agentes

| Agente | Faz | Não faz |
|---|---|---|
| `escriba-clinico` | Transcrição/notas → anamnese, evolução SOAP, encaminhamento, alta | Diagnosticar, prescrever, assinar |
| `evidencia-clinica` | Responde dúvidas clínicas com citação PubMed/diretriz e nível de evidência | Prescrever, decidir conduta |
| `acompanhamento-paciente` | Resumo para o paciente, plano de retorno, rascunhos de follow-up | Enviar mensagem, orientar conduta |

Definições em `.claude/agents/`. A skill de apoio — templates, regras de estilo,
conformidade e scripts — está em `.claude/skills/documentacao-clinica/`.

## Uso

O fluxo típico de um atendimento:

```
1. app/gravador.py          → grava a consulta, transcreve local, apaga o áudio
        ↓
2. escriba-clinico          → rascunho da nota clínica
        ↓
3. evidencia-clinica        → (opcional) dúvida de conduta, com citações
        ↓
4. Médico valida e assina   ← ponto de controle obrigatório
        ↓
5. acompanhamento-paciente  → resumo do paciente + plano de retorno
        ↓
6. Médico aprova os textos antes de qualquer envio
```

Invocação por linguagem natural — o agente certo é selecionado pela descrição:

```
"Estrutura essa consulta em SOAP: <cole a transcrição>"
"O que a literatura diz sobre metformina em DRC estágio 3b?"
"Monta o resumo e o plano de retorno a partir da nota validada"
```

## Captura da consulta

```bash
pip install -r app/requirements.txt   # uma vez só
python3 app/gravador.py               # abre em http://localhost:8765
```

Grava o atendimento, transcreve com Whisper **no próprio computador** e apaga o
áudio em seguida. Nada trafega pela internet. Detalhes e limites conhecidos em
[`app/README.md`](../app/README.md).

## Ferramentas

```bash
# Validar a estrutura de uma nota antes de entregar ao médico
python3 .claude/skills/documentacao-clinica/scripts/validar_nota.py nota.md

# Remover identificadores diretos antes de qualquer chamada externa
python3 .claude/skills/documentacao-clinica/scripts/anonimizar.py \
    transcricao.txt --nomes "Maria Silva" --saida limpa.txt
```

O validador checa seções obrigatórias, bloco de validação médica, marcadores de
incerteza, placeholders esquecidos, abreviações de risco em dose e
identificadores expostos. Sai com código 1 se houver erro — dá para usar em
hook ou CI.

## Conformidade

- **Validação médica obrigatória** antes de qualquer uso ou comunicação
  (Resolução CFM 2.454/2026).
- **Áudio não é armazenado**: transcreve e descarta.
- **Nada identificável sai do ambiente local** — anonimize antes de web, PubMed
  ou qualquer API.
- **Dado de saúde é dado sensível** sob a LGPD (Lei 13.709/2018, art. 5º, II).

Regras completas em
`.claude/skills/documentacao-clinica/references/seguranca-e-conformidade.md`.

## Antes do primeiro atendimento

Confirme que o `.gitignore` cobre os diretórios de trabalho — transcrição bruta,
áudio e rascunho de nota nunca entram no controle de versão. As entradas já
estão no `.gitignore` deste repositório; se você mover a suíte para outro
projeto, leve-as junto.
