"""Envia entradas hostis ao host nativo real e verifica que nao morre.

Os 29 testes de `tests/test_remote_rfcomm.py` correm contra um host falso, e o
`--selftest-envelope` so prova a saida com 5 payloads fixos. Fica por provar o
que o executavel vero faz com o que um cliente de telemovel malformado lhe
manda: um bug no Fortune nao pode derrubar o servidor do PC.

Um acesso invalido no Windows sai com 0xC0000005 (3221225477 em `cmd`,
-1073741819 em `subprocess`). Aqui interessa que isso NUNCA aconteca: o servidor
tem de recusar a entrada e continuar.

Nao e testeautomatico porque precisa do executavel compilado; corre-se a mao.
"""

from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

EXE = Path("build/rfcomm-host/maouse-bluetooth-host.exe")

# Nao interessa o valor exacto do rc, so saber se e um acesso invalido.
ACESSO_INVALIDO = {3221225477, -1073741819}

# O `conn == 0` e o canal de controlo (ver CONN_CONTROLE no host).
CONN_CONTROLE = 0


def envelope(conn: int, payload: bytes) -> bytes:
    return struct.pack("<II", 4 + len(payload), conn) + payload


def correr(entrada: bytes, rotulo: str) -> None:
    p = subprocess.Popen(
        [str(EXE)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    try:
        out, err = p.communicate(entrada, timeout=25)
    except subprocess.TimeoutExpired:
        # Preso num `read` a espera de bytes que nunca chegao e tambem um
        # estrago: um servidor que fica pendurado e pior do que um que diz nao.
        p.kill()
        p.communicate()
        print(f"  [PRESO   ] {rotulo}: 25 s sem sair")
        return

    rc = p.returncode
    if rc in ACESSO_INVALIDO:
        estado = "ACESSO INVALIDO"
    elif rc == 0:
        estado = "saida limpa"
    else:
        estado = f"saida controlada rc={rc}"

    stderr = " | ".join(
        ln for ln in err.decode("utf-8", "replace").replace("\r", "").split("\n") if ln.strip()
    )
    print(f"  [{estado:<17}] {rotulo}")
    if stderr:
        print(f"                       stderr: {stderr[:150]}")


def main() -> int:
    if not EXE.is_file():
        print(f"falta {EXE} — compila com: native\\build-host.bat")
        return 1

    print("entradas hostis ao host nativo real:")
    # Paragem limpa: o unico caminho que deve sair com 0.
    correr(envelope(0, b""), "envelope de paragem (referencia)")
    # Payload de controlo que nao e JSON: `conn=0` com corpo invalido.
    correr(envelope(0, b"isto nao e json"), "controlo com lixo")
    # Bytes aleatorios que nao sao envelope nenhum.
    correr(bytes(range(256)), "256 bytes aleatorios")
    # Cabecalho truncado: o processo tem de sair sem inventar uma ligacao.
    correr(struct.pack("<II", 40, 1)[:6], "cabecalho cortado a meio")
    # Tamanho declarado absurdo: o host nao pode tentar ler 4 GiB.
    correr(struct.pack("<II", 0xFFFFFFFF, 1), "tamanho 0xFFFFFFFF")
    # Tamanho menor que o proprio cabecalho: leitura sob-rosada.
    correr(struct.pack("<II", 0, 7), "tamanho 0 com conn 7")
    # ligacao inexistente: nao ha socket 99, nao ha de rebentar.
    correr(envelope(99, b'{"cmd":"ping"}'), "conn inexistente")
    # Duas mensagens de uma vez, como o pipe faz quando o writer agrupa.
    correr(envelope(0, b"") + envelope(98, b"x"), "paragem + conn inexistente")

    # Fronteira do teto. `MAX_ENVELOPE` = 64 KiB + 4 (o `conn`), porque um
    # payload no maximo do wire (65536) chega ao host como tamanho 65540. Estes
    # dois casos sao os que provam que o teto esta no sitio certo: recusa
    # 65541 mas tem de aceitar 65540, senao a maior mensagem legal do telefone
    # nunca chegava ao PC.
    print("\nfronteira do teto (MAX_ENVELOPE = 65540):")
    maior_legal = envelope(CONN_CONTROLE, b"\x5a" * (64 * 1024))
    correr(maior_legal + envelope(0, b""), "payload no maximo (65540) - tem de aceitar")
    um_a_mais = struct.pack("<II", 64 * 1024 + 5, CONN_CONTROLE) + b"\x5a" * (64 * 1024 + 1)
    correr(um_a_mais, "65541 - tem de recusar")

    print("\nnenhum acesso invalido acima = o host recusa entradas e continua")
    return 0


if __name__ == "__main__":
    sys.exit(main())
