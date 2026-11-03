#!/bin/bash
# Faz a central do punho subir sozinha com o computador (serviço de usuário).
# Desfazer: systemctl --user disable --now punho && rm ~/.config/systemd/user/punho.service
set -e
mkdir -p ~/.config/systemd/user
PASTA=$(cd "$(dirname "$0")" && pwd)
sed "s|PASTA|$PASTA|g" "$PASTA/punho.service" > ~/.config/systemd/user/punho.service
# se houver uma central avulsa (aberta numa sessão do Claude), ela sai pro serviço assumir a porta
pkill -f "python3 central.py" 2>/dev/null && sleep 1 || true
systemctl --user daemon-reload
systemctl --user enable --now punho
systemctl --user --no-pager status punho | head -5
