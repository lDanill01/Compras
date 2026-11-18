"""
config.py — configuração central da API (fonte de verdade para o frontend).

Tudo configurável por variáveis de ambiente (docker-compose). Os mapas
INSTITUTOS/MODALIDADES/URGENCIAS/STATUS definem o domínio de negócio e
também podem ser ajustados por cliente.
"""
import os
import re

# ---------------------------------------------------------------- pastas/dados
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(DATA_DIR, "compras.db"))
ANEXOS_DIR = os.environ.get("ANEXOS_DIR", os.path.join(DATA_DIR, "anexos"))

# SPA servida pelo próprio backend (arquitetura de container único).
# Padrão: pasta frontend/ irmã de backend/ (no Docker: /app/frontend).
SPA_DIR = os.environ.get("SPA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend"))

# ---------------------------------------------------------------- sessão/admin
SESSAO_MINUTOS = int(os.environ.get("SESSAO_MINUTOS", "480"))  # 8h
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@compraflow.com.br").strip().lower()
ADMIN_SENHA_PADRAO = os.environ.get("ADMIN_SENHA_PADRAO", "admin123")
SEED_ADMIN = os.environ.get("SEED_ADMIN", "true").lower() != "false"
# Janela de carência (dias) em que o admin pode entrar com a senha padrão
# após o seed; 0 desativa o bloqueio.
ADMIN_SENHA_VALIDADE_DIAS = int(os.environ.get("ADMIN_SENHA_VALIDADE_DIAS", "7"))

# ---------------------------------------------------------------- rate limiting
# Tentativas por IP+rota na janela deslizante (login, cadastro, reset).
RATE_LIMIT_TENTATIVAS = int(os.environ.get("RATE_LIMIT_TENTATIVAS", "10"))
RATE_LIMIT_JANELA_MIN = int(os.environ.get("RATE_LIMIT_JANELA_MIN", "15"))

# ---------------------------------------------------------------- e-mail institucional
DOMINIO_EMAIL = os.environ.get("DOMINIO_EMAIL", "compraflow.com.br")

# ---------------------------------------------------------------- anexos
ANEXO_MAX_BYTES = int(os.environ.get("ANEXO_MAX_BYTES", str(10 * 1024 * 1024)))
ANEXO_EXTENSOES = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
    ".png", ".jpg", ".jpeg", ".txt", ".zip",
]

# ---------------------------------------------------------------- SSO (Microsoft Entra ID / OIDC)
OIDC_ENABLED = os.environ.get("OIDC_ENABLED", "false").lower() != "false"
# Ex.: https://login.microsoftonline.com/<TENANT-ID>/v2.0
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI", "")
# Base do SPA para o callback redirecionar (ex.: https://compras.suaempresa.com.br)
OIDC_SPA_BASE = os.environ.get("OIDC_SPA_BASE", "")
OIDC_SCOPES = os.environ.get("OIDC_SCOPES", "openid profile email")
# Chave para assinar o `state` do OAuth. Se a env SECRET_KEY não vier,
# gera uma na 1ª execução e **persiste** em <DATA_DIR>/secret_key (0600):
# a chave sobrevive a restarts e é igual em todos os workers.
def _carregar_secret_key() -> str:
    env = os.environ.get("SECRET_KEY", "").strip()
    if env:
        return env
    caminho = os.path.join(DATA_DIR, "secret_key")
    if os.path.isfile(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            chave = f.read().strip()
        if chave:
            return chave
    import secrets as _secrets

    chave = _secrets.token_hex(32)
    os.makedirs(DATA_DIR, exist_ok=True)
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(chave)
    os.chmod(caminho, 0o600)  # umask pode ter relaxado o modo do arquivo
    return chave

SECRET_KEY = _carregar_secret_key()

# ---------------------------------------------------------------- CORS
# A SPA é servida pela própria API (same-origin): CORS desligado por padrão.
# Defina origens separadas por vírgula se consumir a API de outro endereço,
# ex.: CORS_ORIGINS="https://portal.cliente.com.br"
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
]

# ---------------------------------------------------------------- white-label (marca)
# Identidade do cliente: entregue ao frontend em /api/config. A cor primária
# gera toda a paleta no frontend (tema.css mantém o fallback padrão).

def _cor_hex(valor: str, padrao: str) -> str:
    """Normaliza '#RRGGBB'; cai no padrão se vier malformado."""
    v = valor.strip()
    if not re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
        return padrao
    return ("#" + v.lstrip("#")).upper()

PRODUTO_NOME = os.environ.get("PRODUTO_NOME", "").strip() or "CompraFlow"
PRODUTO_COR_PRIMARIA = _cor_hex(os.environ.get("PRODUTO_COR_PRIMARIA", ""), "#1B7A43")
# Logo alternativa por URL (opcional); por padrão o cliente monta seu próprio
# arquivo em frontend/img/logo.svg (ver DEPLOY.md / CUSTOMIZACAO.md).
PRODUTO_LOGO_URL = os.environ.get("PRODUTO_LOGO_URL", "").strip()

# ---------------------------------------------------------------- reset de senha
RESET_VALIDADE_MIN = int(os.environ.get("RESET_VALIDADE_MIN", "30"))
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USUARIO = os.environ.get("SMTP_USUARIO", "")
SMTP_SENHA = os.environ.get("SMTP_SENHA", "")
SMTP_DE = os.environ.get("SMTP_DE", "noreply@compraflow.com.br")
SMTP_TLS = os.environ.get("SMTP_TLS", "true").lower() != "false"

# ---------------------------------------------------------------- domínio de negócio
INSTITUTOS = [
    "Unidade Central - Capital",
    "Unidade Industrial - Distrito",
    "Unidade Logística - Porto",
    "Departamento Corporativo",
]

MODALIDADES = {
    "selecao_com_disputa_aberta": "Seleção com Disputa (Aberta)",
    "selecao_com_disputa_fechada": "Seleção com Disputa (Fechada)",
    "selecao_sem_disputa_dispensa": "Seleção sem Disputa (Dispensa)",
    "selecao_sem_disputa_inexigibilidade": "Seleção sem Disputa (Inexigibilidade)",
    "credenciamento": "Credenciamento",
    "pre_qualificacao": "Pré-qualificação",
    "dialogo_previo": "Diálogo Prévio",
    "registro_preco": "Registro de Preço",
}

URGENCIAS = {"baixa": "Baixa", "media": "Média", "alta": "Alta", "critica": "Crítica"}

STATUS = {
    "aberta": "Aberta",
    "enviada": "Enviada",
    "em_analise": "Em Análise",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
