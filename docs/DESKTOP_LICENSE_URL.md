# Desktop — URL do License Server em Produção

> **Gap de produção (descoberto 2026-09-04, durante verificação do fluxo de licença).
> Estado em 2026-09-26: o URL de produção continua por definir, mas o placeholder
> já não falha em silêncio — ver «O que mudou em 2026-09-26».**
> Este documento descreve como o desktop descobre o servidor de licenças e o que é preciso
> fazer **antes de distribuir o `.exe`** para que a ativação de licenças funcione no cliente.

---

## O problema

O `LicenseManager` do desktop obtém o(s) URL(s) do license-server pela
`core/licensing.py:_default_endpoints()`, nesta ordem:

| # | Origem | Para quê |
|---|---|---|
| 1 | env `AIRMOUSE_LICENSE_URLS` | override: QA/dev e failover (CSV) |
| 2 | `.env` do utilizador (`core/envcfg.py`) | mesmo override, sem export no shell |
| 3 | env `AIRMOUSE_LICENSE_SERVER_URL` | **o URL de produção, injetado no build** |
| 4 | constante `PROD_LICENSE_SERVER_URL` | fallback; tem de ser o URL real |

Sem nenhuma delas, cai num **placeholder** (`licenses.maouse.example.com`, que não existe).
**Clientes não têm nem vão ter env vars nem `.env`** — portanto, num `.exe` distribuído tal
como está hoje, a ativação/validação de licença **falharia sempre** (mas o trial local
continua a funcionar).

O `tools/issue_pro_key.py` (lado operacional) usa `AIRMOUSE_LS_URL`.

## O que mudou em 2026-09-26

O gap já não é silencioso. `core/licensing.py` ganhou:

- `LICENSE_URL_NOT_CONFIGURED` — o valor placeholder, agora nomeado e detetável.
- `license_server_configured()` / `license_server_status()` — o cliente sabe dizer
  se está configurado, e porquê não está.
- `LicenseManager.__init__` faz `log.warning` com a explicação quando o endpoint
  é o placeholder, para o problema aparecer no log de arranque.
- `LicenseManager.activate()` recusa com `last_error == "servidor_nao_configurado"`
  em vez de gastar 8 s por endpoint a resolver um domínio inexistente; a UI
  distingue esse caso de "chave inválida" (`license.server_not_configured`).
- `open_checkout()` já não abre `checkout.paddle.com/0?…` no browser do
  utilizador quando o Paddle não está configurado.
- Coberto por `tests/test_license_server_url.py` (21 testes) para não regredir.

**O que falta é sempre o mesmo: um URL real de produção.** Nenhum destes valores
pode ser inventado — precisam de uma conta Render/CI e de uma conta Paddle.

## O que foi verificado (2026-09-04)

- O **fluxo completo** (trial → emitir chave `MAO-` → ativar → PRO → restart persiste → revalidate)
  **passa de ponta a ponta** contra um license-server real a correr localmente (release `4e12423`).
- As chaves pública/privada do servidor e a chave pública embutida no cliente **coincidem**
  (diferença anterior era só um newline de fim de ficheiro).
- Revalidado em 2026-09-26: `activate` + `revalidate` contra um license-server em
  `127.0.0.1:8899` → `tier=pro`, lease de 7 dias, renovação a funcionar.

## Como corrigir (ações a executar na release)

### 1. Deployar o license-server
Seguir `license-server/DEPLOY_RENDER.md` (conta Render + env vars + disco). Fica um URL real:
`https://<service>.onrender.com`.

### 2. Gravar o URL real como default de produção no build
Passar `AIRMOUSE_LICENSE_SERVER_URL=https://<service>.onrender.com` ao compilar
(ver `build.bat`), **ou** substituir o placeholder em
`PROD_LICENSE_SERVER_URL` (`core/licensing.py`). O passo 1-3 da tabela acima
significa que o `.env` do utilizador não conta — o valor tem de estar no binário.

> Igualar também `tools/issue_pro_key.py` (`AIRMOUSE_LS_URL` default) se o desktop a usar.

### 3. Rebuildar e assinar o `.exe`
Depois do bake, correr `build.bat` (que já assina com `cert\maouse.pfx`, ver
`docs/ASSINATURA_DIGITAL.md`) e redistribuir **simultaneamente** com o novo URL — nunca mudar o
URL depois de distribuir sem o rebuildar.

### 4. Smoke test de ativação no `.exe` final
Abrir o `.exe` distribuído e ativar com uma chave real → confirmar que fica PRO e que o lease
é validado (ver `Get-AuthenticodeSignature` para a assinatura e o fluxo descrito na
`PRONTIDAO_PARA_VENDA.md` §1). O log de arranque **não deve** conter o warning
`Servidor de licencas NAO configurado` — se contiver, o passo 2 falhou.

## Notas

- **Não partilhar o URL**: apesar de público, evitar documentá-lo no README do utilizador;
  deve ficar só no build e nas docs operacionais.
- **Ambiente de teste:** para apontar a um servidor local/QA, definir `AIRMOUSE_LICENSE_URLS`
  (ex.: `http://127.0.0.1:8899`) antes de correr `main.py`, ou pôr a mesma linha no `.env`.
- **Não reverter o URL a meio:** um `.exe` antigo com o placeholder deve ser substituído, não
  "reparado" server-side.
- **Chave privada:** `license-server/private.pem` é a única coisa que assina leases. Está no
  `.gitignore` (modo `600`, não rastreado) e **tem de continuar assim** — se entrar no git,
  qualquer pessoa consegue emitir chaves Pro válidas e o gate de licenciamento deixa de
  valer alguma coisa.

---

*Operacional · Luar Studio Angola · 2026. Complementa `license-server/DEPLOY_RENDER.md`,
`BUSSINES/02_EXECUCAO/PRONTIDAO_PARA_VENDA.md` e `docs/ASSINATURA_DIGITAL.md`.*
