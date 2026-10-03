# Manual do gravador de consulta

Grava o atendimento, transcreve no seu próprio computador e entrega o texto
pronto para virar nota clínica.

|  |  |
|---|---|
| **O que faz** | Captura o áudio, transcreve e estrutura em prontuário |
| **O que não faz** | Diagnóstico, prescrição, assinatura — decisão é sempre sua |
| **Onde roda** | No seu computador. O celular é só o microfone |
| **Internet** | Só para instalar. Depois, funciona offline |

> **Mac ou Windows?** Funciona nos dois. Onde o comando muda, o manual mostra as
> duas versões.

---

## Como abrir, depois de instalado

**O jeito mais fácil: duplo clique.** Na pasta `One-` há dois atalhos:

| Arquivo | Para quê |
|---|---|
| `abrir-gravador` | Gravar pelo computador |
| `abrir-gravador-celular` | Gravar pelo celular |

No Mac são os arquivos `.command`; no Windows, os `.bat`. Duplo clique abre o
gravador e o navegador. Arraste `abrir-gravador` para o Dock (Mac) ou para a
barra de tarefas (Windows) e ele fica a um clique.

**Pelo Terminal**, se preferir:

```bash
cd ~/One-
.venv/bin/python app/gravador.py
```

**Para virar um comando de uma palavra** no Mac, cole isto no Terminal uma vez:

```bash
echo "alias gravador='cd ~/One- && .venv/bin/python app/gravador.py'" >> ~/.zshrc
echo "alias gravador-celular='cd ~/One- && .venv/bin/python app/gravador.py --rede'" >> ~/.zshrc
```

Feche e reabra o Terminal. A partir daí basta digitar `gravador`.

**Para fechar**, aperte `Control + C` na janela do Terminal — a tecla Control,
não a Command. Enquanto a janela estiver aberta, o gravador está no ar.

---

## 1. Instalar — uma vez só

**1.1 Instale o Claude Code.** No Terminal (Mac) ou PowerShell (Windows):

```bash
curl -fsSL https://claude.ai/install.sh | bash     # Mac e Linux
irm https://claude.ai/install.ps1 | iex            # Windows PowerShell
```

Depois rode `claude` uma vez e faça login. Precisa de assinatura Claude Pro ou Max.

**1.2 Baixe o projeto.**

```bash
git clone https://github.com/ludmilaberodia-web/One-.git
cd One-
git checkout claude/app-agent-function-kvz217
```

**1.3 Instale o que o gravador precisa**, numa pasta isolada dentro do projeto:

```bash
python3 -m venv .venv                          # Mac e Linux
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r app/requirements.txt
```

```bash
py -m venv .venv                               # Windows
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r app\requirements.txt
```

Leva de 3 a 10 minutos e baixa uns 350 MB. Termina com uma linha
`Successfully installed` e uns 25 nomes de pacotes.

A pasta `.venv` guarda as bibliotecas sem tocar no Python do seu sistema —
é o que evita o erro `externally-managed-environment` e as brigas de permissão
que o Mac costuma dar. Você **não** precisa "ativar" nada: os comandos deste
manual já apontam para dentro dela.

Para desinstalar tudo um dia, apague a pasta `One-`. Não sobra nada no sistema.

**1.4 Faça uma gravação de teste.** Fale sozinha por dois minutos, como se
estivesse ditando um atendimento. Na primeira vez o modelo de transcrição é
baixado — uns 500 MB, só acontece uma vez. Leia o resultado antes de usar com
paciente: é assim que você descobre a qualidade real na sua voz e no seu
vocabulário.

---

## 2. Gravar pelo computador — toda consulta

É o caminho mais simples e o mais seguro: o áudio não sai da máquina.

**2.1 Abra o gravador**, no Terminal, dentro da pasta do projeto:

```bash
.venv/bin/python app/gravador.py          # Mac e Linux
.venv\Scripts\python app\gravador.py       # Windows
```

O navegador abre sozinho em `localhost:8765`. Deixe o Terminal aberto — é ele
que está rodando o programa.

**2.2 Confirme o consentimento.** Explique ao paciente o que será gravado e para
quê. Marque a caixa na tela — o botão de gravar não libera sem isso.

**2.3 Inicie e atenda.** Aperte *Iniciar gravação* e deixe a aba aberta. O
cronômetro e a barra de nível mostram que o áudio está entrando. Pode pausar e
continuar.

**2.4 Encerre e transcreva.** De um a três minutos para cada dez minutos de
consulta. Ao terminar, o áudio é apagado automaticamente e sobra só o texto.

**2.5 Copie o comando que aparece** e siga para a etapa 5.

---

## 3. Preparar o celular — uma vez só

O navegador do celular só libera o microfone em endereço seguro. Por isso o
gravador cria um certificado próprio, e o celular precisa passar a confiar nele.
É chato uma vez, e depois nunca mais.

**3.1 Ligue os dois no mesmo Wi-Fi.**

**3.2 Abra o gravador em modo rede:**

```bash
.venv/bin/python app/gravador.py --rede       # Mac e Linux
.venv\Scripts\python app\gravador.py --rede  # Windows
```

O Terminal mostra dois endereços e um QR. Guarde o endereço que termina em
`/ca.crt`.

**3.3 Baixe o certificado no celular.** Digite no navegador do celular o
endereço do certificado, algo como `https://192.168.0.15:8765/ca.crt`.

**3.4 Instale — iPhone.** O arquivo baixa como perfil. Vá em *Ajustes › Geral ›
VPN e Gerenciamento de Dispositivo* e instale o perfil.

Depois — e este passo é o que quase todo mundo esquece — vá em *Ajustes › Geral
› Sobre › Ajustes de Confiança do Certificado* e **ative a chave** ao lado de
"Gravador de Consulta".

> **Sem a confiança total, o iPhone não libera o microfone.** Se o botão de
> gravar der erro de permissão, é quase sempre este passo que faltou.

**3.5 Instale — Android.** *Ajustes › Segurança › Criptografia e credenciais ›
Instalar certificado › Certificado CA*, e escolha o arquivo baixado.

**3.6 Teste.** Leia o QR do Terminal, grave dez segundos e encerre. Se a
transcrição sair, está pronto.

O certificado vale um ano. Se o endereço do computador na rede mudar, o gravador
se ajusta sozinho — você não precisa reinstalar nada no celular.

---

## 4. Gravar pelo celular — toda consulta

O computador continua sendo o cérebro: ele transcreve e guarda os arquivos. O
celular é só o microfone.

**4.1 No computador**, abra o gravador em modo rede:

```bash
.venv/bin/python app/gravador.py --rede       # Mac e Linux
.venv\Scripts\python app\gravador.py --rede  # Windows
```

Deixe o computador ligado e o Terminal aberto durante toda a consulta.

Na primeira vez, o sistema vai pedir permissão para o programa aceitar conexões
da rede: no Mac aparece uma janela do firewall, no Windows o Defender pergunta —
**autorize em redes privadas**. Sem isso o celular não alcança o computador.

**4.2 No celular, leia o QR.** Ele já carrega o código de acesso — por isso
digitar só o endereço não funciona.

**4.3 Confirme o consentimento e grave.** Deixe o celular com a tela acesa e o
navegador aberto, apoiado perto de vocês dois.

> **Não troque de aplicativo durante a consulta.** O celular suspende abas em
> segundo plano e a gravação para junto. Uma ligação recebida também interrompe
> — deixe no "não perturbe".

**4.4 Encerre pelo celular.** A transcrição roda no computador e o arquivo fica
salvo lá. A tela do celular mostra o caminho.

**4.5 Volte ao computador para gerar a nota.** O comando roda no Terminal do
computador, não no celular.

> **Em Wi-Fi público, grave pelo computador.** No modo celular o áudio atravessa
> a sua rede — cifrado, e sem passar pela internet, mas ainda assim pela rede.
> Em casa ou na clínica, tudo bem. Em rede de terceiros, prefira o computador.

---

## 5. Gerar a nota clínica — toda consulta

**5.1 Abra o Claude** na pasta do projeto:

```bash
claude
```

**5.2 Peça a estruturação.** Cole o comando que o gravador mostrou, ou escreva
com o caminho do arquivo:

```
Estrutura essa consulta em SOAP: @atendimentos/2026-08-08_14-32-05/transcricao.md
```

Use *anamnese completa* em vez de SOAP quando for primeira consulta.

**5.3 Leia a transcrição, não só a nota.** Nas primeiras semanas, abra os dois
arquivos. É assim que você percebe onde a transcrição erra na sua rotina — nome
de medicamento é o erro mais comum.

**5.4 Revise as pendências.** Toda nota termina com *Pendências de validação*: o
que ficou incerto, contraditório ou inaudível. É o resumo do que precisa da sua
decisão.

**5.5 Valide, assine e arquive** no seu prontuário eletrônico. Só aí o documento
deixa de ser rascunho.

**5.6 Apague a transcrição.** Com a nota validada no prontuário, a transcrição
bruta não tem mais razão de existir.

### Os outros dois agentes

Na mesma sessão do Claude, escrevendo em português normal:

| Para | Peça algo como |
|---|---|
| Dúvida de conduta, com referência científica | "O que a literatura diz sobre metformina em doença renal crônica estágio 3b?" |
| Resumo para o paciente e plano de retorno | "Monta o resumo do paciente e o plano de acompanhamento a partir da nota validada" |

---

## 6. O que não se pula

**Consentimento antes de gravar.** O paciente precisa saber que está sendo
gravado, para quê, e que o áudio é apagado. O app trava a gravação até você
confirmar, mas o registro formal desse consentimento vai no prontuário — isso é
seu.

**Nenhum documento vale sem a sua assinatura.** Tudo que sai do Claude nasce
marcado como rascunho. Prontuário, encaminhamento, resumo do paciente, mensagem
de retorno: nada é utilizável, arquivável ou enviável antes da sua revisão.

**Nome e documento não entram na conversa.** Ao pedir apoio de evidência,
descreva o caso sem identificar: "mulher, 62 anos, diabética" e não o nome. Dado
de saúde é dado sensível sob a LGPD, e você é a controladora.

**A transcrição some quando a nota fica pronta.** O áudio já é apagado sozinho.
A transcrição bruta é você quem apaga, depois que a nota validada estiver no
prontuário eletrônico.

---

## 7. Quando dá errado

| O que você vê | O que fazer |
|---|---|
| Erro de permissão de microfone no iPhone | Falta ativar a confiança total do certificado em *Ajustes › Geral › Sobre › Ajustes de Confiança do Certificado*. Instalar o perfil sozinho não basta |
| "Endereço incompleto: falta o código de acesso" | Você abriu só o endereço, sem o `?t=…`. Leia o QR de novo — o código muda a cada inicialização |
| O celular não abre o endereço | Os dois aparelhos precisam estar no mesmo Wi-Fi. Redes de visitante isolam aparelhos entre si — troque para a principal |
| "faster-whisper não está instalado" | Rode `pip install -r app/requirements.txt` na pasta do projeto |
| A transcrição falhou e perdi a consulta | Não perdeu: quando a transcrição falha, o áudio é preservado de propósito. Resolva o erro e encerre de novo |
| A transcrição erra nome de medicamento | É esperado. Use `--modelo medium`. E confira as doses na nota, sempre |
| A gravação parou no meio | No celular, trocar de app ou receber ligação interrompe. O trecho já enviado está salvo; encerre para transcrever o que houver |
| "Address already in use" | Já existe um gravador rodando. Feche o outro Terminal, ou use `--porta 8766` |
| Windows: "python3 não é reconhecido" | No Windows o comando é `py`, não `python3`. Se nem `py` funcionar, instale o Python em [python.org](https://www.python.org/downloads/) marcando "Add Python to PATH" |
| "error: externally-managed-environment" | O Python da sua máquina não aceita instalação direta. Crie um ambiente isolado dentro da pasta do projeto — veja abaixo |
| O computador avisa que o certificado não é confiável | Normal no modo `--rede`: o certificado é o seu mesmo. Para gravar pelo computador, rode sem `--rede` |
| O celular alcança, mas dá erro de conexão | Firewall bloqueando. No Mac, *Ajustes do Sistema › Rede › Firewall*; no Windows, autorize o Python em redes privadas |

---

## 8. Referência rápida

No Windows, troque `.venv/bin/python` por `.venv\Scripts\python` em todos eles.

| Comando | O que faz |
|---|---|
| `.venv/bin/python app/gravador.py` | Grava pelo computador |
| `.venv/bin/python app/gravador.py --rede` | Libera o celular como microfone |
| `.venv/bin/python app/gravador.py --modelo medium` | Transcrição mais precisa, mais lenta |
| `.venv/bin/python app/gravador.py --porta 8766` | Usa outra porta |
| `claude` | Abre o assistente para gerar a nota |

### Quanto ocupa no computador

| Item | Espaço |
|---|---|
| Claude Code | ~150 MB |
| Bibliotecas do gravador | ~350 MB |
| Modelo de transcrição `small` (padrão) | ~500 MB |
| O projeto em si | menos de 1 MB |
| **Total** | **cerca de 1 GB** |

Cada atendimento gera um arquivo de texto de poucos KB. O áudio ocupa uns 2 MB
por consulta **enquanto** está sendo gravado, e é apagado em seguida. Se um dia
você trocar para o modelo `medium`, somam-se 1,5 GB; para o `large-v3`, 3 GB.

**Onde ficam os arquivos:** `atendimentos/2026-08-08_14-32-05/transcricao.md` —
uma pasta por atendimento, com data e hora. Nada disso vai para o GitHub.

**Qual modelo usar:**

| Modelo | Quando |
|---|---|
| `small` — padrão | Piso para uso clínico. Serve na maioria das máquinas |
| `medium` | Erra menos nome de medicamento. Confortável em Mac com chip Apple |
| `tiny`, `base` | Rápidos demais para serem confiáveis — não use em consulta |

---

Ferramenta de apoio à documentação: sujeita a erro, e seu produto exige revisão
médica. Detalhes técnicos em [`app/README.md`](app/README.md); os agentes em
[`docs/agentes-clinicos.md`](docs/agentes-clinicos.md).
