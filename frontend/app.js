
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
 
function showMessage(text) {
  messageEl.textContent = text;
}
 
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
    const option = document.createElement("option");
    option.value = admin.id;
    option.textContent = `${admin.username} (${admin.email})`;
    loginSelect.appendChild(option);
  });
}
 
function updatePropertySelects(properties) {
  ["contract-property-select"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '<option value="">-- select property --</option>';
    properties.forEach((p) => {
      const option = document.createElement("option");
      option.value = p.id;
      option.textContent = `${p.name} (${p.address})`;
      el.appendChild(option);
    });
  });
}
 
function updateTenantSelect(users) {
  const el = document.getElementById("contract-tenant-select");
  if (!el) return;
  el.innerHTML = '<option value="">-- select tenant --</option>';
  users.filter((u) => u.role === "tenant").forEach((t) => {
    const option = document.createElement("option");
    option.value = t.id;
    option.textContent = `${t.username} (${t.email})`;
    el.appendChild(option);
  });
}
 
function renderProperties(properties, users) {
  if (properties.length === 0) {
    propertiesList.textContent = "No properties yet.";
    return;
  }
  propertiesList.innerHTML = "";
  properties.forEach((property) => {
    const card = document.createElement("div");
    card.className = "card";
    const owner = users.find((u) => u.id === property.owner_id);
    card.innerHTML = `
      <h3>${property.name}</h3>
      <p>${property.address}</p>
      ${property.image_url ? `<img src="${property.image_url}" alt="${property.name}" style="max-width:100%; height:auto; margin-bottom:0.75rem;" />` : ""}
      <p>Owner: ${owner ? owner.username : property.owner_id}</p>
    `;
    propertiesList.appendChild(card);
  });
}
 
registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("reg-username").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  try {
    const res = await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "admin", username, email, password }),
    });
    const data = await res.json();
    if (data.detail) { showMessage(data.detail); return; }
    showMessage(`Admin created: ${data.username}`);
    registerForm.reset();
    currentAdminId = data.id;
    enterDashboard(data);
    fetchData();
  } catch (e) {
    showMessage("Failed to create admin.");
  }
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
  } catch (e) {
    showMessage("Failed to login.");
  }
});
 
function enterDashboard(user) {
  currentAdminName.textContent = `${user.username} (${user.email})`;
  dashboardSection.style.display = "block";
  document.getElementById("login-section").style.display = "none";
}
 
logoutButton.addEventListener("click", () => {
  currentAdminId = null;
  dashboardSection.style.display = "none";
  document.getElementById("login-section").style.display = "block";
  showMessage("");
});
 
refreshButton.addEventListener("click", fetchData);
 
document.getElementById("property-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentAdminId) return showMessage("Select an admin first.");
  const name = document.getElementById("property-name").value.trim();
  const address = document.getElementById("property-address").value.trim();
  const image_url = document.getElementById("property-image").value.trim() || null;
  try {
    const res = await fetch("/api/properties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, address, image_url, owner_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Property created: ${data.name}`);
    document.getElementById("property-form").reset();
    fetchData();
  } catch (e) {
    showMessage("Failed to create property.");
  }
});
 
document.getElementById("tenant-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("tenant-username").value.trim();
  const email = document.getElementById("tenant-email").value.trim();
  const password = document.getElementById("tenant-password").value;
  try {
    const res = await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "tenant", username, email, password }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Tenant created: ${data.username}`);
    document.getElementById("tenant-form").reset();
    fetchData();
  } catch (e) {
    showMessage("Failed to create tenant.");
  }
});
 
document.getElementById("contract-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentAdminId) return showMessage("Select an admin first.");
  const property_id = Number(document.getElementById("contract-property-select").value);
  const tenant_id = Number(document.getElementById("contract-tenant-select").value);
  const amount = Number(document.getElementById("contract-amount").value);
  const year = Number(document.getElementById("contract-year").value);
  const month = Number(document.getElementById("contract-month").value);
  if (!property_id || !tenant_id || !amount) return showMessage("Fill in all contract fields.");
  try {
    const res = await fetch("/api/contracts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ property_id, tenant_id, amount, year, month, admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Contract created for month ${month}/${year}`);
    document.getElementById("contract-form").reset();
    fetchData();
  } catch (e) {
    showMessage("Failed to create contract.");
  }
});
 
document.getElementById("generate-reminders").addEventListener("click", async () => {
  if (!currentAdminId) return showMessage("Select an admin first.");
  const year = Number(document.getElementById("month-year").value);
  const month = Number(document.getElementById("month-month").value);
  try {
    const res = await fetch("/api/admin/generate_reminders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ year, month, admin_id: Number(currentAdminId) }),
    });
    const data = await res.json();
    if (data.detail) return showMessage(data.detail);
    showMessage(`Created ${data.created} contracts`);
    fetchData();
  } catch (e) {
    showMessage("Failed to generate reminders.");
  }
});
 
document.getElementById("view-month").addEventListener("click", async () => {
  if (!currentAdminId) return showMessage("Select an admin first.");
  const year = Number(document.getElementById("month-year").value);
  const month = Number(document.getElementById("month-month").value);
  try {
    const res = await fetch(`/api/admin/month/${year}/${month}?admin_id=${Number(currentAdminId)}`);
    const data = await res.json();
    renderMonthView(data);
  } catch (e) {
    showMessage("Failed to load month summary.");
  }
});
 
function renderMonthView(data) {
  const container = document.getElementById("month-view");
  container.innerHTML = "";
  if (!data || Object.keys(data).length === 0) {
    container.textContent = "No contracts for this month.";
    return;
  }
  Object.values(data).forEach((prop) => {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `<h4>${prop.property}</h4>`;
    const table = document.createElement("table");
    table.style.width = "100%";
    table.innerHTML = `<thead><tr><th>Tenant</th><th>Amount</th><th>Paid</th><th>Signed</th><th>Actions</th></tr></thead>`;
    const tbody = document.createElement("tbody");
    prop.tenants.forEach((t) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${t.tenant}</td><td>${t.amount}</td><td>${t.paid}</td><td>${t.paid_full ? "Yes" : "No"}</td>`;
      const actionsTd = document.createElement("td");
      const sendBtn = document.createElement("button");
      sendBtn.textContent = "Send sign link";
      sendBtn.addEventListener("click", async () => {
        try {
          const res = await fetch(`/api/contracts/${t.contract_id}/generate_token`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ admin_id: Number(currentAdminId) }),
          });
          const resp = await res.json();
          showMessage(resp.link ? "Sign link: " + resp.link : "Failed to generate sign link.");
        } catch (e) {
          showMessage("Error generating sign link.");
        }
      });
      actionsTd.appendChild(sendBtn);
      tr.appendChild(actionsTd);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    el.appendChild(table);
    el.appendChild(document.createElement("hr"));
    const totals = document.createElement("div");
    totals.textContent = `Collected: ${prop.total_collected} — Due: ${prop.total_due}`;
    el.appendChild(totals);
    container.appendChild(el);
  });
}
 
fetchData();
