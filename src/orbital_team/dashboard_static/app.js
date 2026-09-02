/* ----------------------------------------------------------------- i18n
   Mirrors Orbital's locale contract: 'en' | 'zh', localStorage wins, a zh*
   browser language falls back to zh, and any missing key falls back to en. */
const STRINGS = {
  "skip": {en: "Skip to dashboard content", zh: "跳到仪表盘内容"},
  "brand": {en: "Team Workspace", zh: "团队工作区"},
  "projects": {en: "Projects", zh: "项目"},
  "localOnly": {en: "Local-only data.", zh: "仅限本地数据。"},
  "localOnlyBody": {en: "Run logs and optional transcripts stay in the private local runtime and are never committed to Git.", zh: "运行日志与可选转录保存在私有本地运行时中，绝不会提交到 Git。"},
  "tab.board": {en: "Board", zh: "看板"},
  "tab.inbox": {en: "Inbox", zh: "收件箱"},
  "tab.questions": {en: "Questions", zh: "问题"},
  "tab.files": {en: "Files", zh: "文件"},
  "tab.activity": {en: "Activity", zh: "动态"},
  "tab.settings": {en: "Settings", zh: "设置"},
  "board.intro": {en: "Tasks move left to right. Drag a Backlog card onto Ready to release it to the agents, or click any card for details — every other move is made by the agents themselves.", zh: "任务从左向右流转。将「待办」卡片拖到「就绪」列即可释放给智能体认领，点击卡片查看详情——其余流转均由智能体自行完成。"},
  "board.newTask": {en: "New draft task", zh: "新建草稿任务"},
  "form.title": {en: "Title", zh: "标题"},
  "form.titlePh": {en: "What needs to happen?", zh: "需要完成什么？"},
  "form.description": {en: "Description", zh: "描述"},
  "form.descriptionPh": {en: "Optional context for the member who claims it", zh: "给认领成员的补充说明（可选）"},
  "form.acceptance": {en: "Acceptance criterion", zh: "验收标准"},
  "form.acceptancePh": {en: "Optional — one observable outcome", zh: "可选——一条可观察的结果"},
  "form.addToBacklog": {en: "Add to Backlog", zh: "加入 Backlog"},
  "form.cancel": {en: "Cancel", zh: "取消"},
  "form.question": {en: "Question", zh: "问题"},
  "form.questionPh": {en: "What must be decided?", zh: "需要决定什么？"},
  "form.owner": {en: "Owner", zh: "负责人"},
  "form.relatedTask": {en: "Related Task ID", zh: "关联任务 ID"},
  "form.blocking": {en: "Blocking", zh: "阻塞"},
  "form.addQuestion": {en: "Add question", zh: "添加问题"},
  "inbox.intro": {en: "Evidence-backed candidates captured from IM context. Triage, then promote to a Draft Task, convert to a question, or dismiss — nothing here starts work by itself.", zh: "从 IM 上下文捕获、带证据的候选任务。先分诊，再提升为草稿任务、转为问题或忽略——这里的内容不会自动开工。"},
  "questions.intro": {en: "Blocking questions hold their related Tasks in place until answered. Type an answer directly on the card.", zh: "阻塞性问题会挂起关联任务，直到得到回答。可直接在卡片上输入答案。"},
  "files.intro": {en: "Read-only view of the canonical workspace — the code and the orbital/ project memory that agents merge into.", zh: "canonical 工作区的只读视图——智能体合并代码与 orbital/ 项目记忆的地方。"},
  "files.refresh": {en: "Refresh", zh: "刷新"},
  "files.empty": {en: "No files in the canonical workspace.", zh: "canonical 工作区中没有文件。"},
  "files.emptyDir": {en: "empty", zh: "空目录"},
  "files.select": {en: "Select a file to preview it.", zh: "选择一个文件进行预览。"},
  "files.truncated": {en: "truncated at 64 KB", zh: "已截断至 64 KB"},
  "files.unavailable": {en: "File preview unavailable.", zh: "无法预览此文件。"},
  "activity.feed": {en: "Activity feed", zh: "动态时间线"},
  "activity.knowledge": {en: "Knowledge changes", zh: "知识变更"},
  "activity.runs": {en: "Manager runs", zh: "Manager 运行记录"},
  "col.backlog": {en: "Backlog", zh: "待办"},
  "col.ready": {en: "Ready", zh: "就绪"},
  "col.inprogress": {en: "In Progress", zh: "进行中"},
  "col.inreview": {en: "In Review", zh: "审核中"},
  "col.blocked": {en: "Blocked", zh: "已阻塞"},
  "col.done": {en: "Done", zh: "已完成"},
  "state.draft": {en: "draft", zh: "草稿"},
  "state.ready": {en: "ready", zh: "就绪"},
  "state.claimed": {en: "claimed", zh: "已认领"},
  "state.in_progress": {en: "in progress", zh: "进行中"},
  "state.submitted": {en: "submitted", zh: "已提交"},
  "state.integrating": {en: "integrating", zh: "集成中"},
  "state.blocked": {en: "blocked", zh: "已阻塞"},
  "state.changes_requested": {en: "changes requested", zh: "需修改"},
  "state.done": {en: "done", zh: "已完成"},
  "state.cancelled": {en: "cancelled", zh: "已取消"},
  "state.open": {en: "open", zh: "待解决"},
  "state.answered": {en: "answered", zh: "已回答"},
  "state.closed": {en: "closed", zh: "已关闭"},
  "state.deferred": {en: "deferred", zh: "已搁置"},
  "state.new": {en: "new", zh: "新"},
  "state.triaged": {en: "triaged", zh: "已分诊"},
  "state.promoted": {en: "promoted", zh: "已提升"},
  "state.dismissed": {en: "dismissed", zh: "已忽略"},
  "state.duplicate": {en: "duplicate", zh: "重复"},
  "state.queued": {en: "queued", zh: "排队中"},
  "state.running": {en: "running", zh: "运行中"},
  "state.failed": {en: "failed", zh: "失败"},
  "project.meta": {en: "{slug} · {members} members · {jobs} integration jobs · runner {runner}", zh: "{slug} · {members} 名成员 · {jobs} 个集成任务 · runner {runner}"},
  "project.pending": {en: " · {n} pending", zh: " · {n} 个待处理"},
  "manager.idle": {en: " · idle", zh: " · 空闲"},
  "manager.integrating": {en: " · integrating", zh: " · 集成中"},
  "agent.member": {en: "member", zh: "成员"},
  "agent.manager": {en: "manager", zh: "管理者"},
  "agent.idle": {en: "idle", zh: "空闲"},
  "agent.workingOn": {en: "working on", zh: "正在处理"},
  "agent.awaiting": {en: "awaiting integration of", zh: "等待集成"},
  "agent.integratingReport": {en: "integrating a report", zh: "正在集成报告"},
  "agent.runnerIdle": {en: "{runner} runner · idle", zh: "{runner} runner · 空闲"},
  "actor.write": {en: "write enabled", zh: "可写"},
  "actor.readonly": {en: "read-only", zh: "只读"},
  "actor.unknown": {en: "unknown actor", zh: "未知身份"},
  "status.live": {en: "Live · projection {rev} · polls every 2s", zh: "实时 · 投影 {rev} · 每 2 秒轮询"},
  "status.failed": {en: "Refresh failed; runtime files were not modified.", zh: "刷新失败；运行时文件未被修改。"},
  "status.noProjects": {en: "No projects in the shared runtime.", zh: "共享运行时中没有项目。"},
  "error.refresh": {en: "Runtime projection failed: {msg}. Existing view was preserved.", zh: "运行时投影失败：{msg}。当前视图已保留。"},
  "empty.column": {en: "Empty", zh: "空"},
  "empty.inbox": {en: "Nothing captured from IM context yet.", zh: "尚未从 IM 上下文捕获任何内容。"},
  "empty.questions": {en: "No open questions. Blocked tasks will point here when one appears.", zh: "没有待解决的问题。出现阻塞时，任务会指向这里。"},
  "empty.knowledge": {en: "No knowledge summaries yet.", zh: "暂无知识摘要。"},
  "empty.runs": {en: "No manager runs recorded.", zh: "暂无 Manager 运行记录。"},
  "card.blockedBy": {en: "Blocked by", zh: "被阻塞于"},
  "card.counts": {en: "{r} reports · {i} integrations", zh: "{r} 份报告 · {i} 次集成"},
  "card.edit": {en: "Edit", zh: "编辑"},
  "card.setReady": {en: "Set Ready", zh: "设为就绪"},
  "card.promotedTo": {en: "Promoted to {id}", zh: "已提升为 {id}"},
  "card.confidence": {en: "confidence", zh: "置信度"},
  "inbox.triage": {en: "Triage", zh: "分诊"},
  "inbox.promote": {en: "Promote to Draft Task", zh: "提升为草稿任务"},
  "inbox.convert": {en: "Convert to Question", zh: "转为问题"},
  "inbox.duplicate": {en: "Mark Duplicate", zh: "标记重复"},
  "inbox.dismiss": {en: "Dismiss", zh: "忽略"},
  "q.owner": {en: "Owner {owner}", zh: "负责人 {owner}"},
  "q.holds": {en: "Holds {tasks}", zh: "挂起 {tasks}"},
  "q.noTasks": {en: "No related tasks", zh: "无关联任务"},
  "q.blockingWork": {en: "Blocking related work", zh: "阻塞相关工作"},
  "q.answerPh": {en: "Type the decision or answer…", zh: "输入决定或答案…"},
  "q.answer": {en: "Answer", zh: "回答"},
  "q.answerPrefix": {en: "Answer: {answer}", zh: "答案：{answer}"},
  "q.defer": {en: "Defer", zh: "搁置"},
  "q.reopen": {en: "Reopen", zh: "重新打开"},
  "q.close": {en: "Close", zh: "关闭"},
  "k.showPreview": {en: "Show preview", zh: "显示预览"},
  "k.hidePreview": {en: "Hide preview", zh: "隐藏预览"},
  "k.changes": {en: "{n} changes", zh: "{n} 项变更"},
  "run.sensitive": {en: "Sensitive local data — logs never leave this machine.", zh: "敏感本地数据——日志不会离开本机。"},
  "run.view": {en: "View {kind}", zh: "查看 {kind}"},
  "run.hide": {en: "Hide {kind}", zh: "隐藏 {kind}"},
  "run.task": {en: "task {id}", zh: "任务 {id}"},
  "drawer.description": {en: "Description", zh: "描述"},
  "drawer.acceptance": {en: "Acceptance criteria", zh: "验收标准"},
  "drawer.details": {en: "Details", zh: "详情"},
  "drawer.assignee": {en: "Assignee", zh: "指派给"},
  "drawer.branch": {en: "Branch", zh: "分支"},
  "drawer.labels": {en: "Labels", zh: "标签"},
  "drawer.paths": {en: "Paths", zh: "路径"},
  "drawer.created": {en: "Created", zh: "创建于"},
  "drawer.updated": {en: "Updated", zh: "更新于"},
  "drawer.blocking": {en: "Blocking questions", zh: "阻塞问题"},
  "drawer.reports": {en: "Reports", zh: "报告"},
  "drawer.integrations": {en: "Integration jobs", zh: "集成任务"},
  "drawer.none": {en: "none", zh: "无"},
  "drawer.unassigned": {en: "unassigned", zh: "未指派"},
  "prompt.editTitle": {en: "Draft Task title", zh: "草稿任务标题"},
  "prompt.duplicateOf": {en: "Duplicate of Potential Task ID", zh: "重复于哪个候选任务 ID"},
  "prompt.questionText": {en: "Open Question text", zh: "问题内容"},
  "time.justNow": {en: "just now", zh: "刚刚"},
  "time.mAgo": {en: "{m}m ago", zh: "{m} 分钟前"},
  "time.hAgo": {en: "{h}h ago", zh: "{h} 小时前"},
  "onboard.memberId": {en: "Member ID", zh: "成员 ID"},
  "onboard.agentType": {en: "Agent", zh: "智能体"},
  "onboard.copied": {en: "Copied!", zh: "已复制！"},
  "settings.intro": {en: "Team roster and agent setup. Copy a setup message, paste it into an agent session, and the agent configures itself and then briefs you on how to work with it.", zh: "团队名册与智能体设置。复制设置消息并粘贴到智能体会话中，智能体会完成自身配置，然后向你说明如何与它协作。"},
  "settings.members": {en: "Members", zh: "成员"},
  "settings.managerTitle": {en: "Management agent", zh: "管理智能体"},
  "settings.managerHint": {en: "Start an agent session in the canonical workspace on this machine and paste this message. The agent adopts the manager role, inspects the team state, then briefs you on how to run the project with it.", zh: "在本机 canonical 工作区中启动智能体会话并粘贴此消息。智能体将担任管理者角色、检查团队状态，然后向你说明如何与它一起运营该项目。"},
  "settings.memberTitle": {en: "Member agent", zh: "成员智能体"},
  "settings.memberHint": {en: "Pick an ID for the new member, then paste this message into a fresh agent session on this machine. The agent creates the worktree, binds the member identity, installs the /team adapter, and briefs the member on the workflow.", zh: "为新成员选择一个 ID，然后将此消息粘贴到本机的全新智能体会话中。智能体会创建 worktree、绑定成员身份、安装 /team 适配器，并向成员说明工作流程。"},
  "settings.copy": {en: "Copy message", zh: "复制消息"},
  "member.meta": {en: "branch {branch} · joined {when}", zh: "分支 {branch} · 加入于 {when}"},
  "create.open": {en: "+ New project", zh: "+ 新建项目"},
  "create.title": {en: "New project", zh: "新建项目"},
  "create.workspace": {en: "Project folder", zh: "项目文件夹"},
  "create.workspacePh": {en: "/absolute/path/to/folder", zh: "/文件夹的绝对路径"},
  "create.browse": {en: "Browse", zh: "浏览"},
  "create.name": {en: "Project name", zh: "项目名称"},
  "create.gitNote": {en: "Not a Git repository yet — one will be initialized here and the current contents committed locally.", zh: "该文件夹还不是 Git 仓库——将在此初始化仓库，并在本地提交现有内容。"},
  "create.submit": {en: "Create project", zh: "创建项目"},
  "create.creating": {en: "Creating…", zh: "创建中…"},
  "create.useFolder": {en: "Use this folder", zh: "使用此文件夹"},
  "create.newFolder": {en: "New folder", zh: "新建文件夹"},
  "create.newFolderPh": {en: "folder-name", zh: "文件夹名称"},
  "create.recent": {en: "Recent", zh: "最近"},
  "create.emptyDir": {en: "No subfolders", zh: "没有子文件夹"},
  "create.errWorkspace": {en: "Project folder is required.", zh: "必须填写项目文件夹。"},
  "create.errAbsolute": {en: "Folder path must be absolute.", zh: "文件夹路径必须是绝对路径。"},
  "create.errName": {en: "Project name is required.", zh: "必须填写项目名称。"},
  "shortcut.home": {en: "Home", zh: "主目录"},
  "shortcut.desktop": {en: "Desktop", zh: "桌面"},
  "shortcut.documents": {en: "Documents", zh: "文稿"},
  "shortcut.downloads": {en: "Downloads", zh: "下载"},
  "note.triaged": {en: "Reviewed in Team Dashboard", zh: "已在团队仪表盘中审阅"},
  "note.dismissed": {en: "Dismissed in Team Dashboard", zh: "已在团队仪表盘中忽略"},
  "note.deferred": {en: "Deferred in Team Dashboard", zh: "已在团队仪表盘中搁置"},
  "note.reopened": {en: "Reopened in Team Dashboard", zh: "已在团队仪表盘中重新打开"},
  "note.closed": {en: "Closed in Team Dashboard", zh: "已在团队仪表盘中关闭"},
};

function readInitialLocale() {
  try {
    const saved = localStorage.getItem("orbital-team-locale");
    if (saved === "en" || saved === "zh") return saved;
  } catch { /* storage unavailable */ }
  return (navigator.language || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}

let locale = readInitialLocale();

function t(key, vars) {
  const entry = STRINGS[key];
  let text = (entry && (entry[locale] || entry.en)) || key;
  if (vars) for (const [name, value] of Object.entries(vars)) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}

/* -------------------------------------------------------------------- refs */
const ui = {
  activity: document.querySelector("#activity-list"),
  actor: document.querySelector("#actor-badge"),
  composer: document.querySelector("#task-form"),
  composerCancel: document.querySelector("#composer-cancel"),
  composerToggle: document.querySelector("#composer-toggle"),
  createBackdrop: document.querySelector("#create-backdrop"),
  createBrowse: document.querySelector("#create-browse"),
  createCancel: document.querySelector("#create-cancel"),
  createClose: document.querySelector("#create-close"),
  createError: document.querySelector("#create-error"),
  createForm: document.querySelector("#create-form"),
  createGitNote: document.querySelector("#create-git-note"),
  createName: document.querySelector("#create-name"),
  createSubmit: document.querySelector("#create-submit"),
  createWorkspace: document.querySelector("#create-workspace"),
  drawer: document.querySelector("#task-drawer"),
  fbCrumbs: document.querySelector("#fb-crumbs"),
  fbList: document.querySelector("#fb-list"),
  fbNewName: document.querySelector("#fb-newfolder-name"),
  fbNewMake: document.querySelector("#fb-newfolder-make"),
  fbRecent: document.querySelector("#fb-recent"),
  fbShortcuts: document.querySelector("#fb-shortcuts"),
  fbUse: document.querySelector("#fb-use"),
  folderBrowser: document.querySelector("#folder-browser"),
  drawerBody: document.querySelector("#drawer-body"),
  drawerClose: document.querySelector("#drawer-close"),
  drawerTitle: document.querySelector("#drawer-title"),
  error: document.querySelector("#error-banner"),
  filePreview: document.querySelector("#file-preview"),
  fileTree: document.querySelector("#file-tree"),
  filesRefresh: document.querySelector("#files-refresh"),
  inboxCount: document.querySelector("#inbox-count"),
  knowledge: document.querySelector("#knowledge-list"),
  langEn: document.querySelector("#lang-en"),
  langZh: document.querySelector("#lang-zh"),
  managerChip: document.querySelector("#manager-chip"),
  managerCopy: document.querySelector("#manager-copy"),
  managerMessage: document.querySelector("#manager-message"),
  memberList: document.querySelector("#member-list"),
  onboardAgent: document.querySelector("#onboard-agent"),
  onboardCommand: document.querySelector("#onboard-command"),
  onboardCopy: document.querySelector("#onboard-copy"),
  onboardMember: document.querySelector("#onboard-member"),
  potentials: document.querySelector("#potential-list"),
  projectList: document.querySelector("#project-list"),
  projectMeta: document.querySelector("#project-meta"),
  projectNew: document.querySelector("#project-new"),
  projectTitle: document.querySelector("#project-title"),
  questionCount: document.querySelector("#question-count"),
  questionForm: document.querySelector("#question-form"),
  questions: document.querySelector("#question-list"),
  runs: document.querySelector("#run-list"),
  status: document.querySelector("#refresh-status"),
  tasks: document.querySelector("#task-board"),
};

const TABS = ["board", "inbox", "questions", "files", "activity", "settings"];

// Board columns group runtime states into the stages a teammate actually
// scans for; cards keep their exact state as a pill when a column merges two.
const COLUMNS = [
  ["col.backlog", ["draft"]],
  ["col.ready", ["ready"]],
  ["col.inprogress", ["claimed", "in_progress"]],
  ["col.inreview", ["submitted", "integrating"]],
  ["col.blocked", ["blocked", "changes_requested"]],
  ["col.done", ["done", "cancelled"]],
];

const STATE_TONE = {
  blocked: "pill-error",
  cancelled: "",
  changes_requested: "pill-error",
  claimed: "pill-accent",
  draft: "",
  done: "pill-success",
  in_progress: "pill-success",
  integrating: "pill-warning",
  ready: "pill-accent",
  submitted: "pill-warning",
};

let snapshot = null;
let refreshing = false;
let projects = [];
let currentProject = null;
let currentTab = "board";
let dragTaskId = null;
let openTaskId = null;
const answerDrafts = new Map();
const openLogs = new Map();
const filesState = {content: null, expanded: new Set(), listings: new Map(), loaded: false, selected: null};

/* ----------------------------------------------------------------- helpers */
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}

const SVG_NS = "http://www.w3.org/2000/svg";

function icon(kind) {
  const shapes = {
    chevron: ["M6 4l4 4-4 4"],
    file: ["M4 1.5h4.8L12 4.7V14.5H4z", "M8.8 1.5v3.2H12"],
    folder: ["M1.8 5A1.3 1.3 0 013.1 3.7h2.7l1.4 1.7h5.7A1.3 1.3 0 0114.2 6.7v4.6a1.3 1.3 0 01-1.3 1.3H3.1a1.3 1.3 0 01-1.3-1.3z"],
  };
  const element = document.createElementNS(SVG_NS, "svg");
  element.setAttribute("viewBox", "0 0 16 16");
  element.setAttribute("fill", "none");
  element.setAttribute("stroke", "currentColor");
  element.setAttribute("stroke-width", "1.4");
  element.setAttribute("stroke-linecap", "round");
  element.setAttribute("stroke-linejoin", "round");
  element.classList.add(kind === "chevron" ? "chevron" : "glyph");
  for (const d of shapes[kind]) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    element.append(path);
  }
  return element;
}

function clear(element) { element.replaceChildren(); }

function readOnly() { return Boolean(snapshot?.access?.read_only); }

function button(label, className, onClick) {
  const element = node("button", label, className || "btn");
  element.type = "button";
  element.disabled = readOnly();
  element.addEventListener("click", onClick);
  return element;
}

function action(label, command, payload) {
  return button(label, "btn", () => mutate(command, payload));
}

function pill(state) {
  return node("span", t(`state.${state}`), `pill ${STATE_TONE[state] || ""}`.trim());
}

function avatar(name, className) {
  return node("span", (name || "?").slice(0, 1).toUpperCase(), className || "agent-avatar");
}

function relativeTime(timestamp) {
  const then = new Date(timestamp).getTime();
  if (Number.isNaN(then)) return timestamp;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return t("time.justNow");
  if (seconds < 3600) return t("time.mAgo", {m: Math.floor(seconds / 60)});
  if (seconds < 86400) return t("time.hAgo", {h: Math.floor(seconds / 3600)});
  return new Date(then).toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US");
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
    await refresh(true);
  } catch (error) { showError(error.message); }
}

/* ------------------------------------------------------------------ locale */
function applyStatic() {
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  ui.langEn.setAttribute("aria-pressed", String(locale === "en"));
  ui.langZh.setAttribute("aria-pressed", String(locale === "zh"));
}

function setLocale(next) {
  if (next === locale) return;
  locale = next;
  try { localStorage.setItem("orbital-team-locale", next); } catch { /* per-viewer convenience only */ }
  applyStatic();
  if (snapshot) render();
  renderFiles();
}

/* ------------------------------------------------------------ tab switching */
function selectTab(name) {
  currentTab = name;
  for (const tab of TABS) {
    document.querySelector(`#tab-${tab}`).setAttribute("aria-selected", String(tab === name));
    document.querySelector(`#panel-${tab}`).hidden = tab !== name;
  }
  if (name === "files") activateFiles();
}

/* ------------------------------------------------------------- project list */
function activateProject(slug) {
  currentProject = slug;
  const url = new URL(window.location.href);
  url.searchParams.set("project", currentProject);
  window.history.replaceState(null, "", url);
  filesState.listings.clear();
  filesState.expanded.clear();
  filesState.loaded = false;
  filesState.selected = null;
  filesState.content = null;
  openTaskId = null;
  ui.drawer.hidden = true;
  renderProjectList();
  renderFiles();
  refresh(true);
}

function renderProjectList() {
  clear(ui.projectList);
  for (const project of projects) {
    const item = node("li");
    const row = node("button", undefined, "project-row");
    row.type = "button";
    row.setAttribute("aria-current", String(project.slug === currentProject));
    if (project.workspace) row.title = project.workspace;
    row.append(avatar(project.display_name, "project-avatar"));
    const text = node("span");
    text.append(node("span", project.display_name), node("span", project.slug, "slug"));
    row.append(text);
    row.addEventListener("click", () => {
      if (project.slug === currentProject) return;
      activateProject(project.slug);
    });
    item.append(row);
    ui.projectList.append(item);
  }
}

/* ------------------------------------------------------------ project header */
function renderHeader() {
  const manager = snapshot.manager;
  ui.projectTitle.textContent = snapshot.project.display_name;
  ui.projectMeta.textContent =
    t("project.meta", {
      jobs: snapshot.integrations.length,
      members: snapshot.members.length,
      runner: manager.runner.runner,
      slug: snapshot.project.slug,
    }) + (manager.pending_jobs ? t("project.pending", {n: manager.pending_jobs}) : "");

  clear(ui.managerChip);
  const dot = node("span", undefined, "dot status-dot");
  if (manager.slot_busy) dot.classList.add("busy");
  const label = node("span");
  label.append(node("strong", `manager:${manager.active_manager_id}`));
  label.append(document.createTextNode(manager.slot_busy ? t("manager.integrating") : t("manager.idle")));
  ui.managerChip.append(dot, label);
  ui.managerChip.title = manager.runner.detail;
}

/* ----------------------------------------------------------------- members */
function memberStatus(member) {
  const working = snapshot.tasks.find((task) =>
    task.assignee === member.id && ["claimed", "in_progress"].includes(task.state));
  if (working) return {dot: "working", ref: working.id, text: t("agent.workingOn")};
  const reviewing = snapshot.tasks.find((task) =>
    task.assignee === member.id && ["submitted", "integrating"].includes(task.state));
  if (reviewing) return {dot: "busy", ref: reviewing.id, text: t("agent.awaiting")};
  return {dot: "", ref: null, text: t("agent.idle")};
}

function renderMembers() {
  clear(ui.memberList);
  for (const member of snapshot.members) {
    const chip = node("div", undefined, "agent-chip");
    chip.append(avatar(member.id));
    const text = node("div");
    text.append(node("div", `${member.id} · ${member.agent_type}`, "agent-name"));
    const status = memberStatus(member);
    const sub = node("div", undefined, "agent-sub");
    sub.append(node("span", undefined, `status-dot ${status.dot}`.trim()), node("span", status.text));
    if (status.ref) sub.append(node("span", status.ref, "task-ref"));
    text.append(sub);
    text.append(node("div", t("member.meta", {branch: member.branch, when: relativeTime(member.joined_at)}), "agent-sub"));
    chip.append(text);
    ui.memberList.append(chip);
  }
  const manager = snapshot.manager;
  const chip = node("div", undefined, "agent-chip is-manager");
  chip.append(avatar(manager.active_manager_id));
  const text = node("div");
  text.append(node("div", `${manager.active_manager_id} · ${t("agent.manager")}`, "agent-name"));
  const sub = node("div", undefined, "agent-sub");
  sub.append(
    node("span", undefined, `status-dot ${manager.slot_busy ? "busy" : ""}`.trim()),
    node("span", manager.slot_busy ? t("agent.integratingReport") : t("agent.runnerIdle", {runner: manager.runner.runner})),
  );
  text.append(sub);
  chip.append(text);
  ui.memberList.append(chip);
}

/* ---------------------------------------------------------- setup messages
   Agent-facing prompts pasted into an interactive session. Kept in English so
   the same message works for every agent type; each one ends by telling the
   agent to brief the human before doing anything else. */
function managerSetupMessage() {
  const project = snapshot?.project || {};
  const canonical = project.canonical_workspace || "<canonical-workspace>";
  const slug = project.slug || "<project>";
  const name = project.display_name || slug;
  const skill = snapshot?.manager_skill
    ? `"${snapshot.manager_skill}"`
    : `skills/orbital-team-manager/SKILL.md inside the workspace`;
  return [
    `You are the management agent for the Orbital Team project "${name}" (${slug}).`,
    ``,
    `Set up:`,
    `1. Work from the canonical workspace: cd "${canonical}" — every command below runs from there.`,
    `2. Read the Manager Skill at ${skill} and treat it as your contract for integration and knowledge compilation.`,
    `3. Inspect the current state: run \`teamctl status\` and \`teamctl manager inbox --project ${slug}\`.`,
    ``,
    `How you operate:`,
    `- List pending reports and jobs with \`teamctl manager inbox --project ${slug}\`; open one with \`teamctl manager review <job-id>\`.`,
    `- Integrate approved work only through the guarded merge: \`teamctl manager merge <job-id> --expected-head <commit> --validation '<json>'\`.`,
    `- Send work back with \`teamctl manager request-changes <job-id> --change <text>\`, or block on a decision with \`teamctl manager block <job-id> --reason <text> --question <text>\`.`,
    `- After a merge, compile durable knowledge with \`teamctl manager knowledge propose|validate|apply\` as the Skill directs.`,
    `- Never run raw \`git merge/commit/push\`; state changes only through the guarded commands.`,
    ``,
    `When setup is complete, before doing anything else, brief the user in plain language: what this project is, the current team and task state, what you will handle for them, and what they still own (answering Open Questions and releasing tasks to Ready in the dashboard). Keep the briefing short, then wait for instructions.`,
  ].join("\n") + briefingLanguageLine();
}

function memberSetupMessage() {
  const memberId = ui.onboardMember.value.trim() || "<member-id>";
  const agent = ui.onboardAgent.value;
  const project = snapshot?.project || {};
  const canonical = project.canonical_workspace || "<canonical-workspace>";
  const slug = project.slug || "<project>";
  const name = project.display_name || slug;
  const parent = canonical.includes("/") ? canonical.split("/").slice(0, -1).join("/") : canonical;
  const worktree = `${parent}/${memberId}`;
  const adapterAgent = agent === "claude-code" ? "claude-code" : "generic";
  const installer = snapshot?.member_installer
    ? `python3 "${snapshot.member_installer}" --agent ${adapterAgent} --target . --mode copy`
    : `python3 skills/orbital-team-member/scripts/install_adapter.py --agent ${adapterAgent} --target . --mode copy  # installer lives in the orbital-team checkout`;
  return [
    `You are joining the Orbital Team project "${name}" (${slug}) as member "${memberId}" (agent type ${agent}).`,
    ``,
    `Run these commands to create the worktree and bind this member identity:`,
    `git -C "${canonical}" worktree add -b member/${memberId} "${worktree}"`,
    `cd "${worktree}"`,
    `teamctl member join --project ${slug} --member ${memberId} --agent ${agent}`,
    installer,
    ``,
    `Verify the setup with \`teamctl task status\` from the worktree.`,
    ``,
    `When setup is complete, brief the user in plain language: confirm the member identity and branch; tell them to start future agent sessions from "${worktree}" so the /team command and session hook are active; and walk them through the workflow — check \`/team status\` and \`/team questions ${slug}\`, claim one Ready task with \`/team claim ${slug} <task>\`, enter work with \`/team start <task-id>\`, commit locally on branch member/${memberId}, submit with \`/team report <task-id>\`, and raise blockers with \`/team block <task-id> <reason>\`. Members never merge or push; the manager integrates reports. Keep the briefing short, then wait for instructions.`,
  ].join("\n") + briefingLanguageLine();
}

function briefingLanguageLine() {
  // The setup prompt stays English for every agent type, but the briefing is
  // for the human — ask for it in the dashboard's language.
  return locale === "zh" ? "\n\n请用中文向用户进行上述说明。" : "";
}

function setPre(element, text) {
  // Leave the DOM alone when unchanged so polling doesn't clear a selection.
  if (element.textContent !== text) element.textContent = text;
}

function renderSetup() {
  setPre(ui.managerMessage, managerSetupMessage());
  setPre(ui.onboardCommand, memberSetupMessage());
}

/* -------------------------------------------------------------------- board */
function taskCard(task) {
  const card = node("article", undefined, "card");
  if (["done", "cancelled"].includes(task.state)) card.classList.add("is-muted");

  const top = node("div", undefined, "card-top");
  top.append(pill(task.state), node("span", task.id, "card-id"));
  card.append(top, node("h4", task.title, "card-title"));

  if (task.assignee) {
    const who = node("span", undefined, "assignee");
    who.append(avatar(task.assignee), node("span", task.assignee));
    card.append(who);
  }

  for (const questionId of task.blocking_questions) {
    const note = node("span", undefined, "blocked-note");
    note.append(node("span", t("card.blockedBy")));
    const jump = node("button", questionId);
    jump.type = "button";
    jump.addEventListener("click", () => selectTab("questions"));
    note.append(jump);
    card.append(note);
  }

  if (task.report_ids.length || task.integration_job_ids.length) {
    card.append(node("p",
      t("card.counts", {i: task.integration_job_ids.length, r: task.report_ids.length}),
      "card-meta"));
  }

  if (task.state === "draft") {
    const actions = node("div", undefined, "actions");
    actions.append(button(t("card.edit"), "btn btn-quiet", () => {
      const title = window.prompt(t("prompt.editTitle"), task.title);
      if (title) mutate("task.edit", {task_id: task.id, title});
    }));
    actions.append(action(t("card.setReady"), "task.ready", {task_id: task.id}));
    card.append(actions);

    if (!readOnly()) {
      card.draggable = true;
      card.addEventListener("dragstart", (event) => {
        dragTaskId = task.id;
        card.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", task.id);
      });
      card.addEventListener("dragend", () => {
        dragTaskId = null;
        card.classList.remove("dragging");
        document.querySelectorAll(".column.drop-ok").forEach((column) => column.classList.remove("drop-ok"));
      });
    }
  }

  card.addEventListener("click", (event) => {
    if (event.target.closest("button")) return;
    openTaskId = task.id;
    renderDrawer();
  });
  return card;
}

function renderBoard() {
  clear(ui.tasks);
  for (const [labelKey, states] of COLUMNS) {
    const column = node("div", undefined, "column");
    const head = node("div", undefined, "column-head");
    const tasks = snapshot.tasks.filter((task) => states.includes(task.state));
    head.append(node("h3", t(labelKey)), node("span", tasks.length, "column-count"));
    column.append(head);
    if (!tasks.length) column.append(node("p", t("empty.column"), "empty"));
    for (const task of tasks) column.append(taskCard(task));
    if (states.includes("ready")) {
      column.addEventListener("dragover", (event) => {
        if (!dragTaskId) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        column.classList.add("drop-ok");
      });
      column.addEventListener("dragleave", () => column.classList.remove("drop-ok"));
      column.addEventListener("drop", (event) => {
        event.preventDefault();
        column.classList.remove("drop-ok");
        if (!dragTaskId) return;
        const taskId = dragTaskId;
        dragTaskId = null;
        mutate("task.ready", {task_id: taskId});
      });
    }
    ui.tasks.append(column);
  }
}

/* ------------------------------------------------------------------- drawer */
function drawerSection(labelKey) {
  return node("p", t(labelKey), "drawer-section-label");
}

function renderDrawer() {
  if (!openTaskId || !snapshot) { ui.drawer.hidden = true; return; }
  const task = snapshot.tasks.find((item) => item.id === openTaskId);
  if (!task) { openTaskId = null; ui.drawer.hidden = true; return; }
  ui.drawer.hidden = false;
  ui.drawerTitle.textContent = task.title;
  clear(ui.drawerBody);
  const top = node("div", undefined, "card-top");
  top.append(pill(task.state), node("span", task.id, "card-id"));
  ui.drawerBody.append(top);

  if (task.description) {
    ui.drawerBody.append(drawerSection("drawer.description"), node("p", task.description, "card-body"));
  }
  if (task.acceptance_criteria.length) {
    ui.drawerBody.append(drawerSection("drawer.acceptance"));
    const list = node("ul");
    for (const criterion of task.acceptance_criteria) list.append(node("li", criterion));
    ui.drawerBody.append(list);
  }

  ui.drawerBody.append(drawerSection("drawer.details"));
  const kv = node("dl", undefined, "drawer-kv");
  const addRow = (labelKey, value, mono) => {
    kv.append(node("dt", t(labelKey)));
    const dd = node("dd", value);
    if (mono) dd.classList.add("mono");
    kv.append(dd);
  };
  addRow("drawer.assignee", task.assignee || t("drawer.unassigned"));
  if (task.branch) addRow("drawer.branch", task.branch, true);
  addRow("drawer.labels", task.labels.join(", ") || t("drawer.none"));
  addRow("drawer.paths", task.paths.join(", ") || t("drawer.none"), true);
  addRow("drawer.created", relativeTime(task.created_at));
  addRow("drawer.updated", relativeTime(task.updated_at));
  ui.drawerBody.append(kv);

  if (task.blocking_questions.length) {
    ui.drawerBody.append(drawerSection("drawer.blocking"));
    const actions = node("div", undefined, "actions");
    for (const questionId of task.blocking_questions) {
      actions.append(button(questionId, "btn btn-quiet", () => {
        ui.drawer.hidden = true;
        openTaskId = null;
        selectTab("questions");
      }));
    }
    ui.drawerBody.append(actions);
  }

  const reports = snapshot.reports.filter((report) => report.task_id === task.id);
  if (reports.length) {
    ui.drawerBody.append(drawerSection("drawer.reports"));
    for (const report of reports) {
      const card = node("article", undefined, "card");
      const head = node("div", undefined, "card-top");
      head.append(node("span", report.id, "card-id"), node("span", report.commit.slice(0, 8), "card-id"));
      card.append(head, node("p", report.summary, "card-body"));
      for (const check of report.validation) {
        card.append(node("p", `${check.command} — ${check.outcome}`, check.outcome === "passed" ? "card-meta" : "card-body"));
      }
      if (report.diff_summary) card.append(node("pre", report.diff_summary));
      ui.drawerBody.append(card);
    }
  }

  const jobs = snapshot.integrations.filter((job) => job.task_id === task.id);
  if (jobs.length) {
    ui.drawerBody.append(drawerSection("drawer.integrations"));
    for (const job of jobs) {
      const line = node("div", undefined, "card-top");
      line.append(pill(job.state), node("span", job.id, "card-id"));
      ui.drawerBody.append(line);
    }
  }

  if (task.state === "draft") {
    const actions = node("div", undefined, "actions");
    actions.append(button(t("card.edit"), "btn", () => {
      const title = window.prompt(t("prompt.editTitle"), task.title);
      if (title) mutate("task.edit", {task_id: task.id, title});
    }));
    const ready = action(t("card.setReady"), "task.ready", {task_id: task.id});
    ready.className = "btn btn-primary";
    actions.append(ready);
    ui.drawerBody.append(actions);
  }
}

/* -------------------------------------------------------------------- inbox */
function renderPotentials() {
  clear(ui.potentials);
  const actionable = snapshot.potential_tasks.filter((item) => ["new", "triaged"].includes(item.state));
  ui.inboxCount.textContent = actionable.length;
  ui.inboxCount.hidden = !actionable.length;
  if (!snapshot.potential_tasks.length) {
    ui.potentials.append(node("p", t("empty.inbox"), "empty"));
    return;
  }
  for (const potential of snapshot.potential_tasks) {
    const card = node("article", undefined, "card");
    if (!["new", "triaged"].includes(potential.state)) card.classList.add("is-muted");
    const top = node("div", undefined, "card-top");
    top.append(pill(potential.state), node("span", potential.id, "card-id"));
    card.append(top, node("h4", potential.suggested_title, "card-title"));
    card.append(node("p", potential.summary, "card-body"));

    const confidence = node("span", undefined, "confidence");
    const track = node("span", undefined, "confidence-track");
    const fill = node("span", undefined, "confidence-fill");
    fill.style.width = `${Math.round((potential.confidence || 0) * 100)}%`;
    track.append(fill);
    confidence.append(node("span", t("card.confidence")), track, node("span", potential.confidence));
    card.append(confidence);

    for (const evidence of potential.evidence) card.append(node("blockquote", evidence.quote, "evidence"));
    if (potential.promoted_task_id) {
      card.append(node("p", t("card.promotedTo", {id: potential.promoted_task_id}), "card-meta"));
    }

    if (["new", "triaged"].includes(potential.state)) {
      const actions = node("div", undefined, "actions");
      if (potential.state === "new") {
        actions.append(action(t("inbox.triage"), "potential.triage", {note: t("note.triaged"), potential_id: potential.id}));
      }
      if (potential.state === "triaged") {
        const promote = action(t("inbox.promote"), "potential.promote", {potential_id: potential.id});
        promote.className = "btn btn-primary";
        actions.append(promote);
      }
      actions.append(button(t("inbox.convert"), "btn", () => {
        const question = window.prompt(t("prompt.questionText"), potential.suggested_title);
        if (question) mutate("potential.question", {owner: `human:${snapshot.manager.active_manager_id}`, potential_id: potential.id, question});
      }));
      actions.append(button(t("inbox.duplicate"), "btn btn-quiet", () => {
        const target = window.prompt(t("prompt.duplicateOf"));
        if (target) mutate("potential.duplicate", {duplicate_of: target, potential_id: potential.id});
      }));
      actions.append(button(t("inbox.dismiss"), "btn btn-quiet", () => mutate("potential.dismiss", {potential_id: potential.id, reason: t("note.dismissed")})));
      card.append(actions);
    }
    ui.potentials.append(card);
  }
}

/* ---------------------------------------------------------------- questions */
function renderQuestions() {
  clear(ui.questions);
  const open = snapshot.open_questions.filter((item) => item.state === "open");
  ui.questionCount.textContent = open.length;
  ui.questionCount.hidden = !open.length;
  if (!snapshot.open_questions.length) {
    ui.questions.append(node("p", t("empty.questions"), "empty"));
    return;
  }
  for (const question of snapshot.open_questions) {
    const card = node("article", undefined, "card");
    if (["closed", "answered"].includes(question.state)) card.classList.add("is-muted");
    const top = node("div", undefined, "card-top");
    top.append(pill(question.state), node("span", question.id, "card-id"));
    card.append(top, node("h4", question.question, "card-title"));

    const related = question.related.task_ids;
    const meta = node("p", undefined, "card-meta");
    meta.append(document.createTextNode(
      `${t("q.owner", {owner: question.owner})} · ${related.length ? t("q.holds", {tasks: related.join(", ")}) : t("q.noTasks")}`));
    card.append(meta);
    if (question.blocking && question.state === "open") {
      card.append(node("span", t("q.blockingWork"), "pill pill-warning"));
    }
    if (question.answer) card.append(node("p", t("q.answerPrefix", {answer: question.answer}), "card-body"));

    if (["open", "deferred"].includes(question.state)) {
      const row = node("div", undefined, "answer-row");
      const input = node("input");
      input.placeholder = t("q.answerPh");
      input.disabled = readOnly();
      input.value = answerDrafts.get(question.id) || "";
      input.addEventListener("input", () => answerDrafts.set(question.id, input.value));
      const submit = button(t("q.answer"), "btn btn-primary", () => {
        const answer = input.value.trim();
        if (!answer) return;
        answerDrafts.delete(question.id);
        mutate("question.answer", {answer, question_id: question.id});
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") { event.preventDefault(); submit.click(); }
      });
      row.append(input, submit);
      card.append(row);
    }

    const actions = node("div", undefined, "actions");
    if (question.state === "open") actions.append(button(t("q.defer"), "btn btn-quiet", () => mutate("question.defer", {question_id: question.id, reason: t("note.deferred")})));
    if (question.state === "deferred") actions.append(button(t("q.reopen"), "btn", () => mutate("question.reopen", {question_id: question.id, reason: t("note.reopened")})));
    if (["answered", "deferred"].includes(question.state)) actions.append(button(t("q.close"), "btn btn-quiet", () => mutate("question.close", {question_id: question.id, reason: t("note.closed")})));
    if (actions.childNodes.length) card.append(actions);
    ui.questions.append(card);
  }
}

/* -------------------------------------------------------------------- files */
async function fetchDir(path) {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  return jsonFetch(`/api/projects/${encodeURIComponent(currentProject)}/files${query}`);
}

async function ensureDir(path) {
  if (filesState.listings.has(path)) return;
  try {
    const listing = await fetchDir(path);
    filesState.listings.set(path, listing.entries);
  } catch (error) {
    filesState.listings.set(path, null);
    showError(error.message);
  }
}

async function toggleDir(path) {
  if (filesState.expanded.has(path)) {
    filesState.expanded.delete(path);
  } else {
    filesState.expanded.add(path);
    await ensureDir(path);
  }
  renderFiles();
}

async function openFile(path) {
  filesState.selected = path;
  renderFiles();
  try {
    filesState.content = await jsonFetch(
      `/api/projects/${encodeURIComponent(currentProject)}/files/content?path=${encodeURIComponent(path)}`);
  } catch (error) {
    filesState.content = {available: false, path, reason: error.message};
  }
  renderFiles();
}

async function activateFiles() {
  if (!filesState.loaded && currentProject) {
    filesState.loaded = true;
    await ensureDir("");
    const root = filesState.listings.get("") || [];
    if (root.some((entry) => entry.name === "orbital" && entry.type === "directory")) {
      filesState.expanded.add("orbital");
      await ensureDir("orbital");
    }
  }
  renderFiles();
}

function renderTreeLevel(container, dirPath, depth) {
  const entries = filesState.listings.get(dirPath);
  if (!entries) return;
  if (!entries.length) {
    const empty = node("p", t("files.emptyDir"), "tree-empty");
    empty.style.paddingLeft = `${depth * 16 + 8}px`;
    container.append(empty);
    return;
  }
  for (const entry of entries) {
    const path = dirPath ? `${dirPath}/${entry.name}` : entry.name;
    const row = node("button", undefined, "tree-row");
    row.type = "button";
    row.style.paddingLeft = `${depth * 16 + 8}px`;
    if (entry.type === "directory") {
      const expanded = filesState.expanded.has(path);
      if (expanded) row.classList.add("expanded");
      row.setAttribute("role", "treeitem");
      row.setAttribute("aria-expanded", String(expanded));
      row.append(icon("chevron"), icon("folder"));
      const name = node("span", entry.name, "name");
      if (path === "orbital") name.classList.add("memory");
      row.append(name);
      row.addEventListener("click", () => toggleDir(path));
      container.append(row);
      if (expanded) renderTreeLevel(container, path, depth + 1);
    } else {
      row.setAttribute("role", "treeitem");
      row.setAttribute("aria-selected", String(filesState.selected === path));
      row.append(node("span", undefined, "spacer"), icon("file"));
      const name = node("span", entry.name, "name");
      if (dirPath === "orbital") name.classList.add("memory");
      row.append(name);
      row.addEventListener("click", () => openFile(path));
      container.append(row);
    }
  }
}

function renderFiles() {
  clear(ui.fileTree);
  const root = filesState.listings.get("");
  if (root === undefined) {
    ui.fileTree.append(node("p", "…", "tree-empty"));
  } else if (root === null || !root.length) {
    ui.fileTree.append(node("p", t("files.empty"), "tree-empty"));
  } else {
    renderTreeLevel(ui.fileTree, "", 0);
  }

  clear(ui.filePreview);
  const content = filesState.content;
  if (!filesState.selected || !content) {
    ui.filePreview.append(node("p", t("files.select"), "empty"));
    return;
  }
  const head = node("div", undefined, "file-preview-head");
  head.append(node("span", content.path || filesState.selected, "file-preview-path"));
  const meta = [];
  if (content.available && content.truncated) meta.push(t("files.truncated"));
  head.append(node("span", meta.join(" · "), "file-preview-meta"));
  ui.filePreview.append(head);
  if (content.available) {
    ui.filePreview.append(node("pre", content.content));
  } else {
    ui.filePreview.append(node("p", content.reason || t("files.unavailable"), "empty"));
  }
}

async function refreshFiles() {
  const expanded = [...filesState.expanded];
  filesState.listings.clear();
  await ensureDir("");
  for (const path of expanded) await ensureDir(path);
  if (filesState.selected) await openFile(filesState.selected);
  renderFiles();
}

/* ----------------------------------------------------------------- activity */
function eventTone(type) {
  if (type.startsWith("task.completed") || type.startsWith("integration.merged") || type.startsWith("knowledge.applied")) return "kind-success";
  if (type.startsWith("integration") || type.startsWith("run")) return "kind-accent";
  if (type.includes("blocked") || type.includes("failed")) return "kind-warning";
  return "";
}

function renderActivity() {
  clear(ui.activity);
  clear(ui.knowledge);
  clear(ui.runs);
  for (const event of [...snapshot.activity].reverse().slice(0, 80)) {
    const item = node("li", undefined, eventTone(event.type));
    item.append(node("div", event.type, "event-type"));
    item.append(node("div", `${event.actor} · ${relativeTime(event.timestamp)}`, "event-meta"));
    ui.activity.append(item);
  }

  if (!snapshot.knowledge.length) ui.knowledge.append(node("p", t("empty.knowledge"), "empty"));
  for (const summary of snapshot.knowledge) {
    const card = node("article", undefined, "card");
    const top = node("div", undefined, "card-top");
    top.append(node("span", summary.summary_id, "card-id"), node("span", relativeTime(summary.applied_at), "card-meta"));
    card.append(top);
    for (const change of summary.changes) {
      card.append(node("p", `${change.operation} ${change.path} — ${change.summary}`, "card-body"));
      if (change.preview.available) {
        const key = `${summary.summary_id}:${change.path}`;
        const toggle = button(openLogs.has(key) ? t("k.hidePreview") : t("k.showPreview"), "btn btn-quiet", () => {
          if (openLogs.has(key)) openLogs.delete(key); else openLogs.set(key, change.preview.content);
          renderActivity();
        });
        toggle.disabled = false;
        card.append(toggle);
        if (openLogs.has(key)) card.append(node("pre", openLogs.get(key)));
      }
    }
    ui.knowledge.append(card);
  }

  if (!snapshot.runs.length) ui.runs.append(node("p", t("empty.runs"), "empty"));
  for (const run of snapshot.runs.slice(0, 8)) {
    const card = node("article", undefined, "card");
    const top = node("div", undefined, "card-top");
    top.append(pill(run.state === "succeeded" ? "done" : run.state), node("span", run.id, "card-id"));
    card.append(top);
    card.append(node("p", `${run.actor} · ${run.agent_type} · ${t("run.task", {id: run.task_id})}`, "card-body"));
    card.append(node("p", t("run.sensitive"), "card-meta"));
    const actions = node("div", undefined, "actions");
    for (const kind of ["stdout", "stderr", "transcript"]) {
      const key = `${run.id}:${kind}`;
      const toggle = node("button", openLogs.has(key) ? t("run.hide", {kind}) : t("run.view", {kind}), "btn btn-quiet");
      toggle.type = "button";
      toggle.disabled = !run.log_availability[kind];
      toggle.addEventListener("click", async () => {
        if (openLogs.has(key)) {
          openLogs.delete(key);
          renderActivity();
          return;
        }
        try {
          const result = await jsonFetch(`/api/projects/${snapshot.project.slug}/runs/${run.id}/logs/${kind}`);
          openLogs.set(key, result.available ? result.content : result.reason);
          renderActivity();
        } catch (error) { showError(error.message); }
      });
      actions.append(toggle);
    }
    card.append(actions);
    for (const kind of ["stdout", "stderr", "transcript"]) {
      const key = `${run.id}:${kind}`;
      if (openLogs.has(key)) card.append(node("pre", openLogs.get(key)));
    }
    ui.runs.append(card);
  }
}

/* ------------------------------------------------------------------- render */
function render() {
  ui.error.hidden = true;
  clear(ui.actor);
  const dot = node("span", undefined, "dot");
  ui.actor.append(dot, node("span",
    `${snapshot.access.actor || t("actor.unknown")} · ${readOnly() ? t("actor.readonly") : t("actor.write")}`));
  ui.actor.classList.toggle("read-only", readOnly());

  const owner = ui.questionForm.querySelector('[name="owner"]');
  if (!owner.dataset.touched && document.activeElement !== owner) {
    owner.value = `human:${snapshot.manager.active_manager_id}`;
  }
  document.querySelectorAll("form button, form input, form textarea").forEach((element) => {
    element.disabled = readOnly();
  });
  ui.composerToggle.disabled = readOnly();

  renderHeader();
  renderMembers();
  renderSetup();
  renderBoard();
  renderPotentials();
  renderQuestions();
  renderActivity();
  renderDrawer();
  if (snapshot.errors.length) showError(snapshot.errors.map((item) => item.message).join(" "));
  ui.status.textContent = t("status.live", {rev: snapshot.projection_revision.slice(0, 10)});
}

function typingNow() {
  const element = document.activeElement;
  return element && ["INPUT", "TEXTAREA"].includes(element.tagName);
}

async function refresh(force = false) {
  if (refreshing || !currentProject) return;
  if (!force && (typingNow() || dragTaskId)) return;
  refreshing = true;
  try {
    snapshot = await jsonFetch(`/api/projects/${encodeURIComponent(currentProject)}`);
    render();
  } catch (error) {
    showError(t("error.refresh", {msg: error.message}));
    ui.status.textContent = t("status.failed");
  } finally { refreshing = false; }
}

/* -------------------------------------------------------------------- forms */
ui.composerToggle.addEventListener("click", () => {
  ui.composer.hidden = false;
  ui.composerToggle.hidden = true;
  ui.composer.querySelector('[name="title"]').focus();
});
ui.composerCancel.addEventListener("click", () => {
  ui.composer.reset();
  ui.composer.hidden = true;
  ui.composerToggle.hidden = false;
});
ui.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  await mutate("task.create", {
    acceptance_criteria: data.get("acceptance") ? [data.get("acceptance")] : [],
    description: data.get("description"),
    title: data.get("title"),
  });
  ui.composer.reset();
  ui.composer.hidden = true;
  ui.composerToggle.hidden = false;
});

ui.questionForm.querySelector('[name="owner"]').addEventListener("input", (event) => {
  event.currentTarget.dataset.touched = "true";
});
ui.questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  await mutate("question.add", {
    blocking: data.get("blocking") === "on",
    owner: data.get("owner"),
    question: data.get("question"),
    task_ids: data.get("task_id") ? [data.get("task_id")] : [],
  });
  event.target.reset();
});

for (const tab of TABS) {
  document.querySelector(`#tab-${tab}`).addEventListener("click", () => selectTab(tab));
}
ui.filesRefresh.addEventListener("click", refreshFiles);
ui.onboardMember.addEventListener("input", renderSetup);
ui.onboardAgent.addEventListener("change", renderSetup);

function wireCopy(copyButton, message) {
  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(message());
      copyButton.textContent = t("onboard.copied");
      window.setTimeout(() => { copyButton.textContent = t("settings.copy"); }, 1500);
    } catch (error) { showError(error.message); }
  });
}
wireCopy(ui.onboardCopy, memberSetupMessage);
wireCopy(ui.managerCopy, managerSetupMessage);
ui.langEn.addEventListener("click", () => setLocale("en"));
ui.langZh.addEventListener("click", () => setLocale("zh"));
ui.drawerClose.addEventListener("click", () => { openTaskId = null; ui.drawer.hidden = true; });
ui.drawer.addEventListener("click", (event) => {
  if (event.target === ui.drawer) { openTaskId = null; ui.drawer.hidden = true; }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && openTaskId) { openTaskId = null; ui.drawer.hidden = true; }
});

/* ------------------------------------------------------------- new project */
const createState = {browseGit: false, browsePath: null, entries: [], nameTouched: false, shortcuts: null};

function basename(path) {
  const trimmed = path.replace(/\/+$/, "");
  const index = trimmed.lastIndexOf("/");
  return index >= 0 ? trimmed.slice(index + 1) : trimmed;
}

function joinPath(base, name) {
  return base.endsWith("/") ? `${base}${name}` : `${base}/${name}`;
}

function readRecentFolders() {
  try {
    const value = JSON.parse(localStorage.getItem("orbital-team-recent-folders") || "[]");
    return Array.isArray(value) ? value.filter((item) => typeof item === "string").slice(0, 5) : [];
  } catch { return []; }
}

function rememberFolder(path) {
  const recents = [path, ...readRecentFolders().filter((item) => item !== path)].slice(0, 5);
  try { localStorage.setItem("orbital-team-recent-folders", JSON.stringify(recents)); } catch { /* convenience only */ }
}

function showCreateError(message) {
  ui.createError.textContent = message;
  ui.createError.hidden = false;
}

function openCreate() {
  ui.createForm.reset();
  createState.nameTouched = false;
  createState.browsePath = null;
  ui.createError.hidden = true;
  ui.createGitNote.hidden = true;
  ui.folderBrowser.hidden = true;
  ui.createBackdrop.hidden = false;
  ui.createWorkspace.focus();
}

function closeCreate() { ui.createBackdrop.hidden = true; }

function deriveProjectName() {
  if (createState.nameTouched) return;
  const path = ui.createWorkspace.value.trim();
  ui.createName.value = path ? basename(path) : "";
}

async function inspectWorkspacePath() {
  const path = ui.createWorkspace.value.trim();
  ui.createGitNote.hidden = true;
  if (!path.startsWith("/") && !path.startsWith("~")) return;
  try {
    const info = await jsonFetch(`/api/platform/browse?path=${encodeURIComponent(path)}`);
    ui.createGitNote.hidden = info.is_git_repo;
  } catch { /* resolved on submit */ }
}

async function browseTo(path) {
  try {
    const listing = await jsonFetch(`/api/platform/browse?path=${encodeURIComponent(path || "")}`);
    createState.browsePath = listing.path;
    createState.browseGit = listing.is_git_repo;
    createState.entries = listing.entries;
    ui.createError.hidden = true;
    renderBrowser();
  } catch (error) { showCreateError(error.message); }
}

function folderChip(label, title, onClick) {
  const element = node("button", label, "btn btn-quiet fb-chip");
  element.type = "button";
  if (title) element.title = title;
  element.addEventListener("click", onClick);
  return element;
}

function renderBrowser() {
  clear(ui.fbShortcuts);
  for (const shortcut of createState.shortcuts || []) {
    ui.fbShortcuts.append(folderChip(t(`shortcut.${shortcut.key}`), shortcut.path, () => browseTo(shortcut.path)));
  }
  clear(ui.fbRecent);
  const recents = readRecentFolders();
  ui.fbRecent.hidden = !recents.length;
  if (recents.length) {
    ui.fbRecent.append(node("span", t("create.recent"), "fb-label"));
    for (const recent of recents) {
      ui.fbRecent.append(folderChip(basename(recent), recent, () => browseTo(recent)));
    }
  }
  clear(ui.fbCrumbs);
  const path = createState.browsePath || "/";
  const root = node("button", "/");
  root.type = "button";
  root.addEventListener("click", () => browseTo("/"));
  ui.fbCrumbs.append(root);
  let accumulated = "";
  for (const part of path.split("/").filter(Boolean)) {
    accumulated += `/${part}`;
    const target = accumulated;
    const crumb = node("button", part);
    crumb.type = "button";
    crumb.addEventListener("click", () => browseTo(target));
    ui.fbCrumbs.append(node("span", "›", "fb-sep"), crumb);
  }
  clear(ui.fbList);
  if (!createState.entries.length) {
    ui.fbList.append(node("p", t("create.emptyDir"), "tree-empty"));
  }
  for (const entry of createState.entries) {
    const row = node("button", undefined, "tree-row");
    row.type = "button";
    row.append(node("span", undefined, "spacer"), icon("folder"), node("span", entry.name, "name"));
    row.addEventListener("click", () => browseTo(joinPath(path, entry.name)));
    ui.fbList.append(row);
  }
}

async function openBrowser() {
  if (!ui.folderBrowser.hidden) {
    ui.folderBrowser.hidden = true;
    return;
  }
  ui.folderBrowser.hidden = false;
  if (!createState.shortcuts) {
    try {
      createState.shortcuts = (await jsonFetch("/api/platform/folders")).entries;
    } catch (error) {
      createState.shortcuts = [];
      showCreateError(error.message);
    }
  }
  const typed = ui.createWorkspace.value.trim();
  await browseTo(typed.startsWith("/") ? typed : "");
}

function useBrowsedFolder() {
  if (!createState.browsePath) return;
  ui.createWorkspace.value = createState.browsePath;
  deriveProjectName();
  ui.createGitNote.hidden = createState.browseGit;
  ui.folderBrowser.hidden = true;
}

async function makeNewFolder() {
  const name = ui.fbNewName.value.trim();
  if (!name || !createState.browsePath) return;
  try {
    const made = await jsonFetch("/api/platform/mkdir", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({path: joinPath(createState.browsePath, name)}),
    });
    ui.fbNewName.value = "";
    await browseTo(made.path);
  } catch (error) { showCreateError(error.message); }
}

async function submitCreate(event) {
  event.preventDefault();
  const workspace = ui.createWorkspace.value.trim();
  const name = ui.createName.value.trim();
  if (!workspace) { showCreateError(t("create.errWorkspace")); return; }
  if (!workspace.startsWith("/") && !workspace.startsWith("~")) { showCreateError(t("create.errAbsolute")); return; }
  if (!name) { showCreateError(t("create.errName")); return; }
  ui.createError.hidden = true;
  ui.createSubmit.disabled = true;
  ui.createSubmit.textContent = t("create.creating");
  try {
    const result = await jsonFetch("/api/projects", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name, workspace}),
    });
    rememberFolder(result.project.workspace);
    closeCreate();
    await loadBootstrap();
    activateProject(result.project.slug);
    ensurePolling();
  } catch (error) {
    showCreateError(error.message);
  } finally {
    ui.createSubmit.disabled = false;
    ui.createSubmit.textContent = t("create.submit");
  }
}

ui.projectNew.addEventListener("click", openCreate);
ui.createClose.addEventListener("click", closeCreate);
ui.createCancel.addEventListener("click", closeCreate);
ui.createBackdrop.addEventListener("click", (event) => {
  if (event.target === ui.createBackdrop) closeCreate();
});
ui.createBrowse.addEventListener("click", openBrowser);
ui.createWorkspace.addEventListener("input", deriveProjectName);
ui.createWorkspace.addEventListener("change", inspectWorkspacePath);
ui.createName.addEventListener("input", () => { createState.nameTouched = true; });
ui.fbUse.addEventListener("click", useBrowsedFolder);
ui.fbNewMake.addEventListener("click", makeNewFolder);
ui.fbNewName.addEventListener("keydown", (event) => {
  if (event.key === "Enter") { event.preventDefault(); makeNewFolder(); }
});
ui.createForm.addEventListener("submit", submitCreate);
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || ui.createBackdrop.hidden) return;
  // Scoped like Orbital: the first Escape closes the folder picker, the next
  // one the modal, so one keypress never destroys the typed form.
  if (!ui.folderBrowser.hidden) {
    ui.folderBrowser.hidden = true;
    return;
  }
  closeCreate();
});

/* -------------------------------------------------------------------- start */
let pollTimer = null;

function ensurePolling() {
  if (pollTimer === null) pollTimer = window.setInterval(refresh, 2000);
}

async function loadBootstrap() {
  const bootstrap = await jsonFetch("/api/bootstrap");
  projects = bootstrap.projects;
  ui.projectNew.hidden = !bootstrap.actor;
  if (bootstrap.errors?.length) {
    showError(bootstrap.errors.map((item) => item.message).join(" "));
  }
  renderProjectList();
  return bootstrap;
}

async function start() {
  applyStatic();
  try {
    await loadBootstrap();
    if (!projects.length) {
      ui.status.textContent = t("status.noProjects");
      ui.projectTitle.textContent = t("status.noProjects");
      return;
    }
    const requested = new URL(window.location.href).searchParams.get("project");
    currentProject = projects.some((project) => project.slug === requested)
      ? requested
      : projects[0].slug;
    renderProjectList();
    await refresh(true);
    ensurePolling();
  } catch (error) { showError(error.message); }
}
start();
