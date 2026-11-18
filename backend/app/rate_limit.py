"""rate_limit.py — limitador de tentativas em memória (sem dependências).

Janela deslizante por IP+rota para os endpoints de autenticação (login,
cadastro, reset). O estado vive no processo: com o uvicorn de 1 worker,
um dicionário basta; ao reiniciar, o limite volta do zero — aceitável,
pois ninguém já logado é afetado.
"""
import time
from collections import defaultdict

from . import config
from .deps import ErroNegocio

MSG = "Muitas tentativas. Aguarde alguns minutos e tente novamente."

LIMITADAS = {
    "/api/auth/login",
    "/api/auth/cadastro",
    "/api/auth/reset/solicitar",
    "/api/auth/reset/redefinir",
}

_registros: dict[str, list[float]] = defaultdict(list)


def chave(request) -> str:
    """Chave do limite: IP de origem + rota (atrás do proxy Caddy)."""
    ip = request.client.host if request.client else "?"
    return f"{ip}:{request.url.path}"


def excedido(c: str) -> None:
    """Lança ErroNegocio se a janela desta chave já estourou.

    Tentativas fora da janela são descartadas; tentativas bloqueadas não
    são registradas — o lockout não se estende sozinho.
    """
    agora = time.monotonic()
    janela = config.RATE_LIMIT_JANELA_MIN * 60
    tentativas = [t for t in _registros[c] if agora - t < janela]
    _registros[c] = tentativas
    if len(tentativas) >= config.RATE_LIMIT_TENTATIVAS:
        raise ErroNegocio(MSG)


def registrar(c: str) -> None:
    """Registra UMA falha (chamado só quando a resposta é 4xx).

    Sucesso não gasta o orçamento: um escritório atrás de um NAT
    compartilhado loga quantos colegas precisar.
    """
    _registros[c].append(time.monotonic())
    _registros[c] = _registros[c][-config.RATE_LIMIT_TENTATIVAS:]


def limpar() -> None:
    """Zera o estado (isolamento entre casos de teste)."""
    _registros.clear()
