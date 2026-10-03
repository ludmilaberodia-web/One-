#!/bin/bash
# Abre o gravador liberando o celular como microfone. Duplo clique para usar.
# Computador e celular precisam estar no mesmo Wi-Fi.

exec "$(dirname "$0")/abrir-gravador.command" --rede
