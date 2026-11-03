# punho

A cheap, locked-down smartwatch turned into a PC remote, through a loophole in the music player.

*Leia em português: [README.pt.md](README.pt.md)*

The **Redmi Watch 5 Active** (Xiaomi, paired with Mi Fitness) installs no apps, has no SDK and
won't take custom firmware. All it knows is showing notifications and controlling the phone's
music. punho uses its **Music screen** as a terminal: the "track title" becomes the display, and
⏮ ⏯ ⏭ become three buttons that reach the PC. On the other side, a Python server decides what
each button does.

The modes I liked most: clicking through slides, and turning the servers I run at home on and
off. There's also one-tap mood logging, flashcards, and a few more I made up along the way.

No root, no custom firmware, no Gadgetbridge: it works with the stock watch and the stock app.

## Engineering on top of the limitations

The starting point was one "no" after another:

| Limitation | How it became a feature |
|---|---|
| Closed system, no third-party apps, no custom firmware | The watch already trusts one app: the phone's music player. An Android app **pretends to be a player** (a `MediaSession` in the "playing" state), and the watch starts talking to it. |
| The music buttons only control music | ⏮ ⏯ ⏭ arrive as `onSkipToPrevious` / `onPlay` / `onSkipToNext`, and the app forwards each one to the PC. **Three input buttons.** |
| The screen only shows the track name | The track title is text the app controls, so it becomes **one line of output**. Artist and album art don't show up on this model (tested). |
| Android sends media buttons to whoever played audio last | The app plays **half a second of silence** on every press and "steals" the buttons from YouTube Music. |
| The watch font lacks most symbols | I mapped, with photos, which emoji and symbols exist (🔴 ✅ ⭐ 🔥 💚 💛 ❤️ ■ □ ← → ① …; colored squares and ❌ become empty boxes). `modos/tela.py` strips whatever doesn't exist. |
| Long text scrolls, which is bad to read on a wrist | Rulers on the watch itself: 16 digits, 9 emoji or 9 squares fit. Every line is cut to that width and **never scrolls**. |
| The watch's volume buttons change the phone's real volume | In theory they could be captured as two more buttons, but they change the sound and get in the way. So it's 3 buttons, and navigation is designed around that: in the menu ⏮⏭ choose and ⏯ enters; inside a mode ⏭ moves, ⏯ acts and ⏮ goes back to the menu. Single presses only, since double presses don't work well on the watch. |
| The app shouldn't need an update for every new idea | The phone became a **dumb terminal**: `POST /botao` and a long poll (`GET /espera`) for the next line. All the logic lives on the PC, and a new mode never requires reinstalling anything. |
| One line is too little for long content | Long text (a flashcard question, an agent's permission request) goes out as a **notification**, which vibrates and shows up on the watch. The line is kept for choices. |

## Modes

Each mode is a file in `modos/` and gives the three buttons a different meaning. Names below are
as they appear on the watch (Portuguese).

- **Apresentação (slides):** ⏭ next, ⏯ previous slide. Takes a PDF, pptx/odp (via LibreOffice) or
  a Google Slides link; the presentation runs full screen in the browser at `/slides`.
- **Servidores (servers):** turns systemd user services or standalone scripts on and off
  (💚 on, ❤️ off) and opens their page in the PC's browser when they start. List in
  `dados/servidores.json` (see `servidores.exemplo.json`).
- **Termômetro (mood):** asks "how are you?" at set times; ⏭ picks 😴😐🤔💪🔥 and ⏯ logs it.
- **Aprovações (approvals):** when Claude Code asks for permission, the wrist vibrates and ⏯
  approves or denies (hook in `hooks/`).
- **Flashcards**, **Mestre RPG** (initiative tracker + dice), **Metrônomo** (metronome through the
  PC speakers), **Aventura** (Claude narrates, one choice per press), **Próxima prova / Cardápio /
  Pendências** (read files from a personal folder, if configured) and **Testar** (test).

The dashboard (`http://punho.localhost:8787`) lets you pick which modes show up on the watch,
simulate the three buttons with the keyboard, and configure each mode.

## Installing

**Ask your agent.** Send this to Claude Code, Codex or whatever agent you use:

```
Install this for me: https://github.com/canpse/punho
```

The repo has an `AGENTS.md` written for it: the agent checks your machine, downloads the bare
minimum of the Android SDK, builds the app already configured, starts the server, and sends you
**a link to open on your phone and install the app**. You only touch the phone and the watch.

**By hand:**

You need: a Xiaomi/Redmi watch whose Music screen shows the track title (tested on the
Redmi Watch 5 Active with Mi Fitness), an Android phone, and a Linux PC with Python 3 that the
phone can reach (same network or Tailscale).

**On the PC:**
```
git clone https://github.com/canpse/punho && cd punho
./build.sh                              # downloads the SDK the first time and builds punho.apk
python3 central.py &                    # the server (creates token.txt)
python3 config.py link-apk              # link to open on the phone and download the app
```
(`config.json` is optional: without it, the app points to your Tailscale IP or LAN IP.)
Dashboard at `http://punho.localhost:8787`. To start with the computer, with a shortcut in the
GNOME menu: `./instalar.sh` (`--remover` undoes it).

**On the phone:** open the link, install `punho.apk`, tap **Ligar** (address and token come
pre-filled), pause any other player and open **Music** on the watch. The app is plain Java and
builds without Gradle; `./preparar-sdk.sh` installs only what's needed (platform 34,
build-tools 36).

**Claude Code approvals from the wrist** (optional): `python3 hooks/instalar.py`.

## How it works inside

```
watch ──Bluetooth── Mi Fitness ──MediaSession── punho app ──HTTP── central.py ── modos/
Music screen          (phone)           (pretends to be a player)    (PC)
```

- `app/`: the terminal. `PunhoService` keeps the `MediaSession`, forwards the buttons
  (`POST /botao`) and waits for the next line or notification (`GET /espera`, 25 s long poll).
- `central.py`: menu, mode switching, interruptions (approvals, mood), web dashboard, API.
- `modos/`: one file per mode. `tela.py` decides what fits on the line.

## Ideas and contributions

Three buttons and one line sound like little, but there's a whole computer on the other side.

- **Got a mode idea?** Open an issue describing what the three buttons would do. A mode is one
  file in `modos/` (see `modos/base.py`: `entrar`, `botao`, `estado`, `api`).
- **Different watch?** If your watch's Music screen shows the track title, tell me whether it
  worked (model, phone app, what shows up). It helps build a compatibility list.

### Open ideas (up for grabs)

Things that would make sense and that I didn't build, some because I don't use them:

- **Home Assistant.** The watch already has Alexa, but what about people who use Home Assistant,
  or don't want to depend on Alexa? A mode listing scenes and devices (⏭ moves, ⏯ toggles) over
  the HA REST API would make any home controllable from the wrist. Probably the most useful mode
  for the most people.
- **Streaming / OBS.** Switch scenes, start and stop recording, mute the mic, via obs-websocket.
  I don't stream, so someone who does will get right what matters.
- **PC media.** Pause, skip and change the volume of whatever is playing (`playerctl`, MPRIS).
- **Sleep timer.** ⏭ picks 15/30/60 min; at the end it pauses media and suspends the PC.
- **Speaker notes.** Each slide's pptx notes arriving as a notification, plus a timer that
  vibrates when 5 minutes are left.
- **One-button markers.** 💡 had an idea, ⭐ did something good, 🔥 anxiety hit: the press is the
  data point, the time gets logged, and the pattern shows up later.
- **Other watches.** Test and document Xiaomi Smart Band, Redmi Watch 4/5, Amazfit and similar.

## How it was made

In one evening, from about 9 to 11:30 pm, with Claude Code. **All of the code was written by the
agent.** My part was the interception idea, testing with the watch on my wrist (screen photos,
rulers, symbols) and the usage decisions.

What changes isn't the cost of programming, it's how I use software. Utility software is now
almost free: I don't have to find something that already exists and adapt myself to it. I build
the software that fits my use, in real time. punho itself changed while I was using it: double
presses didn't work on the wrist, so they became single presses; the middle button turned into
"previous slide" because that's what I needed in the moment.

MIT license.
