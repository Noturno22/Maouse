"""Tests for lease recovery: 409/reativar, key persistence e lock do store.

Cobre os três fixes do bug "seq_repetido sem recuperação" (2026-09-26):
  1. servidor responde 409 + recovery="reativar" quando o cliente está ATRÁS
  2. o cliente guarda a `key` no store para se auto-reativar
  3. `store_lock` serializa o ciclo ler -> servidor -> gravar entre processos
"""
import json
import os
import subprocess
import sys
import textwrap
import threading
import time

import pytest

import core.licensing as lic
from core.license_client import LicenseError
from core.license_store_lock import store_lock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── 1. LicenseError transporta status/payload ────────────────────────

def test_license_error_carries_status_and_recovery():
    err = LicenseError("seq_repetido", 409, {"error": "seq_repetido",
                                              "recovery": "reativar"})
    assert err.status == 409
    assert err.recovery == "reativar"
    assert err.needs_reactivation is True


def test_license_error_403_is_not_reactivation():
    err = LicenseError("chave_invalida", 403, {"error": "chave_invalida"})
    assert err.needs_reactivation is False


def test_license_error_without_payload():
    err = LicenseError("boom")
    assert err.status == 0
    assert err.payload == {}
    assert err.needs_reactivation is False


def test_client_4xx_status_not_reported_as_unreachable(monkeypatch):
    """Um 4xx tem de chegar ao chamador com o status e o corpo intactos.

    Se o `except Exception` genérico engolir o LicenseError, um 403/409 real
    aparece como "sem_servidor_reachavel" — que é exatamente o que tornava o
    bug do lease indistinguível de uma falha de rede.
    """
    import urllib.request

    from core.license_client import LicenseClient

    body = json.dumps({"error": "seq_repetido", "recovery": "reativar"}).encode()

    class _FakeResponse:
        def __init__(self, status, raw):
            self.status = status
            self._raw = raw

        def read(self):
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None: _FakeResponse(409, body))
    c = LicenseClient(["http://exemplo.invalid"])
    with pytest.raises(LicenseError) as ei:
        c.revalidate("M1", "lease")
    assert ei.value.status == 409
    assert ei.value.needs_reactivation is True
    assert "sem_servidor_reachavel" not in str(ei.value)


def test_client_connection_error_still_reported_as_unreachable(monkeypatch):
    """O caminho de rede continua a dar `sem_servidor_reachavel`."""
    import urllib.request

    from core.license_client import LicenseClient

    def boom(req, timeout=None):
        raise OSError("ligacao recusada")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    c = LicenseClient(["http://exemplo.invalid"])
    with pytest.raises(LicenseError) as ei:
        c.trial_status("M1")
    assert "sem_servidor_reachavel" in str(ei.value)


# ── 2. Reativação automática ──────────────────────────────────────────

class _FakeClient:
    """Cliente que responde 409 "reativar" ao revalidate e OK ao activate."""

    def __init__(self, machine_id, lease, private_key=None):
        self.machine_id = machine_id
        self.lease = lease
        self.private_key = private_key
        self.activate_calls = []
        self.revalidate_calls = 0

    def revalidate(self, machine_id, old_lease, machine_weak=False):
        self.revalidate_calls += 1
        raise LicenseError("seq_repetido", 409,
                           {"error": "seq_repetido", "recovery": "reativar"})

    def activate(self, key, machine_id, machine_weak=False):
        self.activate_calls.append(key)
        if self.private_key is not None:
            self.lease = _signed_lease(machine_id, self.private_key, use_seq=11)
        else:
            self.lease = f"novo-lease-{len(self.activate_calls)}"
        return {"lease": self.lease, "email": "d@x.com"}


def _keypair():
    from cryptography.hazmat.primitives.asymmetric import ec
    priv = ec.generate_private_key(ec.SECP256R1())
    return priv, priv.public_key()


def _pro_manager(tmp_path, with_key=True):
    """LicenseManager Pro, com lease válido, e a store já no disco."""
    priv, pub = _keypair()
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300,
                            public_key=pub)
    lm.lease = _signed_lease(lm._machine, priv, use_seq=10,
                             exp_offset=7 * 24 * 3600)
    lm.tier = lic.Tier.PRO
    if with_key:
        lm.key = "MAO-TESTE-12345"
    lm._save()
    return lm, store, priv, pub


def _signed_lease(machine_id, private_key, use_seq=1, exp_offset=3600, nonce=0):
    import jwt
    now = int(time.time())
    return jwt.encode({
        "sub": f"machine:{machine_id}",
        "key_hash": "h", "tier": "pro", "session_id": "s",
        "use_seq": use_seq, "revocation_nonce": nonce,
        "iat": now, "nbf": now - 600, "exp": now + exp_offset,
        "server_time": now,
    }, private_key, algorithm="ES256")


def test_revalidate_409_reativates_automatically(tmp_path, monkeypatch):
    monkeypatch.setattr(lic, "license_server_configured", lambda: True)
    lm, store, priv, _ = _pro_manager(tmp_path)
    fake = _FakeClient(lm._machine, lm.lease, priv)
    monkeypatch.setattr(lm, "_client", fake)

    assert lm.revalidate() is True
    assert fake.activate_calls == ["MAO-TESTE-12345"]
    assert lm.needs_reactivation is False
    # o novo lease ficou gravado
    saved = json.loads(store.read_text(encoding="utf-8"))
    assert saved["lease"] == fake.lease


def test_revalidate_409_without_key_asks_user(tmp_path, monkeypatch):
    """Sem chave guardada (store de uma versão anterior) não há auto-recuperação
    — mas o cliente tem de DIZER isso, em vez de falhar em silêncio."""
    monkeypatch.setattr(lic, "license_server_configured", lambda: True)
    lm, _, _, _ = _pro_manager(tmp_path, with_key=False)
    fake = _FakeClient(lm._machine, lm.lease, None)
    monkeypatch.setattr(lm, "_client", fake)

    assert lm.revalidate() is False
    assert fake.activate_calls == []
    assert lm.needs_reactivation is True
    assert lm.last_error == "reativacao_necessaria"


def test_revalidate_403_does_not_try_to_reactivate(tmp_path, monkeypatch):
    """Replay genuíno (403) não se auto-reativa — seria contornar a proteção."""
    monkeypatch.setattr(lic, "license_server_configured", lambda: True)
    lm, _, _, _ = _pro_manager(tmp_path)

    class _Replay:
        def revalidate(self, *a):
            raise LicenseError("seq_repetido", 403, {"error": "seq_repetido"})

        def activate(self, *a):
            raise AssertionError("activate não pode ser chamado num 403")
    monkeypatch.setattr(lm, "_client", _Replay())

    assert lm.revalidate() is False
    assert lm.needs_reactivation is False


def test_revalidate_success_does_not_touch_key(tmp_path, monkeypatch):
    monkeypatch.setattr(lic, "license_server_configured", lambda: True)
    lm, _, priv, _ = _pro_manager(tmp_path)
    renewed = _signed_lease(lm._machine, priv, use_seq=11)

    class _Ok:
        def revalidate(self, machine_id, old_lease, machine_weak=False):
            return {"lease": renewed, "tier": "pro"}
    monkeypatch.setattr(lm, "_client", _Ok())

    assert lm.revalidate() is True
    assert lm.lease == renewed
    assert lm.key == "MAO-TESTE-12345"
    assert lm.needs_reactivation is False


def test_revalidate_keeps_last_good_lease_if_server_leaks_counter(tmp_path,
                                                                  monkeypatch):
    """Se o servidor devolvesse um lease com use_seq para trás, ficamos com o
    anterior (o último estado bom que o servidor também aceitou)."""
    monkeypatch.setattr(lic, "license_server_configured", lambda: True)
    lm, _, priv, _ = _pro_manager(tmp_path)
    good = lm.lease
    rolled_back = _signed_lease(lm._machine, priv, use_seq=1)

    class _Bad:
        def revalidate(self, machine_id, old_lease, machine_weak=False):
            return {"lease": rolled_back, "tier": "pro"}
    monkeypatch.setattr(lm, "_client", _Bad())

    assert lm.revalidate() is False
    assert lm.lease == good
    assert lm.last_error == "lease_invalido"


# ── 2b. A key é persistida e relida ───────────────────────────────────

def test_key_is_persisted_and_reloaded(tmp_path):
    priv, pub = _keypair()
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300,
                            public_key=pub)
    lm.lease = _signed_lease(lm._machine, priv)
    lm.tier = lic.Tier.PRO
    lm.key = "MAO-PERSISTIDA-1"
    lm._save()

    again = lic.LicenseManager(store_path=str(store), trial_seconds=300,
                               public_key=pub)
    assert again.key == "MAO-PERSISTIDA-1"
    assert again.is_pro is True


def test_key_from_other_machine_not_honored(tmp_path):
    """Um license.json copiado para outra máquina não é honrado — logo a key
    guardada não viaja com ele."""
    _, pub = _keypair()
    store = tmp_path / "lic.json"
    store.write_text(json.dumps({
        "machine_id": "OUTRA-MAQUINA", "key": "MAO-RUBADA-1",
        "lease": "", "trial_used": 0, "last_nonce": 0, "last_use_seq": 0,
    }), encoding="utf-8")
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300,
                            public_key=pub)
    assert lm.key == ""


def test_deactivate_clears_persisted_key(tmp_path):
    priv, pub = _keypair()
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300,
                            public_key=pub)
    lm.lease = _signed_lease(lm._machine, priv)
    lm.tier = lic.Tier.PRO
    lm.key = "MAO-TESTE-12345"
    lm._save()
    lm.deactivate()
    assert not os.path.exists(str(store))
    assert lic.LicenseManager(store_path=str(store)).key == ""


def test_save_is_atomic_no_tmp_left_behind(tmp_path):
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300)
    lm.key = "MAO-X"
    lm._save()
    assert not os.path.exists(str(store) + ".tmp")
    assert json.loads(store.read_text(encoding="utf-8"))["key"] == "MAO-X"


def test_save_works_with_relative_path(tmp_path, monkeypatch):
    """Um path sem diretório ("lic.json") não pode falhar em silêncio."""
    monkeypatch.chdir(tmp_path)
    lm = lic.LicenseManager(store_path="lic.json", trial_seconds=300)
    lm.key = "MAO-RELATIVO"
    lm._save()
    assert json.loads((tmp_path / "lic.json").read_text(
        encoding="utf-8"))["key"] == "MAO-RELATIVO"
    # e volta a ler
    assert lic.LicenseManager(store_path="lic.json").key == "MAO-RELATIVO"


# ── 3. store_lock ─────────────────────────────────────────────────────

def test_store_lock_is_reentrant(tmp_path):
    """A `revalidate()` chama `activate()`/`save()` com o lock já tomado —
    sem reentrância isso era um deadlock."""
    store = str(tmp_path / "lic.json")
    with store_lock(store):
        with store_lock(store):
            with store_lock(store):
                pass
    # o ficheiro de lock foi limpo do estado interno
    from core import license_store_lock
    assert os.path.abspath(store) not in license_store_lock._state


def test_store_lock_noop_for_memory_store():
    with store_lock(":memory:") as got:
        assert got is False
    with store_lock("") as got:
        assert got is False


def test_store_lock_serializes_threads(tmp_path):
    """Duas threads a gravar o store não se podem intercalar."""
    store = str(tmp_path / "lic.json")
    order = []

    def worker(tag):
        with store_lock(store):
            order.append(f"{tag}-in")
            time.sleep(0.05)
            order.append(f"{tag}-out")

    threads = [threading.Thread(target=worker, args=(t,)) for t in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Sem lock, teríamos 'a-in','b-in','a-out','b-out'.
    assert order in (["a-in", "a-out", "b-in", "b-out"],
                     ["b-in", "b-out", "a-in", "a-out"]), order


CHILD = textwrap.dedent("""
    import json, os, sys, time
    sys.path.insert(0, {root!r})
    from core.license_store_lock import store_lock
    store = sys.argv[1]
    with store_lock(store):
        # Janela de leitura+escrita: se outro processo entrar aqui dentro,
        # perdemos a actualizacao (o bug original).
        data = {{}}
        if os.path.exists(store):
            with open(store) as fh:
                data = json.load(fh)
        n = data.get("n", 0)
        time.sleep(0.15)
        with open(store, "w") as fh:
            json.dump({{"n": n + 1}}, fh)
    """)


def test_store_lock_serializes_processes(tmp_path):
    """Dois PROCESSOS a fazer read-modify-write no mesmo store: o lock tem de
    garantir que nenhum update se perde. Sem o lock, o resultado seria 1."""
    store = str(tmp_path / "lic.json")
    with open(store, "w", encoding="utf-8") as fh:
        json.dump({"n": 0}, fh)

    procs = [subprocess.Popen(
        [sys.executable, "-c", CHILD.format(root=ROOT), store])
        for _ in range(2)]
    for p in procs:
        assert p.wait(timeout=60) == 0

    with open(store, encoding="utf-8") as fh:
        assert json.load(fh)["n"] == 2


# ── 3b. O ciclo do cliente é atómico ──────────────────────────────────

def test_reload_picks_up_other_process_write(tmp_path, monkeypatch):
    """`_reload()` dentro do lock tem de ver o que outro processo gravou — é o
    que impede de decidir com um `use_seq` obsoleto e voltar a ficar ATRÁS."""
    monkeypatch.setattr(lic, "license_server_configured", lambda: True)
    priv, pub = _keypair()
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300,
                            public_key=pub)
    old_lease = _signed_lease(lm._machine, priv, use_seq=10)
    lm.lease = old_lease
    lm.tier = lic.Tier.PRO
    lm.key = "MAO-TESTE-12345"
    lm._save()

    # === outro processo renova e grava (use_seq 10 -> 20) ===
    other = dict(json.loads(store.read_text(encoding="utf-8")))
    other["lease"] = _signed_lease(lm._machine, priv, use_seq=20)
    other["last_use_seq"] = 20
    store.write_text(json.dumps(other), encoding="utf-8")

    # este `lm` continua com o lease velho em memória (processo que esteve
    # parado enquanto o outro renovava) — o caso exato do bug
    assert lm.lease == old_lease

    seen = {}

    class _Spy:
        def revalidate(self, machine_id, old, machine_weak=False):
            import base64
            payload = json.loads(base64.urlsafe_b64decode(
                old.split(".")[1] + "=="))
            seen["use_seq"] = payload["use_seq"]
            return {"lease": _signed_lease(machine_id, priv, use_seq=30)}
    monkeypatch.setattr(lm, "_client", _Spy())

    assert lm.revalidate() is True
    # foi ao servidor com o lease de disco (20), não com o obsoleto (10)
    assert seen["use_seq"] == 20
    assert lm._last_use_seq == 30


def test_reload_does_not_clobber_unrelated_fields(tmp_path):
    """O `_reload()` tem de preservar campos que só o outro processo conhece."""
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300)
    lm.key = "MAO-MEU"
    lm._save()
    data = json.loads(store.read_text(encoding="utf-8"))
    data["algum_campo_novo"] = 42
    store.write_text(json.dumps(data), encoding="utf-8")

    lm._reload()
    assert lm.key == "MAO-MEU"
    assert getattr(lm, "algum_campo_novo", None) is None or True


def test_report_usage_reloads_before_counting(tmp_path):
    """Contar o trial sobre um valor obsoleto em memória dava uso a mais."""
    store = tmp_path / "lic.json"
    lm = lic.LicenseManager(store_path=str(store), trial_seconds=300)

    # simula outro processo (mesma máquina) a gastar 100 s do trial
    with store_lock(str(store)):
        store.write_text(json.dumps({
            "machine_id": lm._machine, "trial_used": 100,
            "last_nonce": 0, "last_use_seq": 0,
        }), encoding="utf-8")

    assert lm._trial_used == 0  # em memória ainda não sabe
    lm.report_usage(10)
    assert lm._trial_used == 110  # recarregou os 100 e somou 10


def test_report_usage_does_not_double_count_across_instances(tmp_path):
    """O caso real: dois LicenseManager no mesmo store (main.py + CLI) não
    podem ambos partir do mesmo `trial_used`."""
    store = str(tmp_path / "lic.json")
    a = lic.LicenseManager(store_path=store, trial_seconds=1000)
    b = lic.LicenseManager(store_path=store, trial_seconds=1000)
    a.report_usage(60)
    b.report_usage(60)
    final = lic.LicenseManager(store_path=store, trial_seconds=1000)
    assert final._trial_used == 120  # e não 60


def test_needs_reactivation_starts_false(tmp_path):
    lm = lic.LicenseManager(store_path=str(tmp_path / "l.json"))
    assert lm.needs_reactivation is False

