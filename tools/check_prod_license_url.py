"""Verifica que o URL de produção do license-server está gravado antes do build.

Falha (exit 1) se `PROD_LICENSE_SERVER_URL` ainda for o placeholder
(`https://licenses.maouse.example.com`) — impede distribuir um `.exe` que nunca
conseguiria ativar licenças. Usado pelo `build.bat` (passo 0) e pelos releases.

Uso:
  python tools/check_prod_license_url.py
  python tools/check_prod_license_url.py --allow-placeholder   # força (dev/QA)

Sem argumentos, o build falha enquanto o placeholder não for substituído pelo URL
real do Render (ver docs/DESKTOP_LICENSE_URL.md).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.licensing import PROD_LICENSE_SERVER_URL

_PLACEHOLDER = "https://licenses.maouse.example.com"
_ALLOW_ENV = "MAOUSE_ALLOW_PLACEHOLDER_URL"
_BAD_HINTS = ("example.com", "example.org", "placeholder", "<", ">", " ", ":memory:", "{", "}")


def url_is_ready(url: str) -> bool:
    """True se o URL parece um endpoint HTTPS real (não placeholder/gabarito)."""
    url = (url or "").strip().rstrip("/")
    if not url:
        return False
    if not url.startswith("https://"):
        return False
    return not any(hint in url for hint in _BAD_HINTS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-placeholder", action="store_true",
                    help="não falhar mesmo com placeholder (dev/QA)")
    args = ap.parse_args()

    forced = args.allow_placeholder or os.getenv(_ALLOW_ENV) == "1"
    if url_is_ready(PROD_LICENSE_SERVER_URL):
        print(f"[OK] URL de produção: {PROD_LICENSE_SERVER_URL}")
        return 0
    if forced:
        print("[AVISO] URL de produção ainda é o placeholder — build FORÇADO "
              f"(URL atual: {PROD_LICENSE_SERVER_URL})")
        return 0
    print("[ERRO] PROD_LICENSE_SERVER_URL ainda é o placeholder "
          f"({_PLACEHOLDER}).")
    print("       O .exe distribuído não conseguiria ativar licenças.")
    print("       Grava o URL real do Render em core/licensing.py "
          "(docs/DESKTOP_LICENSE_URL.md §2) ou passa --allow-placeholder "
          "para um build de dev/QA.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
