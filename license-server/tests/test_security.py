"""Leases ES256: assinatura com chave privada via caminho OU conteúdo PEM.

O conftest carrega as chaves por caminho (envs apontam para ficheiros). Aqui
forçamos o modo Render: MAOUSE_LS_PRIVATE_KEY/PUBLIC_KEY contêm o PEM literal
multi-linha, como quem cola o valor no painel do Render.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import security
from jwt import InvalidSignatureError


@pytest.fixture
def content_keys(monkeypatch):
    """Troca as envs de caminho para o conteúdo PEM (modo Render)."""
    with open(security._private_key_path(), "rb") as fh:
        priv_pem = fh.read().decode()
    with open(os.environ["MAOUSE_LS_PUBLIC_KEY"], "rb") as fh:
        pub_pem = fh.read().decode()
    monkeypatch.setenv("MAOUSE_LS_PRIVATE_KEY", priv_pem)
    monkeypatch.setenv("MAOUSE_LS_PUBLIC_KEY", pub_pem)


def test_sign_decode_roundtrip_with_content_envs(content_keys):
    claims = {"sub": "machine:abc", "tier": "pro", "use_seq": 3}
    token = security.sign(claims)
    decoded = security.decode_jwt(token)
    assert decoded["tier"] == "pro"
    assert decoded["use_seq"] == 3


def test_tampered_token_rejected_with_content_envs(content_keys):
    token = security.sign({"sub": "machine:abc", "tier": "pro"})
    # Adultera o 1.º carácter da assinatura (bits significativos). O último
    # carácter base64url pode seguir bits descartados -> assinatura íntegra.
    sig = token.split(".")[2]
    repl = "A" if sig[0] != "A" else "B"
    tampered = token[: -len(sig)] + repl + sig[1:]
    with pytest.raises(InvalidSignatureError):
        security.decode_jwt(tampered)


class TestVariavelDefinidaEVazia:
    """`os.getenv(nome, default)` só usa o default quando a variável **não existe**.

    Quando existe e está vazia devolve `""`, e o `default` nunca é tocado. É a
    diferença entre "defini MAOUSE_LS_PRIVATE_KEY mas deixei-a vazia" e "a
    variável não existe": no Render, onde o `private.pem`
    do repositório não está, a primeira dava `open("")` -> FileNotFoundError na
    **primeira activação**, com health checks a passar e a landing a servir.
    Ninguém descobre isso até haver uma compra para activar.

    Estes testes existem para o erro dizer o que falta, não para o `""` passar a
    ser-o-key do default: `_load_public_key` trata `""` como "usa a emparelhada"
    de propósito (dev), e isso não deve mudar.
    """

    def test_a_privada_vazia_diz_qual_variavel_falta(self, monkeypatch):
        monkeypatch.setenv("MAOUSE_LS_PRIVATE_KEY", "")
        with pytest.raises(RuntimeError) as exc:
            security.sign({"sub": "machine:abc"})
        assert "MAOUSE_LS_PRIVATE_KEY" in str(exc.value)
        # o erro tem de ser sobre a configuração, não um "no such file: ''"
        assert "No such file" not in str(exc.value)

    def test_publica_sem_emparelhada_diz_qual_variavel_falta(self, monkeypatch):
        monkeypatch.setenv("MAOUSE_LS_PUBLIC_KEY", "")
        monkeypatch.setenv("MAOUSE_LS_PRIVATE_KEY", "C:/nao/existe/private.pem")
        with pytest.raises(RuntimeError) as exc:
            security._load_public_key()
        assert "MAOUSE_LS_PUBLIC_KEY" in str(exc.value)

    def test_apagar_a_variavel_continua_a_usar_o_default(self, monkeypatch):
        """O outro lado da distinção: ausente ≠ vazia.

        Sem a variável, `_private_key_path()` tem de continuar a devolver o
        `private.pem` ao lado do módulo — que é como o dev funciona sem `.env`.
        """
        monkeypatch.delenv("MAOUSE_LS_PRIVATE_KEY", raising=False)
        assert security._private_key_path().endswith("private.pem")
        assert os.path.isabs(security._private_key_path())
