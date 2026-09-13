const LABELS = {
  socios: "Sócios", investidores: "Investidores", funcionarios: "Funcionários",
  pagantes: "Pagantes", maquinas_ativas: "Máquinas ativas",
  fases_concluidas: "Fases concluídas", metas_abertas: "Metas em aberto",
  marcos: "Marcos", chat_mensagens: "Mensagens no chat",
};
fetch("/api/admin/dashboard")
  .then(r => r.json())
  .then(kpi => {
    document.getElementById("kpis").innerHTML = Object.entries(LABELS)
      .map(([k, l]) => `<div class="card kpi">
          <div class="v">${kpi[k] ?? 0}</div><div class="l">${l}</div></div>`)
      .join("");
  })
  .catch(console.error);
