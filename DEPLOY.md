# DEPLOY — Implantação do CompraFlow por cliente

Cada cliente = uma instância do CompraFlow: um conjunto de containers, um
banco SQLite no volume e seus anexos em disco. Toda a configuração é feita
por variáveis de ambiente — **um `.env` define um cliente**.

## Arquitetura

```
                       ┌─ :80  (redirect)
[compras-proxy Caddy] ─┤
                       └─ :443 (TLS) ─► [compras-web nginx] ─► [compras-api FastAPI] ─► [volume compras-data]
                                          SPA (pasta frontend/)  /api/{acao}              /data/compras.db
                                          proxy /api/ ──────────┘                    /data/anexos/REQ-xxx/
```

| Componente | Papel |
|---|---|
| `compras-api` | FastAPI: regras de negócio, REST `/api/*`, banco SQLite e anexos no volume |
| `compras-web` | nginx servindo a SPA (`frontend/`) e fazendo proxy de `/api/` para a API |
| `compras-proxy` | Caddy: TLS automático (Let's Encrypt ou cert interno) |

## 1. Requisitos

- Docker + Docker Compose no servidor
- (Produção) Domínio apontando para o host e portas 80/443 liberadas

## 2. Subindo

```bash
cp .env.example .env     # edite: domínio, senha do admin, SMTP, SSO
docker compose up -d --build
```

Acesse `https://SEU-DOMINIO`. Login inicial da Gestão:
`admin@compraflow.com.br` / `admin123` — **trocar a senha no 1º login**.

### Variáveis principais

| Variável | Padrão | Uso |
|---|---|---|
| `CADDY_DOMAIN` | `localhost` | `localhost` → TLS interno; domínio real → Let's Encrypt |
| `PORTA_HTTP` / `PORTA_HTTPS` | `80` / `443` | Portas publicadas do proxy |
| `ADMIN_EMAIL` | `admin@compraflow.com.br` | Conta de Gestão inicial |
| `ADMIN_SENHA_PADRAO` | `admin123` | Trocar em produção |
| `SEED_ADMIN` | `true` | Criar admin no 1º boot |
| `SESSAO_MINUTOS` | `480` | Duração da sessão |
| `SMTP_*` | vazio | "Esqueci minha senha"; sem SMTP o link vai ao log |
| `SECRET_KEY` | — | Assinatura do state do SSO (gerar string longa) |
| `OIDC_*` | `false` | SSO Microsoft Entra (seção abaixo) |

## 3. SSO corporativo — Microsoft Entra ID (opcional, híbrido)

Login alternativo "Entrar com Microsoft": usuário autentica no Entra ID
sem senha interna; na 1ª entrada a conta é provisionada automaticamente
(perfil solicitante). Senhas locais continuam valendo (híbrido).

1. portal.azure.com → Microsoft Entra ID → **App registrations** → New registration
2. Name: "CompraFlow"; Supported accounts: accounts in this org only
3. **Redirect URI (Web)**: `https://SEU-DOMINIO/api/auth/sso/callback`
4. Copie o **Application (client) ID**; crie um **Client secret** (Value);
   no Overview, copie o **Directory (tenant) ID**
5. `.env` do servidor:
   ```
   OIDC_ENABLED=true
   OIDC_ISSUER=https://login.microsoftonline.com/<TENANT-ID>/v2.0
   OIDC_CLIENT_ID=<client-id>
   OIDC_CLIENT_SECRET=<secret>
   OIDC_REDIRECT_URI=https://SEU-DOMINIO/api/auth/sso/callback
   OIDC_SPA_BASE=https://SEU-DOMINIO
   SECRET_KEY=<string longa aleatória>
   ```
6. `docker compose up -d` → o botão "Entrar com Microsoft" aparece no login

Segurança: `state` OAuth assinado com HMAC e validade de 5 min;
`id_token` validado contra o JWKS (RS256/ES256); conta inativa é rejeitada.

## 4. API

RESTful: Bearer token no header `Authorization`, códigos HTTP corretos
(400 regra de negócio, 401 sessão, 404 não achado):

```
POST /api/auth/login | /auth/cadastro | /auth/logout | /auth/senha
POST /api/auth/reset/solicitar | /auth/reset/redefinir
GET  /api/me · /api/config · /api/responsaveis · /api/documentos
     /api/dashboard · /api/performance?de=&ate=&usuario=
GET  /api/pedidos?status=&modalidade=   POST /api/pedidos
GET  /api/pedidos/{numero}              DELETE /api/pedidos/{numero}
POST /api/pedidos/{numero}/enviar | /assumir | /designar | /tramitar
GET  /api/pedidos/{numero}/anexos       POST /api/pedidos/{numero}/anexos
GET  /api/anexos/{id}/arquivo           (binário, Content-Disposition)
GET  /api/usuarios    POST /api/usuarios
PATCH /api/usuarios/{email} ({grupo}|{ativo})   DELETE /api/usuarios/{email}
```

Swagger: exponha temporariamente a porta 8000 do container `api`
(descomente em `docker-compose.yml`) e abra `/api/docs`.

## 5. Importação de dados legados (CSV)

Para migrar dados de uma planilha/CSV antiga do cliente:

```bash
docker compose cp ./import compras-api:/data/import
docker compose exec api python -m app.import_csv /data/import \
       --anexos-dir /data/import/anexos
# --recriar apaga o banco atual e importa do zero
```

Senhas legadas (SHA-256+salt) migram para bcrypt no 1º login; IDs
(`REQ-xxxxxx`, `ANX-xxxxxx`) são preservados; import é transacional.

## 6. Segurança e operação

- Toda regra de negócio (perfil, transição, permissão, anexos) é validada
  **no servidor** (`backend/`).
- Sessões: token de 8h na tabela `sessoes` (revogável); trocar senha
  invalida as demais sessões.
- nginx limita `client_max_body_size 15m`; a API não fica exposta
  diretamente (rede interna do compose).
- TLS termina no Caddy com renovação automática.
- Backup: copie o volume `compras-data` (contém `compras.db` + `anexos/`).

## 7. Free tiers possíveis para a fase inicial

| Serviço | Papel | Plano gratuito |
|---|---|---|
| Render / Railway / Fly.io | Roda a stack (containers) | Free/trial com sleep |
| Oracle Cloud Always Free | VPS permanente (2 VMs) | Grátis para sempre |
| Neon / Supabase | Postgres gerenciado (quando escalar de SQLite) | Free tier |

Consulte a seção de customização (`CUSTOMIZACAO.md`) para adaptar tema,
nome e textos por cliente.
