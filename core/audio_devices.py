"""Query e selecao de microfones (sounddevice).

Sem dependencias pesadas: as funcoes aceitam um callable de query injetavel
para testes (os testes nao tocam em audio real).
"""
class DeviceError(Exception):
    pass


def _normalize(devices):
    out = []
    for i, d in enumerate(devices):
        if not isinstance(d, dict):
            continue
        ch = d.get("max_input_channels", 0)
        if not isinstance(ch, (int, float)):
            continue
        name = d.get("name", "")
        if not isinstance(name, str) or not name:
            name = f"Dispositivo {i}"
        if int(ch) > 0:
            out.append((i, name))
    return out


def list_input_devices(query=None):
    """Lista de (indice, nome) dos dispositivos com canais de entrada."""
    if query is None:
        import sounddevice as sd

        query = sd.query_devices
    try:
        devices = query()
    except Exception:
        return []
    return _normalize(devices)


def select_device(pref, query=None):
    """Devolve o indice audio para pref, ou None para default do sistema.

    pref vazio/None -> None (default). Match por substring do nome
    (case-insensitive); senao interpreta o pref como indice numerico.
    Falha -> DeviceError com a lista dos microfones disponiveis.
    """
    if pref is None or pref == "":
        return None
    if query is None:
        import sounddevice as sd

        query = sd.query_devices
    try:
        devices = query()
    except Exception as exc:
        raise DeviceError(f"Sem microfones: {exc}") from exc
    inputs = _normalize(devices)
    low = str(pref).lower()
    for idx, name in inputs:
        if low in name.lower():
            return idx
    if str(pref).strip().isdigit() and int(pref) in [i for i, _ in inputs]:
        return int(pref)
    available = ", ".join(name for _, name in inputs) or "nenhum"
    raise DeviceError(f"Microfone '{pref}' nao encontrado. Disponiveis: {available}")
