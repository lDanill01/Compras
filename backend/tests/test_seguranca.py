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

print()
if falhas:
    print(f"FALHOU: {len(falhas)} caso(s): {falhas}")
    sys.exit(1)
print("TODOS OS TESTES DE SEGURANÇA PASSARAM")
