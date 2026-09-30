"""Spy das caixas de mensagem do diálogo de licença.

`ModernMessageBox.information()` chama `exec()`, que é um event loop modal:
sem um substituto, qualquer teste que dispare um aviso bloqueia para sempre.
O substituto antigo era um `pass` mudo, e por isso nenhuma These tests
afirmavam nada sobre a mensagem — trocavam o `QMessageBox` por uma caixa
que aprova tudo e desliga o alarme.

Este spy regista o que foi mostrado, para o teste poder afirmar que o
utilizador foi avisado. Vive num módulo só porque dois ficheiros de teste
precisam dele e duas cópias escritas à mão divergem — que é a mesma lição
que o `BADGES`/`GESTURE_LABELS` e as teclas do `--record` já deram.
"""


class MessageSpy:
    """Regista as chamadas a `show_information` / `show_warning` / `show_error`."""

    def __init__(self):
        self.calls = []

    # ── o substituto em si ────────────────────────────────────────────────
    def _record(self, kind, parent, title, text):
        self.calls.append({"kind": kind, "parent": parent,
                           "title": title, "text": text})

    def information(self, parent, title, text):
        self._record("information", parent, title, text)

    def warning(self, parent, title, text):
        self._record("warning", parent, title, text)

    def error(self, parent, title, text):
        self._record("error", parent, title, text)

    # ── o que os testes perguntam ──────────────────────────────────────────
    def of_kind(self, kind):
        """Todas as chamadas de um tipo, por ordem."""
        return [c for c in self.calls if c["kind"] == kind]

    def titles(self, kind=None):
        return [c["title"] for c in self.calls if kind is None or c["kind"] == kind]

    def texts(self, kind=None):
        return [c["text"] for c in self.calls if kind is None or c["kind"] == kind]

    @property
    def count(self):
        return len(self.calls)

    def said_something_about(self, fragment):
        """True se alguma mensagem contiver o fragmento.

        Comparado por subcadeia e não por igualdade: a igualdade exacta
        obrigaria o teste a repetir a string da fonte, e uma segunda cópia
        é uma coisa que diverge em silêncio.
        """
        return any(fragment in t for t in self.texts())

    def __repr__(self):
        return f"<MessageSpy {len(self.calls)} chamada(s): {self.titles()}>"


def install(monkeypatch, license_dialog_module):
    """Instala o spy e devolve-o.

    Os nomes sao `show_information` etc. no modulo do dialogo, e nao no
    `ui.modern_messagebox`: o dialogo faz `from ... import show_information`,
    por isso o que ele chama em tempo de execucao e o nome que tem no
    proprio modulo. Fazer patch do modulo de origem nao chegaria.

    So e instalado o que o dialogo importa. `show_error` chegou a ser
    importado e nao usado — o `ruff` removeu-o, e um spy que insistisse em
    patchar um nome ausente rebentava em todos os testes sem dizer nada de
    util. Nao e um guard: o que interessa e o feedback que o utilizador
    recebe, e um `show_error` que ninguem chama nao da feedback a ninguem.
    """
    spy = MessageSpy()
    for kind in ("information", "warning", "error"):
        nome = f"show_{kind}"
        if hasattr(license_dialog_module, nome):
            monkeypatch.setattr(license_dialog_module, nome, getattr(spy, kind))
    return spy
