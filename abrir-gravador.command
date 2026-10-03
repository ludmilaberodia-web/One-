#!/bin/bash
# Abre o gravador de consulta no Mac. Dê um duplo clique neste arquivo.
#
# Usa o Python da pasta isolada (.venv), então não depende de ativar nada
# nem de qual Python está no PATH.

cd "$(dirname "$0")" || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo
  echo "  A instalação não está completa: falta a pasta .venv."
  echo
  echo "  Abra o Terminal nesta pasta e rode:"
  echo "      python3 -m venv .venv"
  echo "      .venv/bin/pip install -r app/requirements.txt"
  echo
  read -r -p "  Aperte Enter para fechar. "
  exit 1
fi

exec .venv/bin/python app/gravador.py "$@"
