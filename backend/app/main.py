"""
main.py — API CompraFlow (FastAPI).

Superfície única RESTful (app/rest.py): recursos no path, Bearer token e
códigos HTTP corretos. O frontend fala REST por completo via adapter em
frontend/js/api.js.
"""
import os
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .database import Base, engine
from .seed import garantir_admin

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("compraflow")


# ------------------------------ inicialização ------------------------------

def inicializar() -> None:
    os.makedirs(config.ANEXOS_DIR, exist_ok=True)
    Base.metadata.create_all(engine)
    if not config.SEED_ADMIN:
        return
    from .database import SessionLocal

    db = SessionLocal()
    try:
        garantir_admin(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar()
    yield


# --------------------------------- app --------------------------------------

app = FastAPI(
    title=f"{config.PRODUTO_NOME} API",
    version="2.2.0",
    lifespan=lifespan,
)

# Same-origin por padrão (SPA servida aqui). CORS só com origens externas;
# allow_credentials porque a sessão viaja em cookie httpOnly.
if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

# Superfície RESTful — casos de uso do negócio (auth, pedidos, anexos,
# usuários, agregações, reset).
from .rest import router as rest_router  # noqa: E402
app.include_router(rest_router)


# ------------------------------- rate limiting -------------------------------
# Tentativas de autenticação (POST) limitadas por IP+rota, em memória.
from fastapi.responses import JSONResponse
from fastapi import Request

from . import rate_limit  # noqa: E402
from .deps import ErroNegocio  # noqa: E402


@app.middleware("http")
async def limitar_tentativas(request: Request, call_next):
    if request.method == "POST" and request.url.path in rate_limit.LIMITADAS:
        c = rate_limit.chave(request)
        try:
            rate_limit.excedido(c)
        except ErroNegocio as e:
            return JSONResponse({"detail": e.mensagem}, status_code=429)
        resposta = await call_next(request)
        # conta só FALHA (4xx): sucesso não gasta orçamento — um escritório
        # atrás de um NAT não se tranca; o 429 do próprio limite também não
        # estende a janela
        if 400 <= resposta.status_code < 500 and resposta.status_code != 429:
            rate_limit.registrar(c)
        return resposta
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"ok": True, "data": {"status": "up", "version": app.version}}


# --------------------------- SPA (container único) --------------------------
# A pasta frontend/ é servida pelo próprio FastAPI em "/", depois das rotas
# /api (a ordem de registro garante prioridade da API).
if os.path.isdir(config.SPA_DIR):
    app.mount("/", StaticFiles(directory=config.SPA_DIR, html=True), name="spa")
    log.info("SPA servida de %s", config.SPA_DIR)
else:
    log.warning("SPA não encontrada em %s — só /api está disponível.", config.SPA_DIR)
