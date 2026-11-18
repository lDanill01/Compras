"""Teste de segurança — comportamentos das correções críticas.

Estilo das suítes do repo (script standalone com check()); as variáveis de
ambiente são fixadas ANTES de importar app.*. Cada task do plano acrescenta
seus casos ao final.
"""
import os
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone

tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = tmp
os.environ.pop("SECRET_KEY", None)
# Task 2: janelas curtas para o suíte (lidas no import de app.config).
os.environ["RATE_LIMIT_TENTATIVAS"] = "3"
os.environ["RATE_LIMIT_JANELA_MIN"] = "15"
os.environ["ADMIN_SENHA_VALIDADE_DIAS"] = "1"
# Task 3: reset de senha — base do servidor fixa; SMTP vazio; token em log off.
os.environ["APP_BASE_URL"] = "https://compras.ms.senai.br"
os.environ["SMTP_HOST"] = ""
os.environ.pop("RESET_TOKEN_EM_LOG", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

falhas = []


def check(nome, cond, extra=""):
    ok = "✅" if cond else "❌"
    if not cond:
        falhas.append(nome)
    print(f"  {ok} {nome} {extra}")


print("— SECRET_KEY persistida (Task 1) —")
import importlib

from app import config  # noqa: E402

segredo = config.SECRET_KEY
check("SECRET_KEY nunca vazia", bool(segredo), f"len={len(segredo or '')}")
check("64 hex", len(segredo) == 64 and all(c in "0123456789abcdef" for c in segredo))

arquivo = os.path.join(tmp, "secret_key")
check("arquivo persistido em DATA_DIR", os.path.isfile(arquivo))
modo = stat.S_IMODE(os.stat(arquivo).st_mode)
check("permissão 0600", modo == 0o600, oct(modo))

config2 = importlib.reload(config)
check("reload lê a MESMA chave do arquivo", config2.SECRET_KEY == segredo)

env_segredo = "abc123" * 10  # 90 chars: env tem prioridade
os.environ["SECRET_KEY"] = env_segredo
config3 = importlib.reload(config)
check("env SECRET_KEY tem prioridade", config3.SECRET_KEY == env_segredo)
os.environ.pop("SECRET_KEY", None)

print("— rate limiting (Task 2) —")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app import rate_limit  # noqa: E402
from app import security  # noqa: E402

EMAIL_ADMIN = "admin@compraflow.com.br"

with TestClient(app, raise_server_exceptions=False) as c:
    B = "/api"
    rate_limit.limpar()
    for _ in range(3):
        r = c.post(f"{B}/auth/login",
                   json={"email": EMAIL_ADMIN, "senha": "errada"})
    check("3 tentativas erradas não bloqueiam (400)", r.status_code == 400,
          str(r.status_code))
    r = c.post(f"{B}/auth/login", json={"email": EMAIL_ADMIN, "senha": "errada"})
    check("4ª tentativa → 429", r.status_code == 429, str(r.status_code))
    check("mensagem 'Muitas tentativas'", "Muitas tentativas" in r.text)

    rate_limit.limpar()

    print("— janela da senha provisória do admin (Task 2) —")
    # sentinel datado de 2 dias atrás; validade do suíte = 1 dia → bloqueado
    import datetime as _dt
    semente = (_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
               - _dt.timedelta(days=2))
    with open(os.path.join(tmp, "admin_seed_em"), "w") as f:
        f.write(semente.isoformat())
    r = c.post(f"{B}/auth/login", json={"email": EMAIL_ADMIN, "senha": "admin123"})
    check("senha padrão fora da janela → 400", r.status_code == 400,
          str(r.status_code))
    msg = r.text
    check("mensagem fala de senha provisória", "senha provisória" in msg, msg[:80])
    check("mensagem NÃO casa com MSG_SESSAO", "sessão expirada" not in msg.lower())

print("— reset de senha (Task 3) —")
import logging as _logging
import re as _re
from unittest import mock as _mock

config.RESET_TOKEN_EM_LOG = False  # monkeypatch de config é lido a cada chamada
config.RATE_LIMIT_TENTATIVAS = 100
log_reset = _logging.getLogger("compraflow")

with TestClient(app, raise_server_exceptions=False) as c:
    B = "/api"
    rate_limit.limpar()

    r = c.post(f"{B}/auth/cadastro", json={
        "email": "bia@compraflow.com.br", "nome_completo": "Bia Teste",
        "senha": "senha123", "senha2": "senha123"})
    check("cadastro bia 201", r.status_code == 201, str(r.status_code))
    r = c.post(f"{B}/auth/login", json={
        "email": "bia@compraflow.com.br", "senha": "senha123"})
    check("login bia 200", r.status_code == 200 and "token" in r.json(),
          str(r.status_code))
    token_bia = r.json()["token"]

    # 1) base_url do cliente é ignorada; sem SMTP e sem RESET_TOKEN_EM_LOG,
    #    nada do link vai para o log
    with _mock.patch.object(log_reset, "info") as mi, \
            _mock.patch.object(log_reset, "warning") as mw:
        r = c.post(f"{B}/auth/reset/solicitar", json={
            "email": "bia@compraflow.com.br", "base_url": "https://evil.com"})
        check("solicitar reset 200", r.status_code == 200, str(r.status_code))
        textos = " ".join(
            " ".join(map(str, ca.args))
            for ch in (mi, mw) for ca in ch.call_args_list)
        check("evil.com não aparece no log", "evil.com" not in textos)
        check("link não vai ao log (RESET_TOKEN_EM_LOG=false)",
              "#/redefinir/" not in textos)

    # 2) com RESET_TOKEN_EM_LOG=True (dev/homolog), o link aparece — com a
    #    base do SERVIDOR, não a do cliente
    config.RESET_TOKEN_EM_LOG = True
    with _mock.patch.object(log_reset, "info") as mi:
        r = c.post(f"{B}/auth/reset/solicitar", json={
            "email": "bia@compraflow.com.br", "base_url": "https://evil.com"})
        textos = " ".join(" ".join(map(str, ca.args)) for ca in mi.call_args_list)
        check("log mostra o link", "#/redefinir/" in textos, textos[:100])
        m = _re.search(r"#/redefinir/([0-9a-f]+)", textos)
        check("base do link é a do servidor",
              bool(m) and "https://compras.ms.senai.br#/redefinir/" in textos)
    token_reset = m.group(1) if m else ""

    # 3) redefinir senha mata as sessões anteriores do e-mail
    r = c.post(f"{B}/auth/reset/redefinir", json={
        "token": token_reset, "senha": "novasenha1", "senha2": "novasenha1"})
    check("redefinir 200", r.status_code == 200, str(r.status_code))
    r = c.get(f"{B}/me", headers={"Authorization": f"Bearer {token_bia}"})
    check("sessão antiga morreu → 401", r.status_code == 401, str(r.status_code))

print("— sessão via cookie httpOnly (Task 4) —")
with TestClient(app, raise_server_exceptions=False) as c:
    B = "/api"
    rate_limit.limpar()
    # janela da senha provisória reiniciada (sentinel = agora)
    with open(os.path.join(tmp, "admin_seed_em"), "w") as f:
        f.write(security.agora().isoformat())

    r = c.post(f"{B}/auth/login", json={"email": EMAIL_ADMIN, "senha": "admin123"})
    check("login 200", r.status_code == 200, str(r.status_code))
    setc = (r.headers.get("set-cookie") or "").lower()
    check("Set-Cookie cf_sessao", "cf_sessao=" in setc, setc[:70])
    check("HttpOnly", "httponly" in setc)
    check("SameSite=strict", "samesite=strict" in setc)
    token_admin = r.json()["token"]

    r = c.get(f"{B}/me")
    check("/me sem Bearer, só com cookie → 200", r.status_code == 200
          and r.json().get("email") == EMAIL_ADMIN, str(r.status_code))

    c.cookies.clear()
    r = c.get(f"{B}/me", headers={"Authorization": f"Bearer {token_admin}"})
    check("Bearer continua aceito (compat) → 200", r.status_code == 200,
          str(r.status_code))

    r = c.post(f"{B}/auth/login", json={"email": EMAIL_ADMIN, "senha": "admin123"})
    check("2º login 200", r.status_code == 200, str(r.status_code))
    r = c.post(f"{B}/auth/logout")
    check("logout com cookie → 200", r.status_code == 200, str(r.status_code))
    setc_logout = (r.headers.get("set-cookie") or "").lower()
    check("logout apaga o cookie", "cf_sessao=" in setc_logout)
    r = c.get(f"{B}/me")
    check("/me após logout → 401", r.status_code == 401, str(r.status_code))

print("— passe de correção (revisão final) —")
with TestClient(app, raise_server_exceptions=False) as c:
    B = "/api"
    config.RATE_LIMIT_TENTATIVAS = 3

    # (C1) logins CORRETOS não consomem o orçamento do rate limit
    with open(os.path.join(tmp, "admin_seed_em"), "w") as f:
        f.write(security.agora().isoformat())
    rate_limit.limpar()
    bloq = False
    for _ in range(5):
        r = c.post(f"{B}/auth/login", json={"email": EMAIL_ADMIN, "senha": "admin123"})
        if r.status_code == 429:
            bloq = True
            break
    check("5 logins corretos não bloqueiam", not bloq,
          f"último={r.status_code}")

    # (I3) conta NÃO-admin com senha "admin123" não entra no bloqueio do admin
    r = c.post(f"{B}/auth/cadastro", json={
        "email": "carla@compraflow.com.br", "nome_completo": "Carla",
        "senha": "admin123", "senha2": "admin123"})
    check("cadastro carla 201", r.status_code == 201, str(r.status_code))
    semente = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2))
    with open(os.path.join(tmp, "admin_seed_em"), "w") as f:
        f.write(semente.isoformat())
    r = c.post(f"{B}/auth/login", json={
        "email": "carla@compraflow.com.br", "senha": "admin123"})
    check("não-admin com senha admin123 → 200", r.status_code == 200,
          str(r.status_code))

    # (I4) sem APP_BASE_URL, base_url de MESMA origem do servidor é aceita
    config.APP_BASE_URL = ""
    with _mock.patch.object(log_reset, "info") as mi:
        r = c.post(f"{B}/auth/reset/solicitar",
                   json={"email": "carla@compraflow.com.br",
                         "base_url": "http://testserver/"},
                   headers={"Host": "testserver"})
        textos = " ".join(" ".join(map(str, ca.args)) for ca in mi.call_args_list)
    check("base_url de mesma origem aceita (default deploy)",
          "http://testserver#/redefinir/" in textos, textos[:80])

    # (I5) logout com Bearer morto + cookie válido: 200, cookie sai, sessão morre
    config.RATE_LIMIT_TENTATIVAS = 100
    # janela da senha provisória reaberta para o admin logar
    with open(os.path.join(tmp, "admin_seed_em"), "w") as f:
        f.write(security.agora().isoformat())
    c.cookies.clear()
    r = c.post(f"{B}/auth/login", json={"email": EMAIL_ADMIN, "senha": "admin123"})
    check("login para teste de logout 200", r.status_code == 200, str(r.status_code))
    r = c.post(f"{B}/auth/logout",
               headers={"Authorization": "Bearer token-inexistente"})
    check("logout com Bearer morto + cookie → 200", r.status_code == 200,
          str(r.status_code))
    setc_logout = (r.headers.get("set-cookie") or "").lower()
    check("logout apaga o cookie mesmo com Bearer morto", "cf_sessao=" in setc_logout)
    r = c.get(f"{B}/me")
    check("sessão do cookie morreu após logout → 401", r.status_code == 401,
          str(r.status_code))

print()
if falhas:
    print(f"FALHOU: {len(falhas)} caso(s): {falhas}")
    sys.exit(1)
print("TODOS OS TESTES DE SEGURANÇA PASSARAM")
