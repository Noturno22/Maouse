# Deploy do License Server no Render

> Guia operacional **v2.1** para pôr o license server online e fazer o *bake* do
> URL de produção no desktop e no mobile.
> **Pré-requisito:** o código já está pronto (67 testes a passar, ruff limpo) e o
> `render.yaml` (na **raiz** do repo) + `Dockerfile` existem. Isto requer **a tua conta Render** (execução manual aqui).
>
> **Estado atual:** plano **free** (demo, dados efémeros). Para produção, ver §9.
>
> **Correção v2.1 (2026-09-15):** o `render.yaml` foi **movido para a raiz do repo**
> (`render.yaml`, não `license-server/render.yaml`) — o Render só deteta Blueprints
> com `render.yaml` na raiz por defeito. O `dockerfilePath` aponta para
> `./license-server/Dockerfile`, que usa paths relativos ao build context da raiz.

---

## 0. Estado verificado (v1.1)

Antes de começares, fica registado o que já está confirmado e corrigido:

| Item | Estado | Commit |
|---|---|---|
| `render.yaml` (na raiz) + `Dockerfile` existem e estão corretos | ✅ | `5befa60` |
| Keypair ES256 do servidor == pública embutida no cliente | ✅ (via `tools/check_keypair.py`) | `abb0c60` |
| `AIRMOUSE_LS_PRIVATE_KEY` aceita **conteúdo PEM** direto no env (Render) | ✅ fix + teste | `41c66a7` |
| `AIRMOUSE_LS_PUBLIC_KEY` aceita **conteúdo PEM** direto no env | ✅ já suportava | — |
| Mobile honra `EXPO_PUBLIC_LICENSE_SERVER_URL` (era ignorada) | ✅ fix | `41c66a7` |
| Testes license-server | ✅ 41 passed | — |
| Ruff license-server / tsc mobile | ✅ limpo | — |

> Estas duas correções eram bugs que **iam falhar no deploy**: a privada colada
> como PEM rebentaria `500` em cada emissão/validação de lease, e o `.env` do
> mobile era silenciosamente ignorado (ficaria a apontar para `license.maouse.app`).

---

## 1. Organização (Blueprint vs Manual)

| Via | Quando | Comando/UI |
|---|---|---|
| **Blueprint (recomendado)** | Primeira vez: liga o repo e aplica `render.yaml` (na raiz) | Dashboard Render → *New +* → *Blueprint* → escolhe o repo |
| Manual | Já tens um serviço e só queres ligar o Dockerfile | *New +* → *Web Service* → runtime Docker |

> Nota: o repo é **`Noturno22/Maouse`** (renomeado de AirMouse). Qualquer das vias vai
> aceder a esse repo. Se o repo for privado, liga a conta GitHub ao Render e usa **GitHub deploy**.

---

## 2. Variáveis a definir no painel

O `render.yaml` já define `AIRMOUSE_MOBILE_PRODUCT_ID=maouse_mobile_pro`,
`AIRMOUSE_MOBILE_DEV_ALLOW=0`, SMTP desligado, DB em `/data/license.db`.

**Tens de preencher manualmente as `sync: false`** (Render nunca as mostra/tira do git):

### Obrigatórias
| Var | Valor |
|---|---|
| `AIRMOUSE_LS_ADMIN_TOKEN` | Token forte aleatório (ex.: `openssl rand -hex 24`). Usado como **senha de login** do painel admin e nos endpoints `/admin/*`. |
| `AIRMOUSE_LS_ADMIN_SESSION_SECRET` | Chave forte aleatória (ex.: `openssl rand -hex 24`). Usada para assinar os cookies de sessão do painel admin. |
| `AIRMOUSE_LS_PRIVATE_KEY` | Conteúdo **integral** de `license-server/private.pem` |
| `AIRMOUSE_LS_PUBLIC_KEY` | Conteúdo **integral** de `license-server/public.pem` |

> ⚠️ **Cola o PEM completo, multi-linha**, tal como está no ficheiro (começa em
> `-----BEGIN PRIVATE KEY-----`, acaba em `-----END PRIVATE KEY-----`). O Render
> aceita valores com quebras de linha *as-is*. É **este** keypair obrigatoriamente:
> o cliente já tem a pública emparelhada embutida em `core/licensing_public_key.pem`.

### IAP mobile (endpoint `mobile/entitle`)
| Var | Valor |
|---|---|
| `AIRMOUSE_GOOGLE_PLAY_CREDENTIALS_JSON` | JSON completo da conta de serviço Google (permissão **Android Publisher API**). Sem isto o mobile/entitle só corre em modo dev. |

> **Cuidado:** é um JSON grande (várias linhas). Cola-o intacto. Se o Render
> trunca ou foge aspas, usa Render's *Secret Files* ou monta um ficheiro `.json`

### Opcionais (papel/postal de chaves MAO-)
- `AIRMOUSE_PADDLE_WEBHOOK_SECRET`, `AIRMOUSE_PADDLE_VENDOR_ID`, `AIRMOUSE_PADDLE_API_KEY`
- `AIRMOUSE_SMTP_HOST/PORT/USER/PASSWORD/FROM` — e `AIRMOUSE_SMTP_ENABLED=1`

---

## 3. Disco persistente

- O `render.yaml` aponta `AIRMOUSE_LS_DB=/data/license.db`.
- **Plano free:** o Render **não suporta disco persistente** — `/data` é efémero e a base
  reseta a cada redeploy. Adequado para demo/testes. O serviço também adormece após
  ~15 min sem tráfego (a 1ª chamada demora ~30–60 s a acordar).
- **Plano starter (US$7/mês):** o bloco `disk:` no `render.yaml` deve ser descomentado e o
  `plan:` mudado para `starter` — o disco passa a ser persistente entre redeploys.

---

## 4. Confirmar o deploy

Após o deploy, no painel Render copia a URL (`https://<service>.onrender.com`).

```bash
curl https://<service>.onrender.com/health
# → {"status":"ok", ...}  (200)
```

### Painel admin

O painel admin fica em `https://<service>.onrender.com/admin/login`.

- **Senha de login:** valor de `AIRMOUSE_LS_ADMIN_TOKEN` (o mesmo token usado em `/admin/*`).
- **Áreas disponíveis:** dashboard, clientes/chaves (CRUD), chat, emails, estatísticas.
- **Dados:** no plano free, os dados do painel (clientes, chaves, chats) são efémeros e
  perdem-se a cada redeploy. No plano starter com disco, são persistentes.

Teste rápido do endpoint mobile em **modo dev** (só se `AIRMOUSE_MOBILE_DEV_ALLOW=1`):

```bash
curl -s -X POST https://<service>.onrender.com/api/v1/mobile/entitle \
  -H "Content-Type: application/json" \
  -d '{"purchase_token":"test_abc","product_id":"maouse_mobile_pro","package_name":"com.airmouse.mobile","device_id":"dev-1"}'
```

> Na devo a resposta `403 play_nao_configurado` se a conta de serviço ainda não existir — só
> fecha quando `AIRMOUSE_GOOGLE_PLAY_CREDENTIALS_JSON` estiver preenchido e a conta válida.

Smoke desktop (trial server-authoritative) contra o servidor já em produção:

```bash
# no ficheiro terminal, com o URL real:
curl -s -X POST https://<service>.onrender.com/api/v1/trial/start \
  -H "Content-Type: application/json" -d "{\"device_id\":\"smoke-$(hostname)\"}"
```

---

## 5. Bake do URL — Mobile

Depois de o serviço estar online (URL real conhecido):

- `mobile/airmouse-mobile/.env`:
  ```bash
  EXPO_PUBLIC_LICENSE_SERVER_URL=https://<service>.onrender.com
  ```
- A resolução é: `EXPO_PUBLIC_LICENSE_SERVER_URL` → `extra.licenseServerUrl` (`app.json`) → fallback `https://license.maouse.app`.
- Sem produto Play real, deixa `AIRMOUSE_MOBILE_DEV_ALLOW=1` **só** no ambiente de teste, e
  desliga (`=0`) antes de subir produção.
- **Atenção:** `EXPO_PUBLIC_*` é inlined em **build-time** — mudar o `.env` depois exige novo build (EAS/exp).

---

## 6. Bake do URL — Desktop

Depois de o serviço estar online:

1. Edita o ponto único em `core/licensing.py`:
   ```python
   PROD_LICENSE_SERVER_URL = "https://licenses.maouse.example.com"  # → substituir pelo URL real
   ```
2. Rebuild do `.exe` (ver `docs/DESKTOP_LICENSE_URL.md` para o comando PyInstaller).
3. Redistribui o novo instalador — o binário antigo continua a apontar para o placeholder e fica offline.

> O desktop já suporta override por env `AIRMOUSE_LICENSE_URLS` (vírgulas) para testes/QA.

---

## 8. Redeploys futuros

- Push no branch ligado → Render faz auto-deploy (build incremental da imagem Docker).
- Alterações de env var → *Manual Deploy > Clear build cache & deploy*.
- **Nunca** rodar com `--reload` (1 worker no Dockerfile; SQLite + estado em memória por worker).

---

## 9. Antes da 1ª venda (produção) — 3 passos

O plano **free é só demo** (dados efémeros + cold-start). Antes de haver uma venda real,
ativa o plano **starter** (US$7/mês) para ter dados persistentes e respostas imediatas:

1. **Editar `render.yaml` (raiz do repo):**
   - Mudar `plan: free` → `plan: starter`.
   - Descomentar o bloco `disk:` (descomentado, não o bloco `# disk:`).
2. **Push para `main`** → o Render deteta a mudança e pergunta se queres fazer deploy.
3. **Deploy** → os dados anteriores (free) são perdidos (disco novo). A partir daí, tudo é
   persistente: leases, chaves, clientes, chat, emails, configurações do painel.

> **Notas:**
> - Após o deploy, copia a URL e segue os passos §5 (mobile) e §6 (desktop) para *bake* do
>   URL no build. O painel admin fica em `/admin/login` e continua a funcionar sem alterações.
> - Se não houver disco, o banco reseta a cada push — não é aceitável para clientes reais.

---

*Operacional · Luar Studio Angola · 2026. Complementa `license-server/README.md` e `docs/SEGURANCA_LICENCA.md`.*