const state = {
  report: null,
  hands: [],
  contextsById: new Map(),
  evalsById: new Map(),
  selectedHandId: null,
  selectedStreet: "preflop",
  tierFilter: new Set(),
  positionFilter: "all",
  streetFilter: new Set(),
  resultFilter: "all",
  search: "",
  chipUnit: "bb",
  lang: "en",
  replayTimer: null,
  solverRunning: new Set(),
  solverBatch: { running: false, total: 0, done: 0, failed: 0, changed: 0, up: 0, down: 0, flat: 0 },
};

const els = {};

const LANG_STORAGE_KEY = "phr_lang";

const I18N = {
  en: {
    "schema.noReport": "No report loaded",
    honesty: "EV loss is an engine estimate, not solver EV.",
    "backend.title": "Postflop backend for .txt analysis",
    "lang.title": "Switch language",
    "chipUnit.title": "Toggle chip display units",
    "chipUnit.showingBb": "Currently showing big blinds; click for chips",
    "chipUnit.showingChips": "Currently showing chips; click for BB",
    "loadData.title": "Choose .txt files from ./data",
    "loadData.text": "Load ./data",
    "loadFiles.title": "Load one or more .txt hand histories or .json reports",
    "loadFiles.text": "Load txt / json",
    "picker.status": "Select hand-history files to analyze.",
    "reanalyze.title": "Ignore cached results and analyze again",
    "reanalyze.text": "Re-analyze",
    selectAll: "Select all",
    analyzeSelected: "Analyze selected",
    cancel: "Cancel",
    "metric.hands": "Hands",
    "metric.accuracy": "GTO Accuracy",
    "metric.evloss": "EV Loss / 100",
    "metric.netBb": "Net BB",
    "metric.netChips": "Net Chips",
    "units.chips": "Chips",
    "metric.mistakes": "Mistakes",
    "metric.engineMix": "Engine Mix",
    "solveAll.title": "Run solver for every postflop decision",
    "solveAll.solving": "Solving all...",
    "solveAll.run": "Run all solver ({n})",
    "solveAll.done": "All solver done",
    "search.placeholder": "Hand, card, position",
    "tier.filter": "Tier filter",
    "tier.all": "All",
    "tier.mistake": "Mistake",
    "tier.inaccuracy": "Inaccuracy",
    "tier.good": "Good",
    "tier.unknown": "n/a",
    "street.filter": "Street filter",
    "street.all": "All",
    "street.preflop": "Preflop",
    "street.flop": "Flop",
    "street.turn": "Turn",
    "street.river": "River",
    "street.showdown": "Showdown",
    "street.riverShowdown": "River / Showdown",
    "street.prev": "Previous street",
    "street.next": "Next street",
    "street.play": "Play replay",
    "position.filter": "Position filter",
    "position.all": "All positions",
    "result.filter": "Result filter",
    "result.all": "All results",
    "result.win": "Won chips",
    "result.loss": "Lost chips",
    "panel.hands": "Hands",
    "panel.leaks": "Leaks",
    "panel.positions": "Positions",
    "panel.opponents": "Opponents",
    hero: "Hero",
    "hero.holeCards": "Hero hole cards",
    "section.timeline": "Action Timeline",
    "section.decisions": "Hero Decisions",
    "empty.loadReport.title": "Load a JSON report",
    "empty.loadReport.sub": "Run poker-hand-review analyze with --json, then open it here.",
    "empty.noReport": "No report",
    "empty.noMatch": "No matching hands",
    "empty.noActions": "No actions",
    "empty.noDecision": "No Hero decision on this street",
    "empty.noLeaks": "No leaks",
    "empty.noPosition": "No position data",
    "empty.noOpponents": "No opponents",
    "status.schema": "{name} · schema {schema}",
    "status.fromCache": "{text} · {n}/{total} from cache",
    "status.analyzing": "Analyzing {name} ({backend})",
    "status.analyzingData": "Analyzing {n} ./data files ({backend})",
    "status.analyzeFailed": "Analyze failed: {msg}",
    "status.readingData": "Reading ./data",
    "status.loadedDataList": "Loaded ./data file list",
    "status.loadFailed": "Load failed: {msg}",
    "status.txtCount": "{n} txt files in ./data",
    "status.selectOne": "Select at least one file.",
    "status.loadSeparately": "Load txt and json separately",
    "status.couldNotLoad": "Could not load {name}",
    "datafile.hands": "{n} hands",
    "handSub.decisions": "{n} decisions",
    "batch.changed": "{n} changed",
    "batch.failed": "{n} failed",
    "batch.saved": "saved",
    "solver.run": "Run solver",
    "solver.again": "Run again",
    "solver.solving": "Solving...",
    "solver.unavailable": "Solver unavailable: {msg}",
    "solver.batchFailed":
      "Solver failed after {n} checked decision{plural}.\n\nFirst error: {err}",
    "decision.facing": "facing {facing}",
    "decision.vs": " vs {villain}",
    "decision.pot": "pot {pot}",
    "decision.toCall": "to call {toCall}",
    "decision.noEval": "No evaluation",
    "explain.no_score": "Not enough info to grade",
    "explain.chart_uncovered": "Preflop chart does not cover this spot yet",
    "explain.no_street": "Street data not found",
    "explain.aligned": "Matches current {source} recommendation",
    "explain.deviate": "Recommend {action}; current action deviates by ~{ev_loss}bb",
    "explain.equity.aligned.req":
      "Estimated equity {eq} vs {req} required against {range} range; action aligns. Severity estimate {ev}bb; not exact solver EV.",
    "explain.equity.aligned.noreq":
      "Estimated equity {eq} against {range} range; action aligns. Severity estimate {ev}bb; not exact solver EV.",
    "explain.equity.deviate.req":
      "Estimated equity {eq} vs {req} required against {range} range; recommend {action}. Severity estimate {ev}bb; not exact solver EV.",
    "explain.equity.deviate.noreq":
      "Estimated equity {eq} against {range} range; recommend {action}. Severity estimate {ev}bb; not exact solver EV.",
    "explain.src.preflop_chart": "chart",
    "explain.src.solver": "solver",
    "explain.src.equity_backend": "equity",
    "leak.pattern": "{street}: {action} vs recommended {best}",
    "delta.noChange": "no change",
    "delta.changed": "changed",
    "delta.evLoss": "EV loss {ev}",
    "badge.engine": "engine",
    "meta.net": "net {value}",
    "board.prefix": "board {cards}",
    "pot.info": "Board · total pot {pot}",
    "action.fold": "fold",
    "action.check": "check",
    "action.postsSb": "posts SB {amount}",
    "action.postsBb": "posts BB {amount}",
    "action.returned": "returned {amount}",
    "action.collected": "collected {amount}",
    "action.to": "to",
    "action.allIn": "all-in",
    "opp.meta": "{n} hands · VPIP {vpip} · PFR {pfr}",
    "src.chart.title": "Preflop GTO range chart; no solver needed",
    "src.equity.title": "equity heuristic estimate",
    "src.solver.title": "real GTO solver result",
    "src.unknown.title": "insufficient info; not graded",
    "src.builtIn": "built-in",
    "src.solverChart": "solver chart",
    "src.chartDetail": "chart detail",
    "detail.chart": "chart {v}",
    "detail.source": "source {v}",
    "detail.version": "version {v}",
    "detail.effective": "effective {v}bb",
    "detail.spot": "spot {v}",
    "delta.best": "best {a} -> {b}",
  },
  zh: {
    "schema.noReport": "尚未載入報告",
    honesty: "EV 損失為引擎估計值，非 solver 實際 EV。",
    "backend.title": "翻後分析使用的後端",
    "lang.title": "切換語言",
    "chipUnit.title": "切換籌碼顯示單位",
    "chipUnit.showingBb": "目前以大盲顯示；點擊切換為籌碼",
    "chipUnit.showingChips": "目前以籌碼顯示；點擊切換為大盲",
    "loadData.title": "從 ./data 選擇 .txt 檔",
    "loadData.text": "載入 ./data",
    "loadFiles.title": "載入一個或多個 .txt 手牌歷史或 .json 報告",
    "loadFiles.text": "載入 txt / json",
    "picker.status": "選擇要分析的手牌歷史檔。",
    "reanalyze.title": "忽略快取並重新分析",
    "reanalyze.text": "重新分析",
    selectAll: "全選",
    analyzeSelected: "分析所選",
    cancel: "取消",
    "metric.hands": "手牌數",
    "metric.accuracy": "GTO 準確度",
    "metric.evloss": "EV 損失 / 100",
    "metric.netBb": "淨 BB",
    "metric.netChips": "淨籌碼",
    "units.chips": "籌碼",
    "metric.mistakes": "失誤數",
    "metric.engineMix": "引擎組成",
    "solveAll.title": "對每個翻後決策執行 solver",
    "solveAll.solving": "全部解算中…",
    "solveAll.run": "執行全部 solver（{n}）",
    "solveAll.done": "全部 solver 完成",
    "search.placeholder": "手牌、牌、位置",
    "tier.filter": "等級篩選",
    "tier.all": "全部",
    "tier.mistake": "失誤",
    "tier.inaccuracy": "不精確",
    "tier.good": "良好",
    "tier.unknown": "未評",
    "street.filter": "街道篩選",
    "street.all": "全部",
    "street.preflop": "翻前",
    "street.flop": "翻牌",
    "street.turn": "轉牌",
    "street.river": "河牌",
    "street.showdown": "攤牌",
    "street.riverShowdown": "河牌 / 攤牌",
    "street.prev": "上一街",
    "street.next": "下一街",
    "street.play": "播放重播",
    "position.filter": "位置篩選",
    "position.all": "全部位置",
    "result.filter": "結果篩選",
    "result.all": "全部結果",
    "result.win": "贏得籌碼",
    "result.loss": "輸掉籌碼",
    "panel.hands": "手牌",
    "panel.leaks": "漏洞",
    "panel.positions": "位置",
    "panel.opponents": "對手",
    hero: "英雄",
    "hero.holeCards": "英雄底牌",
    "section.timeline": "行動時間軸",
    "section.decisions": "英雄決策",
    "empty.loadReport.title": "載入 JSON 報告",
    "empty.loadReport.sub": "執行 poker-hand-review analyze --json 後，在此開啟。",
    "empty.noReport": "沒有報告",
    "empty.noMatch": "沒有符合的手牌",
    "empty.noActions": "沒有行動",
    "empty.noDecision": "本街沒有英雄決策",
    "empty.noLeaks": "沒有漏洞",
    "empty.noPosition": "沒有位置資料",
    "empty.noOpponents": "沒有對手",
    "status.schema": "{name} · 綱要 {schema}",
    "status.fromCache": "{text} · {n}/{total} 來自快取",
    "status.analyzing": "分析 {name} 中（{backend}）",
    "status.analyzingData": "分析 {n} 個 ./data 檔案中（{backend}）",
    "status.analyzeFailed": "分析失敗：{msg}",
    "status.readingData": "讀取 ./data 中",
    "status.loadedDataList": "已載入 ./data 檔案清單",
    "status.loadFailed": "載入失敗：{msg}",
    "status.txtCount": "./data 中有 {n} 個 txt 檔",
    "status.selectOne": "請至少選擇一個檔案。",
    "status.loadSeparately": "txt 與 json 請分開載入",
    "status.couldNotLoad": "無法載入 {name}",
    "datafile.hands": "{n} 手",
    "handSub.decisions": "{n} 個決策",
    "batch.changed": "{n} 變更",
    "batch.failed": "{n} 失敗",
    "batch.saved": "已儲存",
    "solver.run": "執行 solver",
    "solver.again": "再次執行",
    "solver.solving": "解算中…",
    "solver.unavailable": "Solver 無法使用：{msg}",
    "solver.batchFailed": "已檢查 {n} 個決策後 solver 失敗。\n\n第一個錯誤：{err}",
    "decision.facing": "面對 {facing}",
    "decision.vs": " 對 {villain}",
    "decision.pot": "底池 {pot}",
    "decision.toCall": "待跟 {toCall}",
    "decision.noEval": "尚無評估",
    "explain.no_score": "資訊不足，暫不評分",
    "explain.chart_uncovered": "翻前圖表尚未涵蓋此情境",
    "explain.no_street": "找不到街段資料",
    "explain.aligned": "符合目前 {source} 建議",
    "explain.deviate": "建議 {action}；目前動作偏離約 {ev_loss}bb",
    "explain.equity.aligned.req":
      "估計勝率 {eq}，需 {req}，對 {range} 範圍；動作一致。嚴重度估計 {ev}bb；非精確 solver EV。",
    "explain.equity.aligned.noreq":
      "估計勝率 {eq}，對 {range} 範圍；動作一致。嚴重度估計 {ev}bb；非精確 solver EV。",
    "explain.equity.deviate.req":
      "估計勝率 {eq}，需 {req}，對 {range} 範圍；建議 {action}。嚴重度估計 {ev}bb；非精確 solver EV。",
    "explain.equity.deviate.noreq":
      "估計勝率 {eq}，對 {range} 範圍；建議 {action}。嚴重度估計 {ev}bb；非精確 solver EV。",
    "explain.src.preflop_chart": "翻前圖表",
    "explain.src.solver": "Solver",
    "explain.src.equity_backend": "勝率",
    "leak.pattern": "{street}：{action} vs 建議 {best}",
    "delta.noChange": "無變化",
    "delta.changed": "已變更",
    "delta.evLoss": "EV 損失 {ev}",
    "badge.engine": "引擎",
    "meta.net": "淨 {value}",
    "board.prefix": "牌面 {cards}",
    "pot.info": "牌面 · 底池 {pot}",
    "action.fold": "蓋牌",
    "action.check": "過牌",
    "action.postsSb": "下小盲 {amount}",
    "action.postsBb": "下大盲 {amount}",
    "action.returned": "退回 {amount}",
    "action.collected": "贏得 {amount}",
    "action.to": "到",
    "action.allIn": "全下",
    "opp.meta": "{n} 手 · VPIP {vpip} · PFR {pfr}",
    "src.chart.title": "翻前 GTO 範圍表，不需要 solver",
    "src.equity.title": "equity 啟發式估計",
    "src.solver.title": "真實 GTO solver 解算",
    "src.unknown.title": "資訊不足，未評分",
    "src.builtIn": "內建",
    "src.solverChart": "solver 表",
    "src.chartDetail": "圖表細節",
    "detail.chart": "圖表 {v}",
    "detail.source": "來源 {v}",
    "detail.version": "版本 {v}",
    "detail.effective": "有效 {v}bb",
    "detail.spot": "情境 {v}",
    "delta.best": "最佳 {a} -> {b}",
  },
};

function t(key, params, lang) {
  const table = I18N[lang || state.lang] || I18N.en;
  let text = table[key] != null ? table[key] : I18N.en[key];
  if (text == null) return key;
  if (params) {
    text = text.replace(/\{(\w+)\}/g, (match, name) =>
      params[name] != null ? String(params[name]) : match,
    );
  }
  return text;
}

function initLang() {
  let stored = null;
  try {
    stored = window.localStorage?.getItem(LANG_STORAGE_KEY);
  } catch {
    stored = null;
  }
  setLang(stored === "en" || stored === "zh" ? stored : "en");
}

function setLang(lang) {
  state.lang = lang === "zh" ? "zh" : "en";
  try {
    window.localStorage?.setItem(LANG_STORAGE_KEY, state.lang);
  } catch {
    /* ignore storage failures */
  }
  document.documentElement.lang = state.lang === "zh" ? "zh-Hant" : "en";
  syncLangToggle();
  applyStaticI18n();
  render();
}

function syncLangToggle() {
  if (!els.langToggle) return;
  els.langToggle.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === state.lang);
  });
}

function applyStaticI18n() {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPh);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAria));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindEvents();
  initLang();
  loadReportFromQuery();
  render();
});

function bindElements() {
  [
    "fileInput",
    "contentGrid",
    "leftResizeHandle",
    "rightResizeHandle",
    "loadDataButton",
    "chipUnitToggle",
    "langToggle",
    "dataFilePicker",
    "dataFileList",
    "dataFileStatus",
    "selectAllDataFiles",
    "analyzeDataSelection",
    "cancelDataSelection",
    "forceReanalyze",
    "analyzeBackend",
    "schemaLabel",
    "metricHands",
    "metricAccuracy",
    "metricEvLoss",
    "metricNetLabel",
    "metricNet",
    "metricMistakes",
    "metricEngines",
    "solveAllButton",
    "solveAllStatus",
    "searchInput",
    "tierFilter",
    "positionFilter",
    "streetFilter",
    "resultFilter",
    "handCount",
    "handList",
    "emptyState",
    "reviewView",
    "selectedTierDot",
    "selectedHandId",
    "selectedMeta",
    "prevStreet",
    "nextStreet",
    "streetTabs",
    "playReplay",
    "heroHoleCards",
    "seatRing",
    "boardCards",
    "potInfo",
    "streetLabel",
    "actionTimeline",
    "decisionCount",
    "decisionList",
    "leakCount",
    "leakList",
    "positionBars",
    "opponentList",
    "loadingOverlay",
    "loadingOverlayText",
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
}

function bindEvents() {
  els.fileInput.addEventListener("change", async (event) => {
    const files = [...(event.target.files || [])];
    if (!files.length) return;
    await loadFiles(files);
    event.target.value = "";
  });

  els.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderHandList();
  });

  bindSegmentedMulti(els.tierFilter, "tier", state.tierFilter);
  bindSegmentedMulti(els.streetFilter, "street", state.streetFilter);

  els.positionFilter.addEventListener("change", (event) => {
    state.positionFilter = event.target.value;
    renderHandList();
  });

  els.resultFilter.addEventListener("change", (event) => {
    state.resultFilter = event.target.value;
    renderHandList();
  });

  els.prevStreet.addEventListener("click", () => stepStreet(-1));
  els.nextStreet.addEventListener("click", () => stepStreet(1));
  els.playReplay.addEventListener("click", toggleReplay);
  els.solveAllButton.addEventListener("click", runAllSolvers);
  els.chipUnitToggle.addEventListener("click", toggleChipUnit);
  els.langToggle.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (button) setLang(button.dataset.lang);
  });
  els.loadDataButton.addEventListener("click", openDataFilePicker);
  els.selectAllDataFiles.addEventListener("click", selectAllDataFiles);
  els.analyzeDataSelection.addEventListener("click", analyzeSelectedDataFiles);
  els.cancelDataSelection.addEventListener("click", () => {
    els.dataFilePicker.hidden = true;
  });
  bindColumnResize();
}

function toggleChipUnit() {
  state.chipUnit = state.chipUnit === "bb" ? "chips" : "bb";
  render();
}

function updateChipUnitToggle() {
  if (!els.chipUnitToggle) return;
  els.chipUnitToggle.textContent = state.chipUnit === "bb" ? "BB" : t("units.chips");
  els.chipUnitToggle.title =
    state.chipUnit === "bb" ? t("chipUnit.showingBb") : t("chipUnit.showingChips");
}

function bindColumnResize() {
  bindResizeHandle(els.leftResizeHandle, "left");
  bindResizeHandle(els.rightResizeHandle, "right");
}

function bindResizeHandle(handle, side) {
  if (!handle || !els.contentGrid) return;
  handle.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const startX = event.clientX;
    const styles = window.getComputedStyle(els.contentGrid);
    const startLeft = parseFloat(styles.getPropertyValue("--left-column")) || 320;
    const startRight = parseFloat(styles.getPropertyValue("--right-column")) || 360;
    els.contentGrid.classList.add("resizing");
    handle.setPointerCapture(event.pointerId);

    const onMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      if (side === "left") {
        setColumnWidth("--left-column", clamp(startLeft + delta, 240, 560));
      } else {
        setColumnWidth("--right-column", clamp(startRight - delta, 260, 560));
      }
    };
    const onUp = () => {
      els.contentGrid.classList.remove("resizing");
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
      handle.removeEventListener("pointercancel", onUp);
    };

    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
    handle.addEventListener("pointercancel", onUp);
  });
}

function setColumnWidth(property, value) {
  els.contentGrid.style.setProperty(property, `${Math.round(value)}px`);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function bindSegmentedMulti(container, datasetKey, set) {
  if (!container) return;
  container.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const value = button.dataset[datasetKey];
    if (value === "all") {
      set.clear();
    } else if (set.has(value)) {
      set.delete(value);
    } else {
      set.add(value);
    }
    syncSegmented(container, datasetKey, set);
    renderHandList();
  });
  syncSegmented(container, datasetKey, set);
}

function syncSegmented(container, datasetKey, set) {
  [...container.querySelectorAll("button")].forEach((button) => {
    const value = button.dataset[datasetKey];
    const active = value === "all" ? set.size === 0 : set.has(value);
    button.classList.toggle("active", active);
  });
}

function loadReport(report, sourceName) {
  state.report = report;
  state.hands = report.hands || [];
  state.contextsById = byId(report.hero_contexts || []);
  state.evalsById = byId(report.hand_evals || []);
  state.selectedHandId = state.hands[0]?.hand_id || null;
  state.selectedStreet = "preflop";
  state.solverBatch = { running: false, total: 0, done: 0, failed: 0, changed: 0, up: 0, down: 0, flat: 0 };
  setStatus(t("status.schema", { name: sourceName, schema: report.schema || "unknown" }));
  hydratePositionFilter();
  render();
}

function loadAnalyzeResponse(data, sourceName) {
  const reports = Array.isArray(data.reports) ? data.reports : data.schema ? [data] : [];
  if (!reports.length) throw new Error("no hands analyzed");
  const cached = reports.filter((report) => report.from_cache).length;
  loadReport(mergeReports(reports), sourceName);
  if (cached) {
    setStatus(t("status.fromCache", { text: els.schemaLabel.textContent, n: cached, total: reports.length }));
  }
}

async function analyzeText(text, sourceName) {
  const postflop = els.analyzeBackend.value || "equity";
  setLoadingStatus(t("status.analyzing", { name: sourceName, backend: postflop }));
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, filename: sourceName, postflop }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    loadAnalyzeResponse(data, sourceName);
  } catch (err) {
    setStatus(t("status.analyzeFailed", { msg: err.message }));
  }
}

async function openDataFilePicker() {
  setLoadingStatus(t("status.readingData"));
  els.loadDataButton.disabled = true;
  try {
    const resp = await fetch("/api/data-files");
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    renderDataFiles(data.files || []);
    els.dataFilePicker.hidden = false;
    setStatus(t("status.loadedDataList"));
  } catch (err) {
    setStatus(t("status.loadFailed", { msg: err.message }));
  } finally {
    els.loadDataButton.disabled = false;
  }
}

function renderDataFiles(files) {
  els.dataFileList.innerHTML = "";
  els.dataFileStatus.textContent = t("status.txtCount", { n: formatNumber(files.length) });
  files.forEach((file) => {
    const label = document.createElement("label");
    label.className = "data-file-item";
    const handCount = Number(file.hand_count || 0);
    label.innerHTML = `
      <input type="checkbox" value="${escapeHtml(file.name)}" ${handCount ? "checked" : ""} />
      <span class="data-file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
      <span class="data-file-hands">${escapeHtml(t("datafile.hands", { n: formatNumber(handCount) }))}</span>
      <span class="data-file-size">${formatBytes(file.size)}</span>
    `;
    els.dataFileList.append(label);
  });
}

function selectAllDataFiles() {
  const boxes = [...els.dataFileList.querySelectorAll('input[type="checkbox"]')];
  const shouldCheck = boxes.some((box) => !box.checked);
  boxes.forEach((box) => {
    box.checked = shouldCheck;
  });
}

async function analyzeSelectedDataFiles() {
  const files = [...els.dataFileList.querySelectorAll('input[type="checkbox"]:checked')].map(
    (box) => box.value,
  );
  if (!files.length) {
    els.dataFileStatus.textContent = t("status.selectOne");
    return;
  }
  await analyzeDataFolder(files);
}

async function analyzeDataFolder(files) {
  const postflop = els.analyzeBackend.value || "equity";
  setLoadingStatus(t("status.analyzingData", { n: formatNumber(files.length), backend: postflop }));
  els.loadDataButton.disabled = true;
  els.analyzeDataSelection.disabled = true;
  try {
    const resp = await fetch("/api/analyze-data", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ postflop, files, refresh: forceReanalyze() }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    loadAnalyzeResponse(data, "./data");
    els.dataFilePicker.hidden = true;
  } catch (err) {
    setStatus(t("status.analyzeFailed", { msg: err.message }));
  } finally {
    els.loadDataButton.disabled = false;
    els.analyzeDataSelection.disabled = false;
  }
}

async function loadFiles(files) {
  const txtFiles = files.filter((file) => file.name.toLowerCase().endsWith(".txt"));
  const jsonFiles = files.filter((file) => !file.name.toLowerCase().endsWith(".txt"));
  if (txtFiles.length && jsonFiles.length) {
    setStatus(t("status.loadSeparately"));
    return;
  }
  if (txtFiles.length) {
    const sources = await Promise.all(
      txtFiles.map(async (file) => ({ filename: file.name, text: await file.text() })),
    );
    await analyzeSources(sources, fileSourceName(txtFiles, "txt"));
    return;
  }
  try {
    const reports = await Promise.all(
      jsonFiles.map(async (file) => JSON.parse(await file.text())),
    );
    loadReport(mergeReports(reports), fileSourceName(jsonFiles, "json"));
  } catch (err) {
    setStatus(t("status.loadFailed", { msg: err.message }));
  }
}

async function analyzeSources(sources, sourceName) {
  const postflop = els.analyzeBackend.value || "equity";
  setLoadingStatus(t("status.analyzing", { name: sourceName, backend: postflop }));
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sources, postflop, refresh: forceReanalyze() }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    loadAnalyzeResponse(data, sourceName);
  } catch (err) {
    setStatus(t("status.analyzeFailed", { msg: err.message }));
  }
}

function forceReanalyze() {
  return Boolean(els.forceReanalyze?.checked);
}

function fileSourceName(files, extension) {
  return files.length === 1 ? files[0].name : `${formatNumber(files.length)} ${extension} files`;
}

async function loadReportFromQuery() {
  const url = new URL(window.location.href);
  const reportUrl = url.searchParams.get("report");
  if (!reportUrl) return;
  try {
    const response = await fetch(reportUrl);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    loadReport(await response.json(), reportUrl);
  } catch (error) {
    setStatus(t("status.couldNotLoad", { name: reportUrl }));
    console.error(error);
  }
}

function setStatus(message) {
  els.schemaLabel.textContent = message;
  hideLoadingOverlay();
}

function setLoadingStatus(message) {
  els.schemaLabel.innerHTML = `<span class="loading-spinner" aria-hidden="true"></span>${escapeHtml(message)}`;
  showLoadingOverlay(message);
}

function showLoadingOverlay(message) {
  if (!els.loadingOverlay) return;
  els.loadingOverlayText.textContent = message;
  els.loadingOverlay.classList.remove("hidden");
}

function hideLoadingOverlay() {
  els.loadingOverlay?.classList.add("hidden");
}

function byId(items) {
  return new Map(items.map((item) => [item.hand_id, item]));
}

function mergeReports(reports) {
  if (reports.length === 1) return reports[0];
  if (!reports.length) throw new Error("no reports selected");
  const schema = reports[0]?.schema || "unknown";
  if (reports.some((report) => (report?.schema || "unknown") !== schema)) {
    throw new Error("selected reports use different schemas");
  }
  const hands = reports.flatMap((report) => report.hands || []);
  assertUniqueHandIds(hands);
  const heroContexts = reports.flatMap((report) => report.hero_contexts || []);
  const handEvals = reports.flatMap((report) => report.hand_evals || []);
  return {
    schema,
    hands,
    hero_contexts: heroContexts,
    hand_evals: handEvals,
    stats: mergeStats(reports, hands, heroContexts, handEvals),
    opponents: mergeOpponents(reports.map((report) => report.opponents || {})),
    leaks: mergeLeaks(reports.flatMap((report) => report.leaks || [])),
  };
}

function assertUniqueHandIds(hands) {
  const seen = new Set();
  for (const hand of hands) {
    const id = hand?.hand_id;
    if (!id) continue;
    if (seen.has(id)) throw new Error(`duplicate hand id: ${id}`);
    seen.add(id);
  }
}

function mergeStats(reports, hands, heroContexts, handEvals) {
  const decisions = handEvals.flatMap((handEval) => handEval.decisions || []);
  const knownDecisions = decisions.filter((decision) => decision.tier && decision.tier !== "unknown");
  const good = knownDecisions.filter((decision) => decision.tier === "good").length;
  const mistakes = knownDecisions.filter((decision) => decision.tier === "mistake").length;
  const totalEvLoss = knownDecisions.reduce((sum, decision) => sum + numeric(decision.ev_loss_bb), 0);
  const byPosition = {};
  heroContexts.forEach((ctx) => {
    if (!ctx.position) return;
    byPosition[ctx.position] = (byPosition[ctx.position] || 0) + numeric(ctx.net);
  });
  return {
    hands: hands.length,
    gto_accuracy: knownDecisions.length ? good / knownDecisions.length : 0,
    ev_loss_per_100: hands.length ? (totalEvLoss / hands.length) * 100 : 0,
    mistakes,
    vpip: weightedStat(reports, "vpip"),
    pfr: weightedStat(reports, "pfr"),
    three_bet: weightedStat(reports, "three_bet"),
    fold_to_three_bet: weightedStat(reports, "fold_to_three_bet"),
    cbet: weightedStat(reports, "cbet"),
    wtsd: weightedStat(reports, "wtsd"),
    wsd: weightedStat(reports, "wsd"),
    aggression_factor: weightedStat(reports, "aggression_factor"),
    net_chips: heroContexts.reduce((sum, ctx) => sum + numeric(ctx.net), 0),
    by_position_net: byPosition,
  };
}

function weightedStat(reports, key) {
  const totalHands = reports.reduce((sum, report) => sum + numeric(report.stats?.hands), 0);
  if (!totalHands) return 0;
  return reports.reduce((sum, report) => {
    const hands = numeric(report.stats?.hands);
    return sum + numeric(report.stats?.[key]) * hands;
  }, 0) / totalHands;
}

function mergeOpponents(opponentSets) {
  const merged = {};
  opponentSets.forEach((opponents) => {
    Object.entries(opponents).forEach(([player, profile]) => {
      merged[player] = merged[player] ? mergeOpponentProfile(merged[player], profile) : profile;
    });
  });
  return merged;
}

function mergeLeaks(leaks) {
  const buckets = {};
  leaks.forEach((leak) => {
    const pattern = leak.pattern || "Unknown leak";
    const current = buckets[pattern] || {
      ...leak,
      pattern,
      count: 0,
      total_ev_loss_bb: 0,
      example_hand_ids: [],
    };
    current.count += numeric(leak.count);
    current.total_ev_loss_bb += numeric(leak.total_ev_loss_bb);
    current.example_hand_ids = uniqueStrings([
      ...(current.example_hand_ids || []),
      ...(leak.example_hand_ids || []),
    ]).slice(0, 3);
    buckets[pattern] = current;
  });
  return Object.values(buckets).sort(
    (a, b) => numeric(b.total_ev_loss_bb) - numeric(a.total_ev_loss_bb),
  );
}

function mergeOpponentProfile(a, b) {
  const totalHands = numeric(a.hands) + numeric(b.hands);
  return {
    ...a,
    ...b,
    player: a.player || b.player,
    hands: totalHands,
    vpip: weightedProfiles(a, b, "vpip", totalHands),
    pfr: weightedProfiles(a, b, "pfr", totalHands),
    three_bet: weightedProfiles(a, b, "three_bet", totalHands),
    fold_to_cbet: weightedProfiles(a, b, "fold_to_cbet", totalHands),
    tags: uniqueStrings([...(a.tags || []), ...(b.tags || [])]),
    exploit_notes: uniqueStrings([...(a.exploit_notes || []), ...(b.exploit_notes || [])]),
    assumed_range_key: b.assumed_range_key || a.assumed_range_key,
  };
}

function weightedProfiles(a, b, key, totalHands) {
  if (!totalHands) return 0;
  return (numeric(a[key]) * numeric(a.hands) + numeric(b[key]) * numeric(b.hands)) / totalHands;
}

function uniqueStrings(items) {
  return [...new Set(items.filter(Boolean))];
}

function numeric(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function render() {
  renderDashboard();
  renderHandList();
  renderInsights();
  renderSelectedHand();
}

function renderDashboard() {
  const stats = state.report?.stats || {};
  const netBb = aggregateNetBb(state.hands, state.contextsById);
  const netChips = Number(stats.net_chips || 0);
  updateChipUnitToggle();
  els.metricNetLabel.textContent = state.chipUnit === "bb" ? t("metric.netBb") : t("metric.netChips");
  els.metricHands.textContent = formatNumber(stats.hands || state.hands.length || 0);
  els.metricAccuracy.textContent = pct(stats.gto_accuracy);
  els.metricEvLoss.textContent = isNumber(stats.ev_loss_per_100)
    ? `${stats.ev_loss_per_100.toFixed(1)}bb`
    : "--";
  els.metricNet.textContent =
    state.chipUnit === "bb"
      ? formatBbValue(netBb, { signed: true })
      : signed(netChips);
  els.metricNet.className = (state.chipUnit === "bb" ? netBb : netChips) >= 0 ? "positive" : "negative";
  els.metricMistakes.textContent = formatNumber(stats.mistakes || 0);
  els.metricEngines.textContent = engineMixText();
  renderSolveAllControl();
}

function renderSolveAllControl() {
  if (!els.solveAllButton) return;
  const remaining = solverTargets().length;
  const batch = state.solverBatch;
  els.solveAllButton.disabled = !state.report || batch.running || remaining === 0;
  if (batch.running) {
    els.solveAllButton.textContent = t("solveAll.solving");
    els.solveAllStatus.textContent = `${formatNumber(batch.done)} / ${formatNumber(batch.total)}`;
    return;
  }
  els.solveAllButton.textContent = remaining
    ? t("solveAll.run", { n: formatNumber(remaining) })
    : t("solveAll.done");
  els.solveAllStatus.textContent =
    batch.error ||
    batchSummary(batch) ||
    (batch.failed ? t("batch.failed", { n: formatNumber(batch.failed) }) : "");
}

function renderHandList() {
  const hands = filteredHands();
  els.handCount.textContent = formatNumber(hands.length);
  els.handList.innerHTML = "";

  if (!state.report) {
    els.handList.append(emptyList(t("empty.noReport")));
    return;
  }

  if (!hands.length) {
    els.handList.append(emptyList(t("empty.noMatch")));
    return;
  }

  if (!hands.some((hand) => hand.hand_id === state.selectedHandId)) {
    state.selectedHandId = hands[0]?.hand_id || null;
    state.selectedStreet = "preflop";
    renderSelectedHand();
  }

  groupHandsBySource(hands).forEach((group) => {
    const header = document.createElement("div");
    header.className = "hand-source-header";
    const { id, rest } = splitSourceTitle(group.source);
    header.innerHTML = `
      <div class="hand-source-name">
        <span class="hand-source-id">${escapeHtml(id)}</span>
        ${rest ? `<span class="hand-source-rest">${escapeHtml(rest)}</span>` : ""}
      </div>
      <span class="hand-source-count">${escapeHtml(t("datafile.hands", { n: formatNumber(group.hands.length) }))}</span>
    `;
    els.handList.append(header);
    group.hands.forEach((hand) => renderHandRow(hand));
  });
}

function renderHandRow(hand) {
    const ctx = state.contextsById.get(hand.hand_id);
    const ev = state.evalsById.get(hand.hand_id);
    const row = document.createElement("button");
    row.type = "button";
    row.className = `hand-row row-${ev?.hand_tier || "unknown"} ${
      hand.hand_id === state.selectedHandId ? "active" : ""
    }`;
    row.addEventListener("click", () => {
      state.selectedHandId = hand.hand_id;
      state.selectedStreet = firstStreet(hand);
      stopReplay();
      renderHandList();
      renderSelectedHand();
    });

    const main = document.createElement("div");
    main.innerHTML = `
      <div class="hand-id">${escapeHtml(hand.hand_id)}</div>
      <div class="hand-sub">
        <span>${escapeHtml(cardsText(hand.hero_hole))}</span>
        <span>${escapeHtml(ctx?.position || "--")}</span>
        <span>${escapeHtml(t("handSub.decisions", { n: decisionCount(ev) }))}</span>
      </div>
    `;
    row.append(main);

    const net = document.createElement("span");
    net.className = `net-badge ${ctx?.net >= 0 ? "positive" : "negative"}`;
    net.textContent = formatChips(ctx?.net || 0, hand, { signed: true });
    row.append(net);

    els.handList.append(row);
}

function splitSourceTitle(source) {
  // 檔名格式為「編號 - 賽事名稱.txt」；以首個 " - " 切開，編號獨立一行。
  const sep = source.indexOf(" - ");
  if (sep === -1) return { id: source, rest: "" };
  return { id: source.slice(0, sep), rest: source.slice(sep + 3) };
}

function groupHandsBySource(hands) {
  const groups = [];
  const bySource = new Map();
  hands.forEach((hand) => {
    const source = hand.source_file || "Unknown source";
    if (!bySource.has(source)) {
      const group = { source, hands: [] };
      bySource.set(source, group);
      groups.push(group);
    }
    bySource.get(source).hands.push(hand);
  });
  return groups;
}

function renderSelectedHand() {
  const hand = selectedHand();
  if (!hand) {
    els.emptyState.classList.remove("hidden");
    els.reviewView.classList.add("hidden");
    return;
  }

  els.emptyState.classList.add("hidden");
  els.reviewView.classList.remove("hidden");

  const ctx = state.contextsById.get(hand.hand_id);
  const ev = state.evalsById.get(hand.hand_id);
  const views = streetViews(hand);
  if (!views.some((view) => view.key === state.selectedStreet)) {
    state.selectedStreet = firstStreet(hand);
  }

  els.selectedHandId.textContent = hand.hand_id;
  els.selectedTierDot.className = `tier-dot tier-${ev?.hand_tier || "unknown"}`;
  els.selectedMeta.textContent = [
    ctx?.position,
    t("meta.net", { value: formatChips(ctx?.net || 0, hand, { signed: true }) }),
    boardText(hand.final_board),
  ]
    .filter(Boolean)
    .join(" · ");

  renderStreetTabs(hand);
  renderHeroHole(hand);
  renderSeats(hand);
  renderBoard(hand);
  renderTimeline(hand);
  renderDecisions(hand);
}

function renderStreetTabs(hand) {
  els.streetTabs.innerHTML = "";
  streetViews(hand).forEach((view) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = view.label;
    button.className = view.key === state.selectedStreet ? "active" : "";
    button.addEventListener("click", () => {
      state.selectedStreet = view.key;
      stopReplay();
      renderSelectedHand();
    });
    els.streetTabs.append(button);
  });
}

function renderSeats(hand) {
  els.seatRing.innerHTML = "";
  const seats = hand.seats || [];
  const count = Math.max(seats.length, 1);
  const positions = playerPositionMap(hand);
  const stacks = stackByPlayerAtStreet(hand);
  const shownCards = shownCardsByPlayer(hand);
  seats.forEach((seat, index) => {
    const point = seatPoint(index, count);
    const position = positions.get(seat.player) || `Seat ${seat.seat}`;
    const seatLabel = seat.is_hero ? "Hero" : "";
    const cards = !seat.is_hero ? shownCards.get(seat.player) || [] : [];
    const node = document.createElement("div");
    node.className = `seat ${seat.is_hero ? "hero" : ""}`;
    node.style.left = `${point.x}%`;
    node.style.top = `${point.y}%`;
    node.style.transform = "translate(-50%, -50%)";
    node.innerHTML = `
      <div class="seat-main">
        <span class="seat-name">${escapeHtml(position)}</span>
        ${seatLabel ? `<span class="seat-player">${escapeHtml(seatLabel)}</span>` : ""}
      </div>
      <div class="seat-stack">${formatChips(stacks.get(seat.player) ?? seat.stack, hand)}</div>
      ${cards.length ? `<div class="seat-cards">${cards.map(cardMarkup).join("")}</div>` : ""}
    `;
    els.seatRing.append(node);
  });
}

function seatPoint(index, count) {
  const angle = -90 + (360 / count) * index;
  const radians = (angle * Math.PI) / 180;
  const radiusX = count <= 6 ? 37 : 38;
  const radiusY = count <= 6 ? 32 : 34;
  return {
    x: 50 + Math.cos(radians) * radiusX,
    y: 50 + Math.sin(radians) * radiusY,
  };
}

function renderHeroHole(hand) {
  els.heroHoleCards.innerHTML = "";
  (hand.hero_hole || []).forEach((card) => els.heroHoleCards.append(cardNode(card)));
}

function renderBoard(hand) {
  const street = currentStreet(hand);
  const board = street?.board?.length ? street.board : [];
  els.boardCards.innerHTML = "";
  els.boardCards.classList.toggle("empty-board", !board.length);
  els.potInfo.classList.toggle("empty-pot", !board.length);
  if (!board.length) {
    els.potInfo.textContent = "";
    return;
  }
  board.forEach((card) => els.boardCards.append(cardNode(card)));
  els.potInfo.textContent = t("pot.info", { pot: formatChips(hand.total_pot || 0, hand) });
}

function cardNode(card) {
  const text = cardText(card);
  const node = document.createElement("span");
  node.className = `card ${isRedCard(card) ? "red-card" : ""}`;
  node.textContent = text;
  return node;
}

function cardMarkup(card) {
  const text = cardText(card);
  const red = isRedCard(card) ? " red-card" : "";
  return `<span class="card mini-card${red}">${escapeHtml(text)}</span>`;
}

function stackByPlayerAtStreet(hand) {
  const stacks = new Map((hand.seats || []).map((seat) => [seat.player, Number(seat.stack || 0)]));
  streetsThroughSelected(hand).forEach((street) => {
    const committed = new Map();
    (street.actions || []).forEach((action) => {
      if (!action.player || !stacks.has(action.player)) return;
      applyChipMovement(stacks, committed, action);
    });
  });
  return stacks;
}

function applyChipMovement(stacks, committed, action) {
  const player = action.player;
  const amount = Number(action.amount || 0);
  const toAmount = Number(action.to_amount || 0);
  const current = Number(committed.get(player) || 0);
  if (action.type === "collect") {
    stacks.set(player, stacks.get(player) + amount);
    return;
  }
  if (action.type === "uncalled") {
    stacks.set(player, stacks.get(player) + amount);
    committed.set(player, Math.max(0, current - amount));
    return;
  }
  if (action.type === "show" || action.type === "muck" || !amount) return;

  if (action.type === "raise" && toAmount > 0) {
    const delta = Math.max(0, toAmount - current);
    stacks.set(player, stacks.get(player) - delta);
    committed.set(player, toAmount);
    return;
  }

  stacks.set(player, stacks.get(player) - amount);
  if (action.type !== "ante") {
    committed.set(player, current + amount);
  }
}

function streetsThroughSelected(hand) {
  const streets = hand.streets || [];
  const index = streets.findLastIndex((street) => streetViewKey(street.street) === state.selectedStreet);
  if (index < 0) return [];
  return streets.slice(0, index + 1);
}

function shownCardsByPlayer(hand) {
  const visible = currentStreetGroup(hand).some((street) => street.street === "showdown");
  if (!visible) return new Map();
  return new Map(
    (hand.showdowns || [])
      .filter((showdown) => !showdown.mucked && showdown.hole?.length)
      .map((showdown) => [showdown.player, showdown.hole]),
  );
}

function currentStreetGroup(hand) {
  return (hand.streets || []).filter((street) => streetViewKey(street.street) === state.selectedStreet);
}

function renderTimeline(hand) {
  const streets = currentStreetGroup(hand);
  els.streetLabel.textContent = labelStreetView(state.selectedStreet, hand);
  els.actionTimeline.innerHTML = "";
  const positions = playerPositionMap(hand);
  const actions = streets.flatMap((street) => street.actions || []).filter((action) => {
    return !(state.selectedStreet === "preflop" && action.type === "ante");
  });
  if (!actions.length) {
    els.actionTimeline.append(emptyList(t("empty.noActions")));
    return;
  }

  actions.forEach((action) => {
    const item = document.createElement("div");
    item.className = `action-item ${action.player === hand.hero ? "hero-action" : ""}`;
    item.innerHTML = `
      <div class="action-player">${escapeHtml(displayPlayer(action.player, hand, positions))}</div>
      <div class="action-text">${escapeHtml(actionText(action, hand))}</div>
      ${action.all_in ? `<span class="pill mistake">${escapeHtml(t("action.allIn"))}</span>` : ""}
    `;
    els.actionTimeline.append(item);
  });
}

function renderDecisions(hand) {
  const ctx = state.contextsById.get(hand.hand_id);
  const ev = state.evalsById.get(hand.hand_id);
  const positions = playerPositionMap(hand);
  const decisions = (ctx?.decisions || [])
    .map((decision, index) => ({
      index,
      ctx: decision,
      ev: ev?.decisions?.[index],
    }))
    .filter((pair) => streetViewKey(pair.ctx.street) === state.selectedStreet);

  els.decisionCount.textContent = `${decisions.length}`;
  els.decisionList.innerHTML = "";

  if (!decisions.length) {
    els.decisionList.append(emptyList(t("empty.noDecision")));
    return;
  }

  decisions.forEach((pair) => {
    const tier = pair.ev?.tier || "unknown";
    const card = document.createElement("div");
    card.className = "decision-card";
    card.innerHTML = `
      <span class="tier-strip tier-${tier}"></span>
      <div class="decision-main">
        <div class="decision-line">
          <strong>${escapeHtml(labelStreet(pair.ctx.street))} · ${escapeHtml(pair.ctx.hero_action.type)}</strong>
          ${sourceBadge(pair.ev)}
          ${sourceDetailBadge(pair.ev)}
          ${solverDeltaBadge(pair.ev)}
          <span class="pill ${tier}">${escapeHtml(t(`tier.${tier}`))}</span>
          ${solverButton(pair, hand, ctx)}
        </div>
        <div class="muted">
          ${escapeHtml(t("decision.facing", { facing: pair.ctx.facing }))}${pair.ctx.villain ? escapeHtml(t("decision.vs", { villain: displayPlayer(pair.ctx.villain, hand, positions) })) : ""}
          · ${escapeHtml(t("decision.pot", { pot: formatChips(pair.ctx.pot_before, hand) }))}
          · ${escapeHtml(t("decision.toCall", { toCall: formatChips(pair.ctx.to_call || 0, hand) }))}
        </div>
        <div>${escapeHtml(explainText(pair.ev))}</div>
        <div class="suggestions">${suggestionPills(pair.ev)}</div>
      </div>
    `;
    const button = card.querySelector("[data-run-solver]");
    if (button) {
      button.addEventListener("click", () => runSolver(hand, ctx, pair));
    }
    els.decisionList.append(card);
  });
}

function solverButton(pair, hand, ctx) {
  if (!ctx || pair.ctx.street === "preflop") return "";
  const source = pair.ev?.suggestion?.source;
  const key = solverRunKey(hand.hand_id, pair.index);
  const running = state.solverRunning.has(key) || state.solverBatch.running;
  const label = source === "solver" ? t("solver.again") : t("solver.run");
  return `<button class="solver-button" data-run-solver="${pair.index}" ${running ? "disabled" : ""}>${escapeHtml(running ? t("solver.solving") : label)}</button>`;
}

async function runSolver(hand, ctx, pair) {
  const key = solverRunKey(hand.hand_id, pair.index);
  state.solverRunning.add(key);
  renderDecisions(hand);
  try {
    await solvePair(hand, ctx, pair);
    renderDashboard();
    renderHandList();
    renderSelectedHand();
  } catch (error) {
    alert(t("solver.unavailable", { msg: error.message || error }));
  } finally {
    state.solverRunning.delete(key);
    renderSelectedHand();
  }
}

async function runAllSolvers() {
  const targets = solverTargets();
  if (!targets.length || state.solverBatch.running) return;
  state.solverBatch = {
    running: true,
    total: targets.length,
    done: 0,
    failed: 0,
    changed: 0,
    up: 0,
    down: 0,
    flat: 0,
    error: "",
  };
  renderDashboard();
  renderSelectedHand();

  let firstError = "";
  for (const target of targets) {
    try {
      const result = await solvePair(target.hand, target.ctx, target.pair);
      recordSolverDelta(result?.decision_eval?.solver_delta, state.solverBatch);
    } catch (error) {
      state.solverBatch.failed += 1;
      const message = error.message || String(error);
      firstError ||= `${target.hand.hand_id} #${target.pair.index}: ${message}`;
      state.solverBatch.error = firstError;
      console.error("Solver failed", target.hand.hand_id, target.pair.index, error);
      if (isGlobalSolverError(message)) {
        break;
      }
    } finally {
      state.solverBatch.done += 1;
      renderDashboard();
    }
  }

  const failed = state.solverBatch.failed;
  const error = state.solverBatch.error;
  const checked = state.solverBatch.done;
  const { changed, up, down, flat } = state.solverBatch;
  state.solverBatch = { running: false, total: 0, done: checked, failed, changed, up, down, flat, error };
  renderDashboard();
  renderHandList();
  renderSelectedHand();
  if (failed) {
    alert(
      t("solver.batchFailed", {
        n: formatNumber(checked),
        plural: state.lang === "zh" || checked === 1 ? "" : "s",
        err: error || "unknown",
      }),
    );
  }
}

function isGlobalSolverError(message) {
  return [
    "UI solver requires starting",
    "solver 後端需要",
    "找不到 solver adapter",
    "solver 沒有輸出策略 JSON",
    "solver stdout 不是合法 JSON",
    "solver 超時",
  ].some((text) => message.includes(text));
}

async function solvePair(hand, ctx, pair) {
  const response = await fetch("/api/solve", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(solverPayload(hand, ctx, pair)),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "Solver request failed");
  }
  applySolverResult(hand.hand_id, pair.index, result.decision_eval);
  return result;
}

function solverTargets() {
  if (!state.report) return [];
  const targets = [];
  state.hands.forEach((hand) => {
    const ctx = state.contextsById.get(hand.hand_id);
    const ev = state.evalsById.get(hand.hand_id);
    if (!ctx || !ev) return;
    (ctx.decisions || []).forEach((decision, index) => {
      if (decision.street === "preflop") return;
      const decisionEval = ev.decisions?.[index];
      if (decisionEval?.suggestion?.source === "solver") return;
      targets.push({
        hand,
        ctx,
        pair: { index, ctx: decision, ev: decisionEval },
      });
    });
  });
  return targets;
}

function solverPayload(hand, ctx, pair) {
  const street = (hand.streets || []).find((item) => item.street === pair.ctx.street);
  const bb = hand.tournament?.bb || 1;
  const opponent = pair.ctx.villain ? state.report?.opponents?.[pair.ctx.villain] : null;
  return {
    hand_id: hand.hand_id,
    decision_index: pair.index,
    source_file: hand.source_file || null,
    node: {
      street: pair.ctx.street,
      hero_hole: hand.hero_hole || [],
      board: street?.board || [],
      pot_before: pair.ctx.pot_before,
      to_call: pair.ctx.to_call || 0,
      eff_stack: Math.round((ctx.eff_stack_bb || 0) * bb),
      villain_range_key: opponent?.assumed_range_key || null,
      bb,
    },
    decision: pair.ctx,
  };
}

function applySolverResult(handId, decisionIndex, decisionEval) {
  const handEval = state.evalsById.get(handId);
  if (!handEval || !decisionEval) return;
  handEval.decisions[decisionIndex] = decisionEval;
  handEval.hand_tier = worstTier(handEval.decisions || []);
  recomputeSolverStats();
}

// Solver persists to a per-file cache, so its returned stats are per-file.
// Recompute the displayed (merged) accuracy/EV-loss/mistakes from all loaded evals instead.
function recomputeSolverStats() {
  const stats = state.report?.stats;
  if (!stats) return;
  const decisions = [];
  state.evalsById.forEach((handEval) => {
    (handEval.decisions || []).forEach((decision) => decisions.push(decision));
  });
  const known = decisions.filter((decision) => decision.tier && decision.tier !== "unknown");
  const good = known.filter((decision) => decision.tier === "good").length;
  const totalEvLoss = known.reduce((sum, decision) => sum + numeric(decision.ev_loss_bb), 0);
  const hands = state.hands.length;
  stats.gto_accuracy = known.length ? good / known.length : 0;
  stats.ev_loss_per_100 = hands ? (totalEvLoss / hands) * 100 : 0;
  stats.mistakes = known.filter((decision) => decision.tier === "mistake").length;
}

function worstTier(decisions) {
  const severity = { good: 0, unknown: 1, inaccuracy: 2, mistake: 3 };
  return decisions.reduce((worst, decision) => {
    return (severity[decision.tier] || 0) > (severity[worst] || 0) ? decision.tier : worst;
  }, "unknown");
}

function solverRunKey(handId, index) {
  return `${handId}:${index}`;
}

const SOURCE_META = {
  preflop_chart: { label: "chart", cls: "src-chart", titleKey: "src.chart.title" },
  equity_backend: { label: "equity", cls: "src-equity", titleKey: "src.equity.title" },
  solver: { label: "solver", cls: "src-solver", titleKey: "src.solver.title" },
  unknown: { label: "n/a", cls: "src-unknown", titleKey: "src.unknown.title" },
};

function explainText(ev) {
  if (!ev) return t("decision.noEval");
  const key = ev.explanation_key;
  const hasKey = key && (I18N[state.lang]?.[key] != null || I18N.en[key] != null);
  if (!hasKey) return ev.explanation || t("decision.noEval");
  const params = { ...(ev.explanation_params || {}) };
  if (params.source != null) {
    const mapped = t(`explain.src.${params.source}`);
    params.source = mapped === `explain.src.${params.source}` ? params.source : mapped;
  }
  return t(key, params);
}

function sourceBadge(ev) {
  const source = ev?.suggestion?.source || "unknown";
  const meta = SOURCE_META[source] || { label: source, cls: "src-unknown", titleKey: "src.unknown.title" };
  const title = meta.titleKey ? t(meta.titleKey) : source;
  return `<span class="src-badge ${meta.cls}" title="${escapeHtml(title)}"><span>${escapeHtml(t("badge.engine"))}</span>${escapeHtml(meta.label)}</span>`;
}

function sourceDetailBadge(ev) {
  const detail = ev?.suggestion?.detail;
  if (!detail || ev?.suggestion?.source !== "preflop_chart") return "";
  const sourceType = detail.chart_source_type === "solver_chart" ? t("src.solverChart") : t("src.builtIn");
  const bucket = detail.stack_bucket || "";
  const action = detail.action || "";
  const label = [bucket, sourceType].filter(Boolean).join(" · ");
  const title = [
    detail.chart_id ? t("detail.chart", { v: detail.chart_id }) : "",
    detail.chart_source ? t("detail.source", { v: detail.chart_source }) : "",
    detail.chart_version ? t("detail.version", { v: detail.chart_version }) : "",
    detail.effective_stack_bb ? t("detail.effective", { v: detail.effective_stack_bb }) : "",
    action ? t("detail.spot", { v: action }) : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `<span class="source-detail-badge" title="${escapeHtml(title)}">${escapeHtml(label || t("src.chartDetail"))}</span>`;
}

function solverDeltaBadge(ev) {
  const delta = ev?.solver_delta;
  if (!delta) return "";
  const direction = ["up", "down", "flat"].includes(delta.direction) ? delta.direction : "flat";
  const label = deltaLabel(delta);
  const evText = evDeltaText(delta.ev_loss_delta_bb);
  const title = [
    delta.summary,
    delta.previous_best_action && delta.best_action
      ? t("delta.best", { a: delta.previous_best_action, b: delta.best_action })
      : "",
    evText ? t("delta.evLoss", { ev: evText }) : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `<span class="delta-badge delta-${direction}" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

function deltaLabel(delta) {
  const marker = delta.direction === "up" ? "↑" : delta.direction === "down" ? "↓" : "→";
  if (!delta.changed) return `${marker} ${t("delta.noChange")}`;
  if (delta.previous_best_action && delta.best_action && delta.previous_best_action !== delta.best_action) {
    return `${marker} ${delta.previous_best_action}→${delta.best_action}`;
  }
  const evText = evDeltaText(delta.ev_loss_delta_bb);
  return evText ? `${marker} ${evText}` : `${marker} ${t("delta.changed")}`;
}

function evDeltaText(value) {
  if (!isNumber(value) || Math.abs(value) < 0.01) return "";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}bb`;
}

function recordSolverDelta(delta, batch) {
  if (!delta) return;
  if (delta.changed) batch.changed += 1;
  if (delta.direction === "up") batch.up += 1;
  else if (delta.direction === "down") batch.down += 1;
  else batch.flat += 1;
}

function batchSummary(batch) {
  if (!batch.done || batch.running) return "";
  const parts = [];
  if (batch.changed) parts.push(t("batch.changed", { n: formatNumber(batch.changed) }));
  if (batch.up) parts.push(`↑${formatNumber(batch.up)}`);
  if (batch.down) parts.push(`↓${formatNumber(batch.down)}`);
  if (batch.flat) parts.push(`→${formatNumber(batch.flat)}`);
  if (batch.failed) parts.push(t("batch.failed", { n: formatNumber(batch.failed) }));
  return parts.length ? `${t("batch.saved")} · ${parts.join(" ")}` : "";
}

function suggestionPills(ev) {
  const actions = ev?.suggestion?.actions || [];
  if (!actions.length) return "";
  return actions
    .map(([action, freq]) => {
      const pctText = `${Math.round((Number(freq) || 0) * 100)}%`;
      return `<span class="pill unknown">${escapeHtml(action)} ${pctText}</span>`;
    })
    .join("");
}

function renderInsights() {
  renderLeaks();
  renderPositionBars();
  renderOpponents();
}

function leakLabel(leak) {
  // 後端附帶結構化欄位時依介面語言重組；否則退回字面 pattern（相容舊報告）。
  if (leak.street && leak.best_action) {
    return t("leak.pattern", {
      street: labelStreet(leak.street),
      action: leak.hero_action || "",
      best: leak.best_action,
    });
  }
  return leak.pattern || "";
}

function renderLeaks() {
  const leaks = state.report?.leaks || [];
  els.leakCount.textContent = formatNumber(leaks.length);
  els.leakList.innerHTML = "";
  if (!leaks.length) {
    els.leakList.append(emptyList(t("empty.noLeaks")));
    return;
  }
  leaks.slice(0, 8).forEach((leak) => {
    const node = document.createElement("button");
    node.type = "button";
    node.className = "leak-card";
    node.innerHTML = `
      <div class="leak-title">${escapeHtml(leakLabel(leak))}</div>
      <div class="leak-meta">${leak.count}x · ${Number(leak.total_ev_loss_bb || 0).toFixed(2)}bb</div>
      <div class="leak-meta">${(leak.example_hand_ids || []).map(escapeHtml).join(", ")}</div>
    `;
    node.addEventListener("click", () => {
      const id = leak.example_hand_ids?.[0];
      if (id) {
        state.selectedHandId = id;
        state.selectedStreet = "preflop";
        renderHandList();
        renderSelectedHand();
      }
    });
    els.leakList.append(node);
  });
}

function renderPositionBars() {
  const values = state.chipUnit === "bb"
    ? positionNetBbEntries()
    : Object.entries(state.report?.stats?.by_position_net || {});
  els.positionBars.innerHTML = "";
  if (!values.length) {
    els.positionBars.append(emptyList(t("empty.noPosition")));
    return;
  }

  const max = Math.max(...values.map(([, value]) => Math.abs(Number(value))), 1);
  values
    .sort(([a], [b]) => positionOrder(a) - positionOrder(b))
    .forEach(([position, value]) => {
      const net = Number(value);
      const node = document.createElement("div");
      node.className = "bar-item";
      node.innerHTML = `
        <strong>${escapeHtml(position)}</strong>
        <div class="bar-track"><div class="bar-fill ${net < 0 ? "loss" : ""}" style="width:${Math.max(4, (Math.abs(net) / max) * 100)}%"></div></div>
        <span class="${net >= 0 ? "positive" : "negative"}">${formatPositionNet(position, net)}</span>
      `;
      els.positionBars.append(node);
    });
}

function positionNetBbEntries() {
  const totals = {};
  state.hands.forEach((hand) => {
    const ctx = state.contextsById.get(hand.hand_id);
    if (!ctx?.position) return;
    totals[ctx.position] = (totals[ctx.position] || 0) + chipsToBb(ctx.net, bigBlind(hand));
  });
  return Object.entries(totals);
}

function formatPositionNet(position, value) {
  if (state.chipUnit === "bb") return formatBbValue(value, { signed: true });
  return signed(value);
}

function renderOpponents() {
  const opponents = Object.values(state.report?.opponents || {});
  els.opponentList.innerHTML = "";
  if (!opponents.length) {
    els.opponentList.append(emptyList(t("empty.noOpponents")));
    return;
  }
  opponents
    .sort((a, b) => (b.hands || 0) - (a.hands || 0))
    .slice(0, 8)
    .forEach((opp) => {
      const node = document.createElement("div");
      node.className = "opponent-card";
      node.innerHTML = `
        <div class="opponent-name">${escapeHtml(opp.player)}</div>
        <div class="opponent-meta">
          ${escapeHtml(t("opp.meta", { n: opp.hands, vpip: pct(opp.vpip), pfr: pct(opp.pfr) }))}
        </div>
        <div class="suggestions">
          ${(opp.tags || []).map((tag) => `<span class="pill unknown">${escapeHtml(tag)}</span>`).join("")}
          ${opp.assumed_range_key ? `<span class="pill good">${escapeHtml(opp.assumed_range_key)}</span>` : ""}
        </div>
      `;
      els.opponentList.append(node);
    });
}

function filteredHands() {
  return state.hands.filter((hand) => {
    const ctx = state.contextsById.get(hand.hand_id);
    const ev = state.evalsById.get(hand.hand_id);
    const text = [
      hand.hand_id,
      cardsText(hand.hero_hole),
      ctx?.position,
      ev?.hand_tier,
      boardText(hand.final_board),
    ]
      .join(" ")
      .toLowerCase();

    if (state.search && !text.includes(state.search)) return false;
    if (state.positionFilter !== "all" && ctx?.position !== state.positionFilter) return false;
    if (state.resultFilter === "win" && !(ctx?.net > 0)) return false;
    if (state.resultFilter === "loss" && !(ctx?.net < 0)) return false;
    if (!matchesTierStreet(ctx, ev, state.tierFilter, state.streetFilter)) return false;
    return true;
  });
}

function matchesTierStreet(ctx, ev, tiers, streets) {
  if (!tiers.size && !streets.size) return true;
  const decisions = ctx?.decisions || [];
  return decisions.some((decision, index) => {
    if (streets.size && !streets.has(decision.street)) return false;
    if (tiers.size && !tiers.has(ev?.decisions?.[index]?.tier || "unknown")) return false;
    return true;
  });
}

function hydratePositionFilter() {
  const positions = [...new Set((state.report?.hero_contexts || []).map((ctx) => ctx.position))]
    .filter(Boolean)
    .sort((a, b) => positionOrder(a) - positionOrder(b));
  els.positionFilter.innerHTML = `<option value="all" data-i18n="position.all">${escapeHtml(t("position.all"))}</option>`;
  positions.forEach((position) => {
    const option = document.createElement("option");
    option.value = position;
    option.textContent = position;
    els.positionFilter.append(option);
  });
  state.positionFilter = "all";
}

function selectedHand() {
  return state.hands.find((hand) => hand.hand_id === state.selectedHandId) || null;
}

function currentStreet(hand) {
  const streets = currentStreetGroup(hand);
  if (state.selectedStreet === "river") {
    return streets.find((street) => street.street === "river") || streets.at(-1);
  }
  return streets[0];
}

function firstStreet(hand) {
  return streetViews(hand)[0]?.key || "preflop";
}

function stepStreet(direction) {
  const hand = selectedHand();
  if (!hand) return;
  const streets = streetViews(hand).map((view) => view.key);
  const current = Math.max(0, streets.indexOf(state.selectedStreet));
  state.selectedStreet = streets[(current + direction + streets.length) % streets.length];
  renderSelectedHand();
}

function toggleReplay() {
  if (state.replayTimer) {
    stopReplay();
    return;
  }
  els.playReplay.textContent = "Ⅱ";
  state.replayTimer = window.setInterval(() => stepStreet(1), 1200);
}

function stopReplay() {
  if (state.replayTimer) {
    window.clearInterval(state.replayTimer);
    state.replayTimer = null;
  }
  els.playReplay.textContent = "▶";
}

function emptyList(text) {
  const node = document.createElement("div");
  node.className = "empty-list";
  node.textContent = text;
  return node;
}

function decisionCount(ev) {
  return ev?.decisions?.length || 0;
}

function engineMixText() {
  if (!state.report) return "--";
  const counts = {};
  (state.report?.hand_evals || []).forEach((handEval) => {
    (handEval.decisions || []).forEach((decision) => {
      const source = normalizeDecisionSource(decision);
      counts[source] = (counts[source] || 0) + 1;
    });
  });
  const order = ["solver", "solver-chart", "equity", "chart", "unknown"];
  const parts = order
    .filter((source) => source === "solver" || counts[source])
    .map((source) => `${source} ${formatNumber(counts[source])}`);
  return parts.length ? parts.join(" · ") : "--";
}

function normalizeSource(source) {
  if (source === "preflop_chart") return "chart";
  if (source === "equity_backend") return "equity";
  if (source === "solver") return "solver";
  return "unknown";
}

function normalizeDecisionSource(decision) {
  if (
    decision?.suggestion?.source === "preflop_chart" &&
    decision?.suggestion?.detail?.chart_source_type === "solver_chart"
  ) {
    return "solver-chart";
  }
  return normalizeSource(decision?.suggestion?.source);
}

function actionText(action, hand) {
  if (!action) return "";
  const amount = action.to_amount
    ? `${formatChips(action.amount, hand)} ${t("action.to")} ${formatChips(action.to_amount, hand)}`
    : formatChips(action.amount, hand);
  if (["fold", "check"].includes(action.type)) return t(`action.${action.type}`);
  if (action.type === "small_blind") return t("action.postsSb", { amount });
  if (action.type === "big_blind") return t("action.postsBb", { amount });
  if (action.type === "uncalled") return t("action.returned", { amount });
  if (action.type === "collect") return t("action.collected", { amount });
  return `${action.type} ${amount}`;
}

function playerPositionMap(hand) {
  const seats = [...(hand.seats || [])].sort((a, b) => a.seat - b.seat);
  if (!seats.length) return new Map();
  const buttonIndex = Math.max(0, seats.findIndex((seat) => seat.seat === hand.button_seat));
  const ordered = seats.slice(buttonIndex).concat(seats.slice(0, buttonIndex));
  const positions = positionsForCount(ordered.length);
  return new Map(ordered.map((seat, index) => [seat.player, positions[index] || `Seat ${seat.seat}`]));
}

function positionsForCount(count) {
  const byCount = {
    2: ["BTN", "BB"],
    3: ["BTN", "SB", "BB"],
    4: ["BTN", "SB", "BB", "CO"],
    5: ["BTN", "SB", "BB", "UTG", "CO"],
    6: ["BTN", "SB", "BB", "UTG", "HJ", "CO"],
    7: ["BTN", "SB", "BB", "UTG", "MP", "HJ", "CO"],
    8: ["BTN", "SB", "BB", "UTG", "UTG+1", "MP", "HJ", "CO"],
  };
  return byCount[count] || byCount[8].slice(0, count);
}

function displayPlayer(player, hand, positions) {
  const position = positions.get(player) || player;
  return player === hand.hero ? `${position} · ${t("hero")}` : position;
}

function labelStreet(street) {
  const keys = {
    preflop: "street.preflop",
    flop: "street.flop",
    turn: "street.turn",
    river: "street.river",
    showdown: "street.showdown",
  };
  return keys[street] ? t(keys[street]) : street || "--";
}

function streetViewKey(street) {
  return street === "showdown" ? "river" : street;
}

function streetViews(hand) {
  const groups = [];
  const seen = new Set();
  (hand?.streets || []).forEach((street) => {
    const key = streetViewKey(street.street);
    if (seen.has(key)) return;
    seen.add(key);
    groups.push({ key, label: labelStreetView(key, hand) });
  });
  return groups;
}

function labelStreetView(key, hand) {
  const hasShowdown = (hand?.streets || []).some((street) => street.street === "showdown");
  if (key === "river" && hasShowdown) return t("street.riverShowdown");
  return labelStreet(key);
}

function positionOrder(position) {
  return ["UTG", "UTG+1", "MP", "HJ", "CO", "BTN", "SB", "BB"].indexOf(position);
}

const SUIT_SYMBOLS = {
  c: "♣",
  d: "♦",
  h: "♥",
  s: "♠",
};

function cardText(card) {
  if (!card) return "";
  if (typeof card === "string") {
    if (card.length === 2 && SUIT_SYMBOLS[card[1]]) return `${card[0]}${SUIT_SYMBOLS[card[1]]}`;
    return card;
  }
  return `${card.rank}${SUIT_SYMBOLS[card.suit] || card.suit}`;
}

function cardSuit(card) {
  if (!card) return "";
  if (typeof card === "string") return card.length === 2 ? card[1] : "";
  return card.suit || "";
}

function isRedCard(card) {
  return ["h", "d", "♥", "♦"].includes(cardSuit(card));
}

function cardsText(cards) {
  return (cards || []).map(cardText).join(" ");
}

function boardText(cards) {
  const text = cardsText(cards);
  return text ? t("board.prefix", { cards: text }) : "";
}

function pct(value) {
  return isNumber(value) ? `${(value * 100).toFixed(1)}%` : "--";
}

function signed(value) {
  if (!isNumber(value)) return "--";
  const rounded = Math.round(value);
  return `${rounded >= 0 ? "+" : ""}${formatNumber(rounded)}`;
}

function bigBlind(hand) {
  return Number(hand?.tournament?.bb || 0);
}

function chipsToBb(value, bb) {
  const blind = Number(bb || 0);
  if (!blind) return Number(value || 0);
  return Number(value || 0) / blind;
}

function aggregateNetBb(hands, contextsById) {
  return (hands || []).reduce((sum, hand) => {
    const ctx = contextsById.get(hand.hand_id);
    return sum + chipsToBb(ctx?.net || 0, bigBlind(hand));
  }, 0);
}

function formatBb(value, bb, options = {}) {
  if (!Number(bb || 0)) {
    return options.signed ? signed(Number(value || 0)) : formatNumber(value);
  }
  return formatBbValue(chipsToBb(value, bb), options);
}

function formatChips(value, hand, options = {}) {
  if (state.chipUnit === "bb") return formatBb(value, bigBlind(hand), options);
  return options.signed ? signed(Number(value || 0)) : formatNumber(value);
}

function formatBbValue(value, options = {}) {
  const number = Number(value || 0);
  const abs = Math.abs(number);
  const decimals = Number.isInteger(number) || abs >= 100 ? 0 : 1;
  const text = number.toFixed(decimals).replace(/\.0$/, "");
  const prefix = options.signed && number > 0 ? "+" : "";
  return `${prefix}${text}bb`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(Number(value || 0));
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${formatNumber(bytes)} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function isNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
