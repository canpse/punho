#!/bin/bash
# Instala o mínimo do Android SDK pra compilar o app (sem Android Studio, sem Gradle).
# Idempotente: se já tem, não baixa de novo. Vai pra ~/Android/Sdk (ou $ANDROID_HOME).
set -e
SDK=${ANDROID_HOME:-$HOME/Android/Sdk}
if [ -x "$SDK/build-tools/36.0.0/d8" ] && [ -f "$SDK/platforms/android-34/android.jar" ]; then
  echo "SDK já pronto em $SDK"; exit 0
fi
for c in java javac curl unzip; do
  command -v $c >/dev/null || { echo "falta '$c' (instale um JDK 17+, curl e unzip)"; exit 1; }
done
mkdir -p "$SDK/cmdline-tools"
if [ ! -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "baixando as ferramentas de linha de comando do Android..."
  tmp=$(mktemp -d)
  curl -sSLo "$tmp/ct.zip" https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  unzip -q "$tmp/ct.zip" -d "$tmp"
  mv "$tmp/cmdline-tools" "$SDK/cmdline-tools/latest"
  rm -rf "$tmp"
fi
SM="$SDK/cmdline-tools/latest/bin/sdkmanager"
yes | "$SM" --sdk_root="$SDK" --licenses >/dev/null 2>&1 || true
echo "instalando platform 34 e build-tools 36 (uns 150 MB)..."
"$SM" --sdk_root="$SDK" "platforms;android-34" "build-tools;36.0.0" >/dev/null
echo "SDK pronto em $SDK"
