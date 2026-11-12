"use strict";
let state = {requests: [], events: []};
let selected = null;
let busy = false;
const el = id => document.getElementById(id);
const labels = {EXECUTE:"Ready to run",CLARIFY:"Needs clarification",STAGE:"Staged for checking",ESCALATE:"Needs approval",REFUSE:"Blocked",completed:"Completed",rejected:"Rejected",halted:"Safely halted"};
const actionLabels = {execute:"Run in sandbox",approve:"Record approval",clarify:"Confirm shown target",refresh:"Confirm simulated fresh check",reject:"Reject request"};
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const shortTime = value => new Date(value).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});
function badge(r) {if(r.status === "pending" && r.reason === "authority_missing") return '<span class="pill REFUSE">Permission missing</span>'; const key = r.status === "pending" ? r.decision : r.status; return `<span class="pill ${escapeHtml(key)}">${escapeHtml(labels[key] || key)}</span>`;}
async function api(path, data) {
  const options = data === undefined ? {} : {method:"POST",headers:{"Content-Type":"application/json","X-ScopeQuay-Token":state.csrf_token},body:JSON.stringify(data)};
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The request could not be completed. Refresh and try again.");
  return body;
}
function showError(message) {el("error").textContent = message || ""; el("error").hidden = !message;}
function render() {
  const filter = el("filter").value;
  const rows = state.requests.filter(r => filter === "all" || (filter === "closed" ? ["halted","rejected"].includes(r.status) : r.status === filter));
  if (!rows.some(r => r.id === selected)) selected = rows[0]?.id || null;
  el("count").textContent = `${rows.length} shown`;
  el("seed").disabled = busy || state.requests.length > 0;
  el("export").disabled = busy || !state.events.length;
  el("seed").textContent = state.requests.length ? "Examples loaded" : "Load example requests";
  el("requests").innerHTML = rows.length ? rows.map(r => `<button class="request ${r.id === selected ? "selected" : ""}" data-id="${r.id}" aria-pressed="${r.id === selected}"><strong>${escapeHtml(r.title)}</strong><span class="request-bottom">${badge(r)}<small>${escapeHtml(r.observation.operation)}</small></span></button>`).join("") : '<p class="muted">No requests match this view.</p>';
  document.querySelectorAll(".request").forEach(button => button.addEventListener("click", () => {selected = button.dataset.id;render();}));
  const r = state.requests.find(r => r.id === selected);
  if (r) {
    const x = r.observation;
    const events = state.events.filter(e => e.request_id === r.id);
    const outcome = r.outcome ? `<div class="outcome ${r.status}"><strong>${r.outcome.completed ? "Simulated effect verified" : "Stopped after recovery check"}</strong><p>Active quantity: ${r.outcome.active_amount} of ${x.requested_amount} · Tool calls: ${r.outcome.tool_calls}</p><p>Recovery: ${escapeHtml(r.outcome.recovery.join(" → ") || "No recovery needed")} · Duplicate effect: ${r.outcome.duplicate_effect ? "yes" : "no"}</p></div>` : "";
    el("detail").innerHTML = `${badge(r)}<h2>${escapeHtml(r.title)}</h2><p class="lead">${escapeHtml(r.explanation)}</p><dl class="facts"><div><dt>Target</dt><dd>${escapeHtml(x.resource)}</dd></div><div><dt>Quantity</dt><dd>${x.requested_amount} simulated units</dd></div><div><dt>Authority</dt><dd>${x.authority_current && x.permitted_operations.includes(x.operation) ? "Present" : "Missing"}</dd></div><div><dt>Policy</dt><dd>${x.policy_allows ? "Permits this operation" : "Does not permit"}</dd></div></dl><h3>Proposed action</h3><pre class="call">${escapeHtml(x.operation)}(${escapeHtml(JSON.stringify({resource:x.proposed_resource,quantity:x.amount}))})</pre>${outcome}${r.allowed_actions.length ? `<label for="note">Review note</label><textarea id="note" maxlength="500" placeholder="Explain your decision. Required when resolving a hold."></textarea><div class="actions">${r.allowed_actions.filter(a => a !== "reject").map(a => `<button type="button" data-action="${a}" ${busy ? "disabled" : ""}>${actionLabels[a]}</button>`).join("")}<button class="danger" type="button" data-action="reject" ${busy ? "disabled" : ""}>Reject request</button></div><p class="muted">Approving or resolving a hold rechecks the gate. Running the action is a separate step. Review notes are local, self-declared records.</p>` : '<p class="muted">This request is closed. Its review and outcome remain in the audit trail.</p>'}<h3>Request history</h3><ol class="timeline">${events.map(e => `<li><time>${escapeHtml(shortTime(e.timestamp))}</time><span><strong>${escapeHtml(e.kind.replaceAll("_"," "))}</strong>${e.detail.note ? `<br>${escapeHtml(e.detail.note)}` : ""}${e.detail.decision ? ` · ${escapeHtml(labels[e.detail.decision] || e.detail.decision)}` : ""}</span></li>`).join("")}</ol>`;
    document.querySelectorAll("[data-action]").forEach(b => b.addEventListener("click", () => transact("/api/action", {id:r.id,action:b.dataset.action,revision:r.revision,note:el("note")?.value || ""})));
  } else {
    el("detail").innerHTML = '<div class="empty"><h2>Your approval queue starts here.</h2><p>Load example requests to try approvals, clarification, policy holds and recovery.</p></div>';
  }
  el("events").innerHTML = state.events.length ? [...state.events].reverse().map(e => `<tr><td>${escapeHtml(shortTime(e.timestamp))}</td><td>${escapeHtml(state.requests.find(r => r.id === e.request_id)?.title || e.request_id)}</td><td>${escapeHtml(e.kind.replaceAll("_"," "))}</td><td>${escapeHtml(e.detail.note || e.detail.reason || e.detail.decision || (e.kind === "sandbox_outcome" ? (e.detail.completed ? "Effect verified" : "Halted after check") : ""))}</td></tr>`).join("") : '<tr><td colspan="4">No events yet. Load the illustrative requests to begin.</td></tr>';
}
async function transact(path, data) {
  if (busy) return;
  busy = true; showError("");
  document.querySelectorAll("button").forEach(b => b.disabled = true);
  try {state = await api(path, data);}
  catch (error) {showError(error.message);}
  finally {busy = false;render();el("detail").classList.remove("changed");requestAnimationFrame(() => el("detail").classList.add("changed"));}
}
el("seed").addEventListener("click", () => transact("/api/seed", {}));
el("filter").addEventListener("change", render);
el("export").addEventListener("click", async () => {
  try {const data = await api("/api/audit"); const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"})); const a = document.createElement("a"); a.href=url;a.download="scopequay-audit.json";a.click();setTimeout(() => URL.revokeObjectURL(url),1000);}
  catch(error) {showError(error.message);}
});
(async () => {try {state = await api("/api/state");el("connection").textContent="Connected to local sandbox";render();}catch(error){el("connection").textContent="Local server unavailable";showError("Start ScopeQuay locally, then refresh this page. " + error.message);}})();
