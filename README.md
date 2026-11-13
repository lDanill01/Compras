# CompraFlow — Gestão de Requisições de Compra

Sistema web white-label para registro e tramitação de requisições de compra.
Cada cliente roda sua própria instância (um container, um banco, seus anexos),
com identidade visual configurável por variáveis de ambiente.

---

## 1. Estrutura do repositório

```
backend/                 # API FastAPI + SPA servida
├── app/
│   ├── main.py          # app FastAPI (serve /api e os assets da SPA)
│   ├── rest.py          # superfície REST (/api/auth, /api/pedidos, ...)
│   ├── routers/         # regras de negócio (auth, pedidos, anexos, usuários, agregações)
│   ├── models.py        # ORM (SQLite; migra para Postgres sem reescrita)
│   ├── config.py        # configuração central por variáveis de ambiente
│   ├── security.py      # senhas (bcrypt) e sessões
│   ├── storage.py       # anexos em disco (abstração p/ S3/R2 futuramente)
│   ├── oidc.py          # SSO corporativo (Microsoft Entra ID / OIDC)
│   └── seed.py          # admin inicial idempotente
├── requirements.txt
└── Dockerfile

frontend/                # SPA (vanilla JS, sem build step)
├── index.html
├── css/                 # tema + seções (variáveis CSS p/ white-label)
├── js/                  # config, sessão, api, roteador e views
└── README.md

proxy/Caddyfile          # TLS/HTTPS opcional na frente do container
docker-compose.yml       # orquestração (api + proxy)
DEPLOY.md                # GUIA COMPLETO DE IMPLANTAÇÃO POR CLIENTE
.env.example             # variáveis de ambiente (um .env = um cliente)
```

## 2. Fluxo de status

```
Aberta ──(Enviar)──▶ Enviada ──(Assumir/Designar)──▶ Em Análise ──▶ Concluída
                                                                  └──▶ Cancelada
```

- Nº da requisição gerado automaticamente (`REQ-000001`);
- **Retorno final** obrigatório ao concluir; Data de Encerramento nos status
  terminais; lead time calculado (Envio → Encerramento, ou hoje, se aberta);
- Assunção atômica (`UPDATE` condicional) — só um membro assume;
- Documentação (anexo) obrigatória no registro; Cotação obrigatória quando
  "Possui cotação? = Sim".

## 3. Perfis (grupos)

| Grupo | Papel |
|---|---|
| `UserISI_IST` | Solicitante — registra, envia, exclui (próprias, Abertas) e acompanha |
| `Time_Compras` | Time de compras — assume e tramita |
| `Manager_Compras` | Gestão — designa/redesigna, tramita, Performance e gestão de usuários |
| `SuperUsuario` | Acesso total |

Regras: ninguém gerencia a si mesmo; a Gestão gerencia só o Time de Compras;
exclusão de usuário bloqueada se houver requisições vinculadas.

## 4. Rodando localmente

```bash
cp .env.example .env            # ajuste o que precisar
docker compose up -d --build    # sobe api (+ proxy com TLS em :80/:443)
```

Acesso inicial da Gestão: `admin@compraflow.com.br` / `admin123` —
trocar a senha no 1º login.

O guia completo (deploy em free tiers, variáveis por cliente, customização
de tema) está em **[`DEPLOY.md`](DEPLOY.md)**.
