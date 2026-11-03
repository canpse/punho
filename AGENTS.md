# AGENTS.md: instruções pro agente de IA

Se alguém te mandou este repositório dizendo "instala isso pra mim", siga os passos abaixo.
Fale com a pessoa na língua dela, um passo de cada vez, e só peça a ela o que só ela pode fazer
(mexer no celular e no relógio, digitar senha de `sudo`).

## O que é

Um relógio Xiaomi/Redmi (testado no **Redmi Watch 5 Active**) vira controle do PC: um app
Android finge ser player de música, a tela de Música do relógio mostra uma linha de texto
nossa e os botões ⏮ ⏯ ⏭ chegam numa central em Python no PC.

## Instalar

1. **Conferir a máquina.** Precisa de Linux, `python3`, um JDK 17+ (`java` e `javac`), `curl`
   e `unzip`. Se faltar algo, diga o comando de instalação da distro dela
   (Fedora: `sudo dnf install java-21-openjdk-devel curl unzip`;
   Debian/Ubuntu: `sudo apt install openjdk-21-jdk-headless curl unzip`) e peça pra ela rodar.

2. **Clonar** (se ainda não estiver clonado):
   `git clone https://github.com/canpse/punho && cd punho`

3. **Configuração.** Não precisa de `config.json`: sem ele, a central escuta em todas as
   interfaces e o app aponta pro IP do Tailscale (se houver) ou da rede local. Confira com
   `python3 config.py`. Sem Tailscale, o **celular precisa estar no mesmo Wi-Fi** que o PC.

4. **Compilar o app:** `./build.sh`. Na primeira vez ele roda o `./preparar-sdk.sh`, que baixa
   o mínimo do Android SDK pra `~/Android/Sdk` (uns 150 MB, sem Android Studio). O APK sai com
   o endereço e o token da central embutidos.

5. **Subir a central:** `python3 central.py` em segundo plano. Se a pessoa quiser que ela
   suba sozinha com o computador e ganhe um atalho no menu, **pergunte antes** e rode
   `./instalar.sh` (desfaz com `./instalar.sh --remover`).

6. **Firewall.** Do próprio PC, teste o endereço do celular:
   `curl -s -o /dev/null -w "%{http_code}" "$(python3 config.py url)/api/estado?t=$(python3 config.py token)"`
   deve dar `200`. Se o celular não alcançar depois (passo 8 mostra "PC fora do ar"), a porta
   pode estar fechada: no Fedora, peça pra ela rodar
   `sudo firewall-cmd --add-port=8787/tcp --permanent && sudo firewall-cmd --reload`.

7. **Entregar o link do app.** Rode `python3 config.py link-apk` e mande o link pra pessoa
   abrir **no navegador do celular**. Ela baixa o `punho.apk` e instala (o Android vai pedir pra
   permitir instalar apps desta fonte). O link carrega o token: não publique em lugar nenhum.

8. **No celular e no relógio** (passos dela, guie um por um):
   - o relógio precisa estar pareado pelo app **Mi Fitness** (é o normal desse relógio);
   - abrir o app **Punho**, permitir notificações, tocar em **Ligar** (endereço e token já vêm
     preenchidos);
   - pausar qualquer outro player (YouTube Music, Spotify);
   - no relógio, abrir o app **Música**. Deve aparecer `1. Próxima prova` (ou o primeiro modo).

9. **Confirmar.** Peça pra ela apertar ⏭ no relógio e veja se chegou: `tail acoes.log`.
   O painel fica em `http://punho.localhost:8787` (no PC, sem token).

### Se der errado

- **Relógio mostra a música de outro app:** feche o outro player e toque em Desligar/Ligar no Punho.
- **"PC fora do ar":** IP errado ou rede diferente (refaça o passo 3), firewall (passo 6), ou a
  central não está rodando.
- **Os botões não chegam:** confirme que o Punho está "tocando" (a notificação dele aparece no
  celular) e que nenhum outro app tocou áudio depois.
- **Trocou o token ou o IP:** rode `./build.sh` de novo e reinstale pelo link novo.

## Depois de instalado: como ajudar

- **Modos novos:** cada modo é um arquivo em `modos/`, uma classe com `entrar`, `botao`,
  `estado` e `api` (veja `modos/base.py`), registrada na lista `self.modos` do `central.py`.
  Dentro de um modo, ⏭ e ⏯ são do modo e ⏮ volta ao menu (a central cuida disso). Reinicie a
  central depois de mudar; **o app não precisa ser recompilado**.
- **A tela tem regras duras:** uma linha só, até 16 "dígitos" (emoji ≈ 1,75), e só os glifos de
  `modos/tela.py` (os outros viram retângulo no relógio). Use `c.mostrar()`, que já corta e
  filtra. Texto longo vai por `c.notificar(titulo, texto)`, que vibra no pulso.
- **Servidores da pessoa:** copie `dados/servidores.exemplo.json` pra `dados/servidores.json`
  e liste os serviços dela (`servico` = unidade do systemd de usuário; `processo` = script
  avulso com `cmd`, `pasta` e `porta`; `abrir` = página que abre no PC ao ligar).
- **Não comite** `config.json`, `token.txt`, `chave.jks` nem nada de `dados/` além dos exemplos.
- **Aprovações do Claude Code pelo pulso** são opcionais e mexem nas configurações do agente:
  só com o pedido explícito da pessoa (`python3 hooks/instalar.py`).
