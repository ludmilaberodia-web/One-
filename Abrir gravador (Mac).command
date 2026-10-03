#!/bin/bash
# Abre o gravador de consulta no Mac. Dê um duplo clique neste arquivo.
#
# Funciona de dentro da pasta do projeto e também se você copiar este arquivo
# para outro lugar (Área de Trabalho, por exemplo): neste caso ele procura o
# projeto nos lugares habituais.

achar_projeto() {
  local aqui
  aqui="$(cd "$(dirname "$0")" && pwd)"

  if [ -f "$aqui/app/gravador.py" ]; then
    printf '%s' "$aqui"
    return 0
  fi

  local tentativa
  for tentativa in "$HOME/One-" "$HOME/Documents/One-" "$HOME/Desktop/One-" \
                   "$HOME/Downloads/One-"; do
    if [ -f "$tentativa/app/gravador.py" ]; then
      printf '%s' "$tentativa"
      return 0
    fi
  done

  return 1
}

if ! PROJETO="$(achar_projeto)"; then
  echo
  echo "  Não encontrei a pasta do projeto."
  echo
  echo "  Este atalho está em:"
  echo "      $(cd "$(dirname "$0")" && pwd)"
  echo
  echo "  Ele precisa estar dentro da pasta One-, ou a pasta One- precisa estar"
  echo "  na sua pasta de usuário. Se você copiou este arquivo para fora do"
  echo "  projeto, apague a cópia e use o que está dentro de One-."
  echo
  read -r -p "  Aperte Enter para fechar. "
  exit 1
fi

cd "$PROJETO" || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo
  echo "  Achei o projeto em $PROJETO, mas a instalação não foi feita."
  echo
  echo "  Abra o Terminal e rode:"
  echo "      cd \"$PROJETO\""
  echo "      python3 -m venv .venv"
  echo "      .venv/bin/pip install -r app/requirements.txt"
  echo
  read -r -p "  Aperte Enter para fechar. "
  exit 1
fi

exec .venv/bin/python app/gravador.py "$@"
