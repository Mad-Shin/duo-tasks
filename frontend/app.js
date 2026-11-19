const RECURRENCE_LABELS = {
  daily: "Quotidien",
  weekly: "Hebdo",
  monthly: "Mensuel"
};

const TEMPORAL_BUCKETS = [
  { key: "today", label: "Aujourd'hui" },
  { key: "tomorrow", label: "Demain" },
  { key: "weekend", label: "Ce week-end" },
  { key: "week", label: "Cette semaine" },
  { key: "later", label: "Plus tard" }
];

const SVG_SNOOZE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></svg>';
const SVG_TRASH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';

const state = {
  composerMode: "task",
  identity: localStorage.getItem("duotasks_identity") || "me",
  theme: localStorage.getItem("duotasks_theme_v2") || "dark",
  profile: {
    me_name: "Valentin",
    wife_name: "Lisa"
  },
  tasks: [],
  allTasks: [],
  staples: [],
  suggestionIndex: 0,
  filterType: "all",
  filterValue: "all",
  searchQuery: "",
  showCompleted: false,
  editingTaskId: null,
  ws: null,
  reconnectDelay: 1000
};

const els = {
  taskCounter: document.getElementById("taskCounter"),
  syncDot: document.getElementById("syncDot"),
  syncText: document.getElementById("syncText"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  installHelpBtn: document.getElementById("installHelpBtn"),
  installModal: document.getElementById("installModal"),
  closeModalBtn: document.getElementById("closeModalBtn"),
  idBtnMe: document.getElementById("idBtnMe"),
  idBtnWife: document.getElementById("idBtnWife"),
  filterChipMe: document.getElementById("filterChipMe"),
  filterChipWife: document.getElementById("filterChipWife"),

  // Profile Modal
  editProfileBtn: document.getElementById("editProfileBtn"),
  profileModal: document.getElementById("profileModal"),
  closeProfileModalBtn: document.getElementById("closeProfileModalBtn"),
  profileForm: document.getElementById("profileForm"),
  profMeName: document.getElementById("profMeName"),
  profWifeName: document.getElementById("profWifeName"),

  // Mode Switch & Composers
  modeTaskBtn: document.getElementById("modeTaskBtn"),
  modeEventBtn: document.getElementById("modeEventBtn"),
  taskComposerCard: document.getElementById("taskComposerCard"),
  eventComposerCard: document.getElementById("eventComposerCard"),
  form: document.getElementById("quickAddForm"),
  input: document.getElementById("quickAddInput"),
  eventAddForm: document.getElementById("eventAddForm"),
  eventTitleInput: document.getElementById("eventTitleInput"),
  eventDateInput: document.getElementById("eventDateInput"),
  eventTimeInput: document.getElementById("eventTimeInput"),
  eventLocationInput: document.getElementById("eventLocationInput"),
  grocerySuggestionRow: document.getElementById("grocerySuggestionRow"),
  grocerySuggestionBtn: document.getElementById("grocerySuggestionBtn"),
  grocerySuggestionSkip: document.getElementById("grocerySuggestionSkip"),

  // Search & List
  toggleSearchBtn: document.getElementById("toggleSearchBtn"),
  searchDrawer: document.getElementById("searchDrawer"),
  searchInput: document.getElementById("taskSearchInput"),
  activeList: document.getElementById("activeTaskList"),
  completedList: document.getElementById("completedTaskList"),
  completedWrap: document.getElementById("completedWrap"),
  emptyState: document.getElementById("emptyState"),
  completedHeading: document.getElementById("completedHeading"),
  toggleCompletedBtn: document.getElementById("toggleCompletedBtn"),
  completedChevron: document.getElementById("completedChevron"),
  resetRoutinesBtn: document.getElementById("resetRoutinesBtn"),
  clearCompletedBtn: document.getElementById("clearCompletedBtn"),

  // Task / Event Drawer
  taskDrawer: document.getElementById("taskDrawer"),
  closeDrawerBtn: document.getElementById("closeDrawerBtn"),
  taskEditForm: document.getElementById("taskEditForm"),
  editTaskId: document.getElementById("editTaskId"),
  editTitle: document.getElementById("editTitle"),
  editNotes: document.getElementById("editNotes"),
  editItemType: document.getElementById("editItemType"),
  editAssignee: document.getElementById("editAssignee"),
  editCategory: document.getElementById("editCategory"),
  editPriority: document.getElementById("editPriority"),
  editDueLabel: document.getElementById("editDueLabel"),
  editRecurrence: document.getElementById("editRecurrence"),
  editEventDate: document.getElementById("editEventDate"),
  editEventTime: document.getElementById("editEventTime"),
  editLocation: document.getElementById("editLocation"),
  editQuantity: document.getElementById("editQuantity"),
  drawerSubtaskList: document.getElementById("drawerSubtaskList"),
  newSubtaskInput: document.getElementById("newSubtaskInput"),
  addSubtaskBtn: document.getElementById("addSubtaskBtn"),
  drawerDeleteBtn: document.getElementById("drawerDeleteBtn"),
  toastContainer: document.getElementById("toastContainer")
};

function partnerName(key) {
  if (key === "me") return state.profile.me_name || "Valentin";
  if (key === "wife") return state.profile.wife_name || "Lisa";
  return "Valentin & Lisa";
}

function toLocalIsoDate(d) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function nextWeekdayDate(targetWeekday) {
  // 0=Sun, 6=Sat
  const now = new Date();
  const diff = (targetWeekday - now.getDay() + 7) % 7;
  const res = new Date(now);
  res.setDate(now.getDate() + diff);
  return toLocalIsoDate(res);
}

function formatShortFrDate(isoDate) {
  if (!isoDate) return "";
  try {
    const [y, m, d] = isoDate.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });
  } catch {
    return isoDate;
  }
}

function inferDueLabelFromIso(isoDate) {
  if (!isoDate) return "today";
  const now = new Date();
  const todayIso = toLocalIsoDate(now);
  const tmr = new Date(now);
  tmr.setDate(now.getDate() + 1);
  if (isoDate === todayIso) return "today";
  if (isoDate === toLocalIsoDate(tmr)) return "tomorrow";
  const [y, m, d] = isoDate.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const diffDays = Math.round((dt - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000);
  if (diffDays >= 0 && diffDays <= 6 && (dt.getDay() === 6 || dt.getDay() === 0)) return "weekend";
  return "later";
}

function buildGoogleCalendarUrl(task) {
  const rawDate = (task.event_date || task.due_date || toLocalIsoDate(new Date())).replace(/-/g, "");
  const rawTime = (task.event_time || "").trim();
  let datesParam = "";
  if (rawTime && rawTime.includes(":")) {
    const [hh, mm] = rawTime.split(":");
    const startH = hh.padStart(2, "0");
    const startM = mm.slice(0, 2).padStart(2, "0");
    const endHour = String((Number(startH) + 2) % 24).padStart(2, "0");
    datesParam = `${rawDate}T${startH}${startM}00/${rawDate}T${endHour}${startM}00`;
  } else {
    const [y, m, d] = (task.event_date || task.due_date || toLocalIsoDate(new Date())).split("-").map(Number);
    const next = new Date(y, m - 1, d + 1);
    const nextCompact = toLocalIsoDate(next).replace(/-/g, "");
    datesParam = `${rawDate}/${nextCompact}`;
  }

  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: task.title,
    dates: datesParam
  });
  if (task.location) params.set("location", task.location);
  if (task.notes) params.set("details", task.notes);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("duotasks_theme_v2", theme);
}

function applyIdentity(identity) {
  state.identity = identity;
  localStorage.setItem("duotasks_identity", identity);
  document.querySelectorAll(".id-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.identity === identity);
  });
}

function renderProfileLabels() {
  const me = partnerName("me");
  const wife = partnerName("wife");
  els.idBtnMe.textContent = me;
  els.idBtnWife.textContent = wife;
  els.filterChipMe.textContent = me;
  els.filterChipWife.textContent = wife;
  if (els.editAssignee.options.length >= 3) {
    els.editAssignee.options[0].textContent = `${me} & ${wife}`;
    els.editAssignee.options[1].textContent = me;
    els.editAssignee.options[2].textContent = wife;
  }
}

function setComposerMode(mode) {
  state.composerMode = mode;
  els.modeTaskBtn.classList.toggle("active", mode === "task");
  els.modeEventBtn.classList.toggle("active", mode === "event");
  els.taskComposerCard.classList.toggle("hidden", mode !== "task");
  els.eventComposerCard.classList.toggle("hidden", mode !== "event");
  if (mode === "event") {
    if (!els.eventDateInput.value) {
      els.eventDateInput.value = nextWeekdayDate(6);
    }
    els.eventTitleInput.focus();
  } else {
    els.input.focus();
  }
}

function showToast(message, actionLabel = null, actionCallback = null) {
  const div = document.createElement("div");
  div.className = "toast";

  const span = document.createElement("span");
  span.textContent = message;
  div.appendChild(span);

  if (actionLabel && typeof actionCallback === "function") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "toast-action-btn";
    btn.textContent = actionLabel;
    btn.addEventListener("click", () => {
      div.remove();
      actionCallback();
    });
    div.appendChild(btn);
  }

  els.toastContainer.appendChild(div);
  setTimeout(() => {
    div.remove();
  }, actionLabel ? 5000 : 2500);
}

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

async function refreshAll() {
  const params = new URLSearchParams();
  if (state.filterType === "assignee") params.set("assignee", state.filterValue);
  else if (state.filterType === "category") params.set("category", state.filterValue);
  else if (state.filterType === "due") params.set("due_label", state.filterValue);
  else if (state.filterType === "recurring") params.set("recurring", "true");
  else if (state.filterType === "item_type") params.set("item_type", state.filterValue);
  if (state.searchQuery.trim()) params.set("search", state.searchQuery.trim());
  const qs = params.toString() ? `?${params.toString()}` : "";

  const [filteredTasks, allTasks, staples, profile] = await Promise.all([
    apiJson(`/api/tasks${qs}`),
    apiJson("/api/tasks"),
    apiJson("/api/groceries/staples"),
    apiJson("/api/couple/profile")
  ]);

  state.tasks = filteredTasks;
  state.allTasks = allTasks;
  state.staples = staples;
  state.profile = profile;

  renderProfileLabels();
  renderOneSuggestion();
  renderTasks();

  if (state.editingTaskId !== null) {
    const fresh = state.allTasks.find((t) => t.id === state.editingTaskId);
    if (fresh) {
      renderDrawerSubtasks(fresh);
    }
  }
}

function renderOneSuggestion() {
  const hasActiveGroceriesTask = state.allTasks.some((t) => !t.completed && t.category === "courses");
  if (hasActiveGroceriesTask || state.staples.length === 0) {
    els.grocerySuggestionRow.classList.add("hidden");
    return;
  }
  const suggestion = state.staples[state.suggestionIndex % state.staples.length];
  els.grocerySuggestionRow.classList.remove("hidden");
  const qtySuffix = suggestion.default_qty ? ` (${suggestion.default_qty})` : "";
  els.grocerySuggestionBtn.textContent = `+ Courses : ${suggestion.name}${qtySuffix}`;
}

function getBucketKey(task) {
  const due = (task.due_label || "today").toLowerCase();
  if (due === "today" || task.priority === 1) return "today";
  if (due === "tomorrow") return "tomorrow";
  if (due === "weekend") return "weekend";
  if (["lundi", "mardi", "mercredi", "jeudi", "vendredi"].includes(due)) return "week";
  return "later";
}

function renderTasks() {
  const active = state.tasks.filter((t) => !t.completed);
  const completed = state.tasks.filter((t) => t.completed);

  const globalActive = state.allTasks.filter((t) => !t.completed).length;
  els.taskCounter.textContent = `${globalActive} à faire`;
  els.completedHeading.textContent = `Terminées (${completed.length})`;

  els.activeList.innerHTML = "";
  els.completedList.innerHTML = "";

  if (active.length === 0) {
    els.emptyState.classList.remove("hidden");
  } else {
    els.emptyState.classList.add("hidden");
    const grouped = new Map();
    TEMPORAL_BUCKETS.forEach((b) => grouped.set(b.key, []));
    active.forEach((task) => grouped.get(getBucketKey(task)).push(task));

    const nonEmptyBuckets = TEMPORAL_BUCKETS.filter((b) => grouped.get(b.key).length > 0);
    const showHeaders = nonEmptyBuckets.length > 1;
    nonEmptyBuckets.forEach((bucket) => {
      if (showHeaders) {
        const hdr = document.createElement("li");
        hdr.className = "task-group-header";
        hdr.textContent = bucket.label;
        els.activeList.appendChild(hdr);
      }
      grouped.get(bucket.key).forEach((task) => els.activeList.appendChild(createTaskElement(task)));
    });
  }

  completed.forEach((task) => els.completedList.appendChild(createTaskElement(task)));
  els.completedWrap.classList.toggle("hidden", !state.showCompleted || completed.length === 0);
  els.completedChevron.textContent = state.showCompleted ? "▾" : "▸";
  els.clearCompletedBtn.classList.toggle("hidden", completed.length === 0);

  const hasDoneRecurring = state.allTasks.some((t) => t.recurring && t.completed);
  els.resetRoutinesBtn.classList.toggle("hidden", !hasDoneRecurring);
}

function createTaskElement(task) {
  const li = document.createElement("li");
  li.className = `task-item${task.completed ? " completed" : ""}`;

  const checkBtn = document.createElement("button");
  checkBtn.type = "button";
  checkBtn.className = `check-btn prio-${task.priority}`;
  checkBtn.setAttribute("aria-label", task.completed ? "Marquer non terminée" : "Marquer terminée");
  checkBtn.textContent = task.completed ? "✓" : "";
  checkBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleTask(task);
  });

  const content = document.createElement("div");
  content.className = "task-content";
  content.addEventListener("click", () => openTaskDrawer(task));

  const title = document.createElement("div");
  title.className = "task-title";
  title.textContent = task.item_type === "event" ? `📅 ${task.title}` : task.title;
  content.appendChild(title);

  if (task.notes) {
    const snippet = document.createElement("div");
    snippet.className = "task-notes-snippet";
    snippet.textContent = task.notes;
    content.appendChild(snippet);
  }

  const metaParts = [];
  if (task.item_type === "event" && task.event_date) {
    const dateTxt = formatShortFrDate(task.event_date);
    metaParts.push({ text: task.event_time ? `${dateTxt} · ${task.event_time}` : dateTxt, accent: true });
    if (task.location) metaParts.push({ text: task.location, accent: false });
  }
  if (task.assignee !== "both") {
    metaParts.push({ text: partnerName(task.assignee), accent: false });
  }
  if (task.category && task.category !== "inbox" && !(task.item_type === "event" && task.category === "date")) {
    metaParts.push({ text: `#${task.category}`, accent: task.category === "courses" });
  }
  if (task.quantity) {
    metaParts.push({ text: task.quantity, accent: true });
  }
  if (task.item_type !== "event" && task.due_label && task.due_label !== "today") {
    metaParts.push({ text: task.due_label, accent: task.due_label === "tomorrow" });
  }
  if (task.recurring) {
    metaParts.push({ text: `↻ ${RECURRENCE_LABELS[task.recurrence_rule] || "Quotidien"}`, accent: false });
  }
  if (task.subtasks && task.subtasks.length > 0) {
    const doneSub = task.subtasks.filter((s) => s.done).length;
    metaParts.push({ text: `${doneSub}/${task.subtasks.length}`, accent: false });
  }

  if (metaParts.length > 0) {
    const metaLine = document.createElement("div");
    metaLine.className = "task-meta-line";
    metaParts.forEach((part, idx) => {
      if (idx > 0) {
        const dot = document.createElement("span");
        dot.className = "meta-dot";
        dot.textContent = "·";
        metaLine.appendChild(dot);
      }
      const sp = document.createElement("span");
      if (part.accent) sp.className = "meta-pill-accent";
      sp.textContent = part.text;
      metaLine.appendChild(sp);
    });
    content.appendChild(metaLine);
  }

  // Seamless 1-Tap Apple & Google Calendar Sync buttons for events
  if (!task.completed && task.item_type === "event") {
    const syncBar = document.createElement("div");
    syncBar.className = "cal-sync-bar";
    syncBar.addEventListener("click", (e) => e.stopPropagation());

    const gLink = document.createElement("a");
    gLink.className = "cal-sync-btn";
    gLink.href = buildGoogleCalendarUrl(task);
    gLink.target = "_blank";
    gLink.rel = "noopener noreferrer";
    gLink.textContent = "+ Google Agenda";

    const aLink = document.createElement("a");
    aLink.className = "cal-sync-btn";
    aLink.href = `/api/tasks/${task.id}/ics`;
    aLink.textContent = "+ Apple Calendrier";

    syncBar.appendChild(gLink);
    syncBar.appendChild(aLink);
    content.appendChild(syncBar);
  }

  // Inline checklist for the living Courses task (or any active task with subtasks)
  const hasInlineChecklist = !task.completed && (task.category === "courses" || (task.subtasks && task.subtasks.length > 0));
  if (hasInlineChecklist) {
    const checklist = document.createElement("div");
    checklist.className = "inline-checklist";
    checklist.addEventListener("click", (e) => e.stopPropagation());

    (task.subtasks || []).forEach((sub) => {
      const row = document.createElement("div");
      row.className = `inline-sub-row${sub.done ? " done" : ""}`;

      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = Boolean(sub.done);
      cb.addEventListener("change", async () => {
        await apiJson(`/api/tasks/${task.id}/subtasks/${sub.id}`, {
          method: "PATCH",
          body: JSON.stringify({ done: cb.checked })
        });
        await refreshAll();
      });

      const lbl = document.createElement("span");
      lbl.textContent = sub.text;

      const del = document.createElement("button");
      del.type = "button";
      del.className = "inline-sub-del";
      del.title = "Retirer";
      del.textContent = "✕";
      del.addEventListener("click", async () => {
        await apiJson(`/api/tasks/${task.id}/subtasks/${sub.id}`, { method: "DELETE" });
        await refreshAll();
      });

      row.appendChild(cb);
      row.appendChild(lbl);
      row.appendChild(del);
      checklist.appendChild(row);
    });

    if (task.category === "courses") {
      const addForm = document.createElement("form");
      addForm.className = "inline-sub-add";
      const inp = document.createElement("input");
      inp.type = "text";
      inp.placeholder = "+ Ajouter un article…";
      inp.maxLength = 200;
      const addBtn = document.createElement("button");
      addBtn.type = "submit";
      addBtn.textContent = "+";
      addForm.appendChild(inp);
      addForm.appendChild(addBtn);
      addForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = inp.value.trim();
        if (!text) return;
        inp.value = "";
        await apiJson(`/api/tasks/${task.id}/subtasks`, {
          method: "POST",
          body: JSON.stringify({ text })
        });
        await refreshAll();
      });
      checklist.appendChild(addForm);
    }

    content.appendChild(checklist);
  }

  const actionsCol = document.createElement("div");
  actionsCol.className = "task-actions-col";

  if (!task.completed && task.item_type !== "event" && task.due_label !== "tomorrow") {
    const snoozeBtn = document.createElement("button");
    snoozeBtn.type = "button";
    snoozeBtn.className = "row-action-btn";
    snoozeBtn.title = "Reporter à demain";
    snoozeBtn.setAttribute("aria-label", "Reporter à demain");
    snoozeBtn.innerHTML = SVG_SNOOZE;
    snoozeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      snoozeToTomorrow(task);
    });
    actionsCol.appendChild(snoozeBtn);
  }

  const delBtn = document.createElement("button");
  delBtn.type = "button";
  delBtn.className = "row-action-btn delete";
  delBtn.setAttribute("aria-label", "Supprimer");
  delBtn.innerHTML = SVG_TRASH;
  delBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteTask(task);
  });
  actionsCol.appendChild(delBtn);

  li.appendChild(checkBtn);
  li.appendChild(content);
  li.appendChild(actionsCol);
  return li;
}

async function toggleTask(task) {
  const targetCompleted = !task.completed;
  task.completed = targetCompleted;
  renderTasks();
  try {
    await apiJson(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: targetCompleted, completed_by: state.identity })
    });
    if (targetCompleted) {
      showToast("Terminée", "Annuler", async () => {
        await apiJson(`/api/tasks/${task.id}`, {
          method: "PATCH",
          body: JSON.stringify({ completed: false })
        });
        await refreshAll();
      });
    }
    await refreshAll();
  } catch (err) {
    console.error(err);
    await refreshAll();
  }
}

async function snoozeToTomorrow(task) {
  try {
    await apiJson(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ due_label: "tomorrow" })
    });
    showToast("Reportée à demain");
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
}

async function deleteTask(taskOrId) {
  const snapshot = typeof taskOrId === "object"
    ? taskOrId
    : state.allTasks.find((t) => t.id === taskOrId) || { id: taskOrId };
  const taskId = snapshot.id;

  state.tasks = state.tasks.filter((t) => t.id !== taskId);
  renderTasks();
  try {
    await apiJson(`/api/tasks/${taskId}`, { method: "DELETE" });
    if (snapshot.raw_input || snapshot.title) {
      showToast("Supprimée", "Annuler", async () => {
        await apiJson("/api/tasks", {
          method: "POST",
          body: JSON.stringify({
            raw_input: snapshot.raw_input || snapshot.title,
            notes: snapshot.notes || "",
            assignee: snapshot.assignee,
            category: snapshot.category,
            priority: snapshot.priority,
            due_label: snapshot.due_label,
            recurring: snapshot.recurring,
            recurrence_rule: snapshot.recurrence_rule,
            quantity: snapshot.quantity,
            aisle: snapshot.aisle,
            item_type: snapshot.item_type || "task",
            event_date: snapshot.event_date || "",
            event_time: snapshot.event_time || "",
            location: snapshot.location || "",
            subtasks: snapshot.subtasks || []
          })
        });
        await refreshAll();
      });
    }
    await refreshAll();
  } catch (err) {
    console.error(err);
    await refreshAll();
  }
}

function ensureSelectOption(selectEl, value) {
  if (!value) return;
  const exists = Array.from(selectEl.options).some((opt) => opt.value === value);
  if (!exists) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    selectEl.appendChild(opt);
  }
}

function openTaskDrawer(task) {
  state.editingTaskId = task.id;
  els.editTaskId.value = String(task.id);
  els.editTitle.value = task.title;
  els.editNotes.value = task.notes || "";
  els.editItemType.value = task.item_type || "task";
  els.editAssignee.value = task.assignee || "both";
  const cat = task.category || "inbox";
  ensureSelectOption(els.editCategory, cat);
  els.editCategory.value = cat;
  els.editPriority.value = String(task.priority || 3);
  const due = task.due_label || "today";
  ensureSelectOption(els.editDueLabel, due);
  els.editDueLabel.value = due;
  els.editRecurrence.value = task.recurrence_rule || (task.recurring ? "daily" : "none");
  els.editEventDate.value = task.event_date || "";
  els.editEventTime.value = task.event_time || "";
  els.editLocation.value = task.location || "";
  els.editQuantity.value = task.quantity || "";
  renderDrawerSubtasks(task);
  els.taskDrawer.classList.remove("hidden");
}

function closeTaskDrawer() {
  state.editingTaskId = null;
  els.taskDrawer.classList.add("hidden");
}

function renderDrawerSubtasks(task) {
  els.drawerSubtaskList.innerHTML = "";
  (task.subtasks || []).forEach((sub) => {
    const li = document.createElement("li");
    li.className = `subtask-item${sub.done ? " done" : ""}`;

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = Boolean(sub.done);
    cb.addEventListener("change", async () => {
      const updated = await apiJson(`/api/tasks/${task.id}/subtasks/${sub.id}`, {
        method: "PATCH",
        body: JSON.stringify({ done: cb.checked })
      });
      renderDrawerSubtasks(updated);
      await refreshAll();
    });

    const span = document.createElement("span");
    span.className = "subtask-text";
    span.textContent = sub.text;

    const del = document.createElement("button");
    del.type = "button";
    del.className = "btn-close";
    del.textContent = "✕";
    del.addEventListener("click", async () => {
      const updated = await apiJson(`/api/tasks/${task.id}/subtasks/${sub.id}`, { method: "DELETE" });
      renderDrawerSubtasks(updated);
      await refreshAll();
    });

    li.appendChild(cb);
    li.appendChild(span);
    li.appendChild(del);
    els.drawerSubtaskList.appendChild(li);
  });
}

async function refreshHealth() {
  try {
    const health = await apiJson("/api/health");
    if (els.syncDot.classList.contains("online")) {
      const count = Math.max(1, health.connected_devices || 1);
      els.syncText.textContent = `Live (${count})`;
    }
  } catch {
    // Silent fallback
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
    refreshHealth();
  });

  socket.addEventListener("message", async (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      if (payload.event === "sync") {
        await refreshAll();
        refreshHealth();
      } else if (payload.event === "devices") {
        refreshHealth();
      }
    } catch {
      await refreshAll();
    }
  });

  socket.addEventListener("close", () => {
    els.syncDot.classList.remove("online");
    els.syncText.textContent = "Reconn...";
    setTimeout(connectWebSocket, state.reconnectDelay);
    state.reconnectDelay = Math.min(state.reconnectDelay * 1.5, 10000);
  });
}

// --- Events ---

document.querySelectorAll(".id-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    applyIdentity(btn.dataset.identity || "me");
  });
});

els.themeToggleBtn.addEventListener("click", () => {
  applyTheme(state.theme === "dark" ? "light" : "dark");
});

els.modeTaskBtn.addEventListener("click", () => setComposerMode("task"));
els.modeEventBtn.addEventListener("click", () => setComposerMode("event"));

// Event template pills & quick date pills
document.querySelectorAll(".preset-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    const preset = pill.dataset.preset || "";
    els.eventTitleInput.value = preset;
    if (preset.includes("Mariage")) els.eventTimeInput.value = "15:00";
    else if (preset.includes("Dîner") || preset.includes("Soirée")) els.eventTimeInput.value = "20:00";
    else if (preset.includes("Week-end")) els.eventTimeInput.value = "10:00";
    els.eventTitleInput.focus();
  });
});

document.querySelectorAll(".date-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".date-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    if (chip.dataset.dateOffset !== undefined) {
      const d = new Date();
      d.setDate(d.getDate() + Number(chip.dataset.dateOffset));
      els.eventDateInput.value = toLocalIsoDate(d);
    } else if (chip.dataset.datePreset === "sat") {
      els.eventDateInput.value = nextWeekdayDate(6);
    } else if (chip.dataset.datePreset === "sun") {
      els.eventDateInput.value = nextWeekdayDate(0);
    }
  });
});

els.eventDateInput.value = nextWeekdayDate(6);

els.eventAddForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const title = els.eventTitleInput.value.trim();
  const eventDate = els.eventDateInput.value;
  if (!title || !eventDate) return;

  try {
    await apiJson("/api/tasks", {
      method: "POST",
      body: JSON.stringify({
        raw_input: title,
        assignee: "both",
        category: "date",
        priority: 2,
        due_label: inferDueLabelFromIso(eventDate),
        due_date: eventDate,
        item_type: "event",
        event_date: eventDate,
        event_time: els.eventTimeInput.value || "",
        location: els.eventLocationInput.value.trim()
      })
    });
    els.eventTitleInput.value = "";
    els.eventLocationInput.value = "";
    showToast("Événement ajouté");
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

els.editProfileBtn.addEventListener("click", () => {
  els.profMeName.value = state.profile.me_name || "Valentin";
  els.profWifeName.value = state.profile.wife_name || "Lisa";
  els.profileModal.classList.remove("hidden");
});

els.closeProfileModalBtn.addEventListener("click", () => els.profileModal.classList.add("hidden"));
els.profileModal.addEventListener("click", (evt) => {
  if (evt.target === els.profileModal) els.profileModal.classList.add("hidden");
});

els.profileForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  try {
    await apiJson("/api/couple/profile", {
      method: "PATCH",
      body: JSON.stringify({
        me_name: els.profMeName.value.trim(),
        wife_name: els.profWifeName.value.trim()
      })
    });
    els.profileModal.classList.add("hidden");
    showToast("Prénoms enregistrés");
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

// 1-Tap Pre-Written Recurring Task Buttons
document.querySelectorAll(".preset-task-pill").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const title = btn.dataset.title || "";
    const rule = btn.dataset.rule || "weekly";
    if (!title) return;
    try {
      const created = await apiJson("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          raw_input: title,
          assignee: "both",
          category: "maison",
          priority: 2,
          due_label: "today",
          recurring: true,
          recurrence_rule: rule
        })
      });
      showToast(`Ajoutée : ${title}`, "Annuler", async () => {
        await apiJson(`/api/tasks/${created.id}`, { method: "DELETE" });
        await refreshAll();
      });
      await refreshAll();
    } catch (err) {
      console.error(err);
    }
  });
});

els.form.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const raw = els.input.value.trim();
  if (!raw) return;

  els.input.value = "";
  try {
    await apiJson("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ raw_input: raw })
    });
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

els.grocerySuggestionBtn.addEventListener("click", async () => {
  if (state.staples.length === 0) return;
  const suggestion = state.staples[state.suggestionIndex % state.staples.length];
  const itemText = suggestion.default_qty
    ? `${suggestion.name} (${suggestion.default_qty})`
    : suggestion.name;
  try {
    await apiJson("/api/tasks", {
      method: "POST",
      body: JSON.stringify({
        raw_input: "Courses #courses @both",
        category: "courses",
        subtasks: [{ id: 1, text: itemText, done: false }]
      })
    });
    showToast("Liste Courses créée");
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

els.grocerySuggestionSkip.addEventListener("click", () => {
  state.suggestionIndex += 1;
  renderOneSuggestion();
});

els.toggleSearchBtn.addEventListener("click", () => {
  els.searchDrawer.classList.toggle("hidden");
  if (!els.searchDrawer.classList.contains("hidden")) {
    els.searchInput.focus();
  } else if (els.searchInput.value) {
    els.searchInput.value = "";
    state.searchQuery = "";
    refreshAll();
  }
});

let searchTimer = null;
els.searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.searchQuery = els.searchInput.value;
    refreshAll();
  }, 160);
});

document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    state.filterType = chip.dataset.filterType || "all";
    state.filterValue = chip.dataset.filterValue || "all";
    refreshAll();
  });
});

els.toggleCompletedBtn.addEventListener("click", () => {
  state.showCompleted = !state.showCompleted;
  renderTasks();
});

els.resetRoutinesBtn.addEventListener("click", async () => {
  const res = await apiJson("/api/routines/reset-daily", { method: "POST" });
  showToast(`${res.reset_count} récurrente(s) relancée(s)`);
  await refreshAll();
});

els.clearCompletedBtn.addEventListener("click", async () => {
  const res = await apiJson("/api/tasks/clear-completed", { method: "POST" });
  showToast(`${res.cleared_count} tâche(s) effacée(s)`);
  await refreshAll();
});

els.closeDrawerBtn.addEventListener("click", closeTaskDrawer);
els.taskDrawer.addEventListener("click", (evt) => {
  if (evt.target === els.taskDrawer) closeTaskDrawer();
});

els.taskEditForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const id = Number(els.editTaskId.value);
  await apiJson(`/api/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      title: els.editTitle.value.trim(),
      notes: els.editNotes.value.trim(),
      item_type: els.editItemType.value,
      assignee: els.editAssignee.value,
      category: els.editCategory.value,
      priority: Number(els.editPriority.value),
      due_label: els.editDueLabel.value,
      recurrence_rule: els.editRecurrence.value,
      event_date: els.editEventDate.value,
      event_time: els.editEventTime.value,
      location: els.editLocation.value.trim(),
      quantity: els.editQuantity.value.trim()
    })
  });
  closeTaskDrawer();
  showToast("Enregistré");
  await refreshAll();
});

els.addSubtaskBtn.addEventListener("click", async () => {
  const id = Number(els.editTaskId.value);
  const text = els.newSubtaskInput.value.trim();
  if (!text) return;
  els.newSubtaskInput.value = "";
  const updated = await apiJson(`/api/tasks/${id}/subtasks`, {
    method: "POST",
    body: JSON.stringify({ text })
  });
  renderDrawerSubtasks(updated);
  await refreshAll();
});

els.newSubtaskInput.addEventListener("keydown", (evt) => {
  if (evt.key === "Enter") {
    evt.preventDefault();
    els.addSubtaskBtn.click();
  }
});

els.drawerDeleteBtn.addEventListener("click", async () => {
  const id = Number(els.editTaskId.value);
  closeTaskDrawer();
  await deleteTask(id);
});

els.installHelpBtn.addEventListener("click", () => els.installModal.classList.remove("hidden"));
els.closeModalBtn.addEventListener("click", () => els.installModal.classList.add("hidden"));
els.installModal.addEventListener("click", (evt) => {
  if (evt.target === els.installModal) els.installModal.classList.add("hidden");
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

applyTheme(state.theme);
applyIdentity(state.identity);
refreshAll();
connectWebSocket();
refreshHealth();
