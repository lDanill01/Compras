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


def verificar(c: str) -> None:
    """Registra a tentativa; lança ErroNegocio se a janela estourar."""
    agora = time.monotonic()
    janela = config.RATE_LIMIT_JANELA_MIN * 60
    tentativas = [t for t in _registros[c] if agora - t < janela]
    if len(tentativas) >= config.RATE_LIMIT_TENTATIVAS:
        _registros[c] = tentativas
        raise ErroNegocio(MSG)
    tentativas.append(agora)
    # guarda só o necessário para a janela atual
    _registros[c] = tentativas[-config.RATE_LIMIT_TENTATIVAS:]


def limpar() -> None:
    """Zera o estado (isolamento entre casos de teste)."""
    _registros.clear()
