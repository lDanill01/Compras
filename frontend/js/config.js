/* Configuração global da SPA.
 *
 * API_URL vazio = mesma origem (o nginx faz proxy de /api para o container
 * FastAPI). Para desenvolvimento fora do Docker, aponte ao uvicorn direto:
 *   API_URL: "http://localhost:8000/api"
 */
const CONFIG = {
  API_URL: "",

  /* Expiração da sessão (ms) — deve bater com SESSAO_MINUTOS do backend */
  SESSAO_MS: 8 * 60 * 60 * 1000,

  /* Domínio institucional obrigatório (sobrescrito pelo /api/config no boot) */
  DOMINIO_EMAIL: "@compraflow.com.br",

  /* Tamanho máximo de anexo (bytes) — deve bater com a validação server-side */
  ANEXO_MAX_BYTES: 10 * 1024 * 1024,

  /* Extensões aceitas para anexos (validação client-side espelha a do server) */
  ANEXO_EXTENSOES: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".txt", ".zip"],

  /* Unidades/locais (cadastro e gráfico por unidade) — vem do backend */
  INSTITUTOS: [
    "Unidade Central - Capital",
    "Unidade Industrial - Distrito",
    "Unidade Logística - Porto",
    "Departamento Corporativo",
  ],

  /* Modalidades de compra (fonte de verdade: backend /api/config) */
  MODALIDADES: {
    selecao_com_disputa_aberta: "Seleção com Disputa (Aberta)",
    selecao_com_disputa_fechada: "Seleção com Disputa (Fechada)",
    selecao_sem_disputa_dispensa: "Seleção sem Disputa (Dispensa)",
    selecao_sem_disputa_inexigibilidade: "Seleção sem Disputa (Inexigibilidade)",
    credenciamento: "Credenciamento",
    pre_qualificacao: "Pré-qualificação",
    dialogo_previo: "Diálogo Prévio",
    registro_preco: "Registro de Preço",
  },

  /* Níveis de urgência (fonte de verdade: backend /api/config) */
  URGENCIAS: {
    baixa: "Baixa",
    media: "Média",
    alta: "Alta",
    critica: "Crítica",
  },

  /* Status do fluxo (fonte de verdade: backend /api/config) */
  STATUS: {
    aberta: "Aberta",
    enviada: "Enviada",
    em_analise: "Em Análise",
    concluida: "Concluída",
    cancelada: "Cancelada",
  },
};
