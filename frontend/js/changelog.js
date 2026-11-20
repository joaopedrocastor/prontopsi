// Histórico de novidades por versão (mostrado ao reabrir após atualizar).
// Ao lançar uma versão nova, adicione a lista de mudanças aqui.

export const CHANGELOG = {
  "1.4.2": [
    "Novo recibo de prestação de serviços psicológicos no padrão do seu modelo: logo, arcos decorativos, número do recibo e rodapé com o endereço do consultório.",
    "O recibo já vem preenchido: responsável (nome, CPF, Sr./Sra.), paciente, valor por extenso, quantidade e dias das sessões — pode ser várias sessões de uma vez.",
    "Escolha a cidade do consultório no recibo e o endereço do rodapé acompanha. Cadastre em Configuração → Dados do recibo.",
    "Numeração dos recibos automática e contínua — você não precisa mais digitar o número.",
    "Todo recibo gerado fica salvo em Recibos → Recibos emitidos: baixe o PDF de novo ou edite e gere novamente com o mesmo número.",
    "No recibo, escolha o paciente numa lista com todos os cadastrados; os responsáveis dele aparecem para escolher quem pagou.",
    "O menu Clientes agora se chama Pacientes.",
    "Logo oficial no app: na barra lateral, na tela de senha e nos PDFs (ficha de anamnese, recibo e declaração).",
    "Correção: ao atualizar, a versão antiga instalada \"para todos os usuários\" é removida — fica apenas um ProntoPsi no computador (seus dados são mantidos).",
  ],
  "1.4.1": [
    "Novo menu Recibos: veja os pagamentos recebidos no mês e gere o recibo em PDF de cada um em 1 clique.",
    "Recibo do mês por cliente: soma todas as sessões pagas no mês em um único recibo (ótimo para reembolso).",
    "Recibo avulso para pagamentos que não estão no Financeiro. O pagador já vem preenchido com o responsável principal.",
  ],
  "1.4.0": [
    "Atualização em 1 clique: ao surgir uma versão nova, o app baixa, instala e reabre sozinho — sem precisar baixar nada pelo navegador.",
    "Instalação por usuário (sem pedir permissão de administrador nas próximas atualizações).",
    "Documentos em PDF: recibo de pagamento e declaração de comparecimento, com sua logo e CRP.",
    "Lembrete de consulta por WhatsApp em 1 clique (mensagem pronta), na Agenda e nas sessões.",
    "Responsáveis do cliente (mãe, pai, escola) na ficha — o lembrete usa o telefone do responsável principal.",
    "Valor da sessão por cliente + cobrança automática quando a sessão é marcada como realizada.",
  ],
  "1.3.0": [
    "Novo: Relatórios com gráficos — receita x despesa por mês, sessões realizadas, situação das sessões e dos clientes.",
    "Indicadores do período: recebido, despesas, saldo, a receber, sessões e clientes ativos.",
  ],
  "1.2.0": [
    "Novo módulo Financeiro: receitas e despesas, saldo do mês, contas vencidas, análise por categoria e lançamentos recorrentes.",
    "Financeiro por cliente na ficha: lance cobranças, marque como pago e veja o que está em aberto.",
    "Prontuário: registre a evolução de cada sessão e acompanhe o histórico clínico (na ficha e na Agenda).",
    "Nova identidade visual: logo, ícone e cores em tom terracota, combinando com a sua marca.",
  ],
  "1.1.6": [
    "Nova identidade visual: logo e ícone do ProntoPsi atualizados.",
  ],
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
