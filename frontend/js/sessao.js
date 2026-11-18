/* Sessão do usuário no client (perfil + nome).
 * O TOKEN DE SESSÃO não mora aqui: viaja em cookie httpOnly setado pela API
 * (impermeável a XSS). O localStorage guarda só os metadados do perfil —
 * de gravação opcional — para sobreviver a recarregamentos da página;
 * para contas antigas ainda com token gravado, ele continua sendo usado
 * via Bearer até expirar.
 */
const Sessao = (() => {
  const CHAVE = "projeto_compras.sessao";

  function ler() {
    try {
      const bruto = localStorage.getItem(CHAVE);
      if (!bruto) return null;
      const s = JSON.parse(bruto);
      if (!s || !s.email) return null;
      if (s.expira_em && Date.now() > s.expira_em) {
        limpar();
        return null;
      }
      return s;
    } catch (e) {
      return null;
    }
  }

  function gravar({ token, email, nome, grupo }) {
    const atual = ler() || {};
    localStorage.setItem(
      CHAVE,
      JSON.stringify({
        // token: mantém o de uma sessão anterior (compat), se houver
        token: token ?? atual.token,
        email,
        nome,
        grupo,
        expira_em: Date.now() + CONFIG.SESSAO_MS,
      })
    );
  }

  function limpar() {
    localStorage.removeItem(CHAVE);
  }

  /** Flags de perfil (iguais às do Django: accounts/perfis.py). */
  function isSolicitante(s) { s = s || ler(); return !!s && s.grupo === "UserISI_IST"; }
  function isTime(s)        { s = s || ler(); return !!s && s.grupo === "Time_Compras"; }
  function isGestor(s)      { s = s || ler(); return !!s && s.grupo === "Manager_Compras"; }
  function isEquipe(s)      { return isTime(s) || isGestor(s); }

  return { ler, gravar, limpar, isSolicitante, isTime, isGestor, isEquipe };
})();
