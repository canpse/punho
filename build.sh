#!/bin/bash
# Compila o APK sem Gradle: javac -> d8 -> aapt2 -> zipalign -> apksigner
set -e
cd "$(dirname "$0")"
SDK=${ANDROID_HOME:-$HOME/Android/Sdk}; BT=$SDK/build-tools/36.0.0; JAR=$SDK/platforms/android-34/android.jar
[ -x "$BT/d8" ] && [ -f "$JAR" ] || ./preparar-sdk.sh
rm -rf build && mkdir -p build/classes build/dex
# o app já sai sabendo onde está a central e qual é o token (config.json + token.txt)
TOKEN=$(python3 config.py token)
URL=$(python3 config.py url)
cat > build/BuildToken.java <<J
package com.canpse.punho;
final class BuildToken {
    static final String TOKEN = "$TOKEN";
    static final String URL = "$URL";
}
J
javac -nowarn -source 11 -target 11 -encoding UTF-8 -cp "$JAR" -d build/classes \
  app/src/com/canpse/punho/*.java build/BuildToken.java 2>&1 | grep -v "warning\|^Note\|^1 warning\|^[0-9]* warnings" || true
"$BT/d8" --release --min-api 26 --lib "$JAR" --output build/dex $(find build/classes -name '*.class')
"$BT/aapt2" link --manifest app/AndroidManifest.xml -I "$JAR" -o build/base.apk
(cd build/dex && zip -q ../base.apk classes.dex)
"$BT/zipalign" -f 4 build/base.apk build/alinhado.apk
[ -f chave.jks ] || keytool -genkeypair -keystore chave.jks -storepass punho123 -keypass punho123 \
  -alias punho -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Punho" >/dev/null 2>&1
"$BT/apksigner" sign --ks chave.jks --ks-pass pass:punho123 --out punho.apk build/alinhado.apk
echo "pronto: $(pwd)/punho.apk"
