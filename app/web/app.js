const stages = [
  ["Research agent", "Discover source material"],
  ["Analysis agent", "Rank relevant evidence"],
  ["Summary agent", "Extract supported findings"],
  ["Evidence-check agent", "Validate source IDs and excerpts"],
  ["Report agent", "Compose a traceable answer"],
];
function trace(items = []) {
  $("trace").innerHTML = stages
    .map(([name, detail], i) => {
      const done = items.find((x) => x.agent === name);
      return `<div class="step"><span class="stepicon">${done ? "✓" : String(i + 1).padStart(2, "0")}</span><div><strong>${name}</strong><p>${esc(done ? done.detail : detail)}</p>${done ? '<span class="muted">' + done.duration_ms + " ms</span>" : ""}</div></div>`;
    })
    .join("");
}
function show(d) {
  $("report").className = "report";
  $("report").innerHTML = d.report
    .split("\n")
    .map((line) => {
      if (line.startsWith("# ")) return `<h2>${esc(line.slice(2))}</h2>`;
      if (line.startsWith("## ")) return `<h3>${esc(line.slice(3))}</h3>`;
      if (line.startsWith("> "))
        return `<blockquote>${esc(line.slice(2))}</blockquote>`;
      return line ? `<p>${esc(line)}</p>` : "";
    })
    .join("");
  $("download").hidden = false;
  $("download").href = "/api/reports/" + d.id + "/download";
  $("sources").innerHTML = d.sources
    .map(
      (s) =>
        `<div class="source"><span class="pill">${esc(s.id)}</span> <a href="${/^https?:\/\//.test(s.url) ? esc(s.url) : "#"}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a><p>${esc(s.text)}</p><span class="muted">${esc(s.provenance)} · relevance ${s.relevance}</span></div>`,
    )
    .join("");
  trace(d.trace);
  stats([
    ["Research stages", 5, "Bounded LangGraph workflow"],
    ["Sources reviewed", d.sources.length, "Provenance preserved"],
    [
      "Accepted findings",
      d.verification.accepted,
      "Exact evidence excerpt checked",
    ],
    [
      "Rejected findings",
      d.verification.rejected,
      "Unsupported excerpts excluded",
    ],
  ]);
}
async function history() {
  const d = await api("/reports");
  $("history").innerHTML =
    d
      .map(
        (r) =>
          `<div class="source"><button class="secondary" data-id="${r.id}">${esc(r.topic)}</button><p>${esc(r.created)} UTC</p></div>`,
      )
      .join("") || "No investigations yet.";
  $("history")
    .querySelectorAll("button")
    .forEach(
      (b) =>
        (b.onclick = () =>
          busy(b, async () => show(await api("/reports/" + b.dataset.id)))),
    );
}
$("research").onsubmit = (e) => {
  e.preventDefault();
  busy(e.submitter, async () => {
    message(
      "Research workflow running. Live searches and evidence review can take a few minutes…",
    );
    const d = await api("/research", {
      method: "POST",
      body: JSON.stringify({ topic: $("topic").value }),
    });
    show(d);
    await history();
    message(
      "Research complete. Review source provenance and limitations before using findings.",
    );
  });
};
trace();
stats([
  ["Research stages", 5, "Specialized processing roles"],
  ["Sources reviewed", "—", "Start an investigation"],
  ["Accepted findings", "—", "Evidence validation enabled"],
  ["Reports", "—", "Persistent local history"],
]);
api("/config")
  .then((d) => ($("mode").textContent = d.mode.toUpperCase() + " MODE"))
  .catch((e) => message(e.message, true));
history().catch((e) => message(e.message, true));
