const messageEl = document.getElementById("message");
const loginSelect = document.getElementById("login-select");
const loginButton = document.getElementById("login-button");
const registerForm = document.getElementById("register-form");
const dashboardSection = document.getElementById("dashboard-section");
const currentAdminName = document.getElementById("current-admin-name");
const logoutButton = document.getElementById("logout-button");
const refreshButton = document.getElementById("refresh-button");
const propertiesList = document.getElementById("properties-list");

let currentAdminId = null;
let activeCell = null;
let yearData = {};

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function showMessage(text) { messageEl.textContent = text; }

async function fetchData() {
  try {
    const [usersRes, propsRes] = await Promise.all([fetch("/api/users"), fetch("/api/properties")]);
    const users = await usersRes.json();
    const properties = await propsRes.json();
    updateLoginSelect(users);
    updatePropertySelects(properties);
    updateTenantSelect(users);
    renderProperties(properties, users);
    showMessage("");
  } catch (e) {
    showMessage("Unable to load data. Make sure docker compose is running.");
  }
}

function updateLoginSelect(users) {
  loginSelect.innerHTML = '<option value="">-- choose admin --</option>';
  users.filter((u) => u.role === "admin").forEach((admin) => {
    const o = document.createElement("option");
    o.value = admin.id;
    o.textContent = `${admin.username} (${admin.email})`;
    loginSelect.appendChild(o);
  });
}

function updatePropertySelects(properties) {
  const el = document.getElementById("contract-property-select");
  if (!el) return;
  el.innerHTML = '<option value="">-- select property --</option>';
  properties.forEach((p) => {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = `${p.name} (${p.address})`;
    el.appendChild(o);
  });
}

function updateTenantSelect(users) {
  const el = document.getElementById("contract-tenant-select");
  if (!el) return;
  el.innerHTML = '<option value="">-- select tenant --</option>';
  users.filter((u) => u.role === "tenant").forEach((t) => {
    const o = document.createElement("option");
    o.value = t.id;
    o.textContent = `${t.username} (${t.email})`;
    el.appendChild(o);
  });
}

function renderProperties(properties, users) {
  if (properties.length === 0) { propertiesList.textContent = "No properties yet."; return; }
  propertiesList.innerHTML = "";
  properties.forEach((p) => {
    const card = document.createElement("div");
    card.className = "card";
    const owner = users.find((u) => u.id === p.owner_id);
    card.innerHTML = `
      <h3>${p.name}</h3>
      <p style="margin:0;color:#555;">${p.address}</p>
      ${p.image_url ? `<img src="${p.image_url}" alt="${p.name}" style="max-width:100%;height:auto;margin-top:0.5rem;" />` : ""}
      <p style="margin:0.5rem 0 0;font-size:13px;color:#777;">Owner: ${owner ? owner.username : p.owner_id}</p>
    `;
    propertiesList.appendChild(card);
  });
}

async function loadYearGrid() {
  const year = Number(document.getElementById("overview-year").value);
  if (!year) return;
  try {
    const res = await fetch(`/api/admin/year/${year}`);
    yearData = await res.json();
    renderYearGrid(yearData, year);
  } catch (e) {
    console.error("loadYearGrid error:", e);
    showMessage("Failed to load year data: " + e.message);
  }
}

function cellStatus(entries) {
  if (!entries || entries.length === 0) return "none";
  const allPaid = entries.every((e) => e.paid_full);
  return allPaid ? "paid" : "unpaid";
}

function renderYearGrid(data, year) {
  const container = document.getElementById("year-grid");
  const properties = Object.values(data);
  if (properties.length === 0) { container.textContent = "No contracts found for this year."; return; }

  const table = document.createElement("table");
  table.className = "year-grid";

  const thead = document.createElement("thead");
  let headerRow = "<tr><th style='text-align:left;padding:6px 8px;'>Property</th>";
  MONTHS.forEach((m) => { headerRow += `<th>${m}</th>`; });
  headerRow += "</tr>";
  thead.innerHTML = headerRow;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");

  properties.forEach((prop) => {
    const propRow = document.createElement("tr");
    propRow.dataset.propId = prop.property_id;

    let cells = `<td class="prop-name">${prop.property}</td>`;
    for (let m = 1; m <= 12; m++) {
      const entries = prop.months[String(m)];
      const status = cellStatus(entries);
      const cls = status === "paid" ? "dot-paid" : status === "unpaid" ? "dot-unpaid" : "dot-none";
      const count = entries ? entries.length : 0;
      const title = count > 0 ? `${count} tenant(s) — ${status}` : "No contract";
      cells += `<td class="cell"><span class="dot ${cls}" title="${title}" data-prop-id="${prop.property_id}" data-month="${m}" data-year="${year}"></span></td>`;
    }
    propRow.innerHTML = cells;
    tbody.appendChild(propRow);

    const detailRow = document.createElement("tr");
    detailRow.className = "detail-row";
    detailRow.id = `detail-${prop.property_id}`;
    detailRow.style.display = "none";
    const detailTd = document.createElement("td");
    detailTd.colSpan = 13;
    detailRow.appendChild(detailTd);
    tbody.appendChild(detailRow);
  });

  table.appendChild(tbody);
  container.innerHTML = "";
  container.appendChild(table);

  table.addEventListener("click", (e) => {
    const dot = e.target.closest(".dot");
    if (!dot || dot.classList.contains("dot-none")) return;
    const propId = dot.dataset.propId;
    const month = dot.dataset.month;
    const yr = dot.dataset.year;
    const key = `${propId}-${month}`;

    if (activeCell === key) {
      document.getElementById(`detail-${propId}`).style.display = "none";
      activeCell = null;
      return;
    }

    activeCell = key;
    document.querySelectorAll(".detail-row").forEach((r) => { r.style.display = "none"; });

    const entries = data[String(propId)]?.months[String(month)];
    if (!entries || entries.length === 0) return;

    const detailRow = document.getElementById(`detail-${propId}`);
    const td = detailRow.querySelector("td");

    let rows = "";
    entries.forEach((entry) => {
      rows += `
        <tr>
          <td>${entry.tenant}</td>
          <td>$${entry.amount.toLocaleString()}</td>
          <td>$${entry.paid.toLocaleString()}</td>
          <td><span class="badge ${entry.admin_signed ? 'badge-yes' : 'badge-no'}">${entry.admin_signed ? "Yes" : "No"}</span></td>
          <td><span class="badge ${entry.tenant_signed ? 'badge-yes' : 'badge-no'}">${entry.tenant_signed ? "Yes" : "No"}</span></td>
          <td>
            <button class="action-btn" onclick="sendSignLink(${entry.contract_id})">Send sign link</button>
            <button class="action-btn" onclick="adminSign(${entry.contract_id})" style="margin-left:4px;">Admin sign</button>
            <button class="action-btn" onclick="markPaid(${entry.contract_id})" style="margin-left:4px;">Mark paid</button>
          </td>
        </tr>
      `;
    });

    td.innerHTML = `
      <div class="detail-panel">
        <table>
          <thead><tr><th>Tenant</th><th>Amount</th><th>Paid</th><th>Admin signed</th><th>Tenant signed</th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
    detailRow.style.display = "";
  });
}

async function sendSignLink(contractId) {
  if (!currentAdminId) return showMessage("Select an admin first.");
  try {
    const res = await fetch(`/api/contracts/${contractId}/generate_token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.link) showMessage("Sign link: " + data.link);
    else showMessage("Failed to generate sign link.");
  } catch (e) { showMessage("Error generating sign link."); }
}

async function adminSign(contractId) {
  if (!currentAdminId) return showMessage("Select an admin first.");
  try {
    const res = await fetch(`/api/contracts/${contractId}/admin_sign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage("Admin signature recorded.");
    await loadYearGrid();
  } catch (e) { showMessage("Error recording admin signature."); }
}

async function markPaid(contractId) {
  const amount = prompt("Enter payment amount:");
  if (!amount) return;
  try {
    const res = await fetch(`/api/contracts/${contractId}/mark_paid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: Number(amount), recorded_by: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage("Payment recorded.");
    await loadYearGrid();
  } catch (e) { showMessage("Failed to record payment."); }
}

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("reg-username").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  try {
    const res = await fetch("/api/users", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "admin", username, email, password }),
    });
    const data = await res.json();
    if (data.detail) { showMessage(data.detail); return; }
    showMessage(`Admin created: ${data.username}`);
    registerForm.reset();
    currentAdminId = data.id;
    enterDashboard(data);
    fetchData();
  } catch (e) { showMessage("Failed to create admin."); }
});

loginButton.addEventListener("click", async () => {
  const id = loginSelect.value;
  if (!id) { showMessage("Select an admin to login."); return; }
  try {
    const res = await fetch("/api/users");
    const users = await res.json();
    const user = users.find((u) => String(u.id) === String(id));
    if (!user) { showMessage("Admin not found"); return; }
    currentAdminId = user.id;
    enterDashboard(user);
  } catch (e) { showMessage("Failed to login."); }
});

function enterDashboard(user) {
  currentAdminName.textContent = `${user.username} (${user.email})`;
  dashboardSection.style.display = "block";
  document.getElementById("login-section").style.display = "none";
  loadYearGrid();
}

logoutButton.addEventListener("click", () => {
  currentAdminId = null;
  dashboardSection.style.display = "none";
  document.getElementById("login-section").style.display = "block";
  showMessage("");
});

refreshButton.addEventListener("click", () => { fetchData(); loadYearGrid(); });
document.getElementById("load-year").addEventListener("click", loadYearGrid);

document.getElementById("property-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentAdminId) return showMessage("Select an admin first.");
  const name = document.getElementById("property-name").value.trim();
  const address = document.getElementById("property-address").value.trim();
  const image_url = document.getElementById("property-image").value.trim() || null;
  try {
    const res = await fetch("/api/properties", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, address, image_url, owner_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Property created: ${data.name}`);
    document.getElementById("property-form").reset();
    fetchData();
  } catch (e) { showMessage("Failed to create property."); }
});

document.getElementById("tenant-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("tenant-username").value.trim();
  const email = document.getElementById("tenant-email").value.trim();
  try {
    const res = await fetch("/api/users", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "tenant", username, email, password: "unused" }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Tenant created: ${data.username}`);
    document.getElementById("tenant-form").reset();
    fetchData();
  } catch (e) { showMessage("Failed to create tenant."); }
});

window.sendSignLink = async function(contractId) {
  if (!currentAdminId) return showMessage("Select an admin first.");
  try {
    const res = await fetch(`/api/contracts/${contractId}/generate_token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.link) showMessage("Sign link: " + data.link);
    else showMessage("Failed to generate sign link.");
  } catch (e) { showMessage("Error generating sign link."); }
}

window.adminSign = async function(contractId) {
  if (!currentAdminId) return showMessage("Select an admin first.");
  try {
    const res = await fetch(`/api/contracts/${contractId}/admin_sign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage("Admin signature recorded.");
    await loadYearGrid();
  } catch (e) { showMessage("Error recording admin signature."); }
}

window.markPaid = async function(contractId) {
  const amount = prompt("Enter payment amount:");
  if (!amount) return;
  try {
    const res = await fetch(`/api/contracts/${contractId}/mark_paid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: Number(amount), recorded_by: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage("Payment recorded.");
    await loadYearGrid();
  } catch (e) { showMessage("Failed to record payment."); }
}

document.getElementById("contract-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentAdminId) return showMessage("Select an admin first.");
  const property_id = Number(document.getElementById("contract-property-select").value);
  const tenant_id = Number(document.getElementById("contract-tenant-select").value);
  const amount = Number(document.getElementById("contract-amount").value);
  const year = Number(document.getElementById("contract-year").value);
  const month = Number(document.getElementById("contract-month").value);
  if (!property_id || !tenant_id || !amount) return showMessage("Fill in all contract fields.");
  try {
    const res = await fetch("/api/contracts", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ property_id, tenant_id, amount, year, month }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Contract created for ${month}/${year}`);
    document.getElementById("contract-form").reset();
    loadYearGrid();
  } catch (e) { showMessage("Failed to create contract."); }
});

document.getElementById("generate-reminders").addEventListener("click", async () => {
  if (!currentAdminId) return showMessage("Select an admin first.");
  const year = Number(document.getElementById("overview-year").value);
  const month = Number(document.getElementById("remind-month").value);
  try {
    const res = await fetch("/api/admin/generate_reminders", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ year, month, admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Created ${data.created} contracts`);
    loadYearGrid();
  } catch (e) { showMessage("Failed to generate reminders."); }
});

fetchData();