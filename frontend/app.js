const messageEl = document.getElementById("message");
const adminSelect = document.getElementById("admin-select");
const dashboardEl = document.getElementById("dashboard");
const propertySelect = document.getElementById("property-select");
const propertiesList = document.getElementById("properties-list");

let currentAdminId = null;

function showMessage(text) {
  messageEl.textContent = text;
}

function fetchData() {
  Promise.all([fetch("/api/users"), fetch("/api/properties")])
    .then(async ([usersRes, propsRes]) => {
      const users = await usersRes.json();
      const properties = await propsRes.json();
      updateAdminSelect(users);
      updatePropertySelect(properties);
      renderProperties(properties, users);
      showMessage("");
    })
    .catch(() => showMessage("Unable to load data. Make sure docker compose is running."));
}

function updateAdminSelect(users) {
  adminSelect.innerHTML = '<option value="">-- choose admin --</option>';
  const admins = users.filter((user) => user.role === "admin");
  admins.forEach((admin) => {
    const option = document.createElement("option");
    option.value = admin.id;
    option.textContent = `${admin.username} (${admin.email})`;
    adminSelect.appendChild(option);
  });
}

function updatePropertySelect(properties) {
  propertySelect.innerHTML = '<option value="">-- select property --</option>';
  properties.forEach((property) => {
    const option = document.createElement("option");
    option.value = property.id;
    option.textContent = `${property.name} (${property.address})`;
    propertySelect.appendChild(option);
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
    const owner = users.find((user) => user.id === property.owner_id);
    const tenants = users.filter((user) => user.property_id === property.id);

    card.innerHTML = `
      <h3>${property.name}</h3>
      <p>${property.address}</p>
      ${property.image_url ? `<img src="${property.image_url}" alt="${property.name}" style="max-width:100%; height:auto; margin-bottom:0.75rem;" />` : ""}
      <p>Owner: ${owner ? owner.username : property.owner_id}</p>
      <p>Tenants: ${tenants.length}</p>
    `;

    tenants.forEach((tenant) => {
      const tenantEl = document.createElement("div");
      tenantEl.textContent = `${tenant.username} (${tenant.email})`;
      tenantEl.style.paddingLeft = "1rem";
      card.appendChild(tenantEl);
    });

    propertiesList.appendChild(card);
  });
}

function handleAdminCreate(event) {
  event.preventDefault();
  const username = document.getElementById("admin-username").value.trim();
  const email = document.getElementById("admin-email").value.trim();
  const password = document.getElementById("admin-password").value;

  fetch("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: "admin", username, email, password }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.detail) {
        showMessage(data.detail);
        return;
      }
      showMessage(`Admin created: ${data.username}`);
      document.getElementById("admin-form").reset();
      fetchData();
    })
    .catch(() => showMessage("Failed to create admin."));
}

function handleAdminChange() {
  currentAdminId = adminSelect.value;
  dashboardEl.style.display = currentAdminId ? "block" : "none";
}

function handlePropertyCreate(event) {
  event.preventDefault();
  if (!currentAdminId) {
    showMessage("Select an admin first.");
    return;
  }

  const name = document.getElementById("property-name").value.trim();
  const address = document.getElementById("property-address").value.trim();
  const image_url = document.getElementById("property-image").value.trim() || null;

  fetch("/api/properties", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, address, image_url, owner_id: Number(currentAdminId) }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.detail) {
        showMessage(data.detail);
        return;
      }
      showMessage(`Property created: ${data.name}`);
      document.getElementById("property-form").reset();
      fetchData();
    })
    .catch(() => showMessage("Failed to create property."));
}

function handleTenantCreate(event) {
  event.preventDefault();
  const username = document.getElementById("tenant-username").value.trim();
  const email = document.getElementById("tenant-email").value.trim();
  const password = document.getElementById("tenant-password").value;
  const property_id = Number(document.getElementById("property-select").value);

  fetch("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: "tenant", username, email, password, property_id }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.detail) {
        showMessage(data.detail);
        return;
      }
      showMessage(`Tenant created: ${data.username}`);
      document.getElementById("tenant-form").reset();
      fetchData();
    })
    .catch(() => showMessage("Failed to create tenant."));
}

document.getElementById("admin-form").addEventListener("submit", handleAdminCreate);
document.getElementById("admin-select").addEventListener("change", handleAdminChange);
document.getElementById("refresh-button").addEventListener("click", fetchData);
document.getElementById("property-form").addEventListener("submit", handlePropertyCreate);
document.getElementById("tenant-form").addEventListener("submit", handleTenantCreate);

fetchData();
