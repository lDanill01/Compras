"""seed.py — criação idempotente da conta administrativa (≈ criarGestorInicial)."""
import logging
import os
from datetime import datetime

from sqlalchemy.orm import Session

from . import config, security
from .models import Usuario

log = logging.getLogger("compraflow")

SENTINELA = "admin_seed_em"


def _caminho_sentinela() -> str:
    return os.path.join(config.DATA_DIR, SENTINELA)


def _marcar_seed() -> None:
    """Data de referência da janela da senha provisória (idempotente).

    Criada no 1º boot após o deploy — inclusive sobre instalações antigas,
    para que a janela de carência comece no deploy e não trave o admin
    existente de imediato.
    """
    caminho = _caminho_sentinela()
    if os.path.isfile(caminho):
        return
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(security.agora().isoformat())


def semente_admin() -> datetime:
    """Quando a conta admin passou a existir (sentinel; ausente → agora)."""
    caminho = _caminho_sentinela()
    if not os.path.isfile(caminho):
        _marcar_seed()
        return security.agora()
    with open(caminho, "r", encoding="utf-8") as f:
        try:
            return datetime.fromisoformat(f.read().strip())
        except ValueError:
            return security.agora()


def garantir_admin(db: Session) -> bool:
    """Garante que a conta ADMIN existe. True se criada agora."""
    existente = db.query(Usuario).filter(
        Usuario.email == config.ADMIN_EMAIL.lower()).first()
    _marcar_seed()
    if existente:
        return False
    db.add(Usuario(
        nome_completo="Administrador do Sistema",
        email=config.ADMIN_EMAIL.lower(),
        grupo="Manager_Compras",
        senha_hash=security.hash_bcrypt(config.ADMIN_SENHA_PADRAO),
        area_atuacao="Gestão", cargo="Administrador",
        instituto=config.INSTITUTOS[0], ativo=True,
    ))
    db.commit()
    log.info("Administrador criado: %s (trocar a senha no 1º login)",
             config.ADMIN_EMAIL)
    return True
