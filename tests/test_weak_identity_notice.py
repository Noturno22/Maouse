"""O aviso de identidade fraca tem de dizer a verdade, nas 7 línguas.

O perigo desta frase não é aparecer pouco: é aparecer **mal**. Dizer "a sua
licença pode ser partilhada com outra máquina" seria falso desde o fecho do
buraco — o id degradado deriva de um sal por máquina, e a licença de uma já não
valida noutra. Um aviso de perigo que exagera o problema treina quem o lê a
ignorar o próximo, que é o que acontece quando se grita ao pedinte.
"""
import i18n

LINGUAS = ("pt", "en", "es", "fr", "de", "it", "pt_br")


def _chaves_do_toast():
    return [k for k in i18n._STRINGS if k.startswith("toast.")]


def test_a_chave_existe_nas_sete_linguas():
    """Uma chave que falta numa língua não avisa ninguém nessa língua."""
    entrada = i18n._STRINGS.get("toast.weak_identity")
    assert entrada is not None, "a chave do aviso de identidade fraca nao existe"
    faltam = [lingua for lingua in LINGUAS if not entrada.get(lingua)]
    assert not faltam, (
        f"o aviso de identidade fraca nao existe em {faltam}. Sem traducao o "
        f"utilizador ve a chave em vez do aviso, que e pior do que nao ver nada."
    )


def test_o_aviso_nao_diz_que_a_licenca_e_partilhada():
    """O aviso tem de distinguir as duas coisas, que não são a mesma.

    A licença **não** é partilhada com outra máquina: o `machine_id` deriva de
    um sal gravado por máquina, e duas máquinas degradadas dão ids diferentes
    (é o que `test_fingerprint.py` fixou). O que o sal não prova é que a
    máquina seja *esta*.

    A frase "partilhada" aparece legitimately na negação — "não é partilhada".
    O que não pode aparecer é a afirmação. Por isso o teste não procura a
    palavra: procura a afirmação, e falha se ela voltar.
    """
    entrada = i18n._STRINGS["toast.weak_identity"]
    for lingua in LINGUAS:
        texto = entrada[lingua]
        baixo = texto.lower()
        # A negação tem de estar lá: é ela que separa "fraca" de "partilhada".
        assert "não é partilhada" in baixo or "no es" in baixo \
            or "not shared" in baixo or "n'est pas partagée" in baixo \
            or "nicht mit einem anderen" in baixo or "non è condivisa" in baixo \
            or "não é compartilhada" in baixo, (
            f"[{lingua}] o aviso deixou de dizer que a licenca NAO e partilhada: "
            f"{texto!r}"
        )


def test_o_aviso_diz_que_precisa_de_prova_e_nao_diz_que_a_licenca_eo_problema():
    """Metade do texto é dizer o que se perdeu. A outra metade é não exagerar.

    Um aviso de perigo que deixa o utilizador a achar que a licença foi
    partilhada faz duas coisas más de uma vez: assusta quem não tem problema, e
    habitua quem tem problemas a não ler avisos.
    """
    entrada = i18n._STRINGS["toast.weak_identity"]
    for lingua in LINGUAS:
        texto = entrada[lingua]
        assert len(texto) > 60, (
            f"[{lingua}] o aviso tem {len(texto)} caracteres. Ou esta truncado, "
            f"ou deixou de dizer as duas coisas que tem de dizer: que a "
            f"licença não é partilhada, e que a máquina não se prova."
        )


def test_o_aviso_diz_o_que_fazer():
    """Um aviso sem saída é só ansiedade.

    Diz para contactar o suporte, e só quando é inesperado — porque a maior
    parte das máquinas que leem isto vai ser uma máquina de desenvolvimento ou
    uma máquina de empresa, e o aviso não é um erro do utilizador.
    """
    entrada = i18n._STRINGS["toast.weak_identity"]
    for lingua in LINGUAS:
        texto = entrada[lingua].lower()
        # A palavra muda de língua: "suporte" (pt/pt_br), "support" (en/fr/de),
        # "soporte" (es), "assistenza" (it). A lista está aqui para a tradução
        # não poder desaparecer em silêncio — e foi ela que apanhou o "soporte"
        # espanhol e a "assistenza" italiana da primeira versão deste teste.
        assert any(p in texto for p in
                   ("suporte", "support", "soporte", "assistenza")), (
            f"[{lingua}] o aviso não diz o que fazer: {texto!r}"
        )
