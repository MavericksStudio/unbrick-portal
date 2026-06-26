#!/data/data/com.termux/files/usr/bin/bash
# One-shot Portal Agent setup — run INSIDE Termux on the Portal after cloning the
# repo:  cd <repo> && bash scripts/setup-termux.sh
# Installs deps, builds whisper.cpp, fetches the model, writes config, creates the
# secrets template, and installs the boot autostart hook.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
echo "==> Portal Agent setup (repo: $REPO)"

echo "==> [1/6] Installing packages (a few minutes the first time)..."
yes | pkg update || true
pkg install -y python openssh termux-api git cmake clang wget

echo "==> [2/6] Python dependencies..."
pip install -r requirements-brain.txt

echo "==> [3/6] Speech-to-text (whisper.cpp)..."
if ! command -v whisper-cli >/dev/null 2>&1; then
  ( cd "$HOME" && rm -rf whisper.cpp \
    && git clone --depth 1 https://github.com/ggerganov/whisper.cpp \
    && cd whisper.cpp \
    && cmake -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build -j --target whisper-cli \
    && cp build/bin/whisper-cli "$PREFIX/bin/" )
fi
mkdir -p "$HOME/whisper-models"
if [ ! -f "$HOME/whisper-models/ggml-tiny.en.bin" ]; then
  wget -O "$HOME/whisper-models/ggml-tiny.en.bin" \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
fi

echo "==> [4/6] Writing brain.json..."
cp -n brain.example.json brain.json
python - "$HOME/whisper-models/ggml-tiny.en.bin" <<'PY'
import json, sys
c = json.load(open("brain.json"))
c["whisper_model"] = sys.argv[1]
json.dump(c, open("brain.json", "w"), indent=2)
print("    whisper_model ->", c["whisper_model"])
PY

echo "==> [5/6] Secrets file (~/.portal-agent.env)..."
ENV="$HOME/.portal-agent.env"
if [ ! -f "$ENV" ]; then
  printf 'ANTHROPIC_API_KEY=\nELEVENLABS_API_KEY=\n' > "$ENV"
  chmod 600 "$ENV"
  echo "    created — EDIT IT and paste your two keys:  nano ~/.portal-agent.env"
else
  echo "    already exists, leaving it untouched."
fi

echo "==> [6/6] Boot autostart hook..."
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/start-portal.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec "$REPO/scripts/supervise.sh" >>"\$HOME/supervise.log" 2>&1
EOF
chmod +x "$HOME/.termux/boot/start-portal.sh"

cat <<DONE

✅ Setup complete.

Next steps:
  1) Add your API keys:   nano ~/.portal-agent.env
  2) Start it now:        bash "$REPO/scripts/supervise.sh" &
  3) In Fully Kiosk: enable Camera/Microphone access, set the Start URL to
     http://127.0.0.1:8088/ , and set Fully as the default launcher.
  4) Reboot — it should come up to the talking orb.

Full walkthrough: docs/GUIDE.md
DONE
