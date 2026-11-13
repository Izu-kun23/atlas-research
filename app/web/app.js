function linked(text, sources) {
 const pattern = /https?:\/\/[^\s<>]+|\[S\d+\]/g;
 let last=0, result="";
 for (const match of text.matchAll(pattern)) {
  result+=esc(text.slice(last,match.index));
  const source=sources.find(s=>"["+s.id+"]"===match[0]);
  const url=source?.url || (match[0].startsWith("http")?match[0]:null);
  result+=url&&/^https?:\/\//.test(url)?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer" class="citation">${esc(match[0])} ↗</a>`:esc(match[0]);
  last=match.index+match[0].length;
 }
 return result+esc(text.slice(last));
}
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
  $("report").innerHTML = d.report.replace(/\n## Inference record[\s\S]*?(?=\n## Limitations|$)/, "").replace(/^Mode:.*$|^Model:.*$/gm, "")
    .split("\n")
    .map((line) => {
      if (line.startsWith("# ")) return `<h2>${linked(line.slice(2), d.sources)}</h2>`;
      if (line.startsWith("## ")) return `<h3>${linked(line.slice(3), d.sources)}</h3>`;
      if (line.startsWith("> "))
        return `<blockquote>${linked(line.slice(2), d.sources)}</blockquote>`;
      return line ? `<p>${linked(line, d.sources)}</p>` : "";
    })
    .join("");
  $("download").hidden = false;
  $("download").href="/api/reports/"+d.id+"/download";
  $("sources").innerHTML = d.sources
    .map(
      (s) =>
        `<div class="source"><span class="pill">${esc(s.id)}</span> <a href="${/^https?:\/\//.test(s.url) ? esc(s.url) : "#"}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a><p>${esc(s.text)}</p><span class="muted">${esc(s.provenance)} · relevance ${s.relevance}</span></div>`,
    )
    .join("");
  trace(d.trace);
  stats([
    ["Research stages", 5, "Five live research stages"],
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
    message("Gathering sources and reviewing evidence. This may take a few minutes…");
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
api("/config").then(d=>{
 $("mode").textContent=d.live_ready?"Live research ready":"Demo corpus";

}).catch(e=>message(e.message,true));
history().catch((e) => message(e.message, true));

document.querySelectorAll("[data-topic]").forEach(
  (button) =>
    (button.onclick = () => {
      $("topic").value = button.dataset.topic;
      $("research").requestSubmit($("research").querySelector("button"));
    }),
);

function navigate(){
 const view=["specs","notebooks"].includes(location.hash.slice(1))?location.hash.slice(1):"research";
 document.querySelectorAll(".page-view").forEach(el=>el.hidden=el.id!==view+"-view");
 document.querySelectorAll("[data-view]").forEach(el=>{el.classList.toggle("active",el.dataset.view===view);if(el.dataset.view===view)el.setAttribute("aria-current","page");else el.removeAttribute("aria-current");});
 $("page-title").textContent={research:"Research workspace",notebooks:"Notebook lab",specs:"System specs"}[view];
}
window.addEventListener("hashchange",navigate);navigate();
