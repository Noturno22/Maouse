async function loadSocios() {
  const r = await fetch("/api/admin/socios");
  const data = await r.json();
  document.getElementById("socios-list").innerHTML = (data.items || [])
    .map(s => `<label style="display:flex;align-items:center;gap:6px">
      <input type="checkbox" value="${s.id}"> ${s.nome}${s.email ? ` — ${s.email}` : ""}</label>`)
    .join("") || '<span class="muted">Sem sócios registados.</span>';
}

document.getElementById("email-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ids = [...document.querySelectorAll("#socios-list input:checked")]
    .map(cb => Number(cb.value));
  const assunto = document.querySelector('[name="assunto"]').value.trim();
  const corpo = document.querySelector('[name="corpo"]').value.trim();
  const out = document.getElementById("email-result");
  if (!ids.length) { out.textContent = "Escolhe pelo menos um sócio."; return; }
  const r = await fetch("/api/admin/emails/send", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ socio_ids: ids, assunto, corpo }) });
  const data = await r.json();
  out.textContent = `Enviados: ${data.sent.length} · Sem envio: ${data.failed.length}`;
  loadHistory();
});

async function loadHistory() {
  const r = await fetch("/api/admin/emails");
  const data = await r.json();
  document.querySelector("#emails-history tbody").innerHTML = (data.items || [])
    .map(m => `<tr><td>${m.para}</td><td>${m.assunto}</td><td>${m.estado}</td>
      <td>${m.erro || ""}</td></tr>`).join("");
}

loadSocios();
loadHistory();
