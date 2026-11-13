"""
main.py — API CompraFlow (FastAPI).

Superfície única RESTful (app/rest.py): recursos no path, Bearer token e
códigos HTTP corretos. O frontend fala REST por completo via adapter em
frontend/js/api.js.
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .database import Base, engine
from .seed import garantir_admin

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("compraflow")

app = FastAPI(title="CompraFlow API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # em produção é same-origin (SPA servida aqui)
    allow_methods=["*"],
    allow_headers=["*"],
)

# Superfície RESTful — casos de uso do negócio (auth, pedidos, anexos,
# usuários, agregações, reset).
from .rest import router as rest_router  # noqa: E402
app.include_router(rest_router)


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


@app.on_event("startup")
def startup() -> None:
    inicializar()
