const box = document.getElementById("chat-box");
let afterId = 0;

async function pollNow() {
  try {
    const r = await fetch(`/api/admin/chat?after_id=${afterId}`);
    const data = await r.json();
    (data.messages || []).forEach(m => {
      const div = document.createElement("div");
      div.className = "msg";
      div.innerHTML = `<div class="meta">${new Date(m.created_at * 1000).toLocaleString()}</div>${m.mensagem}</div>`;
      box.appendChild(div);
      afterId = m.id;
    });
    box.scrollTop = box.scrollHeight;
  } catch (e) { /* ignore */ }
}
setInterval(pollNow, 3000);
pollNow();

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;
  await fetch("/api/admin/chat", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensagem: msg }) });
  input.value = "";
  pollNow();
});
