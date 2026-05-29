const messageEl = document.getElementById("message");
const loginSelect = document.getElementById("login-select");
const loginButton = document.getElementById("login-button");
const registerForm = document.getElementById("register-form");
const dashboardSection = document.getElementById("dashboard-section");
const currentAdminName = document.getElementById("current-admin-name");
const logoutButton = document.getElementById("logout-button");
const refreshButton = document.getElementById("refresh-button");
const propertySelect = document.getElementById("property-select");
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
    updatePropertySelect(properties);
    renderProperties(properties, users);
    showMessage("");
  } catch (e) {
    showMessage("Unable to load data. Make sure docker compose is running.");
  }
}

function updateLoginSelect(users) {
  loginSelect.innerHTML = '<option value="">-- choose admin --</option>';
  const admins = users.filter((user) => user.role === "admin");
  admins.forEach((admin) => {
    const option = document.createElement("option");
    option.value = admin.id;
    option.textContent = `${admin.username} (${admin.email})`;
    loginSelect.appendChild(option);
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
    if (data.detail) {
      showMessage(data.detail);
      return;
    }
    showMessage(`Admin created: ${data.username}`);
    document.getElementById("register-form").reset();
    // set as current admin and show dashboard
    currentAdminId = data.id;
    enterDashboard(data);
    fetchData();
  } catch (e) {
    showMessage("Failed to create admin.");
  }
});

loginButton.addEventListener("click", async () => {
  const id = loginSelect.value;
  if (!id) {
    showMessage("Select an admin to login.");
    return;
  }
  // fetch user info and enter dashboard
  try {
    const res = await fetch(`/api/users`);
    const users = await res.json();
    const user = users.find((u) => String(u.id) === String(id));
    if (!user) {
      showMessage("Admin not found");
      return;
    }
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
  const property_id = Number(document.getElementById("property-select").value);
  try {
    const res = await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "tenant", username, email, password, property_id }),
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

// initialize
fetchData();
