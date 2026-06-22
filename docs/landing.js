const hud = {
  hands: document.getElementById("hud-hands"),
  vpip: document.getElementById("hud-vpip"),
  pfr: document.getElementById("hud-pfr"),
  ats: document.getElementById("hud-ats"),
  threeBet: document.getElementById("hud-three-bet"),
  handsValue: document.getElementById("hud-hands-value"),
  vpipValue: document.getElementById("hud-vpip-value"),
  pfrValue: document.getElementById("hud-pfr-value"),
  atsValue: document.getElementById("hud-ats-value"),
  threeBetValue: document.getElementById("hud-three-bet-value"),
  confidence: document.getElementById("hud-confidence"),
  type: document.getElementById("hud-player-type"),
  desc: document.getElementById("hud-player-desc"),
  strategy: document.getElementById("hud-player-strategy"),
};

const playerProfiles = {
  nit: {
    type: "Nit",
    desc: "Extremely tight and rarely bluffing. This profile waits for premium hands and avoids marginal spots.",
    strategy: "Steal blinds frequently. When this player shows real aggression, continue only with strong hands.",
  },
  weakTight: {
    type: "Weak Tight",
    desc: "Tight preflop but uncomfortable postflop. This player often gives up after missing the board.",
    strategy: "Apply frequent small continuation bets and attack capped ranges after passive lines.",
  },
  tag: {
    type: "TAG",
    desc: "Disciplined entering range with controlled aggression and reasonable position awareness.",
    strategy: "Avoid thin out-of-position battles. Look for over-aggressive spots before fighting back.",
  },
  lag: {
    type: "LAG",
    desc: "Wide and aggressive. This player pressures blinds, attacks weakness, and plays more postflop pots.",
    strategy: "Widen value continues, trap with strong hands, and avoid over-folding top-pair type holdings.",
  },
  maniac: {
    type: "Maniac",
    desc: "Very high entry and raise frequency. Chips go in often, sometimes without positional discipline.",
    strategy: "Wait for hands with real showdown value, then let the aggression continue into you.",
  },
  loosePassive: {
    type: "Loose Passive",
    desc: "Likes seeing flops but rarely drives the action. Most value comes from calling too wide.",
    strategy: "Value bet thinner and reduce pure bluffs, especially when draws complete.",
  },
  callingStation: {
    type: "Calling Station",
    desc: "Calls too many streets and dislikes folding pairs, draws, and bluff-catchers.",
    strategy: "Do not run ambitious bluffs. Use larger value bets when ahead.",
  },
  whale: {
    type: "Whale",
    desc: "Plays almost everything and ignores position, price, and range quality.",
    strategy: "Iso-raise wider for value and keep betting made hands. Expect very light calls.",
  },
  abc: {
    type: "ABC Regular",
    desc: "Straightforward baseline strategy, usually relying on hand strength more than pressure.",
    strategy: "Play solid value poker and give respect when this player chooses a strong aggressive line.",
  },
};

function updateHud() {
  const hands = numberValue(hud.hands);
  const vpip = numberValue(hud.vpip);
  let pfr = numberValue(hud.pfr);
  const ats = numberValue(hud.ats);
  const threeBet = numberValue(hud.threeBet);

  if (pfr > vpip) {
    pfr = vpip;
    hud.pfr.value = String(pfr);
  }

  hud.handsValue.textContent = String(hands);
  hud.vpipValue.textContent = `${vpip}%`;
  hud.pfrValue.textContent = `${pfr}%`;
  hud.atsValue.textContent = `${ats}%`;
  hud.threeBetValue.textContent = `${threeBet}%`;

  const profile = classifyPlayer(vpip, pfr);
  const confidence = classifyConfidence(hands);
  const additions = [];

  if (ats > 45) {
    additions.push("This player steals blinds aggressively, so defend blinds and 3Bet more selectively.");
  }

  if (threeBet > 10) {
    additions.push("The 3Bet frequency is high enough to include more bluffs, so consider traps and disciplined 4Bets.");
  }

  hud.confidence.textContent = confidence.label;
  hud.confidence.className = `confidence-badge ${confidence.className}`;
  hud.type.textContent = profile.type;
  hud.desc.textContent = profile.desc;
  hud.strategy.textContent = [profile.strategy, ...additions].join(" ");
}

function classifyPlayer(vpip, pfr) {
  const gap = vpip - pfr;

  if (vpip < 12) return playerProfiles.nit;
  if (vpip >= 12 && vpip <= 18 && gap > 6) return playerProfiles.weakTight;
  if (vpip >= 12 && vpip <= 22 && gap <= 6) return playerProfiles.tag;
  if (vpip > 22 && vpip <= 32 && gap <= 8) return playerProfiles.lag;
  if (vpip > 32 && pfr > 25) return playerProfiles.maniac;
  if (vpip > 22 && vpip <= 35 && gap > 8) return playerProfiles.loosePassive;
  if (vpip > 35 && vpip <= 50 && gap > 15) return playerProfiles.callingStation;
  if (vpip > 50 && gap > 20) return playerProfiles.whale;

  return playerProfiles.abc;
}

function classifyConfidence(hands) {
  if (hands < 50) {
    return { label: "Low confidence", className: "confidence-low" };
  }
  if (hands >= 200) {
    return { label: "High confidence", className: "confidence-high" };
  }
  return { label: "Medium confidence", className: "" };
}

function numberValue(input) {
  return Number.parseInt(input.value, 10) || 0;
}

[hud.hands, hud.vpip, hud.pfr, hud.ats, hud.threeBet].forEach((input) => {
  input.addEventListener("input", updateHud);
});

updateHud();
