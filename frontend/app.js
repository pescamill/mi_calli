// ── State ──
let currentAdminId = null;
let currentLang = "en";
let allUsers = [];
let allProperties = [];
let allRooms = [];
let activeCell = null;
let activeRoomId = null;
let activePropId = null;

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const MONTHS_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];

// ── Language ──
function t(en, es) { return currentLang === "es" ? es : en; }

function applyLang() {
  document.querySelectorAll("[data-en]").forEach(el => {
    const val = currentLang === "es" ? el.dataset.es : el.dataset.en;
    if (val) el.textContent = val;
  });
  document.getElementById("lang-btn").textContent = currentLang === "en" ? "ES" : "EN";
}

document.getElementById("lang-btn").addEventListener("click", () => {
  currentLang = currentLang === "en" ? "es" : "en";
  applyLang();
});

// ── Message ──
const messageEl = document.getElementById("message");
function showMessage(text, isError = false) {
  if (!text) { messageEl.classList.remove("visible","error"); return; }
  messageEl.textContent = text;
  messageEl.classList.add("visible");
  messageEl.classList.toggle("error", isError);
  if (!isError) setTimeout(() => messageEl.classList.remove("visible"), 4000);
}

// ── Navigation ──
function showSection(name) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  const sec = document.getElementById(`${name}-section`);
  if (sec) sec.classList.add("active");
  document.querySelectorAll(`[data-section="${name}"]`).forEach(b => b.classList.add("active"));
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => showSection(btn.dataset.section));
});

// ── Fetch helpers ──
async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return res.json();
}

async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: fd });
  const data = await res.json();
  return data.url || null;
}

// ── Load all data ──
async function loadAll() {
  try {
    const [users, props, rooms] = await Promise.all([
      api("/users"),
      api("/properties"),
      api("/rooms"),
    ]);
    allUsers = Array.isArray(users) ? users : [];
    allProperties = Array.isArray(props) ? props : [];
    allRooms = Array.isArray(rooms) ? rooms : [];
    populateSelects();
  } catch (e) {
    showMessage(t("Failed to load data.", "Error al cargar datos."), true);
  }
}

function populateSelects() {
  // Login select
  const loginSel = document.getElementById("login-select");
  loginSel.innerHTML = '<option value="">— choose / elegir —</option>';
  allUsers.filter(u => u.role === "admin").forEach(u => {
    const o = document.createElement("option");
    o.value = u.id; o.textContent = u.username;
    loginSel.appendChild(o);
  });

  // Tenant select (contract form)
  const tenantSel = document.getElementById("contract-tenant-select");
  tenantSel.innerHTML = '<option value="">— select —</option>';
  allUsers.filter(u => u.role === "tenant").forEach(u => {
    const o = document.createElement("option");
    o.value = u.id; o.textContent = `${u.username} (${u.email})`;
    tenantSel.appendChild(o);
  });

  // Room select (contract form) — only vacant rooms
  const roomSel = document.getElementById("contract-room-select");
  roomSel.innerHTML = '<option value="">— select —</option>';
  allRooms.filter(r => !r.occupied).forEach(r => {
    const prop = allProperties.find(p => p.id === r.property_id);
    const o = document.createElement("option");
    o.value = r.id;
    o.textContent = `${prop ? prop.name + ' / ' : ''}${r.name}`;
    // Pre-fill defaults on change
    roomSel.addEventListener("change", () => {
      const selected = allRooms.find(rm => rm.id === Number(roomSel.value));
      if (selected) {
        if (selected.default_amount) document.getElementById("contract-amount").value = selected.default_amount;
        if (selected.default_pay_day) document.getElementById("contract-pay-day").value = selected.default_pay_day;
        if (selected.default_duration_months) document.getElementById("contract-duration").value = selected.default_duration_months;
      }
    });
    roomSel.appendChild(o);
  });

  // Property selects
  ["room-property-select", "expense-property-select", "expense-filter-select"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const isFilter = id === "expense-filter-select";
    el.innerHTML = isFilter ? '<option value="">— all / todas —</option>' : '<option value="">— select —</option>';
    allProperties.forEach(p => {
      const o = document.createElement("option");
      o.value = p.id; o.textContent = p.name;
      el.appendChild(o);
    });
  });

  renderTenantList();
  renderPropList();
}

// ── Login / Auth ──
document.getElementById("login-button").addEventListener("click", async () => {
  const id = document.getElementById("login-select").value;
  if (!id) { showMessage(t("Select an admin.", "Selecciona un admin."), true); return; }
  const user = allUsers.find(u => String(u.id) === String(id));
  if (user) enterDashboard(user);
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("reg-username").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  try {
    const data = await api("/users", { method: "POST", body: JSON.stringify({ role: "admin", username, email, password }) });
    if (data.detail) { showMessage(data.detail, true); return; }
    showMessage(t(`Welcome, ${data.username}.`, `Bienvenido, ${data.username}.`));
    e.target.reset();
    await loadAll();
    enterDashboard(data);
  } catch { showMessage(t("Failed to create admin.", "Error al crear admin."), true); }
});

function enterDashboard(user) {
  currentAdminId = user.id;
  document.getElementById("current-admin-name").textContent = user.username;
  document.getElementById("admin-pill").classList.add("visible");
  document.getElementById("logout-button").style.display = "block";
  document.getElementById("main-nav").style.display = "flex";
  document.getElementById("login-section").style.display = "none";
  showSection("dashboard");
  loadYearGrid();
}

document.getElementById("logout-button").addEventListener("click", () => {
  currentAdminId = null;
  document.getElementById("admin-pill").classList.remove("visible");
  document.getElementById("logout-button").style.display = "none";
  document.getElementById("main-nav").style.display = "none";
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.getElementById("login-section").style.display = "block";
  showMessage("");
});

// ── Dashboard / Year Grid ──
async function loadYearGrid() {
  const year = Number(document.getElementById("overview-year").value);
  if (!year) return;
  try {
    const data = await api(`/admin/year/${year}`);
    renderYearGrid(data, year);
  } catch (e) {
    showMessage(t("Failed to load year data: ", "Error al cargar datos: ") + e.message, true);
  }
}

function cellStatus(entries) {
  if (!entries || entries.length === 0) return "none";
  return entries.every(e => e.paid_full) ? "paid" : "unpaid";
}

function renderYearGrid(data, year) {
  const container = document.getElementById("year-grid");
  const properties = Object.values(data);
  const months = currentLang === "es" ? MONTHS_ES : MONTHS;

  if (properties.length === 0) {
    container.textContent = t("No contracts found for this year.", "Sin contratos para este año.");
    return;
  }

  const table = document.createElement("table");
  table.className = "ygrid";
  const thead = document.createElement("thead");
  let hr = `<tr><th class='prop-th'>${t("Property","Propiedad")}</th>`;
  months.forEach(m => { hr += `<th>${m}</th>`; });
  hr += "</tr>";
  thead.innerHTML = hr;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  properties.forEach(prop => {
    const row = document.createElement("tr");
    let cells = `<td class="prop-name">${prop.property}</td>`;
    for (let m = 1; m <= 12; m++) {
      const entries = prop.months[String(m)];
      const status = cellStatus(entries);
      const cls = status === "paid" ? "dot-paid" : status === "unpaid" ? "dot-unpaid" : "dot-none";
      const count = entries ? entries.length : 0;
      const title = count > 0 ? `${count} ${t("tenant(s)","inquilino(s)")} — ${status}` : t("no contract","sin contrato");
      const label = count > 1 ? count : "";
      cells += `<td class="cell"><span class="dot ${cls}" title="${title}" data-prop-id="${prop.property_id}" data-month="${m}" data-year="${year}">${label}</span></td>`;
    }
    row.innerHTML = cells;
    tbody.appendChild(row);

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

  table.addEventListener("click", e => {
    const dot = e.target.closest(".dot");
    if (!dot || dot.classList.contains("dot-none")) return;
    const propId = dot.dataset.propId;
    const month = dot.dataset.month;
    const key = `${propId}-${month}`;

    if (activeCell === key) {
      document.getElementById(`detail-${propId}`).style.display = "none";
      activeCell = null;
      return;
    }
    activeCell = key;
    document.querySelectorAll(".detail-row").forEach(r => r.style.display = "none");

    const entries = data[String(propId)]?.months[String(month)];
    if (!entries || entries.length === 0) return;

    const detailRow = document.getElementById(`detail-${propId}`);
    const td = detailRow.querySelector("td");

    let rows = "";
    entries.forEach(entry => {
      rows += `
        <tr>
          <td style="color:var(--text);">${entry.room}</td>
          <td style="color:var(--text);">${entry.tenant}</td>
          <td>$${entry.amount.toLocaleString()}</td>
          <td>$${entry.paid.toLocaleString()}</td>
          <td><span class="badge ${entry.paid_full ? 'badge-yes' : 'badge-no'}">${entry.paid_full ? t("paid","pagado") : t("unpaid","pendiente")}</span></td>
          <td><span class="badge ${entry.admin_signed ? 'badge-yes' : 'badge-no'}">${entry.admin_signed ? t("signed","firmado") : t("pending","pendiente")}</span></td>
          <td><span class="badge ${entry.tenant_signed ? 'badge-yes' : 'badge-no'}">${entry.tenant_signed ? t("signed","firmado") : t("pending","pendiente")}</span></td>
          <td>
            <div class="actions-cell">
              <button class="btn-ghost btn-sm" onclick="sendSignLink(${entry.contract_id})">${t("send link","enviar link")}</button>
              <button class="btn-ghost btn-sm" onclick="adminSign(${entry.contract_id})">${t("admin sign","firmar")}</button>
              <button class="btn-ghost btn-sm" onclick="markPaid(${entry.contract_month_id})">${t("mark paid","marcar pagado")}</button>
            </div>
          </td>
        </tr>`;
    });

    td.innerHTML = `
      <div class="detail-panel">
        <table>
          <thead><tr>
            <th>${t("Room","Hab.")}</th><th>${t("Tenant","Inquilino")}</th>
            <th>${t("Amount","Monto")}</th><th>${t("Paid","Pagado")}</th>
            <th>${t("Status","Estado")}</th><th>${t("Admin","Admin")}</th>
            <th>${t("Tenant","Inquilino")}</th><th>${t("Actions","Acciones")}</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
    detailRow.style.display = "";
  });
}

document.getElementById("load-year").addEventListener("click", loadYearGrid);

// ── Properties ──
document.getElementById("property-image-file").addEventListener("change", e => {
  document.getElementById("property-upload-name").textContent = e.target.files[0]?.name || "";
});

document.getElementById("property-form").addEventListener("submit", async e => {
  e.preventDefault();
  if (!currentAdminId) return showMessage(t("Login first.","Inicia sesión primero."), true);
  const name = document.getElementById("property-name").value.trim();
  const address = document.getElementById("property-address").value.trim();
  const fileInput = document.getElementById("property-image-file");
  let image_url = null;
  if (fileInput.files.length > 0) {
    image_url = await uploadFile(fileInput.files[0]);
  }
  try {
    const data = await api("/properties", { method: "POST", body: JSON.stringify({ name, address, owner_id: Number(currentAdminId) }) });
    if (data.detail) return showMessage(data.detail, true);
    if (image_url) {
      await api(`/properties/${data.id}/images`, { method: "POST", body: JSON.stringify({ url: image_url }) });
    }
    showMessage(t(`Property created: ${data.name}`, `Propiedad creada: ${data.name}`));
    e.target.reset();
    document.getElementById("property-upload-name").textContent = "";
    await loadAll();
  } catch { showMessage(t("Failed to create property.","Error al crear propiedad."), true); }
});

document.getElementById("room-form").addEventListener("submit", async e => {
  e.preventDefault();
  const property_id = Number(document.getElementById("room-property-select").value);
  const name = document.getElementById("room-name").value.trim();
  const default_amount = document.getElementById("room-default-amount").value || null;
  const default_pay_day = document.getElementById("room-default-pay-day").value || null;
  const default_duration_months = document.getElementById("room-default-duration").value || null;
  if (!property_id || !name) return showMessage(t("Fill in all fields.","Completa todos los campos."), true);
  try {
    const data = await api("/rooms", { method: "POST", body: JSON.stringify({
      property_id, name,
      default_amount: default_amount ? Number(default_amount) : null,
      default_pay_day: default_pay_day ? Number(default_pay_day) : null,
      default_duration_months: default_duration_months ? Number(default_duration_months) : null,
    })});
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t(`Room created: ${data.name}`, `Habitación creada: ${data.name}`));
    e.target.reset();
    await loadAll();
  } catch { showMessage(t("Failed to create room.","Error al crear habitación."), true); }
});

function renderPropList() {
  const container = document.getElementById("prop-list");
  container.innerHTML = "";
  if (allProperties.length === 0) {
    container.innerHTML = `<p style="color:var(--text3);">${t("No properties yet.","Sin propiedades aún.")}</p>`;
    return;
  }
  allProperties.forEach(prop => {
    const rooms = allRooms.filter(r => r.property_id === prop.id);
    const occupied = rooms.filter(r => r.occupied).length;

    const item = document.createElement("div");
    item.className = "prop-item";
    item.innerHTML = `
      <div class="prop-header" onclick="toggleProp(${prop.id})">
        <div class="prop-header-left">
          <h3>${prop.name}</h3>
          <p>${prop.address} · ${rooms.length} ${t("rooms","hab.")} · ${occupied} ${t("occupied","ocupadas")}</p>
        </div>
        <div style="display:flex;gap:0.5rem;align-items:center;">
          <span class="badge badge-neutral">${rooms.length - occupied} ${t("vacant","vacantes")}</span>
          <span style="color:var(--text3);">▾</span>
        </div>
      </div>
      <div class="prop-body" id="prop-body-${prop.id}">
        <div class="rooms-grid" id="rooms-grid-${prop.id}"></div>
        <div id="room-detail-${prop.id}"></div>
      </div>
    `;
    container.appendChild(item);
    renderRoomsGrid(prop.id, rooms);
  });
}

window.toggleProp = function(propId) {
  const body = document.getElementById(`prop-body-${propId}`);
  body.classList.toggle("open");
};

function renderRoomsGrid(propId, rooms) {
  const grid = document.getElementById(`rooms-grid-${propId}`);
  if (!grid) return;
  grid.innerHTML = "";
  if (rooms.length === 0) {
    grid.innerHTML = `<p style="color:var(--text3);font-size:12px;">${t("No rooms yet.","Sin habitaciones aún.")}</p>`;
    return;
  }
  rooms.forEach(room => {
    const card = document.createElement("div");
    card.className = `room-card ${room.occupied ? "occupied" : "vacant"}`;
    const firstImg = room.images && room.images[0] ? `<img src="${room.images[0].url}" alt="${room.name}" />` : "";
    card.innerHTML = `
      ${firstImg}
      <div class="room-status"><span class="badge ${room.occupied ? 'badge-yes' : 'badge-neutral'}">${room.occupied ? t("occupied","ocupada") : t("vacant","vacante")}</span></div>
      <h4>${room.name}</h4>
      <p>${room.default_amount ? `$${Number(room.default_amount).toLocaleString()}/${t("mo","mes")}` : t("no default rent","sin renta base")}</p>
    `;
    card.addEventListener("click", () => showRoomDetail(propId, room.id));
    grid.appendChild(card);
  });
}

async function showRoomDetail(propId, roomId) {
  if (activeRoomId === roomId) {
    document.getElementById(`room-detail-${propId}`).innerHTML = "";
    activeRoomId = null;
    return;
  }
  activeRoomId = roomId;
  const room = allRooms.find(r => r.id === roomId);
  if (!room) return;

  const container = document.getElementById(`room-detail-${propId}`);

  // Load contracts for this room
  let contracts = [];
  try { contracts = await api(`/contracts?room_id=${roomId}`); } catch {}
  const activeContract = contracts.find(c => !c.terminated_at);

  const imgsHtml = (room.images || []).map(img =>
    `<div class="img-thumb"><img src="${img.url}" /><button class="del-img" onclick="deleteRoomImage(${roomId},${img.id},${propId})">×</button></div>`
  ).join("");

  let contractHtml = "";
  if (activeContract) {
    const tenant = allUsers.find(u => u.id === activeContract.tenant_id);
    const monthsHtml = (activeContract.months || []).map(cm => {
      const paid = cm.payments.reduce((s, p) => s + Number(p.amount), 0);
      const isPaid = paid >= Number(activeContract.amount);
      return `
        <div class="month-card ${isPaid ? 'paid' : 'unpaid'}">
          <h5>${MONTHS[cm.month-1]} ${cm.year}</h5>
          <div class="amount">$${Number(activeContract.amount).toLocaleString()}</div>
          <div class="paid-amount">${t("paid","pagado")}: $${paid.toLocaleString()}</div>
          ${!isPaid ? `<button class="btn-primary btn-sm" style="margin-top:0.5rem;" onclick="markPaid(${cm.id})">${t("Mark paid","Marcar pagado")}</button>` : `<span class="badge badge-yes" style="margin-top:0.5rem;">${t("paid","pagado")}</span>`}
          ${cm.file_path ? `<a href="${cm.file_path}" target="_blank" style="display:block;margin-top:0.4rem;font-size:10px;color:var(--accent);">${t("PDF","PDF")}</a>` : ""}
        </div>`;
    }).join("");

    contractHtml = `
      <div style="margin-top:1rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
          <div>
            <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:0.08em;">${t("Active contract","Contrato activo")}</div>
            <div style="color:var(--text);margin-top:0.2rem;">${tenant ? tenant.username : activeContract.tenant_id} · $${Number(activeContract.amount).toLocaleString()}/${t("mo","mes")} · ${t("pay day","día pago")}: ${activeContract.pay_day}</div>
            <div style="font-size:11px;color:var(--text3);">${activeContract.duration_months} ${t("months","meses")} · ${t("starts","inicia")}: ${activeContract.start_month}/${activeContract.start_year}</div>
            <div style="margin-top:0.5rem;display:flex;gap:0.5rem;">
              <span class="badge ${activeContract.admin_signed ? 'badge-yes' : 'badge-no'}">${t("admin","admin")} ${activeContract.admin_signed ? t("signed","firmado") : t("pending","pendiente")}</span>
              <span class="badge ${activeContract.tenant_signed ? 'badge-yes' : 'badge-no'}">${t("tenant","inquilino")} ${activeContract.tenant_signed ? t("signed","firmado") : t("pending","pendiente")}</span>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:0.4rem;align-items:flex-end;">
            <button class="btn-ghost btn-sm" onclick="sendSignLink(${activeContract.id})">${t("Send sign link","Enviar link firma")}</button>
            <button class="btn-ghost btn-sm" onclick="adminSign(${activeContract.id})">${t("Admin sign","Firmar como admin")}</button>
            <button class="btn-danger btn-sm" onclick="terminateContract(${activeContract.id},${propId})">${t("Terminate","Terminar contrato")}</button>
          </div>
        </div>
        <div class="months-grid">${monthsHtml}</div>
      </div>`;
  } else {
    contractHtml = `<p style="color:var(--text3);font-size:12px;margin-top:0.75rem;">${t("No active contract. Create one in the Tenants tab.","Sin contrato activo. Créalo en la pestaña Inquilinos.")}</p>`;
  }

  container.innerHTML = `
    <div class="room-detail">
      <div class="room-detail-header">
        <div>
          <div style="font-family:'Fraunces',serif;font-size:1rem;font-weight:600;">${room.name}</div>
          <div style="font-size:11px;color:var(--text3);">${room.default_amount ? `$${Number(room.default_amount).toLocaleString()} default` : ""}</div>
        </div>
        <div style="display:flex;gap:0.5rem;">
          <label style="cursor:pointer;">
            <input type="file" accept="image/*" style="display:none;" onchange="uploadRoomImage(event,${roomId},${propId})">
            <span class="btn-ghost btn-sm">${t("Add image","Agregar imagen")}</span>
          </label>
          <button class="btn-ghost btn-sm" onclick="closeRoomDetail(${propId})">${t("Close","Cerrar")}</button>
        </div>
      </div>
      <div class="img-strip">${imgsHtml}</div>
      ${contractHtml}
    </div>`;
}

window.closeRoomDetail = function(propId) {
  document.getElementById(`room-detail-${propId}`).innerHTML = "";
  activeRoomId = null;
};

window.uploadRoomImage = async function(event, roomId, propId) {
  const file = event.target.files[0];
  if (!file) return;
  const url = await uploadFile(file);
  if (!url) return showMessage(t("Upload failed.","Error al subir."), true);
  await api(`/rooms/${roomId}/images`, { method: "POST", body: JSON.stringify({ url }) });
  await loadAll();
  showRoomDetail(propId, roomId);
};

window.deleteRoomImage = async function(roomId, imageId, propId) {
  await api(`/rooms/${roomId}/images/${imageId}`, { method: "DELETE" });
  await loadAll();
  showRoomDetail(propId, roomId);
};

// ── Tenants ──
document.getElementById("tenant-form").addEventListener("submit", async e => {
  e.preventDefault();
  const username = document.getElementById("tenant-username").value.trim();
  const email = document.getElementById("tenant-email").value.trim();
  try {
    const data = await api("/users", { method: "POST", body: JSON.stringify({ role: "tenant", username, email, password: "unused" }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t(`Tenant created: ${data.username}`, `Inquilino creado: ${data.username}`));
    e.target.reset();
    await loadAll();
  } catch { showMessage(t("Failed to create tenant.","Error al crear inquilino."), true); }
});

document.getElementById("contract-form").addEventListener("submit", async e => {
  e.preventDefault();
  if (!currentAdminId) return showMessage(t("Login first.","Inicia sesión primero."), true);
  const room_id = Number(document.getElementById("contract-room-select").value);
  const tenant_id = Number(document.getElementById("contract-tenant-select").value);
  const amount = Number(document.getElementById("contract-amount").value);
  const start_year = Number(document.getElementById("contract-start-year").value);
  const start_month = Number(document.getElementById("contract-start-month").value);
  const duration_months = Number(document.getElementById("contract-duration").value);
  const pay_day = Number(document.getElementById("contract-pay-day").value);
  const inventory = document.getElementById("contract-inventory").value.trim() || null;
  if (!room_id || !tenant_id || !amount) return showMessage(t("Fill in all fields.","Completa todos los campos."), true);
  if (pay_day < 1 || pay_day > 28) return showMessage(t("Pay day must be 1-28.","Día de pago debe ser 1-28."), true);
  try {
    const data = await api("/contracts", { method: "POST", body: JSON.stringify({ room_id, tenant_id, amount, start_year, start_month, duration_months, pay_day, inventory }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t(`Contract created — ${duration_months} months`, `Contrato creado — ${duration_months} meses`));
    e.target.reset();
    await loadAll();
  } catch { showMessage(t("Failed to create contract.","Error al crear contrato."), true); }
});

function renderTenantList() {
  const container = document.getElementById("tenant-list");
  const tenants = allUsers.filter(u => u.role === "tenant");
  container.innerHTML = "";
  if (tenants.length === 0) {
    container.innerHTML = `<p style="color:var(--text3);">${t("No tenants yet.","Sin inquilinos aún.")}</p>`;
    return;
  }
  tenants.forEach(t_ => {
    const room = allRooms.find(r => {
      // Find room where tenant has active contract — approximate from room list
      return false; // We'd need contracts loaded; skip for now
    });
    const item = document.createElement("div");
    item.className = "tenant-item";
    item.innerHTML = `
      <div class="tenant-item-left">
        <strong>${t_.username}</strong>
        <span>${t_.email}</span>
      </div>
      <span class="badge badge-neutral">${t_.role}</span>
    `;
    container.appendChild(item);
  });
}

// ── Expenses ──
document.getElementById("expense-form").addEventListener("submit", async e => {
  e.preventDefault();
  const property_id = Number(document.getElementById("expense-property-select").value);
  const description = document.getElementById("expense-description").value.trim();
  const amount = Number(document.getElementById("expense-amount").value);
  const year = Number(document.getElementById("expense-year").value);
  const month = Number(document.getElementById("expense-month").value);
  if (!property_id || !description || !amount) return showMessage(t("Fill in all fields.","Completa todos los campos."), true);
  try {
    const data = await api(`/properties/${property_id}/expenses`, { method: "POST", body: JSON.stringify({ property_id, description, amount, year, month }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t("Expense added.","Gasto agregado."));
    e.target.reset();
    loadExpenses();
  } catch { showMessage(t("Failed to add expense.","Error al agregar gasto."), true); }
});

document.getElementById("expense-filter-select").addEventListener("change", loadExpenses);

async function loadExpenses() {
  const propId = document.getElementById("expense-filter-select").value;
  const container = document.getElementById("expense-list");
  container.innerHTML = "";
  const props = propId ? [allProperties.find(p => p.id === Number(propId))].filter(Boolean) : allProperties;
  for (const prop of props) {
    try {
      const expenses = await api(`/properties/${prop.id}/expenses`);
      if (!Array.isArray(expenses) || expenses.length === 0) continue;
      const header = document.createElement("div");
      header.style.cssText = "font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:0.08em;margin:0.75rem 0 0.4rem;";
      header.textContent = prop.name;
      container.appendChild(header);
      expenses.forEach(exp => {
        const item = document.createElement("div");
        item.className = "expense-item";
        item.innerHTML = `
          <div class="expense-item-left">
            <strong>${exp.description}</strong>
            <span>${exp.month}/${exp.year}</span>
          </div>
          <div class="expense-item-right">
            <span style="color:var(--text);">$${Number(exp.amount).toLocaleString()}</span>
            ${exp.paid_at
              ? `<span class="badge badge-yes">${t("paid","pagado")}</span>`
              : `<button class="btn-ghost btn-sm" onclick="markExpensePaid(${prop.id},${exp.id})">${t("Mark paid","Marcar pagado")}</button>`
            }
          </div>`;
        container.appendChild(item);
      });
    } catch {}
  }
  if (!container.innerHTML) {
    container.innerHTML = `<p style="color:var(--text3);">${t("No expenses found.","Sin gastos registrados.")}</p>`;
  }
}

// Load expenses when switching to expenses tab
document.querySelectorAll(".nav-btn").forEach(btn => {
  if (btn.dataset.section === "expenses") {
    btn.addEventListener("click", loadExpenses);
  }
});

window.markExpensePaid = async function(propId, expId) {
  await api(`/properties/${propId}/expenses/${expId}/mark_paid`, { method: "POST", body: JSON.stringify({}) });
  showMessage(t("Expense marked as paid.","Gasto marcado como pagado."));
  loadExpenses();
};

// ── Contract actions ──
window.sendSignLink = async function(contractId) {
  if (!currentAdminId) return showMessage(t("Login first.","Inicia sesión primero."), true);
  try {
    const data = await api(`/contracts/${contractId}/generate_token`, { method: "POST", body: JSON.stringify({ admin_id: Number(currentAdminId) }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(data.emailed ? t("Email sent to tenant.","Correo enviado al inquilino.") : t("Token generated (email not configured).","Token generado (correo no configurado)."));
  } catch { showMessage(t("Error sending link.","Error al enviar link."), true); }
};

window.adminSign = async function(contractId) {
  if (!currentAdminId) return showMessage(t("Login first.","Inicia sesión primero."), true);
  try {
    const data = await api(`/contracts/${contractId}/admin_sign`, { method: "POST", body: JSON.stringify({ admin_id: Number(currentAdminId) }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t("Admin signature recorded.","Firma del admin registrada."));
    await loadAll();
    loadYearGrid();
  } catch { showMessage(t("Error signing.","Error al firmar."), true); }
};

window.markPaid = async function(contractMonthId) {
  const amount = prompt(t("Enter payment amount:","Ingresa el monto del pago:"));
  if (!amount) return;
  try {
    const data = await api(`/contract_months/${contractMonthId}/mark_paid`, { method: "POST", body: JSON.stringify({ amount: Number(amount), recorded_by: Number(currentAdminId) }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t("Payment recorded.","Pago registrado."));
    await loadAll();
    if (activeRoomId && activePropId) showRoomDetail(activePropId, activeRoomId);
    loadYearGrid();
  } catch { showMessage(t("Failed to record payment.","Error al registrar pago."), true); }
};

window.terminateContract = async function(contractId, propId) {
  const confirmed = confirm(t(
    "Are you sure you want to terminate this contract? All future months will be removed and both parties will be notified.",
    "¿Estás seguro de terminar este contrato? Los meses futuros serán eliminados y ambas partes serán notificadas."
  ));
  if (!confirmed) return;
  try {
    const data = await api(`/contracts/${contractId}/terminate`, { method: "POST", body: JSON.stringify({ admin_id: Number(currentAdminId) }) });
    if (data.detail) return showMessage(data.detail, true);
    showMessage(t("Contract terminated.","Contrato terminado."));
    await loadAll();
    document.getElementById(`room-detail-${propId}`).innerHTML = "";
    activeRoomId = null;
  } catch { showMessage(t("Failed to terminate contract.","Error al terminar contrato."), true); }
};

// ── Init ──
loadAll();