/* app.js */
"use strict";

let startTime = null;
let totalInputTokens = 0;
let totalOutputTokens = 0;

document.addEventListener("DOMContentLoaded", async () => {
  await loadManifests();
});

// ── Tab switching ─────────────────────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("tab-active"));
  document.getElementById(`tab-${name}`).classList.remove("hidden");
  btn.classList.add("tab-active");
}

// ── Manifest helpers ──────────────────────────────────────────────────────
async function loadManifests() {
  const sel = document.getElementById("manifest-select");
  sel.innerHTML = "";
  try {
    const res = await fetch("/api/manifests");
    const data = await res.json();
    const manifests = data.manifests || [];
    if (!manifests.length) {
      const opt = document.createElement("option");
      opt.value = "benchmark/manifests/pilot_hybrid.jsonl";
      opt.textContent = "benchmark/manifests/pilot_hybrid.jsonl";
      sel.appendChild(opt);
      return;
    }
    for (const path of manifests) {
      const opt = document.createElement("option");
      opt.value = path;
      opt.textContent = path;
      sel.appendChild(opt);
    }
  } catch (e) {
    appendEvent("error", `Failed to load manifests: ${e.message}`);
  }
}

// ── GitHub Repo runner ────────────────────────────────────────────────────
function runRepo() {
  const repoUrl    = document.getElementById("repo-url").value.trim();
  const commitId   = document.getElementById("commit-id").value.trim();
  const issueId    = document.getElementById("issue-id").value.trim();
  const targetFile = document.getElementById("target-file").value.trim();
  const testCmd    = document.getElementById("test-command").value.trim();
  const regCmd     = document.getElementById("regression-command").value.trim();
  const model      = document.getElementById("repo-model").value;
  const maxSteps   = document.getElementById("repo-max-steps").value || "10";
  const timeout    = document.getElementById("repo-timeout").value || "300";

  if (!repoUrl || !targetFile || !testCmd) {
    appendEvent("error", "Repo URL, Target File, and Test Command are required.");
    return;
  }

  clearOutput();
  startTime = Date.now();
  totalInputTokens = 0;
  totalOutputTokens = 0;
  setBadge("Running", "blue");
  showTyping(true);
  setRunBtn(false, "repo-run-btn");

  // Show run summary
  const commitLabel = commitId ? commitId.slice(0, 8) : "HEAD";
  const issueLabel  = issueId  ? ` · Issue ${issueId}` : "";
  appendEvent("info", `
    <strong>Repository:</strong> <code>${escHtml(repoUrl)}</code><br>
    <strong>Commit:</strong> <code>${escHtml(commitLabel)}</code>${escHtml(issueLabel)}<br>
    <strong>Target file:</strong> <code>${escHtml(targetFile)}</code><br>
    <strong>Model:</strong> ${escHtml(model)} · Max steps: ${escHtml(maxSteps)} · Timeout: ${escHtml(timeout)}s
  `);

  const form = new FormData();
  form.append("repo_url",                  repoUrl);
  form.append("commit_id",                 commitId);
  form.append("issue_id",                  issueId);
  form.append("target_file",               targetFile);
  form.append("test_command",              testCmd);
  form.append("regression_test_command",   regCmd);
  form.append("model",                     model);
  form.append("max_steps",                 maxSteps);
  form.append("timeout_s",                 timeout);

  fetchSSE("/api/run-repo", form, () => setRunBtn(true, "repo-run-btn"));
}

// ── Manifest runner ───────────────────────────────────────────────────────
async function runManifest() {
  setBadge("Running", "blue");
  clearOutput();
  const form = new FormData();
  form.append("manifest",      document.getElementById("manifest-select").value);
  form.append("models",        document.getElementById("models-input").value || "gemini3pro");
  form.append("max_steps",     document.getElementById("max-steps-input").value || "10");
  form.append("timeout_s",     document.getElementById("timeout-input").value || "300");
  form.append("repetitions",   "1");
  form.append("output",        "logs/benchmark_results.jsonl");
  form.append("report_output", "logs/benchmark_report.json");
  try {
    const res  = await fetch("/api/run-manifest", { method: "POST", body: form });
    const data = await res.json();
    appendEvent("info", `<pre>${escHtml(JSON.stringify(data, null, 2))}</pre>`);
    setBadge(data.ok ? "Ready" : "Failed", data.ok ? "green" : "red");
  } catch (e) {
    appendEvent("error", `Run failed: ${e.message}`);
    setBadge("Failed", "red");
  }
}

async function analyzeLatest() {
  setBadge("Running", "blue");
  const form = new FormData();
  form.append("input_path", "latest");
  form.append("output",     "logs/benchmark_report.json");
  try {
    const res  = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await res.json();
    appendEvent("info", `<pre>${escHtml(JSON.stringify(data, null, 2))}</pre>`);
    setBadge(data.ok ? "Ready" : "Failed", data.ok ? "green" : "red");
  } catch (e) {
    appendEvent("error", `Analyze failed: ${e.message}`);
    setBadge("Failed", "red");
  }
}

async function buildManifest() {
  setBadge("Running", "blue");
  clearOutput();
  const form = new FormData();
  form.append("historical_source", document.getElementById("historical-source").value);
  form.append("synthetic_source",  document.getElementById("synthetic-source").value);
  form.append("output",            document.getElementById("manifest-output").value);
  form.append("target_count",      "30");
  form.append("historical_ratio",  "0.7");
  form.append("synthetic_ratio",   "0.3");
  form.append("seed",              "13");
  try {
    const res  = await fetch("/api/build-manifest", { method: "POST", body: form });
    const data = await res.json();
    appendEvent("info", `<pre>${escHtml(JSON.stringify(data, null, 2))}</pre>`);
    setBadge(data.ok ? "Ready" : "Failed", data.ok ? "green" : "red");
    await loadManifests();
  } catch (e) {
    appendEvent("error", `Build failed: ${e.message}`);
    setBadge("Failed", "red");
  }
}

// ── SSE fetch ─────────────────────────────────────────────────────────────
function fetchSSE(url, form, onDoneCallback) {
  fetch(url, { method: "POST", body: form })
    .then(res => {
      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";

      function pump() {
        reader.read().then(({ done, value }) => {
          if (done) {
            showTyping(false);
            if (onDoneCallback) onDoneCallback();
            return;
          }
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer      = parts.pop();
          for (const part of parts) {
            const eventMatch = part.match(/^event: (.+)/m);
            const dataMatch  = part.match(/^data: (.+)/m);
            if (eventMatch && dataMatch) {
              try { handleSSEEvent(eventMatch[1], JSON.parse(dataMatch[1])); }
              catch { /* ignore parse errors */ }
            }
          }
          pump();
        });
      }
      pump();
    })
    .catch(e => {
      appendEvent("error", `Fetch error: ${e.message}`);
      showTyping(false);
      if (onDoneCallback) onDoneCallback();
    });
}

// ── SSE event handler ─────────────────────────────────────────────────────
function handleSSEEvent(type, data) {
  switch (type) {
    case "status":
      appendPhaseStatus(data.phase, data.message);
      break;
    case "started":
      appendEvent("info", `🚀 Agent started — Model: <strong>${escHtml(data.model)}</strong> | Case: ${escHtml(data.case_id)}`);
      break;
    case "step_start":
      appendStepStart(data.step, data.max_steps);
      break;
    case "reasoning":
      appendReasoningChain(data.step, data.thinking);
      break;
    case "agent_text":
      totalInputTokens  += data.input_tokens  || 0;
      totalOutputTokens += data.output_tokens || 0;
      appendAgentText(data.step, data.text, data.input_tokens, data.output_tokens, data.latency_ms);
      break;
    case "tool_call":
      appendToolCall(data.step, data.name, data.args);
      break;
    case "tool_result":
      appendToolResult(data.step, data.name, data.result);
      break;
    case "dream":
      showDream(data.text);
      break;
    case "done":
      onRepoDone(data);
      break;
    case "error":
      appendEvent("error", `⚠️ ${escHtml(data.message)}`);
      showTyping(false);
      setBadge("Failed", "red");
      break;
    case "info":
      appendEvent("info", escHtml(data.message || ""));
      break;
  }
}

// ── Repo-run result display ───────────────────────────────────────────────
function onRepoDone(data) {
  showTyping(false);
  const elapsed = startTime ? ((Date.now() - startTime) / 1000).toFixed(1) : "?";
  const wallS   = data.wall_time_ms ? (data.wall_time_ms / 1000).toFixed(1) : elapsed;

  if (data.resolved) {
    const el = div("event event-done-resolved");
    el.innerHTML = `
      <div class="event-done-title" style="color:var(--success)">✅ Bug Resolved!</div>
      <div style="color:var(--text-dim);font-size:13px;margin-top:4px">
        Agent fixed the bug in ${escHtml(wallS)}s
        · Input: ${totalInputTokens.toLocaleString()} tok
        · Output: ${totalOutputTokens.toLocaleString()} tok
      </div>`;
    stream().appendChild(el);
    setBadge("Resolved", "green");
  } else {
    const el = div("event event-done-failed");
    const fm = data.failure_mode || "unresolved";
    el.innerHTML = `
      <div class="event-done-title" style="color:var(--danger)">❌ Not Resolved — ${escHtml(fm)}</div>
      <div style="color:var(--text-dim);font-size:13px;margin-top:4px">
        ${escHtml(wallS)}s elapsed
        · Input: ${totalInputTokens.toLocaleString()} tok
        · Output: ${totalOutputTokens.toLocaleString()} tok
      </div>`;
    stream().appendChild(el);
    setBadge("Failed", "red");
  }

  // Show test output
  if (data.test_output) {
    const el = div("event event-tool_result");
    el.innerHTML = `<div class="event-label">📋 Final test output</div>
      <div class="event-body">${escHtml(data.test_output)}</div>`;
    stream().appendChild(el);
  }

  scrollStream();
}

// ── Phase status pills ────────────────────────────────────────────────────
const phaseIcons = { clone: "📦", checkout: "🔀", preflight: "🧪", agent: "🤖" };
function appendPhaseStatus(phase, message) {
  const icon = phaseIcons[phase] || "•";
  const el   = div("event event-phase");
  el.innerHTML = `<span class="phase-icon">${icon}</span> ${escHtml(message)}`;
  stream().appendChild(el);
  scrollStream();
}

// ── Existing stream DOM helpers ───────────────────────────────────────────
function appendStepStart(step, max) {
  const el = div("event event-step_start");
  el.textContent = `Step ${step} / ${max}`;
  stream().appendChild(el);
  scrollStream();
}

function appendReasoningChain(step, thinking) {
  const id = `reasoning-body-${step}-${Date.now()}`;
  const paragraphs = thinking
    .split(/\n(?:---\n|\n+)/)
    .map(p => p.trim())
    .filter(p => p.length > 0);
  const nodesHtml = paragraphs.map((p, i) => `
    <div class="reasoning-node">
      <div class="reasoning-node-dot"></div>
      ${i < paragraphs.length - 1 ? '<div class="reasoning-node-line"></div>' : ''}
      <div class="reasoning-node-text">${escHtml(p)}</div>
    </div>`).join("");
  const el = div("event event-reasoning");
  el.innerHTML = `
    <button class="reasoning-toggle" onclick="toggleReasoning('${id}', this)" aria-expanded="false">
      <span class="reasoning-icon">🧠</span>
      <span class="reasoning-label">Thinking <span class="reasoning-step-badge">Step ${step}</span></span>
      <span class="reasoning-chevron">▸</span>
    </button>
    <div class="reasoning-body" id="${id}" aria-hidden="true">
      <div class="reasoning-chain">${nodesHtml}</div>
    </div>`;
  stream().appendChild(el);
  scrollStream();
}

function toggleReasoning(id, btn) {
  const body     = document.getElementById(id);
  if (!body) return;
  const expanded = btn.getAttribute("aria-expanded") === "true";
  btn.setAttribute("aria-expanded", String(!expanded));
  body.setAttribute("aria-hidden", String(expanded));
  body.classList.toggle("reasoning-open", !expanded);
  btn.querySelector(".reasoning-chevron").textContent = expanded ? "▸" : "▾";
}

function appendAgentText(step, text, inputTok, outputTok, latency) {
  const el = div("event event-agent_text");
  el.innerHTML = `
    <div class="event-label">🤖 Agent — Step ${step}
      <span style="font-weight:400;color:var(--text-muted);margin-left:10px;">
        ↑${inputTok} ↓${outputTok} tok · ${(latency / 1000).toFixed(1)}s
      </span>
    </div>
    <div class="event-body">${escHtml(text)}</div>`;
  stream().appendChild(el);
  scrollStream();
}

function appendToolCall(step, name, args) {
  const el = div("event event-tool_call");
  el.innerHTML = `
    <div class="event-label">🔧 Tool Call — Step ${step}</div>
    <div class="tool-name">${escHtml(name)}()</div>
    <div class="tool-args">${escHtml(JSON.stringify(args, null, 2))}</div>`;
  stream().appendChild(el);
  scrollStream();
}

function appendToolResult(step, name, result) {
  const el = div("event event-tool_result");
  el.innerHTML = `
    <div class="event-label">📤 ${escHtml(name)} output — Step ${step}</div>
    <div class="event-body">${escHtml(result)}</div>`;
  stream().appendChild(el);
  scrollStream();
}

function appendEvent(type, html) {
  const el = div(`event event-${type}`);
  el.innerHTML = html;
  stream().appendChild(el);
  scrollStream();
}

function showDream(text) {
  const el = div("event event-agent_text");
  el.innerHTML = `<div class="event-label">💭 Memory Consolidation</div>
    <div class="event-body">${escHtml(text)}</div>`;
  stream().appendChild(el);
  scrollStream();
}

// ── Utilities ─────────────────────────────────────────────────────────────
function stream()      { return document.getElementById("output-stream"); }
function scrollStream(){ const s = stream(); if (s) s.scrollTop = s.scrollHeight; }
function div(cls)      { const el = document.createElement("div"); el.className = cls; return el; }
function escHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function setBadge(text, color) {
  const b = document.getElementById("status-badge");
  if (b) { b.textContent = text; b.className = `badge badge-${color}`; }
}
function showTyping(show) {
  const w = document.getElementById("typing-wrap");
  if (w) w.classList.toggle("hidden", !show);
}
function setRunBtn(enabled, id = "repo-run-btn") {
  const btn = document.getElementById(id);
  if (btn) btn.disabled = !enabled;
}
function clearOutput() {
  const s = stream();
  if (s) s.innerHTML = "";
  totalInputTokens  = 0;
  totalOutputTokens = 0;
}
function updateStats() { /* stats now shown inline per-step */ }
function onStreamDone() { showTyping(false); setRunBtn(true); }
