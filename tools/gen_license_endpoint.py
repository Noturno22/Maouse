"""Gera `core/_license_endpoint.py` com o URL do license-server de produção.

Porquê um ficheiro gerado e não uma env var: num build PyInstaller não existem
env vars de compilação em runtime. O utilizador final não define
MAOUSE_LICENSE_SERVER_URL, portanto o único jeito de o URL real travelhar
dentro do .exe é ser gerado para um módulo antes do bake.

Uso (normalmente chamado pelo build.bat):
    python tools/gen_license_endpoint.py                 # usa a env var
    python tools/gen_license_endpoint.py https://x.onrender.com

Sem URL (dev): escreve o placeholder, que `core/licensing.py` deteta e
reporta — é preferível a um binário silenciosamente impossibilitado.
"""
import os
import sys

OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "_license_endpoint.py",
)

TEMPLATE = '''"""GERADO por tools/gen_license_endpoint.py — nao editar a mao.

Endpoint do license-server embebido no build. Definir MAOUSE_LICENSE_SERVER_URL
antes de compilar, ou passar o URL como argumento. Ver docs/DESKTOP_LICENSE_URL.md.
"""

LICENSE_SERVER_URL = "{url}"
'''


def resolve_url(argv) -> str:
    """URL do argumento, senão da env var, senão string vazia."""
    if len(argv) > 1 and argv[1].strip():
        return argv[1].strip().rstrip("/")
    return os.environ.get("MAOUSE_LICENSE_SERVER_URL", "").strip().rstrip("/")


def main(argv) -> int:
    url = resolve_url(argv)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(url=url))
    rel = os.path.relpath(OUT_PATH, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if url:
        print(f"[licença] endpoint de produção embebido: {url}  ->  {rel}")
    else:
        print(f"[licença] AVISO: sem MAOUSE_LICENSE_SERVER_URL — o build vai "
              f"trazer o placeholder e a ativação online NÃO vai funcionar "
              f"({rel})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
