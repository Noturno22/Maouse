const RES = window.ADMIN_RESOURCE;
const FIELDS = window.ADMIN_FIELDS;

async function j(url, opts) {
  const r = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok && r.status !== 404) throw new Error(await r.text());
  try { return await r.json(); } catch { return {}; }
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function load() {
  const data = await j(`/api/admin/${RES}`);
  const thead = document.getElementById("items-head");
  const tbody = document.getElementById("items-body");
  thead.innerHTML = "<th>#</th>" + FIELDS.map(f => `<th>${esc(f).replace(/_/g, " ")}</th>`).join("")
    + "<th></th>";
  tbody.innerHTML = (data.items || []).map(item => {
    const tds = FIELDS.map(f => `<td>${esc(item[f])}</td>`).join("");
    return `<tr><td>${item.id}</td>${tds}
      <td>
        <button class="ghost" onclick="editItem(${item.id})">Editar</button>
        <button class="ghost danger" onclick="delItem(${item.id})">Eliminar</button>
      </td></tr>`;
  }).join("");
  window._items = data.items || [];
}

window.editItem = function (id) {
  const item = window._items.find(x => String(x.id) === String(id));
  if (!item) return;
  document.querySelectorAll("#entry-form input, #entry-form textarea")
    .forEach(el => { el.value = item[el.name] ?? ""; });
  const btn = document.getElementById("save-btn");
  btn.textContent = "Guardar";
  btn.dataset.id = id;
};

async function delItem(id) {
  if (!confirm("Eliminar registo?")) return;
  await j(`/api/admin/${RES}/${id}`, { method: "DELETE" });
  await load();
}
window.delItem = delItem;

document.getElementById("entry-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {};
  document.querySelectorAll("#entry-form input, #entry-form textarea")
    .forEach(el => { payload[el.name] = el.value.trim(); });
  const btn = document.getElementById("save-btn");
  if (btn.dataset.id) {
    await j(`/api/admin/${RES}/${btn.dataset.id}`, {
      method: "PATCH", body: JSON.stringify(payload),
    });
    delete btn.dataset.id;
  } else {
    await j(`/api/admin/${RES}`, { method: "POST", body: JSON.stringify(payload) });
  }
  btn.textContent = "Adicionar";
  document.getElementById("entry-form").reset();
  await load();
});

load().catch(console.error);
