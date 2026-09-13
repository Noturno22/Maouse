"""Páginas /admin/* (Jinja2) do painel administrativo."""
import os

import admin_storage
from admin_auth import COOKIE_NAME, make_session, verify_password, verify_session
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

_templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "templates")
templates = Jinja2Templates(directory=_templates_dir)


def _authed(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME, "")
    return bool(verify_session(cookie))


def _render(request: Request, template: str, page: str, **ctx):
    if not _authed(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse(request, template, {
        "page": page, "title": page.title(), **ctx})


@router.get("/admin/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {
        "page": "login", "error": ""})


@router.post("/admin/login")
def login_post(request: Request, password: str = Form("")):
    if verify_password(password):
        resp = RedirectResponse("/admin", status_code=302)
        resp.set_cookie(COOKIE_NAME, make_session(), httponly=True,
                        samesite="lax", max_age=7 * 24 * 3600)
        return resp
    return templates.TemplateResponse(request, "login.html", {
        "page": "login", "error": "Senha inválida."})


@router.get("/admin/logout")
def logout():
    resp = RedirectResponse("/admin/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp


def _crud_ctx(request: Request, page: str, resource: str):
    fields = admin_storage.RESOURCES[resource]["cols"]
    return _render(request, "crud.html", page, resource=resource,
                   fields=fields)


@router.get("/admin")
def dashboard(request: Request):
    return _render(request, "dashboard.html", "dashboard")


@router.get("/admin/socios")
def socios(request: Request):
    return _crud_ctx(request, "sócios", "socios")


@router.get("/admin/investidores")
def investidores(request: Request):
    return _crud_ctx(request, "investidores", "investidores")


@router.get("/admin/funcionarios")
def funcionarios(request: Request):
    return _crud_ctx(request, "funcionários", "funcionarios")


@router.get("/admin/fases")
def fases(request: Request):
    return _crud_ctx(request, "fases", "fases")


@router.get("/admin/marcos")
def marcos(request: Request):
    return _crud_ctx(request, "marcos", "marcos")


@router.get("/admin/metas")
def metas(request: Request):
    return _crud_ctx(request, "metas", "metas")


@router.get("/admin/caixa")
def caixa(request: Request):
    return _crud_ctx(request, "caixa", "movimentos_caixa")


@router.get("/admin/chat")
def chat(request: Request):
    return _render(request, "chat.html", "chat")


@router.get("/admin/emails")
def emails(request: Request):
    return _render(request, "emails.html", "emails")
