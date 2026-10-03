# Gravador de consulta

Grava o atendimento, transcreve **no seu próprio computador** e entrega o texto
pronto para o agente `escriba-clinico` montar a nota clínica.

O áudio não sai da máquina. O servidor escuta apenas em `127.0.0.1` — nem a rede
local alcança. A transcrição roda offline, com Whisper local. O áudio é apagado
assim que a transcrição existe.

Roda em Mac, Windows e Linux. Os comandos abaixo usam `python3`/`pip3`, como no
Mac; **no Windows use `py` e `py -m pip`**.

## Instalar

Uma vez só:

```bash
pip3 install -r app/requirements.txt       # Mac e Linux
py -m pip install -r app/requirements.txt  # Windows
```

Ocupa cerca de 350 MB de bibliotecas, mais o modelo de transcrição (~500 MB no
padrão), baixado no primeiro uso.

## Usar

```bash
python3 app/gravador.py
```

O navegador abre em `http://localhost:8765`. Então:

1. Marque o consentimento do paciente (obrigatório — o botão não libera sem isso).
2. **Iniciar gravação.** Deixe a aba aberta durante a consulta.
3. **Encerrar e transcrever** ao final. Leva de um a três minutos para cada dez
   minutos de consulta.
4. Copie o comando que aparece e cole no terminal — o `escriba-clinico` monta a
   nota a partir da transcrição.

Opções:

```bash
python3 app/gravador.py --modelo medium    # mais preciso, exige máquina com folga
python3 app/gravador.py --rede             # libera o celular (ver abaixo)
python3 app/gravador.py --porta 9000
python3 app/gravador.py --sem-navegador
```

## Gravar pelo celular

O computador continua sendo o cérebro: ele transcreve e guarda os arquivos. O
celular vira só o microfone. Os dois precisam estar no **mesmo Wi-Fi**, e o
computador precisa ficar ligado com o servidor rodando.

```bash
python3 app/gravador.py --rede
```

O terminal mostra o endereço do celular e um QR para não digitar nada.

**Configuração inicial, uma vez só.** O navegador só libera o microfone em
endereço seguro, então o servidor gera um certificado próprio e o celular
precisa passar a confiar nele:

1. No celular, abra `https://SEU-IP:8765/ca.crt` (o terminal mostra o endereço).
2. **iPhone:** o arquivo baixa como perfil. Vá em *Ajustes › Geral › VPN e
   Gerenciamento de Dispositivo*, instale o perfil, e então em *Ajustes › Geral
   › Sobre › Ajustes de Confiança do Certificado* ative a confiança total.
   Sem esse segundo passo o iOS não libera o microfone.
3. **Android:** *Ajustes › Segurança › Criptografia e credenciais › Instalar
   certificado › Certificado CA*.
4. Leia o QR do terminal (ou abra o endereço completo) e grave normalmente.

Depois disso é só ler o QR a cada consulta. O certificado vale um ano, e se o IP
do computador mudar o servidor regenera sozinho — sem precisar reinstalar nada
no celular.

### O que muda em relação ao computador

**O áudio atravessa o seu Wi-Fi.** Continua não indo para a internet, e vai
cifrado por TLS — mas não é mais "não sai da máquina". Em rede doméstica ou da
clínica, com o certificado instalado, é seguro. **Em Wi-Fi público ou de
terceiros, grave pelo computador.**

**O endereço tem um código de acesso** (`?t=...`), gerado a cada vez que você
inicia o servidor. Sem ele o gravador recusa qualquer comando — é o que impede
outro aparelho da rede de usar sua sessão. Por isso o link precisa ser aberto
inteiro; digitar só o IP não funciona.

**Mantenha a tela acesa e o app em primeiro plano.** O celular suspende abas em
segundo plano, e a gravação para junto. A página pede o bloqueio de tela
automaticamente, mas trocar de app durante a consulta interrompe a captura.

**Bateria e ligação.** Uma chamada recebida interrompe a gravação. Se for usar o
celular como microfone, ative o modo avião com Wi-Fi ligado, ou use o "não
perturbe".

## Modelos

A primeira execução baixa o modelo (uma vez só). Depois funciona sem internet.

| Modelo | Tamanho | Uso |
|---|---|---|
| `small` | ~500 MB | **padrão** — piso prático para português clínico |
| `medium` | ~1,5 GB | melhor com nome de medicamento; precisa de máquina com folga |
| `large-v3` | ~3 GB | melhor de todos, lento em CPU |
| `tiny` / `base` | ~75-145 MB | rápidos demais para serem confiáveis — não use em consulta |

Em Mac com chip Apple, `medium` roda confortavelmente. Em notebook antigo, fique
no `small`.

## Onde ficam os arquivos

```
atendimentos/2026-08-08_14-32-05/transcricao.md
```

A pasta `atendimentos/` está no `.gitignore` — transcrição nunca entra no
controle de versão. **Apague a transcrição depois que a nota validada estiver
arquivada no prontuário eletrônico.**

## Limites conhecidos

**O Whisper erra nome de medicamento.** "Losartana" vira "lozartana", doses se
confundem, "hipo" vira "hiper". Por isso o `escriba-clinico` tem regra de marcar
pendência em vez de escolher a versão mais provável — mas isso só funciona se
você **ler a transcrição**, não só a nota. Trate a transcrição como rascunho de
estagiário, não como ditado fiel.

**A transcrição vem depois, não ao vivo.** Transcrever o áudio inteiro de uma vez
dá bem mais precisão do que transcrever pedaço por pedaço durante a consulta — o
modelo usa o contexto todo. Você vê o cronômetro rodando, não o texto aparecendo.

**No celular, a aba precisa ficar em primeiro plano** com a tela acesa. Ver a
seção acima.

**Fechar a aba durante a gravação perde o trecho em buffer** (até 10 segundos).
O navegador avisa antes de fechar.

**Se a transcrição falhar, o áudio é preservado.** Sem transcrição, ele é a única
cópia do atendimento — o servidor não apaga. Resolva o erro e encerre de novo.

**No modo `--rede`, o navegador do próprio computador avisa que o certificado é
desconhecido.** É o certificado da própria máquina, e o aviso é esperado: a CA
foi instalada no celular, não aqui. Para gravar pelo computador, rode sem
`--rede`.

**O firewall pede autorização na primeira vez que você usa `--rede`.** Autorize
em redes privadas, senão o celular não alcança o computador.

## Consentimento

Gravar um atendimento exige consentimento do paciente. A tela inicial trava a
gravação até você confirmar, mas o registro formal desse consentimento é sua
responsabilidade — o app não substitui o que vai no prontuário.
