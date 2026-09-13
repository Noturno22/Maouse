"""API JSON /api/admin/* — autenticada por sessão HMAC.

CRUD genérico para os recursos de RESOURCES, chat, dashboard e envio de email
aos sócios (reutiliza send_generic_email).
"""
import admin_storage
from admin_auth import require_admin
from emailer import send_generic_email
from fastapi import APIRouter, Depends, HTTPException
from storage import connect, init_db

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def get_db():
    conn = connect()
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def _register_crud(resource: str):
    uid = resource.replace("_", "")
    table = resource

    @router.get(f"/{resource}",
                operation_id=f"list_{uid}", response_model=dict)
    def _list(db=Depends(get_db)):
        return {"items": admin_storage.list_rows(db, table)}

    @router.post(f"/{resource}",
                 operation_id=f"create_{uid}", response_model=dict)
    def _create(payload: dict, db=Depends(get_db)):
        row_id = admin_storage.create_row(db, table, payload)
        return {"id": row_id}

    @router.patch(f"/{resource}/{{row_id}}",
                  operation_id=f"patch_{uid}", response_model=dict)
    def _patch(row_id: int, payload: dict, db=Depends(get_db)):
        if admin_storage.get_row(db, table, row_id) is None:
            raise HTTPException(status_code=404, detail="nao_encontrado")
        admin_storage.update_row(db, table, row_id, payload)
        return {"ok": True}

    @router.delete(f"/{resource}/{{row_id}}",
                   operation_id=f"delete_{uid}", response_model=dict)
    def _delete(row_id: int, db=Depends(get_db)):
        if admin_storage.get_row(db, table, row_id) is None:
            raise HTTPException(status_code=404, detail="nao_encontrado")
        admin_storage.delete_row(db, table, row_id)
        return {"ok": True}


for _resource in admin_storage.RESOURCES:
    _register_crud(_resource)


@router.get("/chat", operation_id="chat_list", response_model=dict)
def chat_get(after_id: int = 0, db=Depends(get_db)):
    messages = admin_storage.chat_after(db, after_id)
    next_id = messages[-1]["id"] if messages else after_id
    return {"messages": messages, "next_id": next_id}


@router.post("/chat", operation_id="chat_add", response_model=dict)
def chat_post(payload: dict, db=Depends(get_db)):
    mensagem = str(payload.get("mensagem", "")).strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="mensagem_vazia")
    msg_id = admin_storage.add_chat(db, "fundador", mensagem)
    return {"id": msg_id}


@router.get("/dashboard", operation_id="dashboard_get", response_model=dict)
def dashboard(db=Depends(get_db)):
    return admin_storage.dashboard_kpis(db)


@router.get("/emails", operation_id="emails_list", response_model=dict)
def emails_list(db=Depends(get_db)):
    return {"items": admin_storage.list_emails(db)}


@router.post("/emails/send", operation_id="emails_send", response_model=dict)
def emails_send(payload: dict, db=Depends(get_db)):
    socio_ids = [int(i) for i in payload.get("socio_ids", [])]
    assunto = str(payload.get("assunto", "")).strip()
    corpo = str(payload.get("corpo", "")).strip()
    if not assunto or not corpo:
        raise HTTPException(status_code=400, detail="campos_em_falta")
    sent, failed = [], []
    for sid in socio_ids:
        socio = admin_storage.get_row(db, "socios", sid)
        if socio is None:
            continue
        email = (socio.get("email") or "").strip()
        if not email:
            failed.append({"id": sid, "erro": "sem_email"})
            continue
        result = send_generic_email(email, assunto, corpo)
        estado = "enviado" if result.fired else "nao_fire"
        admin_storage.record_email(db, email, assunto, corpo, estado, result.error)
        if result.fired:
            sent.append(sid)
        else:
            failed.append({"id": sid, "erro": "smtp_desligado"})
    return {"sent": sent, "failed": failed}
