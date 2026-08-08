# Segurança e conformidade

Dado de saúde é **dado pessoal sensível** (LGPD, Lei 13.709/2018, art. 5º, II).
O tratamento indevido gera responsabilidade do médico e da clínica, não do
software. As regras abaixo são obrigatórias, não sugestões.

## 1. Validação médica é obrigatória

Nenhum conteúdo gerado por IA vale como documento clínico antes da revisão e
assinatura do médico responsável. Isso vale para prontuário, receita, atestado,
laudo, encaminhamento e **qualquer mensagem enviada ao paciente**.

Consequência prática: todo arquivo produzido nasce marcado como `RASCUNHO` com o
bloco de validação. O assistente nunca remove essa marcação por conta própria —
quem remove é o médico, ao validar.

O assistente não emite documento com assinatura digital, não simula CRM e não
preenche campo de assinatura.

## 2. Áudio não se armazena

Se o fluxo envolver gravação:

- O áudio é transcrito e descartado ao final do processamento.
- Nenhum arquivo de áudio é commitado, copiado para diretório persistente ou
  anexado a issue/PR.
- A transcrição bruta é tratada como dado sensível: fica fora do repositório e
  é apagada quando a nota validada existir.

Consentimento do paciente para gravação é responsabilidade do médico e deve ser
registrado antes do início.

## 3. Nada identificável sai do ambiente local

Antes de qualquer chamada externa — busca na web, PubMed, API de terceiros,
exemplo em documentação, mensagem de erro em issue — o texto passa por
`scripts/anonimizar.py`.

Identificadores diretos a remover: nome completo, CPF, RG, CNS, número de
prontuário, e-mail, telefone, endereço, CEP, data de nascimento, nome de
familiares, placa, matrícula, foto.

Ao consultar evidência sobre um caso, descreva-o genericamente: "homem, ~60
anos, DM2 e DRC estágio 3" — nunca "o Sr. José, 62 anos, prontuário 44821".

Atenção à reidentificação: a combinação de doença rara + cidade pequena + idade
exata identifica mesmo sem nome. Nesses casos, generalize também idade e local.

## 4. Minimização

Registre o clinicamente pertinente e só isso. Informação sobre vida sexual,
religião, uso de substâncias, situação migratória ou violência doméstica entra
apenas quando relevante para o cuidado — e com a mesma discrição no resumo do
paciente, que pode ser lido por terceiros em casa.

## 5. Comunicação com o paciente

- Canal aberto (SMS, WhatsApp) não carrega diagnóstico, resultado de exame nem
  CID sem aprovação explícita do médico para aquele texto específico.
- Lembretes usam formulação neutra: "você tem retorno na quinta às 14h" — não
  "sua consulta de oncologia".
- Toda mensagem automática identifica o remetente e oferece caminho de contato
  humano.
- Resposta do paciente relatando piora escala ao médico; o assistente não
  orienta conduta.

## 6. Limites do assistente

O assistente **não**:

- Diagnostica, prescreve ou define conduta por conta própria.
- Emite documento final assinado.
- Envia, publica ou compartilha documento clínico com terceiros.
- Acessa prontuário eletrônico ou base de pacientes sem autorização explícita
  do médico naquela sessão.
- Toma decisão que dependa de julgamento clínico, preferência do paciente ou
  alocação de recurso.

A responsabilidade técnica e ética pelo ato médico é do médico. O assistente é
ferramenta de apoio à documentação, sujeita a erro, e seu produto exige revisão.

## 7. Retenção e descarte

| Artefato | Onde vive | Quando se apaga |
|---|---|---|
| Áudio | memória do processo | ao fim da transcrição |
| Transcrição bruta | diretório temporário local | quando a nota validada existir |
| Rascunho de nota | diretório de trabalho local | após validação e arquivamento no PEP |
| Nota validada | prontuário eletrônico | retenção legal (mín. 20 anos, CFM 1.821/2007) |

Nada disso entra no controle de versão. Confirme que o `.gitignore` cobre os
diretórios de trabalho antes do primeiro atendimento.

## 8. Incidentes

Suspeita de exposição indevida (dado de paciente enviado a serviço externo,
arquivo commitado, mensagem enviada ao destinatário errado): pare o fluxo,
comunique o médico responsável imediatamente e registre o que foi exposto, para
quem e quando. Não tente "desfazer" silenciosamente — a LGPD exige comunicação
ao titular e à ANPD quando há risco relevante.
