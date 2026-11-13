const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");
const root = path.resolve(__dirname, "..");
const fixtures = JSON.parse(
  fs.readFileSync(path.join(__dirname, "fixtures/ui.json"), "utf8"),
);
const wait = () => new Promise((r) => setTimeout(r, 30));
async function create(fail = false) {
  const dom = new JSDOM(
    fs.readFileSync(path.join(root, "app/web/index.html"), "utf8"),
    { url: "http://localhost", runScripts: "outside-only" },
  );
  dom.window.fetch = async (url) => {
    const route = new URL(url, "http://localhost").pathname.replace("/api", "");
    if (fail)
      return {
        ok: false,
        json: async () => ({ detail: "Controlled failure" }),
      };
    assert.ok(route in fixtures, "Unexpected route " + route);
    return { ok: true, json: async () => fixtures[route] };
  };
  dom.window.eval(
    fs.readFileSync(path.join(root, "app/web/common.js"), "utf8") +
      "\n" +
      fs.readFileSync(path.join(root, "app/web/app.js"), "utf8") +
      "\n"+fs.readFileSync(path.join(root,"app/web/notebooks.js"),"utf8")+"\nwindow.testEscape=esc;",
  );
  await wait();
  return dom;
}
async function submit(dom, id) {
  const form = dom.window.document.getElementById(id);
  const button = form.querySelector("button");
  const event = new dom.window.SubmitEvent("submit", {
    bubbles: true,
    cancelable: true,
    submitter: button,
  });
  form.dispatchEvent(event);
  await wait();
  assert.equal(button.disabled, false, "Button resets after submission");
}
(async () => {
  const dom = await create(),
    d = dom.window.document;
  assert.equal(
    d.querySelectorAll("#stats .stat").length,
    4,
    "Four real metric cards",
  );
  if (fixtures["/research"]) {
    await submit(dom, "research");
    assert.match(d.getElementById("report").textContent, /Findings/);
    assert.equal(d.querySelectorAll("#sources .source").length, 4);
    assert.equal(d.getElementById("download").hidden, false);
  } else if (fixtures["/predict"]) {
    assert.equal(d.querySelectorAll("#models tr").length, 3);
    await submit(dom, "predict");
    assert.match(d.getElementById("prediction").textContent, /SHAP/);
    assert.equal(d.querySelectorAll("#prediction .feature").length, 6);
    Object.defineProperty(d.getElementById("csv"), "files", {
      value: [{ size: 100, text: async () => "fixture" }],
    });
    await submit(dom, "import");
    assert.equal(d.querySelectorAll("#transactions tr").length, 2);
  } else {
    d.getElementById("query").value = "machine learning";
    await submit(dom, "search");
    assert.ok(d.querySelectorAll("#results .result").length > 0);
    // A programmatic submit can have no submitter (autocomplete uses this path).
    d.getElementById("search").dispatchEvent(
      new dom.window.SubmitEvent("submit", { bubbles: true, cancelable: true }),
    );
    await wait();
    assert.match(d.getElementById("status").textContent, /complete/);
  }
  dom.window.location.hash="notebooks";
  dom.window.dispatchEvent(new dom.window.HashChangeEvent("hashchange"));
  assert.equal(d.getElementById("notebooks-view").hidden,false);
  assert.equal(d.querySelectorAll(".notebook").length,3);
  assert.ok(d.querySelectorAll(".notebook img").length>0);
  dom.window.location.hash="specs";
  dom.window.dispatchEvent(new dom.window.HashChangeEvent("hashchange"));
  assert.equal(d.getElementById("specs-view").hidden,false);
  assert.equal(d.getElementById("research-view").hidden,true);
  assert.ok(d.querySelectorAll("#report a[href^='http']").length>0);
  // External text must be escaped, not executed as markup.
  assert.equal(
    dom.window.testEscape("<img src=x onerror=alert(1)>"),
    "&lt;img src=x onerror=alert(1)&gt;",
  );
  dom.window.close();
  const broken = await create(true);
  assert.match(
    broken.window.document.getElementById("status").textContent,
    /Controlled failure/,
  );
  broken.window.close();
  console.log(
    "DOM integration checks passed: metrics, primary workflow, output rendering, error state and escaping",
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
