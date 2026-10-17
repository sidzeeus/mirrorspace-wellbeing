/**
 * Copy rules that can be checked by machine (spec Part C.4, C.7 and non-negotiable 1).
 * Run with: npm run test:unit
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const MESSAGES = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "messages");
const load = (locale, name) =>
  JSON.parse(readFileSync(path.join(MESSAGES, locale, `${name}.json`), "utf8"));

function flatten(tree, prefix = "") {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string"
      ? [[`${prefix}${key}`, value]]
      : flatten(value, `${prefix}${key}.`),
  );
}

const namespaces = readdirSync(path.join(MESSAGES, "en"))
  .filter((file) => file.endsWith(".json"))
  .map((file) => file.replace(".json", ""));
const everyString = namespaces.flatMap((name) =>
  flatten(load("en", name), `${name}.`).filter(([key]) => !key.split(".").pop().startsWith("_")),
);

// Causal, predictive, diagnostic, judging or advising wording an observation must not use.
const BANNED_IN_OBSERVATIONS = [
  "because", "cause", "leads to", "led to", "due to", "results in", "result of", "makes you",
  "made you", "affects", "impact", "will ", "predict", "likely", "risk", "warning", "diagnos",
  "disorder", "symptom", "depress", "anxi", "insomnia", "illness", "condition", "you are ",
  "you're ", "you have ", "should", "must", "need to", "try to", "better", "worse", "good",
  "bad", "healthy", "unhealthy", "normal", "streak", "missed", "only ", "score",
];

test("pattern observations describe and never diagnose, predict or claim a cause", () => {
  const observations = load("en", "patterns").observations;
  assert.ok(Object.keys(observations).length >= 8);
  for (const [code, text] of Object.entries(observations)) {
    const used = BANNED_IN_OBSERVATIONS.filter((phrase) => text.toLowerCase().includes(phrase));
    assert.deepEqual(used, [], `observation "${code}" uses banned wording`);
  }
});

test("frontend observation wording matches the API's observation codes", () => {
  const source = readFileSync(
    path.resolve(MESSAGES, "..", "..", "backend", "apps", "checkins", "patterns.py"),
    "utf8",
  );
  const codes = [...source.matchAll(/^\s{4}"([a-z_]+)": [("]/gm)].map((match) => match[1]);
  assert.ok(codes.includes("sleep_energy_lower"));
  assert.deepEqual(Object.keys(load("en", "patterns").observations).sort(), [...new Set(codes)].sort());
});

test("no clinical labels about the person anywhere in the interface", () => {
  const labels = [/\byou are (anxious|depressed|unwell|ill|at risk)\b/i, /\byour (diagnosis|disorder|condition|symptoms)\b/i];
  for (const [key, text] of everyString) {
    for (const pattern of labels) assert.ok(!pattern.test(text), `${key}: "${text}"`);
  }
});

test("no streaks, guilt or gamified praise anywhere in the interface", () => {
  const patterns = [/streak/i, /you missed/i, /don.t break/i, /keep it up/i, /great job/i, /well done/i, /points?\b.*earn/i, /level up/i, /congrat/i];
  for (const [key, text] of everyString) {
    // Sentences that state the absence of these things are the point.
    if (/\b(no|not|never|without)\b/i.test(text)) continue;
    for (const pattern of patterns) assert.ok(!pattern.test(text), `${key}: "${text}"`);
  }
});

test("the app never claims to monitor anyone or to have sent an alert", () => {
  const claims = [/\bwe (are|will be) (watching|monitoring)\b/i, /\bis monitored\b(?!.*\bnot\b)/i, /\b(an )?alert (has been|was) sent\b/i, /\bhelp is on (the|its) way\b/i, /\bhas been delivered\b/i];
  for (const [key, text] of everyString) {
    if (/\b(not|never|nobody|no one|cannot)\b/i.test(text)) continue;
    for (const pattern of claims) assert.ok(!pattern.test(text), `${key}: "${text}"`);
  }
});

test("sentence case: no all-caps words in labels", () => {
  const allowed = new Set(["AI", "SOS", "OK", "URL", "PDF"]);
  for (const [key, text] of everyString) {
    const shouting = (text.match(/\b[A-Z]{3,}\b/g) ?? []).filter((word) => !allowed.has(word));
    assert.deepEqual(shouting, [], `${key}: "${text}"`);
  }
});

test("every translated key exists in English", () => {
  for (const locale of readdirSync(MESSAGES).filter((name) => name !== "en")) {
    for (const file of readdirSync(path.join(MESSAGES, locale)).filter((f) => f.endsWith(".json"))) {
      const name = file.replace(".json", "");
      assert.ok(namespaces.includes(name), `${locale}/${file} has no English file`);
      const english = new Set(flatten(load("en", name)).map(([key]) => key));
      for (const [key] of flatten(load(locale, name))) {
        if (key.split(".").pop().startsWith("_")) continue;
        assert.ok(english.has(key), `${locale}/${name}: "${key}" is not in English`);
      }
    }
  }
});
