const state = {
  tasks: [],
  filterType: "all",
  filterValue: "all",
  showCompleted: true,
  ws: null,
  reconnectDelay: 1000
};

const els = {
  form: document.getElementById("quickAddForm"),
  input: document.getElementById("quickAddInput"),
  activeList: document.getElementById("activeTaskList"),
  completedList: document.getElementById("completedTaskList"),
  emptyState: document.getElementById("emptyState"),
  taskCounter: document.getElementById("taskCounter"),
  completedHeading: document.getElementById("completedHeading"),
  toggleCompletedBtn: document.getElementById("toggleCompletedBtn"),
  completedChevron: document.getElementById("completedChevron"),
  syncDot: document.getElementById("syncDot"),
  syncText: document.getElementById("syncText"),
  prevAssignee: document.getElementById("prevAssignee"),
  prevCategory: document.getElementById("prevCategory"),
  prevDue: document.getElementById("prevDue"),
  prevPrio: document.getElementById("prevPrio"),
  installHelpBtn: document.getElementById("installHelpBtn"),
  installModal: document.getElementById("installModal"),
  closeModalBtn: document.getElementById("closeModalBtn")
};

async function apiJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return res.json();
}

async function loadTasks() {
  const params = new URLSearchParams();
  if (state.filterType === "assignee") {
    params.set("assignee", state.filterValue);
  } else if (state.filterType === "category") {
    params.set("category", state.filterValue);
  }
  const qs = params.toString() ? `?${params.toString()}` : "";
  state.tasks = await apiJson(`/api/tasks${qs}`);
  renderTasks();
}

function renderTasks() {
  const active = state.tasks.filter((t) => !t.completed);
  const completed = state.tasks.filter((t) => t.completed);

  els.taskCounter.textContent = `${active.length} active${active.length > 1 ? "s" : ""} · ${completed.length} terminée${completed.length > 1 ? "s" : ""}`;
  els.completedHeading.textContent = `Terminées (${completed.length})`;

  els.activeList.innerHTML = "";
  els.completedList.innerHTML = "";

  if (active.length === 0) {
    els.emptyState.classList.remove("hidden");
  } else {
    els.emptyState.classList.add("hidden");
    active.forEach((task) => els.activeList.appendChild(createTaskElement(task)));
  }

  completed.forEach((task) => els.completedList.appendChild(createTaskElement(task)));
  els.completedList.classList.toggle("hidden", !state.showCompleted);
  els.completedChevron.textContent = state.showCompleted ? "▾" : "▸";
}

function createTaskElement(task) {
  const li = document.createElement("li");
  li.className = `task-item${task.completed ? " completed" : ""}`;

  const checkBtn = document.createElement("button");
  checkBtn.type = "button";
  checkBtn.className = `check-btn prio-${task.priority}`;
  checkBtn.setAttribute("aria-label", task.completed ? "Marquer non terminée" : "Marquer terminée");
  checkBtn.textContent = task.completed ? "✓" : "";
  checkBtn.addEventListener("click", () => toggleTask(task));

  const content = document.createElement("div");
  content.className = "task-content";

  const title = document.createElement("div");
  title.className = "task-title";
  title.textContent = task.title;

  const meta = document.createElement("div");
  meta.className = "task-meta";
  meta.appendChild(makeChip(`@${task.assignee}`, "chip-assignee"));
  meta.appendChild(makeChip(`#${task.category}`, "chip-category"));
  meta.appendChild(makeChip(task.due_label, "chip-due"));
  if (task.priority < 3) {
    meta.appendChild(makeChip(`P${task.priority}`, "chip-prio"));
  }

  content.appendChild(title);
  content.appendChild(meta);

  const delBtn = document.createElement("button");
  delBtn.type = "button";
  delBtn.className = "delete-btn";
  delBtn.setAttribute("aria-label", "Supprimer");
  delBtn.textContent = "🗑";
  delBtn.addEventListener("click", () => deleteTask(task.id));

  li.appendChild(checkBtn);
  li.appendChild(content);
  li.appendChild(delBtn);
  return li;
}

function makeChip(text, cls) {
  const span = document.createElement("span");
  span.className = `chip ${cls}`;
  span.textContent = text;
  return span;
}

async function toggleTask(task) {
  const targetCompleted = !task.completed;
  task.completed = targetCompleted;
  renderTasks();
  try {
    await apiJson(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: targetCompleted })
    });
  } catch (err) {
    console.error(err);
    await loadTasks();
  }
}

async function deleteTask(taskId) {
  state.tasks = state.tasks.filter((t) => t.id !== taskId);
  renderTasks();
  try {
    await apiJson(`/api/tasks/${taskId}`, { method: "DELETE" });
  } catch (err) {
    console.error(err);
    await loadTasks();
  }
}

let previewTimer = null;
async function updateParsePreview() {
  const raw = els.input.value;
  try {
    const parsed = await apiJson("/api/parse", {
      method: "POST",
      body: JSON.stringify({ raw_input: raw })
    });
    els.prevAssignee.textContent = `@${parsed.assignee}`;
    els.prevCategory.textContent = `#${parsed.category}`;
    els.prevDue.textContent = parsed.due_label;
    els.prevPrio.textContent = `P${parsed.priority}`;
  } catch {
    // Silent fallback when offline
  }
}

function connectWebSocket() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${proto}//${window.location.host}/ws`;
  const socket = new WebSocket(wsUrl);
  state.ws = socket;

  socket.addEventListener("open", () => {
    state.reconnectDelay = 1000;
    els.syncDot.classList.add("online");
    els.syncText.textContent = "Live";
  });

  socket.addEventListener("message", async (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      if (payload.event === "sync") {
        await loadTasks();
      }
    } catch {
      await loadTasks();
    }
  });

  socket.addEventListener("close", () => {
    els.syncDot.classList.remove("online");
    els.syncText.textContent = "Reconn...";
    setTimeout(connectWebSocket, state.reconnectDelay);
    state.reconnectDelay = Math.min(state.reconnectDelay * 1.5, 10000);
  });
}

els.form.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const raw = els.input.value.trim();
  if (!raw) return;
  els.input.value = "";
  updateParsePreview();

  try {
    await apiJson("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ raw_input: raw })
    });
    await loadTasks();
  } catch (err) {
    console.error(err);
  }
});

els.input.addEventListener("input", () => {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updateParsePreview, 120);
});

document.querySelectorAll(".shortcut-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const token = btn.dataset.token || "";
    const cur = els.input.value.trim();
    els.input.value = cur ? `${cur} ${token} ` : `${token} `;
    els.input.focus();
    updateParsePreview();
  });
});

document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    state.filterType = chip.dataset.filterType || "all";
    state.filterValue = chip.dataset.filterValue || "all";
    loadTasks();
  });
});

els.toggleCompletedBtn.addEventListener("click", () => {
  state.showCompleted = !state.showCompleted;
  renderTasks();
});

els.installHelpBtn.addEventListener("click", () => els.installModal.classList.remove("hidden"));
els.closeModalBtn.addEventListener("click", () => els.installModal.classList.add("hidden"));
els.installModal.addEventListener("click", (evt) => {
  if (evt.target === els.installModal) {
    els.installModal.classList.add("hidden");
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

loadTasks();
connectWebSocket();
