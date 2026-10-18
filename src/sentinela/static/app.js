(() => {
  const tokenKey = "sentinela_session_token";
  const loginPanel = document.getElementById("login");
  const contentPanel = document.getElementById("content");
  const loginMessage = document.getElementById("login-message");
  const message = document.getElementById("message");
  const api = async (path, options = {}) => {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionStorage.getItem(tokenKey) || ""}`, ...(options.headers || {}) },
    });
    if (!response.ok) {
      if (response.status === 401) sessionStorage.removeItem(tokenKey);
      throw new Error(`Solicitação recusada (${response.status}).`);
    }
    return response.json();
  };
  const cell = (row, value) => {
    const td = document.createElement("td");
    td.textContent = value == null ? "—" : String(value);
    row.appendChild(td);
  };
  async function render() {
    const [dashboard, identity, assets] = await Promise.all([
      api("/api/dashboard"), api("/api/auth/me"), api("/api/assets"),
    ]);
    loginPanel.hidden = true;
    contentPanel.hidden = false;
    document.getElementById("identity").textContent = `Sessão: ${identity.username} (${identity.role})`;
    const metrics = document.getElementById("metrics");
    metrics.replaceChildren();
    Object.entries(dashboard.counts).forEach(([label, value]) => {
      const card = document.createElement("article"); card.className = "card";
      const number = document.createElement("div"); number.className = "metric"; number.textContent = String(value);
      const title = document.createElement("div"); title.textContent = label.replaceAll("_", " ");
      card.append(number, title); metrics.appendChild(card);
    });
    const ledger = document.getElementById("ledger-status");
    ledger.textContent = dashboard.ledger_integrity.valid
      ? `Verificado: ${dashboard.ledger_integrity.events_checked} evento(s).`
      : `Falha de integridade no evento ${dashboard.ledger_integrity.failed_seq}.`;
    const events = document.getElementById("events"); events.replaceChildren();
    dashboard.recent_events.forEach((event) => {
      const row = document.createElement("tr");
      [event.seq, event.timestamp, event.action, event.outcome, event.reason_code].forEach((value) => cell(row, value));
      events.appendChild(row);
    });
    const assetPanel = document.getElementById("assets"); assetPanel.replaceChildren();
    if (!assets.length) { assetPanel.textContent = "Nenhum ativo cadastrado."; return; }
    const list = document.createElement("ul");
    assets.forEach((asset) => {
      const item = document.createElement("li");
      item.textContent = `${asset.name} — ${asset.asset_type}; criticidade ${asset.criticality}; zona ${asset.network_zone}`;
      list.appendChild(item);
    });
    assetPanel.appendChild(list);
  }
  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault(); loginMessage.textContent = "";
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: document.getElementById("username").value, password: document.getElementById("password").value }),
      });
      if (!response.ok) throw new Error("Usuário ou senha inválidos.");
      const result = await response.json(); sessionStorage.setItem(tokenKey, result.access_token);
      document.getElementById("password").value = ""; await render();
    } catch (error) { loginMessage.textContent = error.message; }
  });
  document.getElementById("logout").addEventListener("click", () => {
    sessionStorage.removeItem(tokenKey); contentPanel.hidden = true; loginPanel.hidden = false;
  });
  if (sessionStorage.getItem(tokenKey)) render().catch((error) => {
    sessionStorage.removeItem(tokenKey); loginPanel.hidden = false; message.textContent = error.message;
  });
})();
