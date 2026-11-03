#!/bin/bash
# Instala o punho de vez (rodado pelo Lucas):
#  1. serviço de usuário: a central sobe sozinha com o computador
#  2. app "Punho" no menu do GNOME (abre http://punho.localhost:8787 numa janela própria do Chrome)
#  3. abre o app sozinho ao entrar no computador
# Desfazer: ./instalar.sh --remover
set -e
cd "$(dirname "$0")"
AQUI=$(pwd)
APP=~/.local/share/applications/punho.desktop
AUTO=~/.config/autostart/punho.desktop

if [ "$1" = "--remover" ]; then
  systemctl --user disable --now punho 2>/dev/null || true
  rm -f ~/.config/systemd/user/punho.service "$APP" "$AUTO"
  systemctl --user daemon-reload
  echo "punho removido (serviço, app e abertura automática)"; exit 0
fi

./instalar-servico.sh

mkdir -p ~/.local/share/applications ~/.config/autostart
cat > "$APP" <<DESK
[Desktop Entry]
Type=Application
Name=Punho
Comment=Central do relógio
Exec=google-chrome --app=http://punho.localhost:8787 --class=punho
Icon=$AQUI/web/icone.svg
StartupWMClass=punho
Categories=Utility;
DESK
# ao entrar: espera a central subir e abre
sed 's|^Exec=.*|Exec=sh -c "for i in $(seq 30); do curl -s -o /dev/null http://127.0.0.1:8787/api/estado \&\& break; sleep 1; done; google-chrome --app=http://punho.localhost:8787 --class=punho"|' "$APP" > "$AUTO"
echo "X-GNOME-Autostart-enabled=true" >> "$AUTO"
update-desktop-database ~/.local/share/applications 2>/dev/null || true
echo
echo "Pronto: aperte Super e digite 'punho'. Endereço: http://punho.localhost:8787"
