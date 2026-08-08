# Gravador de consulta

Grava o atendimento, transcreve **no seu próprio computador** e entrega o texto
pronto para o agente `escriba-clinico` montar a nota clínica.

O áudio não sai da máquina. O servidor escuta apenas em `127.0.0.1` — nem a rede
local alcança. A transcrição roda offline, com Whisper local. O áudio é apagado
assim que a transcrição existe.

## Instalar

Uma vez só:

```bash
pip install -r app/requirements.txt
```

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
python3 app/gravador.py --porta 9000
python3 app/gravador.py --sem-navegador
```

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

**Só funciona no computador.** O navegador exige contexto seguro para liberar o
microfone, e `localhost` atende esse requisito; o IP da máquina na rede local,
não. Gravar pelo celular exigiria certificado HTTPS — dá para fazer, mas não está
aqui.

**Fechar a aba durante a gravação perde o trecho em buffer** (até 10 segundos).
O navegador avisa antes de fechar.

**Se a transcrição falhar, o áudio é preservado.** Sem transcrição, ele é a única
cópia do atendimento — o servidor não apaga. Resolva o erro e encerre de novo.

## Consentimento

Gravar um atendimento exige consentimento do paciente. A tela inicial trava a
gravação até você confirmar, mas o registro formal desse consentimento é sua
responsabilidade — o app não substitui o que vai no prontuário.
