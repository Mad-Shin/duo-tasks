const AISLE_ORDER = [
  "Fruits & Légumes",
  "Frais & Laitier",
  "Boulangerie",
  "Viande & Poisson",
  "Épicerie",
  "Boissons",
  "Maison & Hygiène",
  "Autre"
];

const RECURRENCE_LABELS = {
  daily: "🔁 quotidien",
  weekly: "🔁 hebdo",
  monthly: "🔁 mensuel"
};

const TEMPORAL_BUCKETS = [
  { key: "today", label: "🔥 Prioritaires & Aujourd'hui" },
  { key: "tomorrow", label: "🌅 Demain" },
  { key: "weekend", label: "🛋️ Ce Week-end" },
  { key: "week", label: "📅 Cette semaine" },
  { key: "later", label: "🗓️ Plus tard" }
];

const state = {
  activeTab: "tasks",
  identity: localStorage.getItem("duotasks_identity") || "me",
  theme: localStorage.getItem("duotasks_theme") || "light",
  groupedMode: localStorage.getItem("duotasks_grouped") !== "false",
  profile: {
    me_name: "Valentin",
    me_emoji: "🦊",
    wife_name: "Chérie",
    wife_emoji: "🌸",
    love_note: "On fait quoi de beau ce soir ? ✨",
    love_note_author: "both",
    kudos_count: 0
  },
  tasks: [],
  allTasks: [],
  staples: [],
  packs: [],
  stats: null,
  filterType: "all",
  filterValue: "all",
  searchQuery: "",
  stapleAisle: "all",
  showCompleted: true,
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
  groceriesBadge: document.getElementById("groceriesBadge"),
  idBtnMe: document.getElementById("idBtnMe"),
  idBtnWife: document.getElementById("idBtnWife"),
  filterChipMe: document.getElementById("filterChipMe"),
  filterChipWife: document.getElementById("filterChipWife"),

  // Couple Banner & Profile Modal
  loveNoteText: document.getElementById("loveNoteText"),
  loveNoteAuthorLabel: document.getElementById("loveNoteAuthorLabel"),
  toggleLoveNoteBtn: document.getElementById("toggleLoveNoteBtn"),
  loveNoteForm: document.getElementById("loveNoteForm"),
  loveNoteInput: document.getElementById("loveNoteInput"),
  sendKudosBtn: document.getElementById("sendKudosBtn"),
  kudosCountBadge: document.getElementById("kudosCountBadge"),
  karmaScore: document.getElementById("karmaScore"),
  editProfileBtn: document.getElementById("editProfileBtn"),
  profileModal: document.getElementById("profileModal"),
  closeProfileModalBtn: document.getElementById("closeProfileModalBtn"),
  profileForm: document.getElementById("profileForm"),
  profMeName: document.getElementById("profMeName"),
  profMeEmoji: document.getElementById("profMeEmoji"),
  profWifeName: document.getElementById("profWifeName"),
  profWifeEmoji: document.getElementById("profWifeEmoji"),

  // Quick Add & Tasks View
  form: document.getElementById("quickAddForm"),
  input: document.getElementById("quickAddInput"),
  searchInput: document.getElementById("taskSearchInput"),
  groupModeToggleBtn: document.getElementById("groupModeToggleBtn"),
  activeList: document.getElementById("activeTaskList"),
  completedList: document.getElementById("completedTaskList"),
  emptyState: document.getElementById("emptyState"),
  completedHeading: document.getElementById("completedHeading"),
  toggleCompletedBtn: document.getElementById("toggleCompletedBtn"),
  completedChevron: document.getElementById("completedChevron"),
  clearCompletedBtn: document.getElementById("clearCompletedBtn"),
  prevAssignee: document.getElementById("prevAssignee"),
  prevCategory: document.getElementById("prevCategory"),
  prevDue: document.getElementById("prevDue"),
  prevPrio: document.getElementById("prevPrio"),
  prevRecurring: document.getElementById("prevRecurring"),
  prevQty: document.getElementById("prevQty"),
  prevAisle: document.getElementById("prevAisle"),

  // Groceries View
  groceryQuickForm: document.getElementById("groceryQuickForm"),
  groceryQuickInput: document.getElementById("groceryQuickInput"),
  toggleNewStapleBtn: document.getElementById("toggleNewStapleBtn"),
  newStapleForm: document.getElementById("newStapleForm"),
  stapleNameInput: document.getElementById("stapleNameInput"),
  stapleQtyInput: document.getElementById("stapleQtyInput"),
  stapleAisleInput: document.getElementById("stapleAisleInput"),
  stapleEmojiInput: document.getElementById("stapleEmojiInput"),
  staplesGrid: document.getElementById("staplesGrid"),
  groceriesByAisle: document.getElementById("groceriesByAisle"),
  groceriesEmptyState: document.getElementById("groceriesEmptyState"),
  clearGroceriesBtn: document.getElementById("clearGroceriesBtn"),

  // Routines View
  routinesSummary: document.getElementById("routinesSummary"),
  resetRoutinesBtn: document.getElementById("resetRoutinesBtn"),
  routinesList: document.getElementById("routinesList"),
  routinesEmptyState: document.getElementById("routinesEmptyState"),
  packsGrid: document.getElementById("packsGrid"),

  // Stats View
  kpiGrid: document.getElementById("kpiGrid"),
  balanceBars: document.getElementById("balanceBars"),
  categoryBars: document.getElementById("categoryBars"),
  activityFeed: document.getElementById("activityFeed"),

  // Task Drawer
  taskDrawer: document.getElementById("taskDrawer"),
  closeDrawerBtn: document.getElementById("closeDrawerBtn"),
  taskEditForm: document.getElementById("taskEditForm"),
  editTaskId: document.getElementById("editTaskId"),
  editTitle: document.getElementById("editTitle"),
  editNotes: document.getElementById("editNotes"),
  editAssignee: document.getElementById("editAssignee"),
  editCategory: document.getElementById("editCategory"),
  editPriority: document.getElementById("editPriority"),
  editDueLabel: document.getElementById("editDueLabel"),
  editRecurrence: document.getElementById("editRecurrence"),
  editQuantity: document.getElementById("editQuantity"),
  editAisle: document.getElementById("editAisle"),
  drawerSubtaskList: document.getElementById("drawerSubtaskList"),
  newSubtaskInput: document.getElementById("newSubtaskInput"),
  addSubtaskBtn: document.getElementById("addSubtaskBtn"),
  drawerDeleteBtn: document.getElementById("drawerDeleteBtn"),
  toastContainer: document.getElementById("toastContainer")
};

function partnerLabel(key) {
  if (key === "me") return `${state.profile.me_emoji} ${state.profile.me_name}`;
  if (key === "wife") return `${state.profile.wife_emoji} ${state.profile.wife_name}`;
  return "💑 Duo";
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("duotasks_theme", theme);
  els.themeToggleBtn.textContent = theme === "dark" ? "☀️" : "🌙";
}

function applyIdentity(identity) {
  state.identity = identity;
  localStorage.setItem("duotasks_identity", identity);
  document.querySelectorAll(".id-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.identity === identity);
  });
}

function renderCoupleBanner() {
  const p = state.profile;
  els.idBtnMe.textContent = `${p.me_emoji} ${p.me_name}`;
  els.idBtnWife.textContent = `${p.wife_emoji} ${p.wife_name}`;
  els.filterChipMe.textContent = `${p.me_emoji} ${p.me_name}`;
  els.filterChipWife.textContent = `${p.wife_emoji} ${p.wife_name}`;

  els.loveNoteText.textContent = `💬 ${p.love_note || "Belle journée à deux ✨"}`;
  els.loveNoteAuthorLabel.textContent = p.love_note_author && p.love_note_author !== "both"
    ? `— ${partnerLabel(p.love_note_author)}`
    : "";
  els.kudosCountBadge.textContent = `❤️ ${p.kudos_count || 0}`;

  const score = state.stats?.extra?.couple_score ?? 0;
  els.karmaScore.textContent = String(score);
  els.groupModeToggleBtn.textContent = state.groupedMode ? "Vue : Par échéance" : "Vue : Liste plate";
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
  }, actionLabel ? 5000 : 2800);
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

function makeChip(text, cls) {
  const span = document.createElement("span");
  span.className = `chip ${cls}`;
  span.textContent = text;
  return span;
}

async function refreshAll() {
  const params = new URLSearchParams();
  if (state.filterType === "assignee") params.set("assignee", state.filterValue);
  else if (state.filterType === "category") params.set("category", state.filterValue);
  else if (state.filterType === "due") params.set("due_label", state.filterValue);
  if (state.searchQuery.trim()) params.set("search", state.searchQuery.trim());
  const qs = params.toString() ? `?${params.toString()}` : "";

  const [filteredTasks, allTasks, staples, stats, profile] = await Promise.all([
    apiJson(`/api/tasks${qs}`),
    apiJson("/api/tasks"),
    apiJson("/api/groceries/staples"),
    apiJson("/api/stats"),
    apiJson("/api/couple/profile")
  ]);

  state.tasks = filteredTasks;
  state.allTasks = allTasks;
  state.staples = staples;
  state.stats = stats;
  state.profile = profile;

  if (state.packs.length === 0) {
    state.packs = await apiJson("/api/routines/packs");
  }

  renderCoupleBanner();
  renderTasks();
  renderGroceriesView();
  renderRoutinesView();
  renderStatsView();

  if (state.editingTaskId !== null) {
    const fresh = state.allTasks.find((t) => t.id === state.editingTaskId);
    if (fresh) {
      renderDrawerSubtasks(fresh);
    }
  }
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
  const globalDone = state.allTasks.filter((t) => t.completed).length;
  els.taskCounter.textContent = `${globalActive} active${globalActive > 1 ? "s" : ""} · ${globalDone} terminée${globalDone > 1 ? "s" : ""}`;
  els.completedHeading.textContent = `Terminées (${completed.length})`;

  els.activeList.innerHTML = "";
  els.completedList.innerHTML = "";

  if (active.length === 0) {
    els.emptyState.classList.remove("hidden");
  } else {
    els.emptyState.classList.add("hidden");
    if (state.groupedMode) {
      const grouped = new Map();
      TEMPORAL_BUCKETS.forEach((b) => grouped.set(b.key, []));
      active.forEach((task) => grouped.get(getBucketKey(task)).push(task));

      const nonEmptyBuckets = TEMPORAL_BUCKETS.filter((b) => grouped.get(b.key).length > 0);
      const showHeaders = nonEmptyBuckets.length > 1;
      nonEmptyBuckets.forEach((bucket) => {
        if (showHeaders) {
          const hdr = document.createElement("li");
          hdr.className = "task-group-header";
          hdr.textContent = `${bucket.label} (${grouped.get(bucket.key).length})`;
          els.activeList.appendChild(hdr);
        }
        grouped.get(bucket.key).forEach((task) => els.activeList.appendChild(createTaskElement(task)));
      });
    } else {
      active.forEach((task) => els.activeList.appendChild(createTaskElement(task)));
    }
  }

  completed.forEach((task) => els.completedList.appendChild(createTaskElement(task)));
  els.completedList.classList.toggle("hidden", !state.showCompleted);
  els.completedChevron.textContent = state.showCompleted ? "▾" : "▸";
  els.clearCompletedBtn.classList.toggle("hidden", completed.length === 0);
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
  title.textContent = task.title;
  content.appendChild(title);

  if (task.notes) {
    const snippet = document.createElement("div");
    snippet.className = "task-notes-snippet";
    snippet.textContent = `📝 ${task.notes}`;
    content.appendChild(snippet);
  }

  const meta = document.createElement("div");
  meta.className = "task-meta";
  meta.appendChild(makeChip(partnerLabel(task.assignee), "chip-assignee"));
  meta.appendChild(makeChip(`#${task.category}`, "chip-category"));
  meta.appendChild(makeChip(task.due_label, "chip-due"));
  if (task.priority < 3) {
    meta.appendChild(makeChip(`P${task.priority}`, "chip-prio"));
  }
  if (task.recurring) {
    meta.appendChild(makeChip(RECURRENCE_LABELS[task.recurrence_rule] || "🔁 quotidien", "chip-recurring"));
  }
  if (task.quantity) {
    meta.appendChild(makeChip(`📦 ${task.quantity}`, "chip-qty"));
  }
  if (task.aisle) {
    meta.appendChild(makeChip(`🛒 ${task.aisle}`, "chip-aisle"));
  }
  if (task.subtasks && task.subtasks.length > 0) {
    const doneSub = task.subtasks.filter((s) => s.done).length;
    meta.appendChild(makeChip(`☑ ${doneSub}/${task.subtasks.length}`, "chip-subtask"));
  }

  content.appendChild(meta);

  const actionsCol = document.createElement("div");
  actionsCol.className = "task-actions-col";

  if (!task.completed && task.due_label !== "tomorrow") {
    const snoozeBtn = document.createElement("button");
    snoozeBtn.type = "button";
    snoozeBtn.className = "snooze-btn";
    snoozeBtn.title = "Reporter à demain";
    snoozeBtn.setAttribute("aria-label", "Reporter à demain");
    snoozeBtn.textContent = "🌅";
    snoozeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      snoozeToTomorrow(task);
    });
    actionsCol.appendChild(snoozeBtn);
  }

  const delBtn = document.createElement("button");
  delBtn.type = "button";
  delBtn.className = "delete-btn";
  delBtn.setAttribute("aria-label", "Supprimer");
  delBtn.textContent = "🗑";
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

function renderGroceriesView() {
  const groceryTasks = state.allTasks.filter((t) => t.category === "courses");
  const activeGroceries = groceryTasks.filter((t) => !t.completed);
  const completedGroceries = groceryTasks.filter((t) => t.completed);

  els.groceriesBadge.textContent = String(activeGroceries.length);
  els.groceriesBadge.classList.toggle("hidden", activeGroceries.length === 0);
  els.clearGroceriesBtn.classList.toggle("hidden", completedGroceries.length === 0);

  const activeTitles = new Set(activeGroceries.map((t) => t.title.toLowerCase()));
  const filteredStaples = state.staples.filter(
    (s) => state.stapleAisle === "all" || s.aisle === state.stapleAisle
  );
  els.staplesGrid.innerHTML = "";
  filteredStaples.forEach((staple) => {
    const inCart = activeTitles.has(staple.name.toLowerCase());
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `staple-btn${inCart ? " in-cart" : ""}`;

    const emoji = document.createElement("span");
    emoji.className = "staple-emoji";
    emoji.textContent = staple.emoji || "🛒";

    const info = document.createElement("div");
    info.className = "staple-info";

    const name = document.createElement("div");
    name.className = "staple-name";
    name.textContent = staple.name;

    const sub = document.createElement("div");
    sub.className = "staple-sub";
    sub.textContent = inCart ? "✓ Dans le panier" : `${staple.default_qty || staple.aisle}`;

    info.appendChild(name);
    info.appendChild(sub);
    btn.appendChild(emoji);
    btn.appendChild(info);
    btn.addEventListener("click", () => quickAddStaple(staple));
    els.staplesGrid.appendChild(btn);
  });

  els.groceriesByAisle.innerHTML = "";
  if (groceryTasks.length === 0) {
    els.groceriesEmptyState.classList.remove("hidden");
    return;
  }
  els.groceriesEmptyState.classList.add("hidden");

  const groups = new Map();
  AISLE_ORDER.forEach((aisle) => groups.set(aisle, []));
  activeGroceries.forEach((task) => {
    const key = AISLE_ORDER.includes(task.aisle) ? task.aisle : "Autre";
    groups.get(key).push(task);
  });

  groups.forEach((items, aisleName) => {
    if (items.length === 0) return;
    const h = document.createElement("h3");
    h.className = "aisle-heading";
    h.textContent = `${aisleName} (${items.length})`;
    els.groceriesByAisle.appendChild(h);

    const ul = document.createElement("ul");
    ul.className = "task-list";
    items.forEach((t) => ul.appendChild(createTaskElement(t)));
    els.groceriesByAisle.appendChild(ul);
  });

  if (completedGroceries.length > 0) {
    const h = document.createElement("h3");
    h.className = "aisle-heading";
    h.textContent = `Dans le caddie / Achetés (${completedGroceries.length})`;
    els.groceriesByAisle.appendChild(h);

    const ul = document.createElement("ul");
    ul.className = "task-list";
    completedGroceries.forEach((t) => ul.appendChild(createTaskElement(t)));
    els.groceriesByAisle.appendChild(ul);
  }
}

function renderRoutinesView() {
  const recurringTasks = state.allTasks.filter((t) => t.recurring);
  const doneCount = recurringTasks.filter((t) => t.completed).length;
  els.routinesSummary.textContent = `${recurringTasks.length} routine(s) · ${doneCount} cochée(s) aujourd'hui`;

  els.routinesList.innerHTML = "";
  if (recurringTasks.length === 0) {
    els.routinesEmptyState.classList.remove("hidden");
  } else {
    els.routinesEmptyState.classList.add("hidden");
    recurringTasks.forEach((t) => els.routinesList.appendChild(createTaskElement(t)));
  }

  els.packsGrid.innerHTML = "";
  state.packs.forEach((pack) => {
    const card = document.createElement("div");
    card.className = "pack-card";

    const top = document.createElement("div");
    const title = document.createElement("div");
    title.className = "pack-title";
    title.textContent = `${pack.emoji} ${pack.name}`;

    const desc = document.createElement("div");
    desc.className = "muted-text";
    desc.textContent = pack.description;

    const preview = document.createElement("ul");
    preview.className = "pack-preview-list";
    pack.tasks.slice(0, 3).forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      preview.appendChild(li);
    });
    if (pack.tasks.length > 3) {
      const more = document.createElement("li");
      more.textContent = `+ ${pack.tasks.length - 3} autre(s)...`;
      preview.appendChild(more);
    }

    top.appendChild(title);
    top.appendChild(desc);
    top.appendChild(preview);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-small";
    btn.textContent = `Appliquer (${pack.tasks.length} tâches)`;
    btn.addEventListener("click", () => applyPack(pack));

    card.appendChild(top);
    card.appendChild(btn);
    els.packsGrid.appendChild(card);
  });
}

function renderStatsView() {
  if (!state.stats) return;
  const s = state.stats;

  els.kpiGrid.innerHTML = "";
  const kpis = [
    { val: s.total_active, lbl: "À faire" },
    { val: s.overdue_or_urgent, lbl: "Urgentes (P1)" },
    { val: s.courses_active, lbl: "Articles courses" },
    { val: s.total_completed, lbl: "Terminées" }
  ];
  kpis.forEach((k) => {
    const box = document.createElement("div");
    box.className = "kpi-card";
    const v = document.createElement("div");
    v.className = "kpi-val";
    v.textContent = String(k.val);
    const l = document.createElement("div");
    l.className = "kpi-lbl";
    l.textContent = k.lbl;
    box.appendChild(v);
    box.appendChild(l);
    els.kpiGrid.appendChild(box);
  });

  els.balanceBars.innerHTML = "";
  const totalDone = Math.max(1, (s.completed_by_actor.me || 0) + (s.completed_by_actor.wife || 0) + (s.completed_by_actor.both || 0));
  const actors = [
    { key: "me", label: partnerLabel("me"), cls: "" },
    { key: "wife", label: partnerLabel("wife"), cls: "wife" },
    { key: "both", label: partnerLabel("both"), cls: "both" }
  ];
  actors.forEach((a) => {
    const active = s.by_assignee[a.key]?.active || 0;
    const done = s.completed_by_actor[a.key] || 0;
    const pct = Math.round((done / totalDone) * 100);

    const row = document.createElement("div");
    row.className = "bar-row";
    const lbl = document.createElement("div");
    lbl.className = "bar-label";
    const left = document.createElement("span");
    left.textContent = a.label;
    const right = document.createElement("span");
    right.textContent = `${done} faites · ${active} en cours`;
    lbl.appendChild(left);
    lbl.appendChild(right);

    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = `bar-fill ${a.cls}`;
    fill.style.width = `${pct}%`;
    track.appendChild(fill);

    row.appendChild(lbl);
    row.appendChild(track);
    els.balanceBars.appendChild(row);
  });

  els.categoryBars.innerHTML = "";
  const cats = Object.entries(s.by_category || {});
  if (cats.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted-text";
    empty.textContent = "Aucune catégorie active pour le moment.";
    els.categoryBars.appendChild(empty);
  } else {
    const maxCat = Math.max(1, ...cats.map(([, c]) => c.active + c.completed));
    cats.forEach(([catName, counts]) => {
      const total = counts.active + counts.completed;
      const pct = Math.round((total / maxCat) * 100);
      const row = document.createElement("div");
      row.className = "bar-row";
      const lbl = document.createElement("div");
      lbl.className = "bar-label";
      const left = document.createElement("span");
      left.textContent = `#${catName}`;
      const right = document.createElement("span");
      right.textContent = `${counts.active} actives · ${counts.completed} terminées`;
      lbl.appendChild(left);
      lbl.appendChild(right);
      const track = document.createElement("div");
      track.className = "bar-track";
      const fill = document.createElement("div");
      fill.className = "bar-fill both";
      fill.style.width = `${pct}%`;
      track.appendChild(fill);
      row.appendChild(lbl);
      row.appendChild(track);
      els.categoryBars.appendChild(row);
    });
  }

  els.activityFeed.innerHTML = "";
  const actionsMap = {
    created: "a ajouté",
    completed: "a terminé",
    reopened: "a rouvert",
    deleted: "a supprimé",
    quick_added: "a mis au panier",
    applied_pack: "a appliqué",
    reset_routines: "a réinitialisé",
    cleared_completed: "a vidé",
    kudos: "a envoyé",
    love_note: "a écrit un mot doux :"
  };
  if (!s.recent_activity || s.recent_activity.length === 0) {
    const li = document.createElement("li");
    li.className = "muted-text";
    li.textContent = "Aucune activité enregistrée.";
    els.activityFeed.appendChild(li);
  } else {
    s.recent_activity.forEach((entry) => {
      const li = document.createElement("li");
      li.className = "activity-row";
      const msg = document.createElement("span");
      msg.textContent = `${partnerLabel(entry.actor)} ${actionsMap[entry.action] || entry.action} « ${entry.task_title} »`;
      const tm = document.createElement("span");
      tm.className = "activity-time";
      tm.textContent = entry.created_at ? entry.created_at.slice(11, 16) : "";
      li.appendChild(msg);
      li.appendChild(tm);
      els.activityFeed.appendChild(li);
    });
  }
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
      showToast("✓ Tâche terminée !", "Annuler", async () => {
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
    showToast(`🌅 « ${task.title} » reportée à demain`);
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Impossible de reporter");
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
      showToast("🗑 Tâche supprimée", "Annuler", async () => {
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

async function quickAddStaple(staple) {
  try {
    await apiJson(`/api/groceries/staples/${staple.id}/quick-add`, { method: "POST" });
    showToast(`🛒 ${staple.name} ajouté au panier`);
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
}

async function applyPack(pack) {
  try {
    const res = await apiJson(`/api/routines/packs/${pack.id}/apply`, { method: "POST" });
    showToast(`${pack.emoji} ${res.added_count} tâche(s) ajoutée(s)`);
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
}

function ensureSelectOption(selectEl, value, prefix = "") {
  if (!value) return;
  const exists = Array.from(selectEl.options).some((opt) => opt.value === value);
  if (!exists) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = `${prefix}${value}`;
    selectEl.appendChild(opt);
  }
}

function openTaskDrawer(task) {
  state.editingTaskId = task.id;
  els.editTaskId.value = String(task.id);
  els.editTitle.value = task.title;
  els.editNotes.value = task.notes || "";
  els.editAssignee.value = task.assignee || "both";
  const cat = task.category || "inbox";
  ensureSelectOption(els.editCategory, cat, "#");
  els.editCategory.value = cat;
  els.editPriority.value = String(task.priority || 3);
  const due = task.due_label || "today";
  ensureSelectOption(els.editDueLabel, due);
  els.editDueLabel.value = due;
  els.editRecurrence.value = task.recurrence_rule || (task.recurring ? "daily" : "none");
  els.editQuantity.value = task.quantity || "";
  const aisle = task.aisle || "";
  ensureSelectOption(els.editAisle, aisle);
  els.editAisle.value = aisle;
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

let previewTimer = null;
async function updateParsePreview() {
  const raw = els.input.value;
  try {
    const parsed = await apiJson("/api/parse", {
      method: "POST",
      body: JSON.stringify({ raw_input: raw })
    });
    els.prevAssignee.textContent = partnerLabel(parsed.assignee);
    els.prevCategory.textContent = `#${parsed.category}`;
    els.prevDue.textContent = parsed.due_label;
    els.prevPrio.textContent = `P${parsed.priority}`;
    els.prevRecurring.textContent = RECURRENCE_LABELS[parsed.recurrence_rule] || "🔁 quotidien";
    els.prevRecurring.classList.toggle("hidden", !parsed.recurring);
    els.prevQty.textContent = parsed.quantity ? `📦 ${parsed.quantity}` : "";
    els.prevQty.classList.toggle("hidden", !parsed.quantity);
    els.prevAisle.textContent = parsed.aisle ? `🛒 ${parsed.aisle}` : "";
    els.prevAisle.classList.toggle("hidden", !parsed.aisle);
  } catch {
    // Silent fallback when offline
  }
}

async function refreshHealth() {
  try {
    const health = await apiJson("/api/health");
    if (els.syncDot.classList.contains("online")) {
      const count = Math.max(1, health.connected_devices || 1);
      els.syncText.textContent = `Live (${count})`;
    }
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
    refreshHealth();
  });

  socket.addEventListener("message", async (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      if (payload.event === "sync") {
        await refreshAll();
        refreshHealth();
      } else if (payload.event === "kudos") {
        els.sendKudosBtn.classList.remove("pulse");
        void els.sendKudosBtn.offsetWidth;
        els.sendKudosBtn.classList.add("pulse");
        showToast(`💌 ${partnerLabel(payload.from)} : ${payload.message}`);
        await refreshAll();
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

// --- Event Wiring ---

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    state.activeTab = tab;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".view-pane").forEach((pane) => {
      pane.classList.toggle("hidden", pane.id !== `view-${tab}`);
    });
  });
});

document.querySelectorAll(".id-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    applyIdentity(btn.dataset.identity || "me");
    showToast(`Téléphone réglé sur ${btn.textContent}`);
  });
});

els.themeToggleBtn.addEventListener("click", () => {
  applyTheme(state.theme === "dark" ? "light" : "dark");
});

els.groupModeToggleBtn.addEventListener("click", () => {
  state.groupedMode = !state.groupedMode;
  localStorage.setItem("duotasks_grouped", String(state.groupedMode));
  renderCoupleBanner();
  renderTasks();
});

// Couple Banner Events
els.toggleLoveNoteBtn.addEventListener("click", () => {
  els.loveNoteForm.classList.toggle("hidden");
  if (!els.loveNoteForm.classList.contains("hidden")) {
    els.loveNoteInput.value = state.profile.love_note || "";
    els.loveNoteInput.focus();
  }
});

els.loveNoteForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const note = els.loveNoteInput.value.trim();
  els.loveNoteForm.classList.add("hidden");
  try {
    await apiJson("/api/couple/profile", {
      method: "PATCH",
      body: JSON.stringify({ love_note: note, love_note_author: state.identity })
    });
    showToast("💬 Mot doux publié !");
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Impossible de publier");
  }
});

els.sendKudosBtn.addEventListener("click", async () => {
  els.sendKudosBtn.classList.remove("pulse");
  void els.sendKudosBtn.offsetWidth;
  els.sendKudosBtn.classList.add("pulse");
  try {
    await apiJson("/api/couple/kudos", {
      method: "POST",
      body: JSON.stringify({
        from_partner: state.identity,
        message: "Merci pour ce que tu fais aujourd'hui ❤️"
      })
    });
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

els.editProfileBtn.addEventListener("click", () => {
  els.profMeName.value = state.profile.me_name || "Valentin";
  els.profMeEmoji.value = state.profile.me_emoji || "🦊";
  els.profWifeName.value = state.profile.wife_name || "Chérie";
  els.profWifeEmoji.value = state.profile.wife_emoji || "🌸";
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
        me_emoji: els.profMeEmoji.value.trim() || "🦊",
        wife_name: els.profWifeName.value.trim(),
        wife_emoji: els.profWifeEmoji.value.trim() || "🌸"
      })
    });
    els.profileModal.classList.add("hidden");
    showToast("💑 Prénoms enregistrés");
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Erreur de mise à jour");
  }
});

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
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

els.input.addEventListener("input", () => {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updateParsePreview, 120);
});

let searchTimer = null;
els.searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.searchQuery = els.searchInput.value;
    refreshAll();
  }, 160);
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

document.querySelectorAll("#view-tasks .filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll("#view-tasks .filter-chip").forEach((c) => c.classList.remove("active"));
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

els.clearCompletedBtn.addEventListener("click", async () => {
  try {
    const res = await apiJson("/api/tasks/clear-completed", { method: "POST" });
    showToast(`🗑 ${res.cleared_count} tâche(s) supprimée(s)`);
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Erreur lors de la suppression");
  }
});

// Groceries events
els.groceryQuickForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const val = els.groceryQuickInput.value.trim();
  if (!val) return;
  const raw = val.includes("#") ? val : `${val} #courses`;
  els.groceryQuickInput.value = "";
  try {
    await apiJson("/api/tasks", { method: "POST", body: JSON.stringify({ raw_input: raw }) });
    showToast("🛒 Article ajouté au panier");
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Impossible d'ajouter l'article");
  }
});

els.toggleNewStapleBtn.addEventListener("click", () => {
  els.newStapleForm.classList.toggle("hidden");
});

els.newStapleForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  try {
    await apiJson("/api/groceries/staples", {
      method: "POST",
      body: JSON.stringify({
        name: els.stapleNameInput.value.trim(),
        default_qty: els.stapleQtyInput.value.trim(),
        aisle: els.stapleAisleInput.value,
        emoji: els.stapleEmojiInput.value.trim() || "🛒"
      })
    });
    els.newStapleForm.reset();
    els.stapleEmojiInput.value = "🛒";
    els.newStapleForm.classList.add("hidden");
    showToast("⭐ Favori enregistré");
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Erreur lors de l'enregistrement");
  }
});

document.querySelectorAll("#stapleAisleFilters .filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll("#stapleAisleFilters .filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    state.stapleAisle = chip.dataset.aisle || "all";
    renderGroceriesView();
  });
});

els.clearGroceriesBtn.addEventListener("click", async () => {
  try {
    const res = await apiJson("/api/tasks/clear-completed?category=courses", { method: "POST" });
    showToast(`🛍️ ${res.cleared_count} article(s) vidé(s)`);
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Erreur lors du vidage");
  }
});

// Routines events
els.resetRoutinesBtn.addEventListener("click", async () => {
  try {
    const res = await apiJson("/api/routines/reset-daily", { method: "POST" });
    showToast(`🔄 ${res.reset_count} routine(s) réinitialisée(s)`);
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Erreur lors de la réinitialisation");
  }
});

// Drawer events
els.closeDrawerBtn.addEventListener("click", closeTaskDrawer);
els.taskDrawer.addEventListener("click", (evt) => {
  if (evt.target === els.taskDrawer) closeTaskDrawer();
});

els.taskEditForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const id = Number(els.editTaskId.value);
  try {
    await apiJson(`/api/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: els.editTitle.value.trim(),
        notes: els.editNotes.value.trim(),
        assignee: els.editAssignee.value,
        category: els.editCategory.value,
        priority: Number(els.editPriority.value),
        due_label: els.editDueLabel.value,
        recurrence_rule: els.editRecurrence.value,
        quantity: els.editQuantity.value.trim(),
        aisle: els.editAisle.value
      })
    });
    closeTaskDrawer();
    showToast("💾 Tâche mise à jour");
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Impossible d'enregistrer");
  }
});

els.addSubtaskBtn.addEventListener("click", async () => {
  const id = Number(els.editTaskId.value);
  const text = els.newSubtaskInput.value.trim();
  if (!text) return;
  els.newSubtaskInput.value = "";
  try {
    const updated = await apiJson(`/api/tasks/${id}/subtasks`, {
      method: "POST",
      body: JSON.stringify({ text })
    });
    renderDrawerSubtasks(updated);
    await refreshAll();
  } catch (err) {
    console.error(err);
    showToast("⚠️ Erreur sous-tâche");
  }
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

// Install Modal
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
