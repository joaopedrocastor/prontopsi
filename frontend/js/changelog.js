// Histórico de novidades por versão (mostrado ao reabrir após atualizar).
// Ao lançar uma versão nova, adicione a lista de mudanças aqui.

export const CHANGELOG = {
  "1.1.5": [
    "Backup agora salva TAMBÉM a sua logo e os documentos anexados (antes só os dados).",
    "Restaurar aceita o novo backup (.zip) e também os antigos (.db).",
    "Correção na sincronização com o Google (o envio de agendamentos não para mais sozinho).",
    "Nova opção em Configuração → Google: “Testar sincronização” mostra o resultado ou o erro.",
  ],
  "1.1.4": [
    "Agora a versão do app aparece no canto inferior do menu (ajuda a saber se está atualizado).",
    "O instalador no GitHub passa a ter a versão no nome do arquivo.",
  ],
  "1.1.3": [
    "A sincronização com o Google agora traz eventos de TODOS os seus calendários (antes só o principal).",
    "Novo: botão “Salvar no Drive” na ficha — guarda o PDF da anamnese no seu Google Drive.",
    "Importante: entre em Configuração → Google e clique em Conectar de novo para autorizar o Drive e a leitura dos calendários.",
  ],
  "1.1.2": [
    "Agenda em mão dupla com o Google: o que você cria no Google Calendar agora aparece no app.",
    "A Agenda sincroniza ao abrir (se o Google estiver conectado) e tem o botão “Sincronizar Google”.",
  ],
  "1.1.1": [
    "Correção: o aviso “Configure seu consultório” some quando a logo já inclui nome e CRP.",
    "Melhoria: a tela sempre carrega atualizada após uma atualização (sem sobras da versão anterior).",
  ],
  "1.1.0": [
    "Listagem de clientes em tabela (status, e-mail, telefone, data de cadastro) com filtro e busca.",
    "Ficha de Cliente completa: Principal, Cadastro, Anamnese, Sessões realizadas e Documentos.",
    "Timeline de anotações do cliente.",
    "Anexar, baixar e excluir documentos por cliente.",
  ],
  "1.0.0": [
    "Primeira versão do ProntoPsi.",
    "Pacientes, Agenda (mês/semana/dia) e Ficha de Anamnese com PDF.",
    "Backup, exportação de dados e verificação de atualizações.",
  ],
};

// Converte 'v1.2.3' / '1.2.3' em números comparáveis.
function parseV(v) {
  return String(v || "").replace(/^v/, "").split(".").map((n) => parseInt(n, 10) || 0);
}
function cmp(a, b) {
  const A = parseV(a), B = parseV(b);
  for (let i = 0; i < Math.max(A.length, B.length); i++) {
    if ((A[i] || 0) !== (B[i] || 0)) return (A[i] || 0) - (B[i] || 0);
  }
  return 0;
}

// Junta as novidades de todas as versões entre 'fromVersion' (exclusivo) e
// 'toVersion' (inclusivo) — cobre também quem pulou várias versões.
export function novidadesEntre(fromVersion, toVersion) {
  const out = [];
  for (const [ver, itens] of Object.entries(CHANGELOG)) {
    if (cmp(ver, fromVersion) > 0 && cmp(ver, toVersion) <= 0) {
      out.push({ version: ver, items: itens });
    }
  }
  out.sort((a, b) => cmp(b.version, a.version)); // mais nova primeiro
  return out;
}
