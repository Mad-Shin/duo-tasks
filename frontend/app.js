const RECURRENCE_LABELS = {
  daily: "Quotidien",
  weekly: "Hebdo",
  monthly: "Mensuel"
};

const CATEGORY_LABELS = {
  inbox: "Général",
  maison: "Maison",
  courses: "Courses",
  date: "Sortie",
  admin: "Admin"
};

const DEFAULT_PRESETS = ["Deep clean salle de bain hebdo", "Deep clean cuisine hebdo"];
const DEFAULT_COURSE_PRESETS = ["Pâtes", "Riz", "Liquide vaisselle", "Linge"];
const SVG_TRASH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';
const SVG_JP_HEART = '<svg class="jp-heart-ico" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 13.7C8 13.7 2.2 10.1 2.2 5.9C2.2 3.9 3.7 2.5 5.4 2.5C6.55 2.5 7.5 3.15 8 4.05C8.5 3.15 9.45 2.5 10.6 2.5C12.3 2.5 13.8 3.9 13.8 5.9C13.8 10.1 8 13.7 8 13.7Z" fill="currentColor" fill-opacity="0.24" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/><path d="M4.6 5.5C4.7 4.75 5.2 4.35 5.85 4.25" stroke="currentColor" stroke-width="1.05" stroke-linecap="round" opacity="0.72"/></svg>';

const state = {
  composerMode: "task",
  carouselSlide: "tasks",
  recurringWho: "me",
  theme: localStorage.getItem("duotasks_theme_v2") || "dark",
  profile: {
    me_name: "Valentin",
    wife_name: "Lisa",
    preset_tasks: [...DEFAULT_PRESETS],
    preset_courses: [...DEFAULT_COURSE_PRESETS]
  },
  draftPresets: [...DEFAULT_PRESETS],
  draftCoursePresets: [...DEFAULT_COURSE_PRESETS],
  tasks: [],
  searchQuery: "",
  showCompleted: false,
  editingTaskId: null,
  budget: null,
  budgetLocked: false,
  budgetPin: localStorage.getItem("duotasks_duo_pin") || "",
  budgetDrawerOpen: false,
  budgetModalMode: "refill",
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

  // Settings Modal
  editProfileBtn: document.getElementById("editProfileBtn"),
  profileModal: document.getElementById("profileModal"),
  closeProfileModalBtn: document.getElementById("closeProfileModalBtn"),
  profileForm: document.getElementById("profileForm"),
  profMeName: document.getElementById("profMeName"),
  profWifeName: document.getElementById("profWifeName"),
  settingsPresetsList: document.getElementById("settingsPresetsList"),
  newPresetInput: document.getElementById("newPresetInput"),
  addPresetBtn: document.getElementById("addPresetBtn"),
  settingsCoursePresetsList: document.getElementById("settingsCoursePresetsList"),
  newCoursePresetInput: document.getElementById("newCoursePresetInput"),
  addCoursePresetBtn: document.getElementById("addCoursePresetBtn"),

  // Mode Switch & Composers
  modeTaskBtn: document.getElementById("modeTaskBtn"),
  modeEventBtn: document.getElementById("modeEventBtn"),
  modeCourseBtn: document.getElementById("modeCourseBtn"),
  taskComposerCard: document.getElementById("taskComposerCard"),
  eventComposerCard: document.getElementById("eventComposerCard"),
  courseComposerCard: document.getElementById("courseComposerCard"),
  form: document.getElementById("quickAddForm"),
  input: document.getElementById("quickAddInput"),
  recTogglePill: document.getElementById("recTogglePill"),
  taskRecurringCheck: document.getElementById("taskRecurringCheck"),
  taskRecurringAssigneeWrap: document.getElementById("taskRecurringAssigneeWrap"),
  recWhoMe: document.getElementById("recWhoMe"),
  recWhoWife: document.getElementById("recWhoWife"),
  presetTasksRow: document.getElementById("presetTasksRow"),
  eventAddForm: document.getElementById("eventAddForm"),
  eventTitleInput: document.getElementById("eventTitleInput"),
  eventDateInput: document.getElementById("eventDateInput"),
  eventTimeInput: document.getElementById("eventTimeInput"),
  eventLocationInput: document.getElementById("eventLocationInput"),
  courseAddForm: document.getElementById("courseAddForm"),
  courseAddInput: document.getElementById("courseAddInput"),
  presetCoursesRow: document.getElementById("presetCoursesRow"),

  // Carousel & Navigation
  tasksCarousel: document.getElementById("tasksCarousel"),
  secTasks: document.getElementById("sec-tasks"),
  secRecurring: document.getElementById("sec-recurring"),
  catClawFx: document.getElementById("catClawFx"),
  dotTasks: document.getElementById("dotTasks"),
  dotRecurring: document.getElementById("dotRecurring"),
  swipeCueBtn: document.getElementById("swipeCueBtn"),
  swipeCueLabel: document.getElementById("swipeCueLabel"),

  // Search & Sections
  toggleSearchBtn: document.getElementById("toggleSearchBtn"),
  searchDrawer: document.getElementById("searchDrawer"),
  searchInput: document.getElementById("taskSearchInput"),
  activeList: document.getElementById("activeTaskList"),
  emptyState: document.getElementById("emptyState"),
  completedList: document.getElementById("completedTaskList"),
  completedWrap: document.getElementById("completedWrap"),
  completedHeading: document.getElementById("completedHeading"),
  toggleCompletedBtn: document.getElementById("toggleCompletedBtn"),
  completedChevron: document.getElementById("completedChevron"),
  resetRoutinesBtn: document.getElementById("resetRoutinesBtn"),
  clearCompletedBtn: document.getElementById("clearCompletedBtn"),

  // Recurring Unified Panel
  recurringList: document.getElementById("recurringList"),
  recurringEmpty: document.getElementById("recurringEmpty"),

  // Courses & Events Sections
  coursesList: document.getElementById("coursesList"),
  coursesEmptyState: document.getElementById("coursesEmptyState"),
  eventsList: document.getElementById("eventsList"),
  eventsEmptyState: document.getElementById("eventsEmptyState"),

  // Task / Event Drawer
  taskDrawer: document.getElementById("taskDrawer"),
  closeDrawerBtn: document.getElementById("closeDrawerBtn"),
  taskEditForm: document.getElementById("taskEditForm"),
  editTaskId: document.getElementById("editTaskId"),
  editTitle: document.getElementById("editTitle"),
  editAssignee: document.getElementById("editAssignee"),
  editCategory: document.getElementById("editCategory"),
  editUrgentCheck: document.getElementById("editUrgentCheck"),
  editRecurrence: document.getElementById("editRecurrence"),
  editEventDate: document.getElementById("editEventDate"),
  editEventTime: document.getElementById("editEventTime"),
  editLocation: document.getElementById("editLocation"),
  editQuantity: document.getElementById("editQuantity"),
  drawerDeleteBtn: document.getElementById("drawerDeleteBtn"),
  toastContainer: document.getElementById("toastContainer"),

  // Joint Account Budget (#sec-budget + Modals)
  appShell: document.querySelector(".app-shell"),
  secBudget: document.getElementById("sec-budget"),
  dockBudgetBtn: document.getElementById("dockBudgetBtn"),
  openMacrodroidFromSettingsBtn: document.getElementById("openMacrodroidFromSettingsBtn"),
  budgetCard: document.getElementById("budgetCard"),
  budgetPinGate: document.getElementById("budgetPinGate"),
  budgetPinForm: document.getElementById("budgetPinForm"),
  budgetPinInput: document.getElementById("budgetPinInput"),
  budgetPinError: document.getElementById("budgetPinError"),
  budgetCardBody: document.getElementById("budgetCardBody"),
  budgetWebhookDot: document.getElementById("budgetWebhookDot"),
  budgetBalanceValue: document.getElementById("budgetBalanceValue"),
  budgetLastOpLine: document.getElementById("budgetLastOpLine"),
  openRefillModalBtn: document.getElementById("openRefillModalBtn"),
  toggleBudgetDrawerBtn: document.getElementById("toggleBudgetDrawerBtn"),
  budgetDrawerHeading: document.getElementById("budgetDrawerHeading"),
  budgetDrawerPanel: document.getElementById("budgetDrawerPanel"),
  budgetTxList: document.getElementById("budgetTxList"),
  budgetTxEmpty: document.getElementById("budgetTxEmpty"),
  refillModal: document.getElementById("refillModal"),
  closeRefillModalBtn: document.getElementById("closeRefillModalBtn"),
  budgetRefillForm: document.getElementById("budgetRefillForm"),
  refillQuickChips: document.getElementById("refillQuickChips"),
  budgetAmountLabel: document.getElementById("budgetAmountLabel"),
  budgetAmountInput: document.getElementById("budgetAmountInput"),
  budgetMerchantGroup: document.getElementById("budgetMerchantGroup"),
  budgetMerchantInput: document.getElementById("budgetMerchantInput"),
  budgetNoteInput: document.getElementById("budgetNoteInput"),
  budgetModalHint: document.getElementById("budgetModalHint"),
  budgetSubmitBtn: document.getElementById("budgetSubmitBtn"),
  openMacrodroidBtn: document.getElementById("openMacrodroidBtn"),
  macrodroidModal: document.getElementById("macrodroidModal"),
  closeMacrodroidModalBtn: document.getElementById("closeMacrodroidModalBtn"),
  macrodroidSecretBadge: document.getElementById("macrodroidSecretBadge"),
  macroWebhookUrl: document.getElementById("macroWebhookUrl"),
  copyWebhookUrlBtn: document.getElementById("copyWebhookUrlBtn"),
  budgetSettingsForm: document.getElementById("budgetSettingsForm"),
  budgetFilterKeywordInput: document.getElementById("budgetFilterKeywordInput"),
  macrodroidLogsList: document.getElementById("macrodroidLogsList"),
  macrodroidLogsEmpty: document.getElementById("macrodroidLogsEmpty")
};

function partnerName(key) {
  if (key === "me") return state.profile.me_name || "Valentin";
  if (key === "wife") return state.profile.wife_name || "Lisa";
  return `${state.profile.me_name || "Valentin"} & ${state.profile.wife_name || "Lisa"}`;
}

function toLocalIsoDate(d) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function nextWeekdayDate(targetWeekday) {
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
    datesParam = `${rawDate}/${toLocalIsoDate(next).replace(/-/g, "")}`;
  }

  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: task.title,
    dates: datesParam
  });
  if (task.location) params.set("location", task.location);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("duotasks_theme_v2", theme);
}

function syncRecurringToggleUI() {
  const checked = els.taskRecurringCheck.checked;
  els.recTogglePill.classList.toggle("active", checked);
  els.taskRecurringAssigneeWrap.classList.toggle("hidden", !checked);
}

let clawFxTimer = null;

function triggerCatClawTransition(toSlide) {
  if (!els.catClawFx) return;
  const cls = toSlide === "recurring" ? "slash-left" : "slash-right";
  els.catClawFx.classList.remove("slash-left", "slash-right");
  void els.catClawFx.getBoundingClientRect();
  els.catClawFx.classList.add(cls);

  const incomingEl = toSlide === "recurring" ? els.secRecurring : els.secTasks;
  if (incomingEl) {
    incomingEl.classList.remove("slide-bloom");
    void incomingEl.offsetWidth;
    incomingEl.classList.add("slide-bloom");
  }

  clearTimeout(clawFxTimer);
  clawFxTimer = setTimeout(() => {
    els.catClawFx.classList.remove("slash-left", "slash-right");
  }, 600);
}

function scrollToCarouselSlide(slide) {
  if (!els.tasksCarousel) return;
  const targetLeft = slide === "recurring" ? els.tasksCarousel.scrollWidth : 0;
  els.tasksCarousel.scrollTo({ left: targetLeft, behavior: "smooth" });
}

function syncCarouselUI() {
  if (!els.tasksCarousel) return;
  const prevSlide = state.carouselSlide;
  const threshold = Math.max(40, els.tasksCarousel.clientWidth * 0.35);
  const isRecurring = els.tasksCarousel.scrollLeft > threshold;
  const isExpanding = els.tasksCarousel.scrollLeft > 24;
  const nextSlide = isRecurring ? "recurring" : "tasks";
  state.carouselSlide = nextSlide;

  els.dotTasks.classList.toggle("active", !isRecurring);
  els.dotRecurring.classList.toggle("active", isRecurring);
  els.swipeCueBtn.classList.toggle("is-back", isRecurring);
  els.swipeCueLabel.textContent = isRecurring ? "Tâches" : "Récurrentes";
  els.swipeCueBtn.setAttribute(
    "aria-label",
    isRecurring ? "Revenir aux tâches" : "Glisser vers les tâches récurrentes"
  );
  els.secTasks.classList.toggle("slide-active", !isRecurring);
  els.secRecurring.classList.toggle("slide-active", isRecurring);
  els.secRecurring.classList.toggle("in-view", isExpanding);

  if (prevSlide !== nextSlide) {
    triggerCatClawTransition(nextSlide);
  }
}

function setComposerMode(mode, shouldFocus = true) {
  state.composerMode = mode;
  els.modeTaskBtn.classList.toggle("active", mode === "task");
  els.modeEventBtn.classList.toggle("active", mode === "event");
  els.modeCourseBtn.classList.toggle("active", mode === "courses");
  els.taskComposerCard.classList.toggle("hidden", mode !== "task");
  els.eventComposerCard.classList.toggle("hidden", mode !== "event");
  els.courseComposerCard.classList.toggle("hidden", mode !== "courses");

  document.querySelectorAll(".fab-pill").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.dockMode === mode);
  });

  if (mode === "event" && !els.eventDateInput.value) {
    els.eventDateInput.value = nextWeekdayDate(6);
  }

  if (shouldFocus) {
    if (mode === "event") {
      els.eventTitleInput.focus();
    } else if (mode === "courses") {
      els.courseAddInput.focus();
    } else {
      els.input.focus();
    }
  }
}

function renderProfileLabels() {
  const me = partnerName("me");
  const wife = partnerName("wife");
  els.recWhoMe.textContent = me;
  els.recWhoWife.textContent = wife;
  if (els.editAssignee.options.length >= 3) {
    els.editAssignee.options[0].textContent = `${me} & ${wife}`;
    els.editAssignee.options[1].textContent = me;
    els.editAssignee.options[2].textContent = wife;
  }
}

function renderPresetButtons() {
  const presets = Array.isArray(state.profile.preset_tasks)
    ? state.profile.preset_tasks
    : DEFAULT_PRESETS;
  els.presetTasksRow.innerHTML = "";
  els.presetTasksRow.classList.toggle("hidden", presets.length === 0);

  presets.forEach((text) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "preset-task-pill";
    btn.textContent = text.replace(/\s+(?:hebdo|tous les jours|quotidien|mensuel)$/i, "");
    btn.title = text;
    btn.addEventListener("click", () => {
      els.input.value = text;
      const isRec = /\b(?:hebdo|weekly|daily|tous les jours|quotidien|mensuel|monthly)\b/i.test(text);
      els.taskRecurringCheck.checked = isRec;
      syncRecurringToggleUI();
      els.input.focus();
      const len = els.input.value.length;
      els.input.setSelectionRange(len, len);
    });
    els.presetTasksRow.appendChild(btn);
  });

  if (els.presetCoursesRow) {
    const coursePresets = Array.isArray(state.profile.preset_courses)
      ? state.profile.preset_courses
      : DEFAULT_COURSE_PRESETS;
    els.presetCoursesRow.innerHTML = "";
    els.presetCoursesRow.classList.toggle("hidden", coursePresets.length === 0);

    coursePresets.forEach((text) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "preset-task-pill";
      btn.textContent = text;
      btn.title = text;
      btn.addEventListener("click", () => {
        els.courseAddInput.value = text;
        els.courseAddInput.focus();
        const len = els.courseAddInput.value.length;
        els.courseAddInput.setSelectionRange(len, len);
      });
      els.presetCoursesRow.appendChild(btn);
    });
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
  const { headers: customHeaders, ...restOptions } = options;
  const res = await fetch(url, {
    ...restOptions,
    headers: { "Content-Type": "application/json", ...(customHeaders || {}) }
  });
  if (!res.ok) {
    const msg = await res.text();
    const err = new Error(`HTTP ${res.status}: ${msg}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function budgetApiJson(url, options = {}) {
  const extraHeaders = state.budgetPin ? { "X-Duo-Pin": state.budgetPin } : {};
  return apiJson(url, {
    ...options,
    headers: { ...extraHeaders, ...(options.headers || {}) }
  });
}

function formatCentsFr(cents, withSign = false) {
  const num = Number(cents) || 0;
  const absFormatted = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Math.abs(num) / 100);
  if (num < 0) return `-${absFormatted} €`;
  if (withSign && num > 0) return `+${absFormatted} €`;
  return `${absFormatted} €`;
}

function parseEuroInputToCents(raw) {
  const cleaned = String(raw || "")
    .replace(/[\s\u00a0\u202f€]/g, "")
    .replace(",", ".");
  if (!/^-?\d+(?:\.\d{1,2})?$/.test(cleaned)) return null;
  const val = Number(cleaned);
  if (!Number.isFinite(val)) return null;
  return Math.round(val * 100);
}

function formatRelativeFr(iso) {
  if (!iso) return "";
  try {
    const dt = new Date(iso);
    const diffSec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
    if (diffSec < 60) return "à l'instant";
    if (diffSec < 3600) return `il y a ${Math.floor(diffSec / 60)} min`;
    if (diffSec < 86400) return `il y a ${Math.floor(diffSec / 3600)} h`;
    if (diffSec < 172800) return "hier";
    return dt.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  } catch {
    return "";
  }
}

function formatShortTxDate(iso) {
  if (!iso) return "";
  try {
    const dt = new Date(iso);
    const day = dt.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
    const time = dt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    return `${day} · ${time}`;
  } catch {
    return "";
  }
}

async function refreshBudget() {
  try {
    const data = await budgetApiJson("/api/budget");
    state.budget = data;
    state.budgetLocked = false;
    els.budgetPinError.classList.add("hidden");
    renderBudget();
  } catch (err) {
    if (err && err.status === 401) {
      state.budgetLocked = true;
      renderBudget();
    } else {
      console.error(err);
    }
  }
}

function renderBudget() {
  if (state.budgetLocked) {
    els.secBudget.classList.add("hidden");
    els.dockBudgetBtn.classList.add("hidden");
    if (els.appShell) els.appShell.classList.remove("has-budget");
    els.budgetPinGate.classList.remove("hidden");
    els.budgetCardBody.classList.add("hidden");
    return;
  }

  els.budgetPinGate.classList.add("hidden");
  els.budgetCardBody.classList.remove("hidden");

  const b = state.budget;
  if (!b) return;

  const txs = Array.isArray(b.transactions) ? b.transactions : [];
  const bal = Number(b.balance_cents || 0);
  const hasRealFigures = bal !== 0 || txs.length > 0;

  // Keep Compte Joint section & 4th dock button hidden until real Revolut figures arrive
  els.secBudget.classList.toggle("hidden", !hasRealFigures);
  els.dockBudgetBtn.classList.toggle("hidden", !hasRealFigures);
  if (els.appShell) els.appShell.classList.toggle("has-budget", hasRealFigures);

  els.budgetBalanceValue.textContent = formatCentsFr(bal, false);
  els.budgetBalanceValue.classList.toggle("negative", bal < 0);
  els.budgetWebhookDot.classList.toggle("live", Boolean(b.webhook_configured));

  const lastOp = b.last_transaction || b.last_expense;
  if (lastOp) {
    const signedAmt =
      lastOp.kind === "expense"
        ? formatCentsFr(-Math.abs(lastOp.amount_cents))
        : lastOp.kind === "refill"
        ? formatCentsFr(Math.abs(lastOp.amount_cents), true)
        : formatCentsFr(lastOp.amount_cents, true);
    const rel = formatRelativeFr(lastOp.created_at);
    const parts = [signedAmt, lastOp.merchant || "Opération"];
    if (rel) parts.push(rel);
    els.budgetLastOpLine.textContent = `Dernière : ${parts.join(" · ")}`;
  } else {
    els.budgetLastOpLine.textContent = "Aucune opération enregistrée";
  }

  els.budgetDrawerHeading.textContent = `Dernières opérations (${txs.length})`;
  els.budgetDrawerPanel.classList.toggle("open", state.budgetDrawerOpen);
  els.toggleBudgetDrawerBtn.setAttribute("aria-expanded", String(state.budgetDrawerOpen));

  els.budgetTxList.innerHTML = "";
  els.budgetTxEmpty.classList.toggle("hidden", txs.length > 0);

  txs.forEach((tx) => {
    const li = document.createElement("li");
    li.className = "budget-tx-item";

    const main = document.createElement("div");
    main.className = "budget-tx-main";

    const merch = document.createElement("div");
    merch.className = "budget-tx-merchant";
    merch.textContent = tx.merchant || (tx.kind === "refill" ? "Refill" : "Dépense");
    main.appendChild(merch);

    const meta = document.createElement("div");
    meta.className = "budget-tx-meta";

    const dateSp = document.createElement("span");
    dateSp.textContent = formatShortTxDate(tx.created_at);
    meta.appendChild(dateSp);

    const srcBadge = document.createElement("span");
    const isAuto = tx.source === "macrodroid";
    srcBadge.className = `budget-src-badge${isAuto ? " auto" : ""}`;
    srcBadge.textContent = isAuto ? "Auto" : "Manuel";
    meta.appendChild(srcBadge);

    if (tx.note) {
      const noteSp = document.createElement("span");
      noteSp.textContent = tx.note;
      meta.appendChild(noteSp);
    }
    main.appendChild(meta);

    const right = document.createElement("div");
    right.className = "budget-tx-right";

    const amt = document.createElement("span");
    amt.className = `budget-tx-amt ${tx.kind}`;
    if (tx.kind === "expense") {
      amt.textContent = formatCentsFr(-Math.abs(tx.amount_cents));
    } else if (tx.kind === "refill") {
      amt.textContent = formatCentsFr(Math.abs(tx.amount_cents), true);
    } else {
      amt.textContent = formatCentsFr(tx.amount_cents, true);
    }

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "row-action-btn delete";
    delBtn.setAttribute("aria-label", "Supprimer l'opération");
    delBtn.innerHTML = SVG_TRASH;
    delBtn.addEventListener("click", async () => {
      try {
        const updated = await budgetApiJson(`/api/budget/transactions/${tx.id}`, { method: "DELETE" });
        state.budget = updated;
        renderBudget();
        showToast("Opération supprimée");
      } catch (err) {
        console.error(err);
      }
    });

    right.appendChild(amt);
    right.appendChild(delBtn);

    li.appendChild(main);
    li.appendChild(right);
    els.budgetTxList.appendChild(li);
  });

  renderMacrodroidModal();
}

function renderMacrodroidModal() {
  const b = state.budget;
  if (!b) return;
  els.macroWebhookUrl.textContent = `${window.location.origin}/api/budget/webhook/revolut`;
  els.macrodroidSecretBadge.textContent = b.webhook_configured ? "Secret configuré" : "Secret à définir";
  els.macrodroidSecretBadge.classList.toggle("ok", Boolean(b.webhook_configured));
  if (document.activeElement !== els.budgetFilterKeywordInput) {
    els.budgetFilterKeywordInput.value = b.joint_filter_keyword || "";
  }

  const logs = Array.isArray(b.webhook_logs) ? b.webhook_logs : [];
  els.macrodroidLogsList.innerHTML = "";
  els.macrodroidLogsEmpty.classList.toggle("hidden", logs.length > 0);
  logs.forEach((entry) => {
    const li = document.createElement("li");
    li.className = "macro-log-item";

    const top = document.createElement("div");
    top.className = "macro-log-top";

    const st = document.createElement("span");
    st.className = `macro-log-status ${entry.status === "applied" ? "applied" : "ignored"}`;
    const signAmt =
      entry.parsed_kind === "refill"
        ? formatCentsFr(Math.abs(entry.parsed_amount_cents || 0), true)
        : formatCentsFr(-Math.abs(entry.parsed_amount_cents || 0));
    st.textContent =
      entry.status === "applied"
        ? `Appliqué · ${signAmt}`
        : `Filtré${entry.reason ? ` (${entry.reason})` : ""}`;

    const dt = document.createElement("span");
    dt.className = "subtitle";
    dt.textContent = formatShortTxDate(entry.received_at);

    top.appendChild(st);
    top.appendChild(dt);

    const summary = document.createElement("div");
    summary.className = "macro-log-raw";
    summary.textContent = entry.parsed_merchant || (entry.parsed_kind === "refill" ? "Rechargement" : "Paiement");

    li.appendChild(top);
    li.appendChild(summary);
    els.macrodroidLogsList.appendChild(li);
  });
}

function setBudgetModalMode(mode) {
  state.budgetModalMode = mode;
  document.querySelectorAll("[data-budget-mode]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.budgetMode === mode);
  });

  els.refillQuickChips.classList.toggle("hidden", mode !== "refill");
  els.budgetMerchantGroup.classList.toggle("hidden", mode !== "expense");

  const balText = state.budget ? formatCentsFr(state.budget.balance_cents) : "0,00 €";
  els.budgetModalHint.textContent = `Solde actuel : ${balText}`;

  if (mode === "refill") {
    els.budgetAmountLabel.textContent = "Montant à ajouter (€)";
    els.budgetAmountInput.placeholder = "Ex : 200 ou 42,50";
    els.budgetNoteInput.placeholder = "Ex : Virement mensuel";
    els.budgetSubmitBtn.textContent = "Ajouter";
  } else if (mode === "recalibrate") {
    els.budgetAmountLabel.textContent = "Vrai solde exact Revolut (€)";
    els.budgetAmountInput.placeholder = balText.replace(" €", "");
    els.budgetNoteInput.placeholder = "Ex : Recalage appli Revolut";
    els.budgetSubmitBtn.textContent = "Recaler";
  } else {
    els.budgetAmountLabel.textContent = "Montant de la dépense (€)";
    els.budgetAmountInput.placeholder = "Ex : 14,80";
    els.budgetNoteInput.placeholder = "Optionnel";
    els.budgetSubmitBtn.textContent = "Débiter";
  }
}

async function refreshAll() {
  const params = new URLSearchParams();
  if (state.searchQuery.trim()) params.set("search", state.searchQuery.trim());
  const qs = params.toString() ? `?${params.toString()}` : "";

  const [tasks, profile] = await Promise.all([
    apiJson(`/api/tasks${qs}`),
    apiJson("/api/couple/profile")
  ]);

  state.tasks = tasks;
  state.profile = profile;

  renderProfileLabels();
  renderPresetButtons();
  renderAllSections();
  await refreshBudget();
}

function renderAllSections() {
  const active = state.tasks.filter((t) => !t.completed);
  const completed = state.tasks.filter((t) => t.completed);

  const regularTasks = active.filter((t) => t.item_type !== "event" && t.category !== "courses" && !t.recurring);
  const recurringTasks = active.filter((t) => t.recurring && t.item_type !== "event" && t.category !== "courses");
  const courseTasks = active.filter((t) => t.category === "courses" && t.item_type !== "event");
  const eventTasks = active.filter((t) => t.item_type === "event");

  els.taskCounter.textContent = `${active.length} à faire`;

  // 1. Main Flat Tasks (no temporal headers)
  els.activeList.innerHTML = "";
  if (regularTasks.length === 0) {
    els.emptyState.classList.remove("hidden");
  } else {
    els.emptyState.classList.add("hidden");
    regularTasks.forEach((task) => els.activeList.appendChild(createListRow(task)));
  }

  // 2. Recurring Unified List with Discrete Assignee Tag
  els.recurringList.innerHTML = "";
  els.recurringEmpty.classList.toggle("hidden", recurringTasks.length > 0);
  recurringTasks.forEach((t) => els.recurringList.appendChild(createRecurringRow(t)));

  // 3. Courses Section (empty by default)
  els.coursesList.innerHTML = "";
  els.coursesEmptyState.classList.toggle("hidden", courseTasks.length > 0);
  courseTasks.forEach((task) => els.coursesList.appendChild(createListRow(task)));

  // 4. Events Section (always at bottom)
  els.eventsList.innerHTML = "";
  els.eventsEmptyState.classList.toggle("hidden", eventTasks.length > 0);
  eventTasks.forEach((task) => els.eventsList.appendChild(createListRow(task)));

  // 5. Completed
  els.completedHeading.textContent = `Terminées (${completed.length})`;
  els.completedList.innerHTML = "";
  completed.forEach((task) => els.completedList.appendChild(createListRow(task)));
  els.completedWrap.classList.toggle("hidden", !state.showCompleted || completed.length === 0);
  els.completedChevron.textContent = state.showCompleted ? "▾" : "▸";
  els.clearCompletedBtn.classList.toggle("hidden", completed.length === 0);

  const hasDoneRecurring = completed.some((t) => t.recurring);
  els.resetRoutinesBtn.classList.toggle("hidden", !hasDoneRecurring);
}

function createRecurringRow(task) {
  const li = document.createElement("li");
  li.className = "task-item";

  const checkBtn = document.createElement("button");
  checkBtn.type = "button";
  checkBtn.className = `check-btn prio-${task.priority}`;
  checkBtn.setAttribute("aria-label", "Marquer terminée");
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

  const metaLine = document.createElement("div");
  metaLine.className = "task-meta-line";
  const ruleSpan = document.createElement("span");
  ruleSpan.textContent = RECURRENCE_LABELS[task.recurrence_rule] || "Récurrent";
  metaLine.appendChild(ruleSpan);
  content.appendChild(metaLine);

  const actions = document.createElement("div");
  actions.className = "task-actions-col";

  const currentWho = task.assignee === "wife" ? "wife" : task.assignee === "me" ? "me" : "both";
  const nextWho = currentWho === "me" ? "wife" : currentWho === "wife" ? "both" : "me";

  const tagBtn = document.createElement("button");
  tagBtn.type = "button";
  tagBtn.className = `rec-assignee-tag tag-${currentWho}`;
  tagBtn.title = nextWho === "both" ? "Passer à deux" : `Passer à ${partnerName(nextWho)}`;

  if (currentWho === "both") {
    tagBtn.innerHTML = SVG_JP_HEART;
    const labelSpan = document.createElement("span");
    labelSpan.textContent = "À deux";
    tagBtn.appendChild(labelSpan);
  } else {
    const dot = document.createElement("span");
    dot.className = "rec-tag-dot";
    const nameSpan = document.createElement("span");
    nameSpan.textContent = partnerName(currentWho);
    tagBtn.appendChild(dot);
    tagBtn.appendChild(nameSpan);
  }

  tagBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    await apiJson(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ assignee: nextWho })
    });
    await refreshAll();
  });

  const delBtn = document.createElement("button");
  delBtn.type = "button";
  delBtn.className = "row-action-btn delete";
  delBtn.setAttribute("aria-label", "Supprimer");
  delBtn.innerHTML = SVG_TRASH;
  delBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteTask(task);
  });

  actions.appendChild(tagBtn);
  actions.appendChild(delBtn);

  li.appendChild(checkBtn);
  li.appendChild(content);
  li.appendChild(actions);
  return li;
}

function createListRow(task) {
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

  const metaParts = [];
  if (task.item_type === "event" && task.event_date) {
    const dateTxt = formatShortFrDate(task.event_date);
    metaParts.push({ text: task.event_time ? `${dateTxt} · ${task.event_time}` : dateTxt, accent: true });
    if (task.location) metaParts.push({ text: task.location, accent: false });
  } else {
    if (task.event_time) metaParts.push({ text: task.event_time, accent: true });
    if (task.location) metaParts.push({ text: task.location, accent: false });
  }
  if (task.quantity) {
    metaParts.push({ text: task.quantity, accent: true });
  }
  if (task.category && task.category !== "inbox" && task.category !== "courses" && !(task.item_type === "event" && task.category === "date")) {
    metaParts.push({ text: CATEGORY_LABELS[task.category] || task.category, accent: false });
  }
  if (task.recurring && task.completed) {
    metaParts.push({ text: task.assignee === "both" ? "À deux" : partnerName(task.assignee), accent: false });
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

  const actionsCol = document.createElement("div");
  actionsCol.className = "task-actions-col";

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
  renderAllSections();
  try {
    await apiJson(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: targetCompleted, completed_by: task.assignee || "both" })
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

async function deleteTask(taskOrId) {
  const snapshot = typeof taskOrId === "object"
    ? taskOrId
    : state.tasks.find((t) => t.id === taskOrId) || { id: taskOrId };
  const taskId = snapshot.id;

  state.tasks = state.tasks.filter((t) => t.id !== taskId);
  renderAllSections();
  try {
    await apiJson(`/api/tasks/${taskId}`, { method: "DELETE" });
    if (snapshot.raw_input || snapshot.title) {
      showToast("Supprimée", "Annuler", async () => {
        await apiJson("/api/tasks", {
          method: "POST",
          body: JSON.stringify({
            raw_input: snapshot.raw_input || snapshot.title,
            assignee: snapshot.assignee,
            category: snapshot.category,
            priority: snapshot.priority,
            due_label: snapshot.due_label,
            recurring: snapshot.recurring,
            recurrence_rule: snapshot.recurrence_rule,
            quantity: snapshot.quantity,
            item_type: snapshot.item_type || "task",
            event_date: snapshot.event_date || "",
            event_time: snapshot.event_time || "",
            location: snapshot.location || ""
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
  els.editAssignee.value = task.assignee || "both";
  const cat = task.category || "inbox";
  ensureSelectOption(els.editCategory, cat);
  els.editCategory.value = cat;
  els.editUrgentCheck.checked = Number(task.priority) === 1;
  els.editRecurrence.value = task.recurrence_rule || (task.recurring ? "daily" : "none");
  els.editEventDate.value = task.event_date || "";
  els.editEventTime.value = task.event_time || "";
  els.editLocation.value = task.location || "";
  els.editQuantity.value = task.quantity || "";
  els.taskDrawer.classList.remove("hidden");
}

function closeTaskDrawer() {
  state.editingTaskId = null;
  els.taskDrawer.classList.add("hidden");
}

function renderSettingsPresets() {
  els.settingsPresetsList.innerHTML = "";
  state.draftPresets.forEach((text, idx) => {
    const li = document.createElement("li");
    li.className = "settings-preset-item";
    const span = document.createElement("span");
    span.textContent = text;
    const del = document.createElement("button");
    del.type = "button";
    del.className = "btn-close";
    del.textContent = "✕";
    del.addEventListener("click", () => {
      state.draftPresets.splice(idx, 1);
      renderSettingsPresets();
    });
    li.appendChild(span);
    li.appendChild(del);
    els.settingsPresetsList.appendChild(li);
  });

  if (els.settingsCoursePresetsList) {
    els.settingsCoursePresetsList.innerHTML = "";
    state.draftCoursePresets.forEach((text, idx) => {
      const li = document.createElement("li");
      li.className = "settings-preset-item";
      const span = document.createElement("span");
      span.textContent = text;
      const del = document.createElement("button");
      del.type = "button";
      del.className = "btn-close";
      del.textContent = "✕";
      del.addEventListener("click", () => {
        state.draftCoursePresets.splice(idx, 1);
        renderSettingsPresets();
      });
      li.appendChild(span);
      li.appendChild(del);
      els.settingsCoursePresetsList.appendChild(li);
    });
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

els.themeToggleBtn.addEventListener("click", () => {
  applyTheme(state.theme === "dark" ? "light" : "dark");
});

els.modeTaskBtn.addEventListener("click", () => setComposerMode("task", true));
els.modeEventBtn.addEventListener("click", () => setComposerMode("event", true));
els.modeCourseBtn.addEventListener("click", () => setComposerMode("courses", true));

// Carousel Swipe & Tap Controls
els.tasksCarousel.addEventListener("scroll", syncCarouselUI, { passive: true });
els.dotTasks.addEventListener("click", () => scrollToCarouselSlide("tasks"));
els.dotRecurring.addEventListener("click", () => scrollToCarouselSlide("recurring"));
els.swipeCueBtn.addEventListener("click", () => {
  scrollToCarouselSlide(state.carouselSlide === "tasks" ? "recurring" : "tasks");
});

// Tapping the peeking slice of Récurrentes slides it smoothly into view
els.secRecurring.addEventListener(
  "click",
  (evt) => {
    if (state.carouselSlide === "tasks") {
      evt.preventDefault();
      evt.stopPropagation();
      scrollToCarouselSlide("recurring");
    }
  },
  true
);

// 4 Vertically Stacked Floating Bottom-Right Buttons
document.querySelectorAll(".fab-pill").forEach((btn) => {
  btn.addEventListener("click", () => {
    const mode = btn.dataset.dockMode || "";
    const targetId = btn.dataset.dockTarget || "sec-tasks";
    if (mode) {
      setComposerMode(mode, false);
    } else {
      document.querySelectorAll(".fab-pill").forEach((b) => {
        b.classList.toggle("active", b === btn);
      });
    }
    if (targetId === "sec-tasks") {
      scrollToCarouselSlide("tasks");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const targetEl = document.getElementById(targetId);
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

// Bespoke Recurring Toggle Pill
els.taskRecurringCheck.addEventListener("change", syncRecurringToggleUI);

document.querySelectorAll(".rec-who-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.recurringWho = btn.dataset.recWho || "me";
    document.querySelectorAll(".rec-who-btn").forEach((b) => {
      b.classList.toggle("active", b === btn);
    });
  });
});

// Submit Task
els.form.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const raw = els.input.value.trim();
  if (!raw) return;

  const isRecurring = els.taskRecurringCheck.checked;
  const body = { raw_input: raw, item_type: "task" };
  if (isRecurring) {
    body.recurring = true;
    body.recurrence_rule = /\b(?:tous les jours|quotidien|daily)\b/i.test(raw) ? "daily" : "weekly";
    body.assignee = state.recurringWho;
  }

  els.input.value = "";
  els.taskRecurringCheck.checked = false;
  syncRecurringToggleUI();

  try {
    await apiJson("/api/tasks", { method: "POST", body: JSON.stringify(body) });
    await refreshAll();
    if (isRecurring) {
      scrollToCarouselSlide("recurring");
    }
  } catch (err) {
    console.error(err);
  }
});

// Submit Course
els.courseAddForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const raw = els.courseAddInput.value.trim();
  if (!raw) return;
  els.courseAddInput.value = "";
  try {
    await apiJson("/api/tasks", {
      method: "POST",
      body: JSON.stringify({
        raw_input: raw,
        category: "courses",
        item_type: "task",
        recurring: false
      })
    });
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

// Event Presets & Quick Dates
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

// Settings Modal (Names + Pre-Suggestions)
els.editProfileBtn.addEventListener("click", () => {
  els.profMeName.value = state.profile.me_name || "Valentin";
  els.profWifeName.value = state.profile.wife_name || "Lisa";
  state.draftPresets = Array.isArray(state.profile.preset_tasks)
    ? [...state.profile.preset_tasks]
    : [...DEFAULT_PRESETS];
  state.draftCoursePresets = Array.isArray(state.profile.preset_courses)
    ? [...state.profile.preset_courses]
    : [...DEFAULT_COURSE_PRESETS];
  renderSettingsPresets();
  els.profileModal.classList.remove("hidden");
});

els.addPresetBtn.addEventListener("click", () => {
  const txt = els.newPresetInput.value.trim();
  if (!txt) return;
  state.draftPresets.push(txt);
  els.newPresetInput.value = "";
  renderSettingsPresets();
});

els.newPresetInput.addEventListener("keydown", (evt) => {
  if (evt.key === "Enter") {
    evt.preventDefault();
    els.addPresetBtn.click();
  }
});

if (els.addCoursePresetBtn && els.newCoursePresetInput) {
  els.addCoursePresetBtn.addEventListener("click", () => {
    const txt = els.newCoursePresetInput.value.trim();
    if (!txt) return;
    state.draftCoursePresets.push(txt);
    els.newCoursePresetInput.value = "";
    renderSettingsPresets();
  });

  els.newCoursePresetInput.addEventListener("keydown", (evt) => {
    if (evt.key === "Enter") {
      evt.preventDefault();
      els.addCoursePresetBtn.click();
    }
  });
}

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
        wife_name: els.profWifeName.value.trim(),
        preset_tasks: state.draftPresets,
        preset_courses: state.draftCoursePresets
      })
    });
    els.profileModal.classList.add("hidden");
    showToast("Paramètres enregistrés");
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
});

// Search
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

// Completed Section
els.toggleCompletedBtn.addEventListener("click", () => {
  state.showCompleted = !state.showCompleted;
  renderAllSections();
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

// Task Drawer
els.closeDrawerBtn.addEventListener("click", closeTaskDrawer);
els.taskDrawer.addEventListener("click", (evt) => {
  if (evt.target === els.taskDrawer) closeTaskDrawer();
});

els.taskEditForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const id = Number(els.editTaskId.value);
  const pickedDate = els.editEventDate.value;
  await apiJson(`/api/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      title: els.editTitle.value.trim(),
      assignee: els.editAssignee.value,
      category: els.editCategory.value,
      priority: els.editUrgentCheck.checked ? 1 : 3,
      due_label: pickedDate ? inferDueLabelFromIso(pickedDate) : "today",
      due_date: pickedDate || "",
      recurrence_rule: els.editRecurrence.value,
      event_date: pickedDate || "",
      event_time: els.editEventTime.value,
      location: els.editLocation.value.trim(),
      quantity: els.editQuantity.value.trim()
    })
  });
  closeTaskDrawer();
  showToast("Enregistré");
  await refreshAll();
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

// Joint Account Budget Events
els.toggleBudgetDrawerBtn.addEventListener("click", () => {
  state.budgetDrawerOpen = !state.budgetDrawerOpen;
  renderBudget();
});

els.openRefillModalBtn.addEventListener("click", () => {
  els.budgetAmountInput.value = "";
  els.budgetMerchantInput.value = "";
  els.budgetNoteInput.value = "";
  setBudgetModalMode("refill");
  els.refillModal.classList.remove("hidden");
  els.budgetAmountInput.focus();
});

els.closeRefillModalBtn.addEventListener("click", () => els.refillModal.classList.add("hidden"));
els.refillModal.addEventListener("click", (evt) => {
  if (evt.target === els.refillModal) els.refillModal.classList.add("hidden");
});

document.querySelectorAll("[data-budget-mode]").forEach((btn) => {
  btn.addEventListener("click", () => {
    setBudgetModalMode(btn.dataset.budgetMode || "refill");
    els.budgetAmountInput.focus();
  });
});

document.querySelectorAll("[data-quick-eur]").forEach((chip) => {
  chip.addEventListener("click", () => {
    els.budgetAmountInput.value = chip.dataset.quickEur || "";
    els.budgetAmountInput.focus();
  });
});

els.budgetRefillForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const cents = parseEuroInputToCents(els.budgetAmountInput.value);
  if (cents === null || (state.budgetModalMode !== "recalibrate" && cents <= 0)) {
    showToast("Montant invalide");
    return;
  }
  try {
    const updated = await budgetApiJson("/api/budget/refill", {
      method: "POST",
      body: JSON.stringify({
        mode: state.budgetModalMode,
        amount_cents: cents,
        merchant: els.budgetMerchantInput.value.trim(),
        note: els.budgetNoteInput.value.trim()
      })
    });
    state.budget = updated;
    els.refillModal.classList.add("hidden");
    renderBudget();
    const msg =
      state.budgetModalMode === "refill"
        ? `Refill ${formatCentsFr(cents, true)}`
        : state.budgetModalMode === "recalibrate"
        ? `Solde recalé à ${formatCentsFr(cents)}`
        : `Dépense ${formatCentsFr(-cents)}`;
    showToast(msg);
  } catch (err) {
    console.error(err);
    showToast("Erreur lors de l'enregistrement");
  }
});

// MacroDroid Config Modal
els.openMacrodroidBtn.addEventListener("click", () => {
  renderMacrodroidModal();
  els.macrodroidModal.classList.remove("hidden");
});

if (els.openMacrodroidFromSettingsBtn) {
  els.openMacrodroidFromSettingsBtn.addEventListener("click", () => {
    els.profileModal.classList.add("hidden");
    if (state.budgetLocked) {
      els.secBudget.classList.remove("hidden");
      els.secBudget.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    renderMacrodroidModal();
    els.macrodroidModal.classList.remove("hidden");
  });
}

els.closeMacrodroidModalBtn.addEventListener("click", () => els.macrodroidModal.classList.add("hidden"));
els.macrodroidModal.addEventListener("click", (evt) => {
  if (evt.target === els.macrodroidModal) els.macrodroidModal.classList.add("hidden");
});

els.copyWebhookUrlBtn.addEventListener("click", async () => {
  const url = `${window.location.origin}/api/budget/webhook/revolut`;
  try {
    await navigator.clipboard.writeText(url);
    showToast("URL webhook copiée");
  } catch {
    showToast(url);
  }
});

els.budgetSettingsForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  try {
    const updated = await budgetApiJson("/api/budget/settings", {
      method: "PATCH",
      body: JSON.stringify({
        joint_filter_keyword: els.budgetFilterKeywordInput.value.trim()
      })
    });
    state.budget = updated;
    renderBudget();
    showToast("Filtre enregistré");
  } catch (err) {
    console.error(err);
  }
});

// DUO_PIN Unlock Form
els.budgetPinForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const pin = els.budgetPinInput.value.trim();
  if (!pin) return;
  state.budgetPin = pin;
  try {
    const data = await budgetApiJson("/api/budget");
    localStorage.setItem("duotasks_duo_pin", pin);
    state.budget = data;
    state.budgetLocked = false;
    els.budgetPinInput.value = "";
    els.budgetPinError.classList.add("hidden");
    renderBudget();
    showToast("Compte joint déverrouillé");
  } catch (err) {
    state.budgetPin = "";
    localStorage.removeItem("duotasks_duo_pin");
    els.budgetPinError.classList.remove("hidden");
  }
});

if ("serviceWorker" in navigator) {
  const hadController = Boolean(navigator.serviceWorker.controller);
  let swReloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!hadController || swReloading) return;
    swReloading = true;
    window.location.reload();
  });
  navigator.serviceWorker
    .register("/sw.js", { updateViaCache: "none" })
    .then((reg) => {
      reg.update().catch(() => {});
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
          reg.update().catch(() => {});
        }
      });
    })
    .catch(() => {});
}

applyTheme(state.theme);
syncRecurringToggleUI();
syncCarouselUI();
refreshAll();
connectWebSocket();
refreshHealth();
