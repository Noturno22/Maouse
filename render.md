# Render Blueprint — implanta o license server da Mãouse a partir deste repo.
# Uso: liga este repo ao Render (Blueprints) ou usa "New + > Blueprint".
# Um disco persistente é montado em /data — a base SQLite fica lá.
services:
  - type: web
    name: maouse-license-server
    runtime: docker
    repo: https://github.com/Noturno22/Maouse.git
    plan: free
    dockerfilePath: ./license-server/Dockerfile
    envVars:
      - key: MAOUSE_LS_ADMIN_TOKEN
        sync: false # define no painel (não versionar)
      - key: MAOUSE_LS_ADMIN_SESSION_SECRET
        sync: false # definir no painel do Render
      - key: MAOUSE_LS_PRIVATE_KEY
        sync: false
      - key: MAOUSE_LS_PUBLIC_KEY
        sync: false
      - key: MAOUSE_PADDLE_WEBHOOK_SECRET
        sync: false
      - key: MAOUSE_SMTP_ENABLED
        value: "0"
      - key: MAOUSE_SMTP_HOST
        sync: false
      - key: MAOUSE_SMTP_PORT
        value: "587"
      - key: MAOUSE_SMTP_USER
        sync: false
      - key: MAOUSE_SMTP_PASSWORD
        sync: false
      - key: MAOUSE_SMTP_FROM
        sync: false
      # Mobile (IAP Pro) — validação server-side das compras Google Play.
      # Definição no painel: o JSON da conta de serviço é grande e secreto.
      - key: MAOUSE_MOBILE_PRODUCT_ID
        value: maouse_mobile_pro
      - key: MAOUSE_MOBILE_PACKAGE_NAME
        value: com.maouse.mobile
      - key: MAOUSE_GOOGLE_PLAY_CREDENTIALS_JSON
        sync: false
      - key: MAOUSE_MOBILE_DEV_ALLOW
        value: "0"
      # Base de dados persistente no disco.
      - key: MAOUSE_LS_DB
        value: /data/license.db
    disk:
      name: maouse-license-data
      mountPath: /data
      sizeGB: 1
    healthCheckPath: /health
