#!/usr/bin/env bash
# Configura o ambiente do Mãouse no Linux (executar apenas uma vez).
set -e
cd "$(dirname "$0")"

echo "==> A verificar Python 3.10+..."
PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
    echo "ERRO: python3 nao encontrado. Instala-o primeiro."
    exit 1
fi
"$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" || {
    echo "ERRO: precisa de Python 3.10 ou superior."
    exit 1
}

if [ ! -d .venv ]; then
    echo "==> A criar ambiente virtual..."
    "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> A atualizar pip..."
pip install --quiet --upgrade pip

echo "==> A instalar dependencias (pode demorar)..."
pip install -r requirements-linux.txt

echo
echo "Dica (opcional, via apt):"
echo "  sudo apt install libportaudio2 libgl1 espeak-ng   # audio/voT TTS de fallback"
echo
echo "Pronto! Executa ./start.sh para comecar."