# punho

Um relógio barato e fechado virando controle do computador, por uma brecha no player de música.

> **English:** punho turns a **Redmi Watch 5 Active** (Xiaomi, Mi Fitness, closed RTOS: no
> third-party apps, no custom firmware, no root) into a remote control for your PC. An Android app
> pretends to be a music player (`MediaSession`): the watch's **Music screen** shows our text as the
> "track title", and its ⏮ ⏯ ⏭ buttons reach a Python server on the PC. Uses: slide clicker,
> turning home servers on/off, one-tap mood logging, flashcards, approving Claude Code permission
> requests from the wrist. Should work on other Xiaomi/Redmi/Amazfit watches whose Music screen shows
> the track title: please open an issue if you try it. Docs below are in Portuguese.

O Redmi Watch 5 Active não instala app, não tem SDK e não aceita firmware modificado. Ele só
sabe mostrar notificações e controlar a música do celular. O punho usa a **tela de Música**
como um terminal: o título da "faixa" vira a tela, e ⏮ ⏯ ⏭ viram três botões que chegam ao PC.
Do outro lado, uma central em Python decide o que cada botão faz.

Uso no dia a dia pra passar slides na aula, ligar e desligar os servidores que rodo em casa,
registrar como estou com um toque, e mais uns modos que fui inventando.

## A engenharia em cima da limitação

O ponto de partida era um "não" atrás do outro:

| Limitação | Como virou ferramenta |
|---|---|
| Sistema fechado, sem apps de terceiros nem firmware próprio | O relógio já confia num app: o player de música do celular. Um app Android **finge ser um player** (`MediaSession` com estado "tocando"), e o relógio passa a conversar com ele. |
| Os botões de música só servem pra música | ⏮ ⏯ ⏭ chegam como `onSkipToPrevious` / `onPlay` / `onSkipToNext`, e o app repassa cada um ao PC. **Três botões de entrada.** |
| A tela só mostra o nome da faixa | O título da faixa é texto que o app controla, então vira **uma linha de saída**. O artista e a capa nem aparecem nesse modelo (testado). |
| O Android manda os botões de mídia pra quem tocou áudio por último | O app toca **meio segundo de silêncio** a cada toque e "rouba" os botões do YouTube Music. |
| A fonte do relógio não tem a maioria dos símbolos | Mapeei por fotos quais emojis e símbolos existem (🔴 ✅ ⭐ 🔥 💚 💛 ❤️ ■ □ ← → ① …; quadrados coloridos e ❌ viram retângulo). `modos/tela.py` tira o que não existe. |
| Texto comprido rola, e isso é ruim de ler no pulso | Réguas no próprio relógio: cabem 16 dígitos, 9 emojis ou 9 quadrados. Toda linha é cortada nessa medida, e **nunca rola**. |
| O volume do relógio mexe no volume de verdade do celular | Em tese daria pra capturar como mais dois botões, mas muda o som e atrapalha. Ficam 3 botões, e a navegação foi desenhada pra isso: no menu ⏮⏭ escolhem e ⏯ entra; num modo ⏭ passa, ⏯ age e ⏮ volta ao menu. Só toques simples, porque toque duplo não funciona bem no relógio. |
| O app não deveria precisar de atualização a cada ideia | O celular virou **terminal burro**: `POST /botao` e uma espera longa (`GET /espera`) pela próxima linha. Toda a lógica mora no PC, e um modo novo não exige reinstalar nada. |
| Uma linha é pouco pra conteúdo longo | Texto longo (a pergunta de um flashcard, o pedido de permissão de um agente) vai como **notificação**, que vibra e aparece no relógio. A linha fica pras escolhas. |

## Modos

Cada modo é um arquivo em `modos/` e dá um sentido diferente aos três botões.

- **Apresentação:** ⏭ avança, ⏯ volta um slide. Aceita PDF, pptx/odp (via LibreOffice) e link
  do Google Apresentações; a tela fica em `/slides`, em tela cheia no navegador.
- **Servidores:** liga e desliga serviços do systemd de usuário ou scripts avulsos (💚 ligado,
  ❤️ desligado) e abre a página no navegador do PC quando liga. Lista em `dados/servidores.json`
  (veja o `servidores.exemplo.json`).
- **Termômetro:** pergunta "como tá?" em horários marcados; ⏭ escolhe 😴😐🤔💪🔥 e ⏯ registra.
- **Aprovações:** quando o Claude Code pede permissão, o pulso vibra e ⏯ aprova ou nega
  (hook em `hooks/`).
- **Flashcards**, **Mestre de RPG** (iniciativa + dado), **Metrônomo** (pela caixa de som do PC),
  **Aventura** (o Claude narra, uma escolha por toque), **Próxima prova / Cardápio / Pendências**
  (leem arquivos de uma pasta pessoal, se configurada) e **Testar**.

No painel (`http://punho.localhost:8787`) dá pra escolher quais modos aparecem no relógio,
simular os três botões pelo teclado e configurar cada modo.

## Como instalar

Precisa de: um relógio Xiaomi/Redmi cuja tela de Música mostre o título (testado no
Redmi Watch 5 Active, Mi Fitness), um celular Android, e um PC Linux com Python 3 que o
celular alcance (mesma rede ou Tailscale).

**No PC:**
```
git clone https://github.com/canpse/punho && cd punho
cp config.exemplo.json config.json      # "host": o IP onde o celular acha o PC
python3 central.py                      # cria o token.txt e abre a central
```
Painel em `http://punho.localhost:8787`. Pra subir sozinho com o computador, com atalho no
menu do GNOME: `./instalar.sh` (`--remover` desfaz).

**O app** (Java puro, sem Gradle; o token do `token.txt` vai embutido):
```
./build.sh        # precisa do Android SDK (platform 34, build-tools 36) em ~/Android/Sdk
```
Instale o `punho.apk` no celular, ponha o endereço do PC (`http://IP:8787`), toque em
**Ligar**, pause qualquer outro player e abra **Música** no relógio.

**Aprovações do Claude Code pelo pulso** (opcional): `python3 hooks/instalar.py`.

## Como funciona por dentro

```
relógio ──Bluetooth── Mi Fitness ──MediaSession── app punho ──HTTP── central.py ── modos/
  tela de Música          (do celular)          (finge ser player)    (PC)
```

- `app/`: o terminal. `PunhoService` mantém a `MediaSession`, repassa os botões (`POST /botao`) e
  fica esperando a próxima linha ou notificação (`GET /espera`, espera longa de 25 s).
- `central.py`: menu, troca de modo, interrupções (aprovação, termômetro), painel web, API.
- `modos/`: um arquivo por modo. `tela.py` decide o que cabe na linha.

## Ideias e contribuições

Três botões e uma linha parecem pouco, mas do outro lado está um computador inteiro.

- **Ideia de modo?** Abra uma issue contando o que os três botões fariam. Um modo é um arquivo em
  `modos/` (veja `modos/base.py`: `entrar`, `botao`, `estado`, `api`).
- **Outro relógio?** Se a tela de Música do seu mostra o título da faixa, conte se funcionou
  (modelo, app do celular, o que aparece). Ajuda a montar a lista de compatíveis.

### Ideias abertas (pra quem quiser pegar)

Coisas que fariam sentido e que eu não fiz, algumas porque não uso:

- **Home Assistant.** O relógio já tem Alexa, mas e quem usa Home Assistant, ou não quer
  depender da Alexa? Um modo que liste cenas e dispositivos (⏭ passa, ⏯ liga/desliga) pela API
  REST do HA deixaria qualquer casa controlável pelo pulso. Provavelmente o modo mais útil pra mais gente.
- **Streaming / OBS.** Trocar de cena, começar e parar a gravação, silenciar o microfone, pelo
  obs-websocket. Eu não faço streaming, então quem faz vai acertar melhor o que importa.
- **Mídia do PC.** Pausar, avançar e mudar o volume do que estiver tocando (`playerctl`, MPRIS).
- **Timer de dormir.** ⏭ escolhe 15/30/60 min; no fim pausa a mídia e suspende o PC.
- **Notas do apresentador.** As anotações de cada slide do pptx chegando como notificação, e um
  cronômetro que vibra quando faltarem 5 minutos.
- **Marcadores de um botão.** 💡 tive uma ideia, ⭐ fiz algo bom, 🔥 bateu o aperto: o toque é o
  dado, a hora fica registrada e o padrão aparece depois.
- **Outros relógios.** Testar e documentar Xiaomi Smart Band, Redmi Watch 4/5, Amazfit e afins.

## Como foi feito

Numa noite, de umas 21h às 23h30, com o Claude Code. **Todo o código foi escrito pelo agente.**
O meu papel foi a ideia da interceptação, os testes com o relógio no braço (fotos da tela, réguas,
símbolos) e as decisões de uso. A velocidade muda a relação com o software: a pergunta deixa de
ser "vale o esforço de programar isso?" e vira "o que eu quero que isso faça?".

Licença MIT.
