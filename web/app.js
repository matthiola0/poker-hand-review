const state = {
  report: null,
  hands: [],
  contextsById: new Map(),
  evalsById: new Map(),
  selectedHandId: null,
  selectedStreet: "preflop",
  tierFilter: "all",
  positionFilter: "all",
  streetFilter: "all",
  resultFilter: "all",
  search: "",
  replayTimer: null,
  solverRunning: new Set(),
  solverBatch: { running: false, total: 0, done: 0, failed: 0, changed: 0, up: 0, down: 0, flat: 0 },
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindEvents();
  loadReportFromQuery();
  render();
});

function bindElements() {
  [
    "fileInput",
    "analyzeBackend",
    "solverPathInput",
    "schemaLabel",
    "metricHands",
    "metricAccuracy",
    "metricEvLoss",
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
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
}

function bindEvents() {
  els.fileInput.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    if (file.name.toLowerCase().endsWith(".txt")) {
      await analyzeText(text, file.name);
    } else {
      loadReport(JSON.parse(text), file.name);
    }
    event.target.value = "";
  });

  els.analyzeBackend.addEventListener("change", (event) => {
    els.solverPathInput.disabled = event.target.value !== "solver";
  });

  els.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderHandList();
  });

  els.tierFilter.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    state.tierFilter = button.dataset.tier;
    [...els.tierFilter.querySelectorAll("button")].forEach((b) => {
      b.classList.toggle("active", b === button);
    });
    renderHandList();
  });

  els.positionFilter.addEventListener("change", (event) => {
    state.positionFilter = event.target.value;
    renderHandList();
  });

  els.streetFilter.addEventListener("change", (event) => {
    state.streetFilter = event.target.value;
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
}

function loadReport(report, sourceName) {
  state.report = report;
  state.hands = report.hands || [];
  state.contextsById = byId(report.hero_contexts || []);
  state.evalsById = byId(report.hand_evals || []);
  state.selectedHandId = state.hands[0]?.hand_id || null;
  state.selectedStreet = "preflop";
  state.solverBatch = { running: false, total: 0, done: 0, failed: 0, changed: 0, up: 0, down: 0, flat: 0 };
  els.schemaLabel.textContent = `${sourceName} · schema ${report.schema || "unknown"}`;
  hydratePositionFilter();
  render();
}

async function analyzeText(text, sourceName) {
  const postflop = els.analyzeBackend.value || "equity";
  const solverPath = els.solverPathInput.value.trim();
  els.schemaLabel.textContent = `Analyzing ${sourceName}… (${postflop})`;
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, filename: sourceName, postflop, solver_path: solverPath }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    loadReport(data, sourceName);
  } catch (err) {
    els.schemaLabel.textContent = `Analyze failed: ${err.message}`;
  }
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
    els.schemaLabel.textContent = `Could not load ${reportUrl}`;
    console.error(error);
  }
}

function byId(items) {
  return new Map(items.map((item) => [item.hand_id, item]));
}

function render() {
  renderDashboard();
  renderHandList();
  renderInsights();
  renderSelectedHand();
}

function renderDashboard() {
  const stats = state.report?.stats || {};
  els.metricHands.textContent = formatNumber(stats.hands || state.hands.length || 0);
  els.metricAccuracy.textContent = pct(stats.gto_accuracy);
  els.metricEvLoss.textContent = isNumber(stats.ev_loss_per_100)
    ? `${stats.ev_loss_per_100.toFixed(1)}bb`
    : "--";
  els.metricNet.textContent = signed(stats.net_chips);
  els.metricNet.className = stats.net_chips >= 0 ? "positive" : "negative";
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
    els.solveAllButton.textContent = "Solving all...";
    els.solveAllStatus.textContent = `${formatNumber(batch.done)} / ${formatNumber(batch.total)}`;
    return;
  }
  els.solveAllButton.textContent = remaining ? `Run all solver (${formatNumber(remaining)})` : "All solver done";
  els.solveAllStatus.textContent =
    batch.error ||
    batchSummary(batch) ||
    (batch.failed ? `${formatNumber(batch.failed)} failed` : "");
}

function renderHandList() {
  const hands = filteredHands();
  els.handCount.textContent = formatNumber(hands.length);
  els.handList.innerHTML = "";

  if (!state.report) {
    els.handList.append(emptyList("No report"));
    return;
  }

  if (!hands.length) {
    els.handList.append(emptyList("No matching hands"));
    return;
  }

  if (!hands.some((hand) => hand.hand_id === state.selectedHandId)) {
    state.selectedHandId = hands[0]?.hand_id || null;
    state.selectedStreet = "preflop";
    renderSelectedHand();
  }

  hands.forEach((hand) => {
    const ctx = state.contextsById.get(hand.hand_id);
    const ev = state.evalsById.get(hand.hand_id);
    const row = document.createElement("button");
    row.type = "button";
    row.className = `hand-row ${hand.hand_id === state.selectedHandId ? "active" : ""}`;
    row.addEventListener("click", () => {
      state.selectedHandId = hand.hand_id;
      state.selectedStreet = firstStreet(hand);
      stopReplay();
      renderHandList();
      renderSelectedHand();
    });

    const strip = document.createElement("span");
    strip.className = `tier-strip tier-${ev?.hand_tier || "unknown"}`;
    row.append(strip);

    const main = document.createElement("div");
    main.innerHTML = `
      <div class="hand-id">${escapeHtml(hand.hand_id)}</div>
      <div class="hand-sub">
        <span>${escapeHtml(cardsText(hand.hero_hole))}</span>
        <span>${escapeHtml(ctx?.position || "--")}</span>
        <span>${decisionCount(ev)} decisions</span>
      </div>
    `;
    row.append(main);

    const net = document.createElement("span");
    net.className = `net-badge ${ctx?.net >= 0 ? "positive" : "negative"}`;
    net.textContent = signed(ctx?.net || 0);
    row.append(net);

    els.handList.append(row);
  });
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
  const streets = hand.streets || [];
  if (!streets.some((street) => street.street === state.selectedStreet)) {
    state.selectedStreet = firstStreet(hand);
  }

  els.selectedHandId.textContent = hand.hand_id;
  els.selectedTierDot.className = `tier-dot tier-${ev?.hand_tier || "unknown"}`;
  els.selectedMeta.textContent = [
    ctx?.position,
    `net ${signed(ctx?.net || 0)}`,
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
  (hand.streets || []).forEach((street) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = labelStreet(street.street);
    button.className = street.street === state.selectedStreet ? "active" : "";
    button.addEventListener("click", () => {
      state.selectedStreet = street.street;
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
      <div class="seat-stack">${formatNumber(stacks.get(seat.player) ?? seat.stack)}</div>
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
  els.potInfo.textContent = `Board · total pot ${formatNumber(hand.total_pot || 0)}`;
}

function cardNode(card) {
  const text = cardText(card);
  const node = document.createElement("span");
  node.className = `card ${/[hd]$/.test(text) ? "red-card" : ""}`;
  node.textContent = text;
  return node;
}

function cardMarkup(card) {
  const text = cardText(card);
  const red = /[hd]$/.test(text) ? " red-card" : "";
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
  const index = streets.findIndex((street) => street.street === state.selectedStreet);
  if (index < 0) return [];
  return streets.slice(0, index + 1);
}

function shownCardsByPlayer(hand) {
  const visible = state.selectedStreet === "showdown";
  if (!visible) return new Map();
  return new Map(
    (hand.showdowns || [])
      .filter((showdown) => !showdown.mucked && showdown.hole?.length)
      .map((showdown) => [showdown.player, showdown.hole]),
  );
}

function renderTimeline(hand) {
  const street = currentStreet(hand);
  els.streetLabel.textContent = labelStreet(street?.street || "");
  els.actionTimeline.innerHTML = "";
  const positions = playerPositionMap(hand);
  const actions = (street?.actions || []).filter((action) => {
    return !(street?.street === "preflop" && action.type === "ante");
  });
  if (!actions.length) {
    els.actionTimeline.append(emptyList("No actions"));
    return;
  }

  actions.forEach((action) => {
    const item = document.createElement("div");
    item.className = `action-item ${action.player === hand.hero ? "hero-action" : ""}`;
    item.innerHTML = `
      <div class="action-player">${escapeHtml(displayPlayer(action.player, hand, positions))}</div>
      <div class="action-text">${escapeHtml(actionText(action))}</div>
      ${action.all_in ? '<span class="pill mistake">all-in</span>' : ""}
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
    .filter((pair) => pair.ctx.street === state.selectedStreet);

  els.decisionCount.textContent = `${decisions.length}`;
  els.decisionList.innerHTML = "";

  if (!decisions.length) {
    els.decisionList.append(emptyList("No Hero decision on this street"));
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
          <span class="pill ${tier}">${escapeHtml(tier)}</span>
          ${solverButton(pair, hand, ctx)}
        </div>
        <div class="muted">
          facing ${escapeHtml(pair.ctx.facing)}${pair.ctx.villain ? ` vs ${escapeHtml(displayPlayer(pair.ctx.villain, hand, positions))}` : ""}
          · pot ${formatNumber(pair.ctx.pot_before)}
          · to call ${formatNumber(pair.ctx.to_call || 0)}
        </div>
        <div>${escapeHtml(pair.ev?.explanation || "No evaluation")}</div>
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
  const label = source === "solver" ? "Run again" : "Run solver";
  return `<button class="solver-button" data-run-solver="${pair.index}" ${running ? "disabled" : ""}>${running ? "Solving..." : label}</button>`;
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
    alert(`Solver unavailable: ${error.message || error}`);
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
      `Solver failed after ${formatNumber(checked)} checked decision${
        checked === 1 ? "" : "s"
      }.\n\nFirst error: ${error || "unknown"}`,
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
  applySolverResult(hand.hand_id, pair.index, result.decision_eval, result);
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

function applySolverResult(handId, decisionIndex, decisionEval, result = {}) {
  const handEval = state.evalsById.get(handId);
  if (!handEval || !decisionEval) return;
  handEval.decisions[decisionIndex] = decisionEval;
  handEval.hand_tier = worstTier(handEval.decisions || []);
  if (state.report?.stats && result.stats) {
    state.report.stats = result.stats;
  }
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
  preflop_chart: { label: "chart", cls: "src-chart", title: "翻前 GTO 範圍表，不需要 solver" },
  equity_backend: { label: "equity", cls: "src-equity", title: "equity 啟發式估計" },
  solver: { label: "solver", cls: "src-solver", title: "真實 GTO solver 解算" },
  unknown: { label: "n/a", cls: "src-unknown", title: "資訊不足，未評分" },
};

function sourceBadge(ev) {
  const source = ev?.suggestion?.source || "unknown";
  const meta = SOURCE_META[source] || { label: source, cls: "src-unknown", title: source };
  return `<span class="src-badge ${meta.cls}" title="${escapeHtml(meta.title)}"><span>engine</span>${escapeHtml(meta.label)}</span>`;
}

function sourceDetailBadge(ev) {
  const detail = ev?.suggestion?.detail;
  if (!detail || ev?.suggestion?.source !== "preflop_chart") return "";
  const sourceType = detail.chart_source_type === "solver_chart" ? "solver chart" : "built-in";
  const bucket = detail.stack_bucket || "";
  const action = detail.action || "";
  const label = [bucket, sourceType].filter(Boolean).join(" · ");
  const title = [
    detail.chart_id ? `chart ${detail.chart_id}` : "",
    detail.chart_source ? `source ${detail.chart_source}` : "",
    detail.chart_version ? `version ${detail.chart_version}` : "",
    detail.effective_stack_bb ? `effective ${detail.effective_stack_bb}bb` : "",
    action ? `spot ${action}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `<span class="source-detail-badge" title="${escapeHtml(title)}">${escapeHtml(label || "chart detail")}</span>`;
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
      ? `best ${delta.previous_best_action} -> ${delta.best_action}`
      : "",
    evText ? `EV loss ${evText}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `<span class="delta-badge delta-${direction}" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

function deltaLabel(delta) {
  const marker = delta.direction === "up" ? "↑" : delta.direction === "down" ? "↓" : "→";
  if (!delta.changed) return `${marker} no change`;
  if (delta.previous_best_action && delta.best_action && delta.previous_best_action !== delta.best_action) {
    return `${marker} ${delta.previous_best_action}→${delta.best_action}`;
  }
  const evText = evDeltaText(delta.ev_loss_delta_bb);
  return evText ? `${marker} ${evText}` : `${marker} changed`;
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
  if (batch.changed) parts.push(`${formatNumber(batch.changed)} changed`);
  if (batch.up) parts.push(`↑${formatNumber(batch.up)}`);
  if (batch.down) parts.push(`↓${formatNumber(batch.down)}`);
  if (batch.flat) parts.push(`→${formatNumber(batch.flat)}`);
  if (batch.failed) parts.push(`${formatNumber(batch.failed)} failed`);
  return parts.length ? `saved · ${parts.join(" ")}` : "";
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

function renderLeaks() {
  const leaks = state.report?.leaks || [];
  els.leakCount.textContent = formatNumber(leaks.length);
  els.leakList.innerHTML = "";
  if (!leaks.length) {
    els.leakList.append(emptyList("No leaks"));
    return;
  }
  leaks.slice(0, 8).forEach((leak) => {
    const node = document.createElement("button");
    node.type = "button";
    node.className = "leak-card";
    node.innerHTML = `
      <div class="leak-title">${escapeHtml(leak.pattern)}</div>
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
  const byPosition = state.report?.stats?.by_position_net || {};
  const values = Object.entries(byPosition);
  els.positionBars.innerHTML = "";
  if (!values.length) {
    els.positionBars.append(emptyList("No position data"));
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
        <span class="${net >= 0 ? "positive" : "negative"}">${signed(net)}</span>
      `;
      els.positionBars.append(node);
    });
}

function renderOpponents() {
  const opponents = Object.values(state.report?.opponents || {});
  els.opponentList.innerHTML = "";
  if (!opponents.length) {
    els.opponentList.append(emptyList("No opponents"));
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
          ${opp.hands} hands · VPIP ${pct(opp.vpip)} · PFR ${pct(opp.pfr)}
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
    if (state.tierFilter !== "all" && ev?.hand_tier !== state.tierFilter) return false;
    if (state.positionFilter !== "all" && ctx?.position !== state.positionFilter) return false;
    if (state.resultFilter === "win" && !(ctx?.net > 0)) return false;
    if (state.resultFilter === "loss" && !(ctx?.net < 0)) return false;
    if (state.streetFilter !== "all") {
      const decisions = ctx?.decisions || [];
      if (!decisions.some((decision) => decision.street === state.streetFilter)) return false;
    }
    return true;
  });
}

function hydratePositionFilter() {
  const positions = [...new Set((state.report?.hero_contexts || []).map((ctx) => ctx.position))]
    .filter(Boolean)
    .sort((a, b) => positionOrder(a) - positionOrder(b));
  els.positionFilter.innerHTML = '<option value="all">All positions</option>';
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
  return (hand.streets || []).find((street) => street.street === state.selectedStreet);
}

function firstStreet(hand) {
  return hand?.streets?.[0]?.street || "preflop";
}

function stepStreet(direction) {
  const hand = selectedHand();
  if (!hand) return;
  const streets = (hand.streets || []).map((street) => street.street);
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

function actionText(action) {
  if (!action) return "";
  const amount = action.to_amount ? `${formatNumber(action.amount)} to ${formatNumber(action.to_amount)}` : formatNumber(action.amount);
  if (["fold", "check"].includes(action.type)) return action.type;
  if (action.type === "small_blind") return `posts SB ${amount}`;
  if (action.type === "big_blind") return `posts BB ${amount}`;
  if (action.type === "uncalled") return `returned ${amount}`;
  if (action.type === "collect") return `collected ${amount}`;
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
  return player === hand.hero ? `${position} · Hero` : position;
}

function labelStreet(street) {
  return {
    preflop: "Preflop",
    flop: "Flop",
    turn: "Turn",
    river: "River",
    showdown: "Showdown",
  }[street] || street || "--";
}

function positionOrder(position) {
  return ["UTG", "UTG+1", "MP", "HJ", "CO", "BTN", "SB", "BB"].indexOf(position);
}

function cardText(card) {
  if (!card) return "";
  if (typeof card === "string") return card;
  return `${card.rank}${card.suit}`;
}

function cardsText(cards) {
  return (cards || []).map(cardText).join(" ");
}

function boardText(cards) {
  const text = cardsText(cards);
  return text ? `board ${text}` : "";
}

function pct(value) {
  return isNumber(value) ? `${(value * 100).toFixed(1)}%` : "--";
}

function signed(value) {
  if (!isNumber(value)) return "--";
  const rounded = Math.round(value);
  return `${rounded >= 0 ? "+" : ""}${formatNumber(rounded)}`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(Number(value || 0));
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
