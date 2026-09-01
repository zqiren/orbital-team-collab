const ui = {
  activity: document.querySelector("#activity-list"),
  actor: document.querySelector("#actor-badge"),
  error: document.querySelector("#error-banner"),
  knowledge: document.querySelector("#knowledge-list"),
  overview: document.querySelector("#overview-content"),
  potentials: document.querySelector("#potential-list"),
  project: document.querySelector("#project-select"),
  questions: document.querySelector("#question-list"),
  status: document.querySelector("#refresh-status"),
  tasks: document.querySelector("#task-board"),
};
let snapshot = null;
let refreshing = false;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}

function clear(element) { element.replaceChildren(); }

function card(title, body) {
  const element = node("article", undefined, "card");
  element.append(node("h3", title), node("p", body, "meta"));
  return element;
}

function action(label, command, payload) {
  const button = node("button", label);
  button.type = "button";
  button.disabled = Boolean(snapshot?.access?.read_only);
  button.addEventListener("click", () => mutate(command, payload));
  return button;
}

function showError(message) {
  ui.error.textContent = message;
  ui.error.hidden = false;
}

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value?.error?.message || `HTTP ${response.status}`);
  return value;
}

async function mutate(command, payload) {
  try {
    await jsonFetch(`/api/projects/${encodeURIComponent(snapshot.project.slug)}/commands/${command}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    await refresh();
  } catch (error) { showError(error.message); }
}

function renderOverview() {
  clear(ui.overview);
  const manager = snapshot.manager;
  ui.overview.append(
    card(snapshot.project.display_name, `Manager: ${manager.active_manager_id}`),
    card("Members", `${snapshot.members.length} joined identities`),
    card("Integrations", `${snapshot.integrations.length} jobs · slot ${manager.slot_busy ? "busy" : "free"}`),
    card("Manager runner", `${manager.runner.runner}: ${manager.runner.detail}`),
    card("Local runs", `${snapshot.runs.length} records · sensitive local data`),
  );
  for (const job of snapshot.integrations.filter((item) => !["done", "changes_requested"].includes(item.state)).slice(0, 6)) {
    ui.overview.append(card(`Integration ${job.id}`, `${job.state} · Task ${job.task_id} · attempt ${job.attempt}`));
  }
  for (const run of snapshot.runs.slice(0, 4)) {
    const item = card(`Run ${run.id}`, `${run.actor} · ${run.state} · ${run.agent_type}`);
    const actions = node("div", undefined, "actions");
    for (const kind of ["stdout", "stderr", "transcript"]) {
      const button = node("button", `View ${kind}`);
      button.type = "button";
      button.disabled = !run.log_availability[kind];
      button.addEventListener("click", async () => {
        try {
          const result = await jsonFetch(`/api/projects/${snapshot.project.slug}/runs/${run.id}/logs/${kind}`);
          const pre = node("pre", result.available ? result.content : result.reason);
          item.append(pre);
        } catch (error) { showError(error.message); }
      });
      actions.append(button);
    }
    item.append(actions);
    ui.overview.append(item);
  }
}

function renderTasks() {
  clear(ui.tasks);
  const groups = [
    ["backlog", ["draft"]], ["ready", ["ready"]], ["claimed", ["claimed"]],
    ["in progress", ["in_progress"]], ["submitted", ["submitted"]],
    ["integrating", ["integrating"]], ["blocked", ["blocked", "changes_requested"]],
    ["done", ["done", "cancelled"]],
  ];
  for (const [label, states] of groups) {
    const column = node("div", undefined, "column");
    column.append(node("h3", label));
    const tasks = snapshot.tasks.filter((task) => states.includes(task.state));
    if (!tasks.length) column.append(node("p", "No tasks", "muted"));
    for (const task of tasks) {
      const item = card(task.title, `${task.id} · ${task.state} · ${task.assignee || "unassigned"}`);
      if (task.blocking_questions.length) item.append(node("p", `Blocked by ${task.blocking_questions.join(", ")}`, "warning"));
      item.append(node("p", `${task.report_ids.length} reports · ${task.integration_job_ids.length} integrations`, "meta"));
      if (task.state === "draft") {
        const actions = node("div", undefined, "actions");
        const edit = node("button", "Edit Draft");
        edit.type = "button";
        edit.disabled = Boolean(snapshot.access.read_only);
        edit.addEventListener("click", () => {
          const title = window.prompt("Draft Task title", task.title);
          if (title) mutate("task.edit", {task_id: task.id, title});
        });
        actions.append(edit);
        actions.append(action("Set Ready", "task.ready", {task_id: task.id}));
        item.append(actions);
      }
      column.append(item);
    }
    ui.tasks.append(column);
  }
}

function renderPotentials() {
  clear(ui.potentials);
  if (!snapshot.potential_tasks.length) ui.potentials.append(node("p", "No Potential Tasks", "muted"));
  for (const potential of snapshot.potential_tasks) {
    const item = card(potential.suggested_title, `${potential.id} · ${potential.state} · confidence ${potential.confidence}`);
    item.append(node("p", potential.summary));
    for (const evidence of potential.evidence) item.append(node("div", evidence.quote, "evidence"));
    if (["new", "triaged"].includes(potential.state)) {
      const actions = node("div", undefined, "actions");
      if (potential.state === "new") actions.append(action("Triage", "potential.triage", {potential_id: potential.id, note: "Reviewed in Team Dashboard"}));
      if (potential.state === "triaged") actions.append(action("Promote to Draft", "potential.promote", {potential_id: potential.id}));
      actions.append(action("Dismiss", "potential.dismiss", {potential_id: potential.id, reason: "Dismissed in Team Dashboard"}));
      const duplicate = node("button", "Mark Duplicate");
      duplicate.type = "button";
      duplicate.disabled = Boolean(snapshot.access.read_only);
      duplicate.addEventListener("click", () => {
        const target = window.prompt("Duplicate of Potential Task ID");
        if (target) mutate("potential.duplicate", {potential_id: potential.id, duplicate_of: target});
      });
      const convert = node("button", "Convert to Question");
      convert.type = "button";
      convert.disabled = Boolean(snapshot.access.read_only);
      convert.addEventListener("click", () => {
        const question = window.prompt("Open Question text", potential.suggested_title);
        if (question) mutate("potential.question", {potential_id: potential.id, owner: `human:${snapshot.manager.active_manager_id}`, question});
      });
      actions.append(duplicate, convert);
      item.append(actions);
    }
    ui.potentials.append(item);
  }
}

function renderQuestions() {
  clear(ui.questions);
  if (!snapshot.open_questions.length) ui.questions.append(node("p", "No Open Questions", "muted"));
  for (const question of snapshot.open_questions) {
    const item = card(question.question, `${question.id} · ${question.state} · owner ${question.owner}`);
    if (question.blocking) item.append(node("p", "Blocking related work", "warning"));
    item.append(node("p", `Tasks: ${question.related.task_ids.join(", ") || "none"}`, "meta"));
    const actions = node("div", undefined, "actions");
    if (["open", "deferred"].includes(question.state)) actions.append(action("Answer", "question.answer", {question_id: question.id, answer: "Answered in Team Dashboard"}));
    if (question.state === "open") actions.append(action("Defer", "question.defer", {question_id: question.id, reason: "Deferred in Team Dashboard"}));
    if (question.state === "deferred") actions.append(action("Reopen", "question.reopen", {question_id: question.id, reason: "Reopened in Team Dashboard"}));
    if (["answered", "deferred"].includes(question.state)) actions.append(action("Close", "question.close", {question_id: question.id, reason: "Closed in Team Dashboard"}));
    item.append(actions);
    ui.questions.append(item);
  }
}

function renderActivity() {
  clear(ui.activity); clear(ui.knowledge);
  for (const event of [...snapshot.activity].reverse().slice(0, 80)) {
    const item = node("li");
    item.append(node("strong", event.type), document.createTextNode(` — ${event.actor} · ${event.timestamp}`));
    ui.activity.append(item);
  }
  if (!snapshot.knowledge.length) ui.knowledge.append(node("p", "No knowledge summaries", "muted"));
  for (const summary of snapshot.knowledge) {
    const item = card(summary.summary_id, `${summary.applied_at} · ${summary.changes.length} changes`);
    for (const change of summary.changes) {
      item.append(node("p", `${change.operation} ${change.path}: ${change.summary}`));
      if (change.preview.available) item.append(node("pre", change.preview.content));
    }
    ui.knowledge.append(item);
  }
}

function render() {
  ui.error.hidden = true;
  ui.actor.textContent = `${snapshot.access.actor || "unknown actor"} · ${snapshot.access.read_only ? "read-only" : "write enabled"}`;
  document.querySelector('#question-form [name="owner"]').value = `human:${snapshot.manager.active_manager_id}`;
  document.querySelectorAll("form button, form input, form textarea").forEach((element) => { element.disabled = snapshot.access.read_only; });
  renderOverview(); renderTasks(); renderPotentials(); renderQuestions(); renderActivity();
  if (snapshot.errors.length) showError(snapshot.errors.map((item) => item.message).join(" "));
  ui.status.textContent = `Projection ${snapshot.projection_revision.slice(0, 10)} · polled every 2 seconds`;
}

async function refresh() {
  if (refreshing || !ui.project.value) return;
  refreshing = true;
  try {
    const next = await jsonFetch(`/api/projects/${encodeURIComponent(ui.project.value)}`);
    snapshot = next;
    render();
  } catch (error) {
    showError(`Runtime projection failed: ${error.message}. Existing view was preserved.`);
    ui.status.textContent = "Refresh failed; runtime files were not modified.";
  } finally { refreshing = false; }
}

document.querySelector("#task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  await mutate("task.create", {title: data.get("title"), description: data.get("description"), acceptance_criteria: data.get("acceptance") ? [data.get("acceptance")] : []});
  event.currentTarget.reset();
});
document.querySelector("#question-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  await mutate("question.add", {question: data.get("question"), owner: data.get("owner"), blocking: data.get("blocking") === "on", task_ids: data.get("task_id") ? [data.get("task_id")] : []});
});
ui.project.addEventListener("change", refresh);

async function start() {
  try {
    const bootstrap = await jsonFetch("/api/bootstrap");
    for (const project of bootstrap.projects) {
      const option = node("option", project.display_name);
      option.value = project.slug;
      ui.project.append(option);
    }
    if (!bootstrap.projects.length) {
      ui.status.textContent = "No projects in the shared runtime.";
      return;
    }
    await refresh();
    window.setInterval(refresh, 2000);
  } catch (error) { showError(error.message); }
}
start();
