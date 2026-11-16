# branding/ — identidade visual do cliente (white-label)

Esta pasta guarda os arquivos de marca do cliente. Nada aqui é usado pela
aplicação até que os **mounts** sejam ativados no `docker-compose.yml`:

```yaml
    volumes:
      - compra-data:/data
      - ./branding/logo.svg:/srv/frontend/img/logo.svg:ro
      - ./branding/favicon.svg:/srv/frontend/img/favicon.svg:ro
```

## Arquivos

| Arquivo | Papel | Formato |
|---|---|---|
| `logo.svg` | Aparece na sidebar (topo e rodapé) e nas telas de login/cadastro | SVG, idealmente horizontal (o padrão tem proporção 560×160) |
| `favicon.svg` | Ícone da aba do navegador | SVG quadrado |

## Sem logo próprio?

A aplicação usa o padrão (`frontend/img/logo.svg`) e o nome/cor definidos por
ambiente (`.env`):

- `PRODUTO_NOME` — título da página, alt do logo, e-mails de reset
- `PRODUTO_COR_PRIMARIA` — hex `#RRGGBB`; gera toda a paleta no frontend
- `PRODUTO_LOGO_URL` — alternativa ao mount: logo servido de outra URL
