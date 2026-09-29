"""Lock de ficheiro para o store de licença (`~/AirMouse/license.json`).

O store é um read-modify-write com estado anti-replay monotónico
(`last_nonce`, `last_use_seq`). Com dois processos a partilhar o ficheiro — um
`main.py` e uma ferramenta de linha de comandos, por exemplo — ambos podiam ler
o mesmo `use_seq` e gravar por cima, deixando o cliente ATRÁS do servidor. Daí
resultava um `seq_repetido` sem recuperação possível.

Este lock serializa o ciclo completo (ler → contactar o servidor → gravar), não
só a escrita, que é o que elimina a corrida.

Notas de implementação:
- O lock tem de fechar DOIS buracos, e são independentes:
  · entre PROCESSOS: `flock`/`msvcrt.locking`;
  · entre THREADS do mesmo processo: os locks do SO são por *file description*,
    logo duas threads a usar o mesmo handle NÃO se bloqueiam sozinhas. Um
    `threading.RLock` por path faz essa parte.
- O lock tem de ser REENTRANTE no mesmo thread: a `revalidate()` segura-o e
  chama `activate()`/`save()`, que o voltam a tomar. Como o lock do SO não
  permite isso no mesmo handle, a profundidade é rastreada POR THREAD
  (threading.local) e o lock do SO só é tomado na entrada mais externa.
- Consequência de a profundidade ser por thread: duas threads diferentes
  tratadas como Level 0, ou seja a segunda bloqueia no `RLock` em vez de
  escaparem para a secção crítica sem lock nenhum.
- POSIX usa `fcntl.flock`; Windows usa `msvcrt.locking`, que é onde o Mãouse é
  realmente distribuído.
"""
import contextlib
import os
import threading

# store_path -> {"guard": RLock, "fh": handle, "users": threads attached}
_state: dict = {}
_state_guard = threading.Lock()
_local = threading.local()


def _depths() -> dict:
    """Mapa path -> profundidade, por thread (o `store_lock` é reentrante)."""
    depths = getattr(_local, "depths", None)
    if depths is None:
        depths = {}
        _local.depths = depths
    return depths


@contextlib.contextmanager
def store_lock(store_path: str):
    """Lock exclusivo sobre `store_path`. Reentrante no mesmo thread.

    No-op para store paths em memória (`:memory:`) ou vazios.
    """
    if not store_path or store_path == ":memory:":
        yield False
        return

    key = os.path.abspath(store_path)
    lock_path = key + ".lock"
    depths = _depths()
    reentrant = depths.get(key, 0) > 0

    with _state_guard:
        entry = _state.get(key)
        if entry is None:
            os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
            entry = {"guard": threading.RLock(), "fh": open(lock_path, "a+b"),
                     "users": 0}
            _state[key] = entry
        # `users` conta quem está dentro E quem está à espera, para o handle só
        # ser fechado quando já ninguém precisa dele.
        entry["users"] += 1

    try:
        if reentrant:
            depths[key] += 1
            try:
                yield True
            finally:
                depths[key] -= 1
            return

        with entry["guard"]:
            _lock_os(entry["fh"])
            depths[key] = 1
            try:
                yield True
            finally:
                depths[key] = 0
                _unlock_os(entry["fh"])
    finally:
        with _state_guard:
            entry["users"] -= 1
            if entry["users"] == 0 and _state.get(key) is entry:
                _state.pop(key, None)
                entry["fh"].close()


def _lock_os(fh) -> None:
    try:
        import fcntl
    except ImportError:
        import msvcrt
        fh.seek(0)
        # O locking do Win32 precisa de pelo menos 1 byte para assentar.
        if fh.read(1) == b"":
            fh.write(b"\0")
            fh.flush()
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)


def _unlock_os(fh) -> None:
    try:
        import fcntl
    except ImportError:
        import msvcrt
        fh.seek(0)
        with contextlib.suppress(OSError):
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
