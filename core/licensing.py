"""Licenciamento AirMouse — trial 5min server-auth + ativacao online + lease ES256 + gate."""
import base64
import json
import os
import time
import webbrowser
from enum import Enum

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from core.envcfg import env_value
from core.fingerprint import machine_id
from core.license_client import LicenseClient, LicenseError
from core.license_store_lock import store_lock
from core.log import get_logger

log = get_logger("licensing")

TRIAL_DEFAULT_SECONDS = 5 * 60
LEASE_DEFAULT_DAYS = 7

# Domínio reservado (RFC 2606) que marca "servidor de licenças NÃO configurado".
# Enquanto o endpoint de produção for este valor, a ativação online não pode
# funcionar — e o cliente passa a dizer isso em vez de falhar com um erro de
# rede genérico. Ver docs/DESKTOP_LICENSE_URL.md.
LICENSE_URL_NOT_CONFIGURED = "https://licenses.maouse.example.com"

# URL do license-server de PRODUÇÃO — FONTE ÚNICA do endpoint.
#
# Prioridade de resolução (ver docs/DESKTOP_LICENSE_URL.md):
#   1. env MAOUSE_LICENSE_URLS      — override, QA/dev e multi-endpoint
#   2. ficheiro .env do utilizador    — mesmo override, sem export no shell
#   3. core/_license_endpoint.py      — o URL real EMBUTIDO no build
#   4. esta constante                  — fallback; TEM de ser o URL real
#
# O build distribuído NÃO leva env vars nem .env, por isso o passo 3 é o que
# torna a ativação possível num .exe: `tools/gen_license_endpoint.py` escreve
# esse módulo a partir de MAOUSE_LICENSE_SERVER_URL antes do bake (ver
# build.bat) e o PyInstaller inclui-o no binário.
#
# TODO(producao): substituir pelo URL do Render e NÃO mudar depois de
# distribuir sem rebuildar (clients antigos ficam com o placeholder).
PROD_LICENSE_SERVER_URL = LICENSE_URL_NOT_CONFIGURED


def _baked_endpoint() -> str:
    """URL embebido no build, ou "" se o módulo não foi gerado (dev)."""
    try:
        from core import _license_endpoint  # type: ignore[attr-defined]
    except ImportError:
        return ""
    return (getattr(_license_endpoint, "LICENSE_SERVER_URL", "") or "").strip().rstrip("/")

_PUBLIC_KEY_PEM = os.path.join(os.path.dirname(__file__), "licensing_public_key.pem")


class Tier(Enum):
    FREE = "free"
    PRO = "pro"


PRO_LOCKED = ("snap", "voice", "two_hands", "tts", "ai", "autotune", "low_light", "trading_master")

# Produtos Paddle (Pay Links). Preencher com os IDs reais dos preços quando a
# entidade UE e o catálogo Paddle existirem. Mantido por compat (checkout).
PADDLE_PRODUCT_URLS = {
    "lifetime": env_value("MAOUSE_PADDLE_LIFETIME_URL"),
    "subscription": env_value("MAOUSE_PADDLE_SUBSCRIPTION_URL"),
    "family": env_value("MAOUSE_PADDLE_FAMILY_URL"),
    "access": env_value("MAOUSE_PADDLE_ACCESS_URL"),
    "trading_master": env_value("MAOUSE_PADDLE_TRADING_MASTER_URL"),
}


def entitlements(tier: Tier) -> dict:
    base = {"move": True, "click": True}
    pro_on = tier == Tier.PRO
    for f in PRO_LOCKED:
        base[f] = pro_on
    return base


def is_pro_locked(tier: Tier, feature: str) -> bool:
    return feature in PRO_LOCKED and tier != Tier.PRO


def _load_public_key():
    with open(_PUBLIC_KEY_PEM, "rb") as fh:
        return serialization.load_pem_public_key(fh.read())


class LicenseManager:
    def __init__(self, secret: str = "", store_path=None,
                 agency: "LicenseAgency | None" = None,
                 endpoints=None, trial_seconds=TRIAL_DEFAULT_SECONDS,
                 public_key=None):
        self._store_path = store_path or _default_store_path()
        self._agency = agency
        self._endpoints = endpoints or _default_endpoints()
        self._client = LicenseClient(self._endpoints)
        self._trial_seconds = trial_seconds
        self._public_key = public_key or _load_public_key()
        self._machine = machine_id()
        self.tier = Tier.FREE
        self.key = ""
        self.email = ""
        self.lease = ""
        self._trial_used = 0
        self._last_nonce = 0
        self._last_use_seq = 0
        self._blocked = False
        self._block_reason = ""
        self._last_error = ""
        self._needs_reactivation = False
        if not license_server_configured():
            log.warning("%s", license_server_status())
        with store_lock(self._store_path):
            self._reload()

    # ── Trial (server-authoritative + best-effort offline) ──
    def trial_used_seconds(self) -> int:
        return self._trial_used

    def trial_remaining_seconds(self) -> int:
        return max(0, self._trial_seconds - self._trial_used)

    def report_usage(self, seconds: int) -> None:
        with store_lock(self._store_path):
            self._reload()
            self._trial_used = min(self._trial_seconds,
                                    self._trial_used + max(0, seconds))
            if self._trial_used >= self._trial_seconds:
                self._blocked = True
                self._block_reason = "trial_esgotado"
            self._save()

    def reconcile_trial(self) -> None:
        """Quando há rede, o servidor é a fonte de verdade: adota o MAIOR uso
        entre local e servidor, e reporta o uso local para o servidor persistir.

        Regra anti-reset: se não há registo local do trial (ex.: ficheiro apagado)
        e o servidor não está alcançável, este aparece como "primeira vez" sem prova
        — bloqueia com pedido de ligação em vez de conceder 5 min novos.
        """
        if self.is_pro:
            return
        with store_lock(self._store_path):
            self._reload()
            had_local = self._trial_used > 0 or _store_exists(self._store_path)
            try:
                status = self._client.trial_status(self._machine)
                server_used = max(0, self._trial_seconds - status["remaining_seconds"])
            except LicenseError:
                if not had_local:
                    # sem registo local E sem servidor -> não pode provar 1ª vez
                    self._blocked = True
                    self._block_reason = "trial_requer_ligacao"
                return
            try:
                self._client.trial_report(self._machine, self._trial_used)
            except LicenseError as e:
                log.debug("Relat\u00f3rio de trial ao servidor falhou: %s", e)
            self._trial_used = max(self._trial_used, server_used)
            if self._trial_used >= self._trial_seconds:
                self._blocked = True
                self._block_reason = "trial_esgotado"
            self._save()

    def tier_pending(self) -> str:
        if self.is_pro:
            return "pro"
        if self.is_blocked():
            return "trial_esgotado"
        return "trial"

    # ── Persistência ──
    #
    # save()/load() são a API pública (compat com UI/CLI) e ficam simples. O
    # trabalho a sério está em _reload()/_save(), que ficam SEM lock e são
    # chamados de dentro de `with store_lock(...)` para tornar atómico o ciclo
    # ler → servidor → gravar. Quem segura o lock tem de repor o estado do
    # ficheiro antes de decidir, senão decide com um `use_seq` obsoleto.
    def save(self) -> None:
        with store_lock(self._store_path):
            self._save()

    def _save(self) -> None:
        if self._store_path == ":memory:":
            return
        try:
            # `or "."` porque um path relativo ("lic.json") dá dirname vazio e
            # o makedirs("") rebentava — engolido pelo except de baixo, o que
            # fazia o store nunca ser gravado, em silêncio.
            os.makedirs(os.path.dirname(self._store_path) or ".", exist_ok=True)
            # ATOMICIDADE: escreve num temporário e renomeia. Sem isto, um
            # crash a meio deixava um license.json truncado — o lease
            # deserialize mal e o utilizador perdia o Pro.
            tmp = self._store_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({
                    "lease": self.lease,
                    "email": self.email,
                    "key": self.key,
                    "machine_id": self._machine,
                    "trial_used": self._trial_used,
                    "last_nonce": self._last_nonce,
                    "last_use_seq": self._last_use_seq,
                }, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._store_path)
        except OSError as e:
            log.debug("Falha ao gravar estado de licen\u00e7a em %s: %s", self._store_path, e)

    def load(self) -> None:
        with store_lock(self._store_path):
            self._reload()

    def _reload(self) -> None:
        if self._store_path == ":memory:":
            return
        data = self._read_store()
        if data is None:
            return
        if data.get("machine_id") != self._machine:
            return  # ficheiro de outra máquina -> não honrar
        self._trial_used = int(data.get("trial_used", 0))
        self._last_nonce = int(data.get("last_nonce", 0))
        self._last_use_seq = int(data.get("last_use_seq", 0))
        # A chave é guardada para permitir REATIVAR sem o utilizador a digitar
        # (o servidor responde 409/"reativar" quando o lease guardado fica
        # atrás do servidor). Só é lida se o machine_id bater, logo um
        # license.json copiado para outra máquina não é honrado — e o servidor
        # liga 1 chave a 1 máquina, o que limita o alcance de um vazamento.
        self.key = data.get("key", "") or self.key
        if data.get("lease") and self._validate_local_lease(data["lease"]):
            self.lease = data["lease"]
            self.email = data.get("email", "")
            self.tier = Tier.PRO

    def _read_store(self):
        try:
            with open(self._store_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    # ── Validação local do lease (ES256, anti-forgery) ──
    def _verify_es256_with(self, pub_key, signing_input: bytes, raw_sig: bytes) -> bool:
        """Verifica a assinatura ES256 (raw r||s -> DER) com a chave pública."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        try:
            r = int.from_bytes(raw_sig[:32], "big")
            s = int.from_bytes(raw_sig[32:], "big")
            der_sig = encode_dss_signature(r, s)
            pub_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

    def _validate_local_lease(self, lease: str) -> bool:
        try:
            header_b64, payload_b64, sig_b64 = lease.split(".")
        except ValueError:
            return False
        try:
            header = json.loads(_b64d(header_b64))
            payload = json.loads(_b64d(payload_b64))
            raw_sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
        except Exception:
            return False
        if header.get("alg") != "ES256":
            return False  # rejeita alg:none e outras
        if not self._verify_es256_with(self._public_key,
                                       f"{header_b64}.{payload_b64}".encode(), raw_sig):
            return False
        if payload.get("sub") != f"machine:{self._machine}":
            return False
        if int(time.time()) > int(payload.get("exp", 0)):
            return False
        # Anti-replay: rejeita apenas leases ESTRITAMENTE mais antigos do que o
        # último já visto. O lease atual (use_seq/revocation_nonce iguais aos
        # últimos vistos) tem de continuar válido ao revalidar/reabrir (senão um
        # lease gravado nunca carregaria e `is_blocked()` bloquearia um PRO bom).
        if int(payload.get("revocation_nonce", -1)) < self._last_nonce:
            return False
        if int(payload.get("use_seq", -1)) < self._last_use_seq:
            return False
        # Avança monotonicamente os contadores (nunca regredem).
        self._last_nonce = max(self._last_nonce, int(payload.get("revocation_nonce", 0)))
        self._last_use_seq = max(self._last_use_seq, int(payload.get("use_seq", 0)))
        return True

    def is_pro_offline_valid(self) -> bool:
        return bool(self.lease and self._validate_local_lease(self.lease))

    # ── Ativação online ──
    def activate(self, key: str) -> bool:
        key = key.strip()
        if not key:
            self._last_error = "chave_vazia"
            return False
        if not license_server_configured():
            # Falhar aqui com uma mensagem clara é melhor do que gastar 8s por
            # endpoint a tentar resolver um domínio que não existe.
            self._last_error = "servidor_nao_configurado"
            log.warning("%s", license_server_status())
            return False
        with store_lock(self._store_path):
            self._reload()
            try:
                result = self._client.activate(key, self._machine)
            except LicenseError as exc:
                # NOTA: uma ativação falhada (chave errada, servidor em baixo) NÃO
                # bloqueia a app — apenas regista o motivo. Bloquear aqui deixava o
                # utilizador sem poder usar nem o Free depois de escrever a chave
                # com um typo.
                self._last_error = str(exc)
                log.warning("Ativacao falhou: %s", exc)
                return False
            self.lease = result["lease"]
            self.key = key
            self.email = result.get("email", "")
            self.tier = Tier.PRO
            self._last_error = ""
            self._needs_reactivation = False
            self._save()
            return True

    @property
    def last_error(self) -> str:
        """Motivo da última ativação falhada (para a UI mostrar texto útil)."""
        return self._last_error

    @property
    def needs_reactivation(self) -> bool:
        """True quando o lease guardado ficou atrás do servidor e a renovação
        falhou. Se houver `key` guardada, a recuperação foi tentada
        automaticamente; se não houver, a UI tem de pedir a chave."""
        return self._needs_reactivation

    def revalidate(self) -> bool:
        with store_lock(self._store_path):
            self._reload()
            if not self.lease:
                return False
            try:
                result = self._client.revalidate(self._machine, self.lease)
            except LicenseError as exc:
                if not exc.needs_reactivation:
                    return False
                # 409 "reativar": o lease guardado está ATRÁS do que o servidor
                # já emitiu (dois processos a escrever o store, restore de
                # backup, store copiado). Não é replay — é estado revertido, e
                # a única saída é voltar a ativar a chave. Com a chave guardada
                # fazemo-lo sem bother o utilizador.
                log.warning(
                    "Lease atrás do servidor (%s): a reativar automaticamente.",
                    exc)
                key = self.key
                if not key:
                    self._needs_reactivation = True
                    self._last_error = "reativacao_necessaria"
                    log.warning(
                        "Sem chave guardada — o utilizador tem de ativar de novo "
                        "(a chave nao foi persistida por uma versao anterior).")
                    return False
                # `activate()` é reentrante no lock (store_lock é reentrante).
                if not self.activate(key):
                    self._needs_reactivation = True
                    return False
                self._needs_reactivation = False
                return True
            # Validar localmente ANTES de gravar: `_validate_local_lease` é o
            # que avança `_last_nonce`/`_last_use_seq`. Sem isto, gravávamos o
            # lease novo com os contadores velhos e o store ficava outra vez
            # ATRÁS do servidor — que é exactamente o bug que estamos a corrigir.
            new_lease = result["lease"]
            if not self._validate_local_lease(new_lease):
                # Lease que o servidor emissou e que não valida aqui (rollback
                # de contadores, assinatura inesperada): fica o lease antigo, que
                # é o último estado bom que o servidor também aceitou.
                self._last_error = "lease_invalido"
                log.warning("Servidor devolveu um lease que não valida "
                            "localmente — mantido o anterior.")
                return False
            self.lease = new_lease
            self._last_error = ""
            self._save()
            return True

    def maybe_revalidate(self) -> None:
        if not self.is_pro:
            return
        if self._needs_revalidation():
            self.revalidate()

    def _needs_revalidation(self) -> bool:
        try:
            payload = self._decode_payload(self.lease)
            issued = int(payload.get("iat", 0))
        except Exception:
            return True
        return (time.time() - issued) >= 7 * 24 * 3600 - 3600  # ~1h antes de expirar 7d

    def _decode_payload(self, lease: str) -> dict:
        payload_b64 = lease.split(".")[1]
        return json.loads(_b64d(payload_b64))

    # ── Bloqueio / gate ──
    def is_blocked(self) -> bool:
        if self.tier == Tier.PRO:
            if not self._validate_local_lease(self.lease):
                self._blocked = True
                self._block_reason = "lease_invalido_ou_expirado"
                return True
            return False
        if self._blocked:
            return True
        if self._trial_used >= self._trial_seconds:
            return True
        return False

    def block_reason(self) -> str:
        if self._block_reason:
            return self._block_reason
        return "trial_esgotado" if self.is_blocked() else ""

    # ── Compat com UI / CLI / tools (API preservada) ──
    @property
    def is_pro(self) -> bool:
        return self.tier == Tier.PRO

    def can(self, feature: str) -> bool:
        return bool(entitlements(self.tier).get(feature, True))

    def deactivate(self) -> None:
        with store_lock(self._store_path):
            self.tier = Tier.FREE
            self.key = ""
            self.email = ""
            self.lease = ""
            self._blocked = False
            self._block_reason = ""
            self._last_error = ""
            self._needs_reactivation = False
            if os.path.exists(self._store_path):
                try:
                    os.remove(self._store_path)
                except OSError as e:
                    log.debug("Falha ao remover store de licen\u00e7a em %s: %s",
                              self._store_path, e)

    def checkout_urls(self, vendor_id: int) -> dict[str, str]:
        url = PADDLE_PRODUCT_URLS.get("lifetime")
        payment = PADDLE_PRODUCT_URLS.get("subscription")
        family = PADDLE_PRODUCT_URLS.get("family")
        access = PADDLE_PRODUCT_URLS.get("access")
        trading = PADDLE_PRODUCT_URLS.get("trading_master")
        return {
            "lifetime": url or f"https://checkout.paddle.com/{vendor_id}?product=maouse-pro-lifetime",
            "subscription": payment or f"https://checkout.paddle.com/{vendor_id}?product=maouse-pro-subscription",
            "family": family or f"https://checkout.paddle.com/{vendor_id}?product=maouse-family",
            "access": access or f"https://checkout.paddle.com/{vendor_id}?product=maouse-pro-access",
            "trading_master": trading or f"https://checkout.paddle.com/{vendor_id}?product=maouse-trading-master",
        }

    def open_checkout(self, product: str, vendor_id: int) -> bool:
        # Sem vendor_id e sem URL de produto configurada, `checkout_urls` cairia
        # no placeholder "checkout.paddle.com/0?..." e abriria uma página de
        # erro no browser do utilizador. Melhor falhar em silêncio com aviso.
        if not vendor_id and not PADDLE_PRODUCT_URLS.get(product):
            log.warning(
                "Checkout de '%s' nao aberto: Paddle nao configurado. Definir "
                "MAOUSE_PADDLE_%s_URL ou MAOUSE_PADDLE_VENDOR_ID "
                "(ver docs/SEGURANCA_LICENCA.md).",
                product, product.upper(),
            )
            return False
        urls = self.checkout_urls(vendor_id)
        url = urls.get(product)
        if not url:
            return False
        try:
            return bool(webbrowser.open(url, new=2))
        except webbrowser.Error:
            return False

    # issue_pro_key / validate_key: mantidos NA API pública mas já NÃO usados
    # no caminho de produção (o servidor emite; o cliente só ativa online).
    def issue_pro_key(self, email: str) -> str:
        raise NotImplementedError(
            "Emissão de chaves é feita pelo servidor (license-server). "
            "Use tools/issue_pro_key.py remoto.")


class LicenseAgency:
    """Interface opcional para validação ONLINE (compat mit UI).

    Mantida da API anterior; o caminho de produção é a ativação online
    (LicenseManager.activate / lease ES256), não a validação offline.
    """

    def online_validate(self, license_doc: str) -> bool:
        return True


# ── Helpers ─────────────────────────────────────────────────────────────────
def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _default_store_path() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "AirMouse", "license.json")


def _store_exists(store_path: str) -> bool:
    return store_path != ":memory:" and os.path.exists(store_path)


def _default_endpoints():
    """Resolve a lista de endpoints do license-server (ver ordem em
    PROD_LICENSE_SERVER_URL). Sempre devolve pelo menos um."""
    raw = env_value("MAOUSE_LICENSE_URLS")
    if raw:
        urls = [u.strip().rstrip("/") for u in raw.split(",") if u.strip()]
        if urls:
            return urls
    configured = (env_value("MAOUSE_LICENSE_SERVER_URL")
                  or _baked_endpoint()
                  or PROD_LICENSE_SERVER_URL)
    return [configured.strip().rstrip("/")]


def license_server_configured() -> bool:
    """True se o endpoint de produção é um URL real (não o placeholder).

    Com False, a ativação online é IMPOSSÍVEL — o trial local ainda funciona,
    mas `--activate-key` e a renovação de lease vão falhar. Chamar isto no
    arranque evita distribuir um build que só falha em silêncio.
    """
    return not all(_is_placeholder(u) for u in _default_endpoints())


def _is_placeholder(url: str) -> bool:
    return url.rstrip("/") == LICENSE_URL_NOT_CONFIGURED


def license_server_status() -> str:
    """Mensagem legível para o utilizador quando o servidor não está configurado."""
    if license_server_configured():
        return ""
    return (
        "Servidor de licencas NAO configurado: o endpoint de producao ainda e o "
        f"placeholder ({LICENSE_URL_NOT_CONFIGURED}). A ativacao online de chaves "
        "Pro e a renovacao de lease nao vao funcionar. Definir "
        "MAOUSE_LICENSE_SERVER_URL (build) ou MAOUSE_LICENSE_URLS (dev) — "
        "ver docs/DESKTOP_LICENSE_URL.md."
    )


_ACTIVE: "LicenseManager | None" = None


class UsageWatchdog:
    """Reporta o tempo de uso efetivo ao trial enquanto está Free.

    Chamado ``tick()`` a cada frame processado. Só reporta quando não é Pro nem
    está bloqueado; o tempo decorrido é acumulado a partir do último tick.
    Quando o trial esgota, marca ``state["license_blocked"]=True`` para o gate
    de ``process_frame`` bloquear o movimento. Partilhado entre o preview
    OpenCV (main.py) e a janela PySide6 (main_window.py).
    """

    def __init__(self, lic: "LicenseManager", state: dict):
        self._lic = lic
        self._state = state
        self._t0 = time.time()

    def tick(self) -> None:
        if self._lic.is_pro or self._lic.is_blocked():
            return
        now = time.time()
        delta = int(now - self._t0)
        self._t0 = now
        if delta >= 1:
            self._lic.report_usage(delta)
            if self._lic.is_blocked():
                self._state["license_blocked"] = True


def set_active_license(manager: "LicenseManager") -> None:
    global _ACTIVE
    _ACTIVE = manager


def active_license() -> "LicenseManager":
    return _ACTIVE or LicenseManager()


def active_tier() -> Tier:
    return active_license().tier


__all__ = [
    "Tier", "PRO_LOCKED", "entitlements", "is_pro_locked",
    "LicenseManager", "LicenseAgency", "UsageWatchdog",
    "set_active_license", "active_license", "active_tier",
    "license_server_configured", "license_server_status",
    "LICENSE_URL_NOT_CONFIGURED",
]
