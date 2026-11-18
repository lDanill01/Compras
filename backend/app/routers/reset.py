"""routers/reset.py — port do fluxo de reset de senha (Setup.gs).

MailApp → SMTP configurável; sem SMTP configurado, o link é registrado
no log do container (útil para dev/homolog).
"""
import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import config, security
from ..deps import (
    ErroNegocio,
    buscar_usuario,
    exigir,
    exigir_email_institucional,
    is_valido,
)
from ..models import ResetSenha, Sessao, Usuario

log = logging.getLogger("compraflow")


def _resposta_padrao():
    return {"ok": True, "data": {
        "mensagem": "Se existir uma conta com este e-mail, enviaremos as "
                    "instruções de redefinição.",
    }}


def _base_permitido(cliente: str, origens_servidor: set[str] | None = None) -> str:
    """Base dos links de redefinição — decidida no servidor.

    APP_BASE_URL (env do servidor) tem prioridade e vence sempre. Sem ela,
    o base_url do cliente só é aceito se a origem (scheme://netloc) constar
    de CORS_ORIGINS ou das origens do próprio servidor (Host do request —
    incontrolável pelo chamador atrás do Caddy). Caso contrário, '' (o
    e-mail traz só o código) — nunca um domínio escolhido por quem chama.
    """
    if config.APP_BASE_URL:
        return config.APP_BASE_URL.rstrip("/")
    permitidas: set[str] = {o.rstrip("/") for o in (origens_servidor or set()) if o}
    for origem in config.CORS_ORIGINS:
        p = urlsplit(origem)
        permitidas.add(f"{p.scheme}://{p.netloc}".rstrip("/"))
    p = urlsplit(str(cliente or "").split("#")[0])
    origem_cliente = f"{p.scheme}://{p.netloc}".rstrip("/")
    return origem_cliente if origem_cliente in permitidas else ""


def api_solicitar_reset_senha(db: Session, payload: dict):
    email = str(payload.get("email") or "").strip().lower()
    exigir_email_institucional(email)

    # limpeza de tokens expirados/usados
    db.execute(delete(ResetSenha).where(
        (ResetSenha.expira_em <= security.agora()) | (ResetSenha.usado == True)
    ))
    db.commit()

    u = buscar_usuario(db, email)
    if not u or not is_valido(u):
        return _resposta_padrao()

    # invalida tokens anteriores deste e-mail
    db.execute(delete(ResetSenha).where(ResetSenha.email == email))

    token = security.novo_token_reset()
    db.add(ResetSenha(token=token, email=email,
                      expira_em=security.expiracao_reset(),
                      usado=False, criado_em=security.agora()))
    db.commit()

    base = _base_permitido(payload.get("base_url"),
                           payload.get("_origens_servidor"))
    link = (base + "#/redefinir/" + token) if base else token

    nome = u.nome_completo or email
    produto = config.PRODUTO_NOME
    assunto = f"{produto} — redefinição de senha"
    corpo = (
        f"Olá, {nome}!\n\n"
        f"Recebemos um pedido de redefinição de senha da sua conta no {produto}.\n\n"
        + (f"Abra o link abaixo para definir uma nova senha:\n{link}\n\n"
           if base else
           f"Use este código para redefinir sua senha: {token}\n\n")
        + f"O link/código é válido por {config.RESET_VALIDADE_MIN} minutos.\n"
        "Se você não solicitou, ignore este e-mail.\n\n"
        f"Equipe {produto}"
    )

    if config.SMTP_HOST:
        try:
            _enviar_email(email, assunto, corpo)
        except Exception as e:
            log.warning("Falha ao enviar e-mail de reset: %s", e)
    elif config.RESET_TOKEN_EM_LOG:
        log.info("SMTP não configurado — link de reset para %s: %s", email, link)
    else:
        log.warning(
            "SMTP não configurado e RESET_TOKEN_EM_LOG=false — o e-mail de "
            "redefinição não pôde ser enviado. Configure SMTP_HOST "
            "(produção) ou RESET_TOKEN_EM_LOG=true (apenas dev/homolog).")

    return _resposta_padrao()


def api_redefinir_senha(db: Session, payload: dict):
    token = str(payload.get("token") or "").strip()
    senha = str(payload.get("senha") or "")
    senha2 = str(payload.get("senha2") or "")

    exigir(token, "Token ausente. Solicite uma nova redefinição.")
    exigir(len(senha) >= 6, "A senha deve ter ao menos 6 caracteres.")
    exigir(not senha2 or senha == senha2, "As senhas não coincidem.")

    r = db.get(ResetSenha, token)
    exigir(r, "Link de redefinição inválido. Solicite uma nova redefinição.")
    exigir(not r.usado, "Este link de redefinição já foi utilizado.")
    exigir(r.expira_em > security.agora(),
           "Este link de redefinição expirou. Solicite outro.")

    email = str(r.email).lower()
    alvo = buscar_usuario(db, email)
    exigir(alvo, "Usuário não encontrado.")

    alvo.salt = ""
    alvo.senha_hash = security.hash_bcrypt(senha)
    # Redefinir a senha mata TODAS as sessões do e-mail (inclusive a atual).
    db.execute(delete(Sessao).where(Sessao.email == email))
    r.usado = True
    db.commit()
    return {"ok": True, "data": {"email": email,
            "mensagem": "Senha redefinida com sucesso. Faça login."}}


def _enviar_email(destino: str, assunto: str, corpo: str) -> None:
    msg = EmailMessage()
    msg["From"] = config.SMTP_DE
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.set_content(corpo)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as srv:
        if config.SMTP_TLS:
            srv.starttls()
        if config.SMTP_USUARIO:
            srv.login(config.SMTP_USUARIO, config.SMTP_SENHA)
        srv.send_message(msg)
