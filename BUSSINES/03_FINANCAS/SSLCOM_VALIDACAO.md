# SSL.com — Validação do Code Signing IV (ref# co-3c1laihs7ca)

> Estado da encomenda **Personal ID Code Signing (IV)** — **VALIDADA**.
> **Titular:** Jeronimo Dadiva Samaina · **Ordem:** `co-3c1laihs7ca` ·
> **Email de validação:** jeronimo.samaina239898@gmail.com (confirmado por Patricia, apoio SSL.com).
> **Data:** 2026-09-15 · Luar Studio Angola · Ticket `#133702727` (Resolved)

---

## 1. O que já está pago/avançado

- [x] Plano/produto adquirido (SSL.com cobrou no checkout)
- [x] Passos 1 (Registrant) e 2 (Contacts) do formulário de compra
- [x] **Pipeline de assinatura validado** (eSigner/thumbprint no `build.bat` + upload do instalador para Vercel Blob — commit `5be39c1`): testado, funciona
- [x] Passo 3 (Upload Documents) — subido e aceite (BI + comprovativo de morada)
- [x] Passo 4 (Complete) — **validação concluída pela SSL.com** (notificação "your order is now validated" — 2026-09-23)
- [x] **Certificado VALIDADO** pela SSL.com — pronto para ativar no **eSigner** (a chave fica na nuvem SSL.com; não há `.pfx`)

> Nota: o certificado IV (pessoa natural) tem o **nome pessoal como Publisher**
> ("Jeronimo Dadiva Samaina"), não "Luar Studio Angola" — aceite como trade-off
> até existir entidade formal (OV depois).

---

## 2. Documentos exigidos (tradução do formulário)

O formulário pede (com texto padrão de validação OV, mas para IV serve):

| # | Campo SSL.com | Documento que funciona | Estado |
|---|---|---|---|
| 1 | **Documentation of Legal Existence** | **BI (Bilhete de Identidade)** ou **Passaporte** (frente + verso) | ✅ |
| 2 | **Documentation of Physical Existence** | **Fatura de água/eletricidade (ENEL)** ou **extrato bancário recente** com morada | ✅ |
| 3 | **Documentation of Order Authorization** | **BI/Passaporte** (é quem autoriza o pedido) | ✅ |

**Regras do upload:**
- Formatos: `jpg, jpeg, jpe, jfif, png, pdf, tif, tiff, gif, bmp, zip, odt, doc, docx, mp3, m4a, mp4, webm, txt, text`
- Máx. **5 ficheiros**; zips são desempacotados automaticamente
- Legíveis (digitalizar ~300 dpi); PDF/JPG recomendados

## 3. Ordem de execução

1. Reunir digitalizações (BI/passaporte + fatura/extrato com morada).
2. Subir na encomenda: `secure.ssl.com` → painel da encomenda `co-3c1laihs7ca` →
   separador **Validation** → 3 caixas de upload.
3. Clicar submit → aguardar a SSL.com contactar para validar identidade
   (e-mail/chamada — responder prontamente; chamadas perdidas adiam dias).
4. Após aprovação: baixar o **certificado** (token/PFX + key — cloud ou software).
5. Instalar no build (ver `CHECKLIST_POS_PAGAMENTO.md` §1 + `docs/ASSINATURA_DIGITAL.md`).

---

## 4. PRÓXIMO PASSO — Ativar o eSigner (VALIDADO ✅)

A SSL.com validou a ordem (2026-09-23). Para assinar o .exe/instalador é preciso
**ativar o certificado no eSigner** e configurar o `build.bat`:

- [ ] **Enroll do certificado no eSigner** — portal SSL.com → pedido "eSigner Ready"
  (guia: https://www.ssl.com/how-to/enroll-esigner-remote-document-ev-code-signing)
- [ ] **Descarregar o CodeSignTool** (Windows, inclui Java) em
  https://www.ssl.com/downloads/ → descompactar (ex.: `C:\tools\CodeSignTool`)
- [ ] **(Opcional) OTP SMS 2FA** para o eSigner:
  https://www.ssl.com/guide/how-to-enable-otp-sms-two-factor-authentication-for-esigner-cloud-code-or-document-signing
- [ ] **(Opcional) Partilha da equipa**: https://www.ssl.com/how-to/team-sharing-for-esigner-document-and-ev-code-signing-certificates
- [ ] **Definir no ambiente antes do build** (o `build.bat` usa eSigner se estiverem definidas):
  - `ESIGNER_PATH` = pasta do CodeSignTool
  - `ESIGNER_USERNAME` = e-mail da conta SSL.com
  - `ESIGNER_PASSWORD` = password da conta SSL.com
  - `ESIGNER_CREDENTIAL_ID` = opcional (mais de 1 certificado)
  - `ESIGNER_TOTP_SECRET` = opcional (assina sem pedir OTP na hora)
- [ ] Correr `build.bat` → confirmar no portal SSL.com que o instalador ficou assinado
- [ ] Subir o instalador assinado para o Vercel Blob (same URL de `NEXT_PUBLIC_DOWNLOAD_URL`)

> NÃO usar YubiKey a menos que queira: para a própria YubiKey, submete a
> attestation (https://www.ssl.com/how-to/key-generation-and-attestation-with-yubikey
> e https://www.ssl.com/how-to/how-to-add-yubikeys-to-your-certificate-order).

---

## 5. Estado financeiro do direcionamento (US$222)

| Item | Orçado | Real | Estado |
|---|---|---|---|
| Domínio `maouse.app` (Cloudflare) | US$12 | **US$14.342** | ✅ comprado |
| SSL.com IV code signing | US$129 | ~US$129 (1 ano) | ✅ pago, **VALIDADO** (eSigner por ativar) |
| Play Developer (Google) | — | US$25 | ✅ ativo |
| **Subtotal usado** | | **~US$168.34** | |
| Reserva restante | ~US$81 | **~US$53.66** | 🟡 guardada |

---

*Validação operacional — Luar Studio Angola · 2026. Atualizar assim que a SSL.com confirmar.
Complementa `CHECKLIST_POS_PAGAMENTO.md` e `docs/ASSINATURA_DIGITAL.md`.*