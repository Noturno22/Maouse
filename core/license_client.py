"""Cliente HTTPS para o License Server (urllib + endpoint failover)."""
import json
import urllib.error
import urllib.request


class LicenseError(Exception):
    """Erro de licença (HTTP 4xx com corpo).

    Transporta o `status` e o corpo inteiro para o cliente distinguir
    situações que partilham o mesmo código — em especial o **409** de
    `/api/v1/revalidate`, que significa "o lease guardado está atrás do
    servidor, reativa a chave" e não "erro genérico".
    """

    def __init__(self, message: str, status: int = 0, payload: dict | None = None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}

    @property
    def recovery(self) -> str:
        """Pista de recuperação do servidor ("reativar"), ou ""."""
        return self.payload.get("recovery", "")

    @property
    def needs_reactivation(self) -> bool:
        """True quando o servidor diz explicitamente para reativar a chave."""
        return self.status == 409 and self.recovery == "reativar"


def _try_json(raw: bytes) -> dict:
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        return {}


class LicenseClient:
    def __init__(self, endpoints, timeout=8):
        self._endpoints = [e.rstrip("/") for e in endpoints]
        self._timeout = timeout

    def _request(self, method, path, payload=None):
        last_err = None
        for base in self._endpoints:
            url = base + path
            data = None
            headers = {}
            if payload is not None:
                data = json.dumps(payload).encode()
                headers["Content-Type"] = "application/json"
                req = urllib.request.Request(url, data=data, headers=headers, method=method)
                try:
                    with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                        status = int(getattr(resp, "status", 200))
                        raw = resp.read()
                        if status >= 400:
                            body = _try_json(raw)
                            if status >= 500:
                                # erro de servidor -> tentar o próximo endpoint
                                last_err = body.get("error", f"http {status}")
                                continue
                            raise LicenseError(body.get("error", f"http {status}"),
                                               status, body)
                        return json.loads(raw.decode("utf-8")) if raw else {}
                except urllib.error.HTTPError as exc:
                    try:
                        body = json.loads(exc.read().decode("utf-8"))
                    except Exception:
                        body = {}
                    if exc.code >= 500:
                        last_err = body.get("error", f"http {exc.code}")
                        continue
                    raise LicenseError(body.get("error", f"http {exc.code}"),
                                       exc.code, body) from exc
                except LicenseError:
                    # Um 4xx que o urlopen devolveu em vez de levantar chega
                    # aqui já transformado em LicenseError. NÃO pode cair no
                    # `except Exception` seguinte — senão um 403/409 real
                    # aparecia ao utilizador como "sem_servidor_reachavel",
                    # que é o que torna estes erros impossíveis de diagnosticar.
                    raise
                except Exception as exc:
                    last_err = exc
                    continue
        raise LicenseError(f"sem_servidor_reachavel: {last_err}")

    # `machine_weak` diz ao servidor que o `machine_id` não foi derivado de
    # hardware. Vai em todos os pedidos, e não só no `activate`, porque o trial
    # também é chaveado por `machine_id`: é o mesmo id a ser usado como prova
    # de vez, e é o mesmo id a poder ser clonado. O default e `False` para que
    # um cliente velho — que nao manda o campo — continue a ser aceito, e para
    # que o servidor tenha de tratar a ausencia como "nao sei", nunca como
    # "forte".
    def activate(self, key, machine_id, machine_weak=False):
        return self._request("POST", "/api/v1/activate",
                             {"key": key, "machine_id": machine_id,
                              "machine_weak": bool(machine_weak)})

    def revalidate(self, machine_id, old_lease, machine_weak=False):
        return self._request("POST", "/api/v1/revalidate",
                             {"machine_id": machine_id, "old_lease": old_lease,
                              "machine_weak": bool(machine_weak)})

    def trial_start(self, machine_id, machine_weak=False):
        return self._request("POST", "/api/v1/trial/start",
                             {"machine_id": machine_id,
                              "machine_weak": bool(machine_weak)})

    def trial_report(self, machine_id, used_seconds, machine_weak=False):
        return self._request("POST", "/api/v1/trial/report",
                             {"machine_id": machine_id,
                              "used_seconds": used_seconds,
                              "machine_weak": bool(machine_weak)})

    def trial_status(self, machine_id):
        return self._request("GET", f"/api/v1/trial/status?machine_id={machine_id}")
