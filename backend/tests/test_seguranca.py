"""Teste de segurança — comportamentos das correções críticas.

Estilo das suítes do repo (script standalone com check()); as variáveis de
ambiente são fixadas ANTES de importar app.*. Cada task do plano acrescenta
seus casos ao final.
"""
import os
import stat
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = tmp
os.environ.pop("SECRET_KEY", None)
# Task 2: janelas curtas para o suíte (lidas no import de app.config).
os.environ["RATE_LIMIT_TENTATIVAS"] = "3"
os.environ["RATE_LIMIT_JANELA_MIN"] = "15"
os.environ["ADMIN_SENHA_VALIDADE_DIAS"] = "1"

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

print()
if falhas:
    print(f"FALHOU: {len(falhas)} caso(s): {falhas}")
    sys.exit(1)
print("TODOS OS TESTES DE SEGURANÇA PASSARAM")
