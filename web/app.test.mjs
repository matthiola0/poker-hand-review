import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(__dirname, "app.js"), "utf8");

function loadApp() {
  const context = {
    console,
    document: { addEventListener() {}, getElementById() {} },
    window: {},
    URL,
    fetch() {},
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return context;
}

test("mergeReports combines multiple JSON reports into one report", () => {
  const { mergeReports } = loadApp();
  const first = {
    schema: "0.1",
    hands: [{ hand_id: "A" }],
    hero_contexts: [{ hand_id: "A", net: 120 }],
    hand_evals: [{ hand_id: "A", decisions: [{ ev_loss_bb: 1.5, tier: "mistake" }] }],
    leaks: [{ pattern: "preflop: call vs 建議 fold", count: 1, total_ev_loss_bb: 1.5, example_hand_ids: ["A"] }],
    opponents: { Villain1: { hands: 1 } },
    stats: { hands: 1, gto_accuracy: 0, ev_loss_per_100: 150, mistakes: 1, net_chips: 120 },
  };
  const second = {
    schema: "0.1",
    hands: [{ hand_id: "B" }],
    hero_contexts: [{ hand_id: "B", net: -40 }],
    hand_evals: [{ hand_id: "B", decisions: [{ ev_loss_bb: 0.25, tier: "good" }] }],
    leaks: [{ pattern: "preflop: call vs 建議 fold", count: 1, total_ev_loss_bb: 0.25, example_hand_ids: ["B"] }],
    opponents: { Villain2: { hands: 1 } },
    stats: { hands: 1, gto_accuracy: 1, ev_loss_per_100: 25, mistakes: 0, net_chips: -40 },
  };

  const merged = mergeReports([first, second]);

  assert.equal(merged.schema, "0.1");
  assert.deepEqual(
    merged.hands.map((hand) => hand.hand_id),
    ["A", "B"],
  );
  assert.deepEqual(
    merged.hero_contexts.map((ctx) => ctx.hand_id),
    ["A", "B"],
  );
  assert.deepEqual(
    merged.hand_evals.map((handEval) => handEval.hand_id),
    ["A", "B"],
  );
  assert.equal(merged.stats.hands, 2);
  assert.equal(merged.stats.gto_accuracy, 0.5);
  assert.equal(merged.stats.ev_loss_per_100, 87.5);
  assert.equal(merged.stats.mistakes, 1);
  assert.equal(merged.stats.net_chips, 80);
  assert.equal(merged.leaks.length, 1);
  assert.equal(merged.leaks[0].count, 2);
  assert.equal(merged.leaks[0].total_ev_loss_bb, 1.75);
  assert.equal(JSON.stringify(merged.leaks[0].example_hand_ids), JSON.stringify(["A", "B"]));
  assert.deepEqual(Object.keys(merged.opponents), ["Villain1", "Villain2"]);
});

test("groupHandsBySource keeps hands in source-file sections", () => {
  const { groupHandsBySource } = loadApp();

  const groups = groupHandsBySource([
    { hand_id: "A", source_file: "first.txt" },
    { hand_id: "B", source_file: "first.txt" },
    { hand_id: "C", source_file: "second.txt" },
    { hand_id: "D" },
  ]);

  assert.equal(
    JSON.stringify(groups.map((group) => [group.source, group.hands.map((hand) => hand.hand_id)])),
    JSON.stringify([
      ["first.txt", ["A", "B"]],
      ["second.txt", ["C"]],
      ["Unknown source", ["D"]],
    ]),
  );
});

test("matchesTierStreet filters hero decisions by tier and street together", () => {
  const { matchesTierStreet } = loadApp();
  const ctx = { decisions: [{ street: "preflop" }, { street: "flop" }] };
  const ev = { decisions: [{ tier: "mistake" }, { tier: "good" }] };

  // No filters selected matches everything.
  assert.equal(matchesTierStreet(ctx, ev, new Set(), new Set()), true);
  // Tier only: a preflop mistake matches the "mistake" selection.
  assert.equal(matchesTierStreet(ctx, ev, new Set(["mistake"]), new Set()), true);
  assert.equal(matchesTierStreet(ctx, ev, new Set(["inaccuracy"]), new Set()), false);
  // Tier + street must match on the same decision.
  assert.equal(matchesTierStreet(ctx, ev, new Set(["mistake"]), new Set(["flop"])), false);
  assert.equal(matchesTierStreet(ctx, ev, new Set(["good"]), new Set(["flop"])), true);
  // Multi-select streets: flop OR turn, with a flop good decision present.
  assert.equal(matchesTierStreet(ctx, ev, new Set(["good"]), new Set(["flop", "turn"])), true);
  // Street only: no turn decision exists.
  assert.equal(matchesTierStreet(ctx, ev, new Set(), new Set(["turn"])), false);
  // A hand with no hero decisions cannot match an active filter.
  assert.equal(matchesTierStreet({ decisions: [] }, {}, new Set(["mistake"]), new Set()), false);
});

test("t resolves keys per language, interpolates params, and falls back", () => {
  const { t, labelStreet } = loadApp();

  // Default language is "en" (runtime overrides to zh in the browser via initLang).
  assert.equal(t("tier.mistake"), "Mistake");
  assert.equal(t("handSub.decisions", { n: 3 }), "3 decisions");
  assert.equal(labelStreet("flop"), "Flop");

  // Explicit language override.
  assert.equal(t("tier.mistake", null, "zh"), "失誤");
  assert.equal(t("handSub.decisions", { n: 3 }, "zh"), "3 個決策");

  // Unknown keys return the key itself; missing placeholders are left intact.
  assert.equal(t("does.not.exist"), "does.not.exist");
  assert.equal(t("handSub.decisions", null, "zh"), "{n} 個決策");
});

test("cardText renders suit symbols", () => {
  const { cardText, cardsText } = loadApp();

  assert.equal(cardText({ rank: "A", suit: "h" }), "A♥");
  assert.equal(cardText({ rank: "K", suit: "d" }), "K♦");
  assert.equal(cardText({ rank: "7", suit: "c" }), "7♣");
  assert.equal(cardText({ rank: "2", suit: "s" }), "2♠");
  assert.equal(cardsText([{ rank: "A", suit: "h" }, { rank: "K", suit: "d" }]), "A♥ K♦");
});

test("formatBb displays chip values in big blinds", () => {
  const { actionText, formatBb, aggregateNetBb, streetViewKey, streetViews } = loadApp();

  assert.equal(formatBb(1420, 100, { signed: true }), "+14.2bb");
  assert.equal(formatBb(-50, 100, { signed: true }), "-0.5bb");
  assert.equal(formatBb(100, 0), "100");
  assert.equal(
    actionText({ type: "raise", amount: 100, to_amount: 300 }, { tournament: { bb: 100 } }),
    "raise 1bb to 3bb",
  );
  assert.equal(
    aggregateNetBb(
      [
        { hand_id: "A", tournament: { bb: 100 } },
        { hand_id: "B", tournament: { bb: 200 } },
      ],
      new Map([
        ["A", { net: 100 }],
        ["B", { net: -400 }],
      ]),
    ),
    -1,
  );
  assert.equal(streetViewKey("showdown"), "river");
  assert.equal(
    JSON.stringify(streetViews({ streets: [{ street: "preflop" }, { street: "river" }, { street: "showdown" }] })),
    JSON.stringify([
      { key: "preflop", label: "Preflop" },
      { key: "river", label: "River / Showdown" },
    ]),
  );
});
