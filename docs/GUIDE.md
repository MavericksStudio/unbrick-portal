# 📖 The Complete Guide — Turn your bricked Meta Portal into an AI assistant

This guide assumes **no technical background**. If you can follow steps carefully and
copy-paste, you can do this. Take your time and don't skip steps.

**What you'll have at the end:** a Portal that boots straight to a glowing orb you can
tap, talk to, and get spoken answers from — running on the device itself.

**Time:** ~1 hour · **Difficulty:** patient beginner · **Cost:** a few dollars of AI usage.

> 💡 Throughout, text in `code boxes` is something you type or paste. On the Portal you
> type with the on-screen keyboard; on your computer you type in a "terminal"
> (Mac: *Terminal* app; Windows: *PowerShell*; Linux: your terminal).

---

## Table of contents
1. [What you need](#1-what-you-need)
2. [Get your two AI keys](#2-get-your-two-ai-keys)
3. [Install ADB on your computer](#3-install-adb-on-your-computer)
4. [Turn on ADB on the Portal](#4-turn-on-adb-on-the-portal)
5. [Connect the Portal to your computer](#5-connect-the-portal-to-your-computer)
6. [Install the apps onto the Portal](#6-install-the-apps-onto-the-portal)
7. [Install Portal Agent (one command)](#7-install-portal-agent-one-command)
8. [Add your keys](#8-add-your-keys)
9. [First run & test](#9-first-run--test)
10. [Set up the screen (Fully Kiosk)](#10-set-up-the-screen-fully-kiosk)
11. [Make it automatic (boots on its own)](#11-make-it-automatic-boots-on-its-own)
12. [Using it](#12-using-it)
13. [Troubleshooting](#troubleshooting)
14. [Customizing](#customizing)
15. [Undo / revert](#undo--revert)

---

## 1. What you need
- 📺 A **Meta Portal** that still powers on (built/tested on the **Portal Mini**).
- 💻 A **computer** (Mac / Windows / Linux).
- 🔌 A **USB-C data cable** to connect the Portal to the computer.
- 🌐 **Wi-Fi** (the Portal and the internet).
- 🔑 An **Anthropic** account and an **ElevenLabs** account (next step).

---

## 2. Get your two AI keys

These are like passwords that let your Portal use cloud AI. Keep them private.

**Anthropic (the "brain"):**
1. Go to **https://console.anthropic.com** and sign up / log in.
2. Add a little credit (Billing → add ~$5; conversations cost cents).
3. Open **API Keys → Create Key**, copy it. It starts with `sk-ant-`.

**ElevenLabs (the "voice"):**
1. Go to **https://elevenlabs.io** and sign up (free tier is fine to start).
2. Open your **Profile → API Key**, copy it.

Paste both somewhere safe for a few minutes — you'll need them in step 8.

---

## 3. Install ADB on your computer

**ADB** is a tool that lets your computer talk to the Portal over USB.

**macOS** (needs [Homebrew](https://brew.sh)):
```bash
brew install android-platform-tools
```

**Windows:**
1. Download "SDK Platform Tools" from
   https://developer.android.com/tools/releases/platform-tools
2. Unzip it (e.g. to `C:\platform-tools`).
3. Open **PowerShell** in that folder (Shift-right-click → "Open PowerShell here").
   Use `.\adb` instead of `adb` in the commands below.

**Linux (Debian/Ubuntu):**
```bash
sudo apt install adb
```

Verify it works:
```bash
adb version
```
You should see a version number.

---

## 4. Turn on ADB on the Portal

On the **Portal's touchscreen**:
1. Open **Settings**.
2. Find **About** (may be "About Portal" / "System") and tap the **Build number**
   (or "Software version") **7 times** quickly. You'll see *"You are now a developer!"*
3. Go back to Settings → a new **Developer options** menu appears. Open it.
4. Turn **ON** the toggle named **"ADB Enabled"** (a.k.a. USB debugging).

---

## 5. Connect the Portal to your computer
1. Plug the Portal into your computer with the USB-C cable.
2. In your computer's terminal:
   ```bash
   adb devices
   ```
3. **Look at the Portal screen** — a popup asks *"Allow USB debugging?"*. Check
   **"Always allow"** and tap **OK**.
4. Run `adb devices` again. You should see a line ending in `device` (e.g.
   `819LCM01...   device`). If it says `unauthorized`, redo step 3.

✅ Your computer can now talk to the Portal.

---

## 6. Install the apps onto the Portal

We'll sideload four free apps. **Use the GitHub builds for the three Termux apps** so
their signatures match (mixing sources fails).

Download these four files to your computer:
- **Termux** — https://github.com/termux/termux-app/releases (latest, file ending `arm64-v8a.apk`)
- **Termux:API** — https://github.com/termux/termux-api/releases (latest `arm64-v8a.apk`)
- **Termux:Boot** — https://github.com/termux/termux-boot/releases (latest `.apk`)
- **Fully Kiosk Browser** — https://www.fully-kiosk.com (the "Download APK" link)

Then install each (replace the filename with what you downloaded):
```bash
adb install termux-app_*_arm64-v8a.apk
adb install termux-api_*_arm64-v8a.apk
adb install termux-boot_*.apk
adb install Fully-Kiosk-Browser-*.apk
```
Each should print `Success`.

Now **open each app once** on the Portal so Android registers it (tap their icons:
Termux, Termux:API, Termux:Boot, Fully Kiosk). For Termux:Boot, just opening it is enough.

**Allow them to run in the background** (so they survive). On your computer:
```bash
adb shell dumpsys deviceidle whitelist +com.termux
adb shell dumpsys deviceidle whitelist +com.termux.boot
adb shell dumpsys deviceidle whitelist +com.termux.api
adb shell dumpsys deviceidle whitelist +de.ozerov.fully
```

---

## 7. Install Portal Agent (one command)

Open **Termux** on the Portal. The first time, it sets itself up for a few seconds.
Then type this **one line** (use the on-screen keyboard) and press Enter:

```bash
pkg install -y git && git clone https://github.com/MavericksStudio/unbrick-portal && cd unbrick-portal && bash scripts/setup-termux.sh
```

This downloads the project and runs the installer: it fetches dependencies, builds
the speech engine, downloads the voice-recognition model, and sets up auto-start.
**It takes several minutes** (it compiles whisper). Let it finish — you'll see
`✅ Setup complete.`

> ⌨️ Typing on a touchscreen is tedious. Tip: in Termux you can paste — long-press the
> screen → Paste. You can type the line on your phone's notes, copy it, and paste.

---

## 8. Add your keys

Still in Termux, open the secrets file:
```bash
nano ~/.portal-agent.env
```
You'll see two lines. Put your keys right after the `=` signs (no spaces, no quotes):
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
ELEVENLABS_API_KEY=your-elevenlabs-key-here
```
Save and exit nano: press **Ctrl+O**, **Enter**, then **Ctrl+X**.

---

## 9. First run & test

Start everything (in Termux):
```bash
bash ~/unbrick-portal/scripts/supervise.sh &
```
Wait ~10 seconds. This launches the brain and the on-screen UI.

Now open **Fully Kiosk** on the Portal. The first time it'll likely show a blank/error
page — that's fine, we point it at the orb next.

---

## 10. Set up the screen (Fully Kiosk)

Open **Fully Kiosk → Settings** (swipe in from the far-left edge of the screen).

1. **Web Content Settings → Start URL** → set to:
   ```
   http://127.0.0.1:8088/
   ```
2. **Web Content Settings → Enable Camera/Microphone Access** → **ON**.
   (If the microphone toggle is greyed out, fully close and reopen Fully Kiosk, then try again.)
3. **Web Content Settings → Reload on Connection Error** (or "Auto Reload") → **ON**.
4. **Power Settings → Keep Screen On** → **ON**.
5. Tap **Load Start URL** (or back out to the page).

You should now see the **glowing orb**. **Tap it, say "hello", tap again** — it should
think, then talk back. 🎉 (If the mic is blocked, see step 2 again.)

---

## 11. Make it automatic (boots on its own)

So it comes up by itself after a power cut or reboot:

1. **Make Fully Kiosk the home screen.** In **Fully Kiosk → Settings → Device
   Management → Set as Default Launcher** (or Android **Settings → Apps → Default apps
   → Home app → Fully Kiosk**). Choose **Always**. Now "home" *is* the orb.
   *(The boot autostart for the brain was already installed by the setup script via
   Termux:Boot.)*
2. **Reboot the Portal** (hold the power button, or unplug/replug).
3. After it boots, it should land on the **orb**, ready to talk — no computer needed.

✅ **That's it — your Portal is now a standalone AI appliance.**

---

## 12. Using it
- **Tap** the orb → it listens (turns green, reacts to your voice).
- **Tap again** → it thinks, then speaks.
- Examples: *"What's the capital of France?"*, *"What's the weather in Tokyo?"*,
  *"What do you see?"* (camera blips on briefly), *"Tell me a joke."*

---

## Troubleshooting

**The orb shows but it doesn't answer.**
In Termux: `tail ~/brain-errors.log`. A `401` or `402` means a key is missing or your
AI account needs credit (check step 2 and step 8).

**"I can't search the web right now."**
Your `ANTHROPIC_API_KEY` is missing/empty — re-check `nano ~/.portal-agent.env`.

**Microphone blocked / no reaction to voice.**
Fully Kiosk → Web Content Settings → enable Camera/Microphone Access, then fully
restart Fully Kiosk. Also ensure you tapped the orb first (a tap is needed to unlock audio).

**After a reboot my computer can't see the Portal with `adb`.**
A reboot drops the ADB permission. On the Portal: Settings → re-enable **ADB Enabled**
and re-accept the popup. (The appliance doesn't need ADB — only you do, for changes.)

**It worked, then stopped after a few days.**
Open Termux and run `bash ~/unbrick-portal/scripts/supervise.sh &` again. If this keeps
happening, make sure the background-whitelist commands in step 6 were run.

**I need to see what the brain is doing.**
`tail -f ~/brain.log` (the brain) and `tail -f ~/supervise.log` (the keep-alive).

---

## Customizing

Edit `~/unbrick-portal/brain.json`:
- `tts_voice_id` — an ElevenLabs voice ID (from your ElevenLabs voice library).
- `claude_model` — e.g. a bigger model for smarter (slower/pricier) answers.
- `persona` — change its personality/name (it's "Portal" by default).

After editing, restart: `pkill -f "python -m brain"` (the supervisor restarts it in ~15s).

---

## Undo / revert
- **Give the Portal its normal home screen back:** Android Settings → Apps → Default
  apps → Home app → pick the original launcher.
- **Remove everything:** uninstall Termux, Termux:API, Termux:Boot, and Fully Kiosk
  (`adb uninstall com.termux` etc.), and turn ADB back off in Developer options.

---

Made something cool or hit a snag? Open an
[issue](https://github.com/MavericksStudio/unbrick-portal/issues) — and ⭐ the repo to
help others find it.
