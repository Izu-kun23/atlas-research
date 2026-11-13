"""Export checked-in notebook code and saved outputs into the read-only UI lab."""

from pathlib import Path
import json
from html import escape

root = Path(__file__).resolve().parents[1]
blocks = []
for i, path in enumerate(sorted((root / "notebooks").glob("*.ipynb")), 1):
    nb = json.loads(path.read_text())
    cells = nb["cells"]
    title = "".join(cells[0]["source"]).split("\n")[0].lstrip("# ")
    outputs = []
    count = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        count += 1
        rendered = []
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if "image/png" in data:
                rendered.append(
                    '<img loading="lazy" alt="Executed notebook experiment chart" src="data:image/png;base64,'
                    + "".join(data["image/png"])
                    + '">'
                )
            elif "text/plain" in data:
                rendered.append(
                    "<pre>" + escape("".join(data["text/plain"])) + "</pre>"
                )
            elif "text" in output:
                rendered.append("<pre>" + escape("".join(output["text"])) + "</pre>")
        if rendered:
            outputs.append(
                "<details><summary>Cell "
                + str(count)
                + ' · Code & output</summary><pre class="code">'
                + escape("".join(cell["source"]))
                + "</pre>"
                + "".join(rendered)
                + "</details>"
            )
    blocks.append(
        '<article class="card notebook"><div class="eyebrow">Experiment 0'
        + str(i)
        + "</div><h2>"
        + escape(title)
        + '</h2><p class="muted">'
        + str(count)
        + ' executed code cells · Saved outputs from the repository</p><a target="_blank" rel="noopener noreferrer" href="https://github.com/Izu-kun23/atlas-research/blob/main/notebooks/'
        + path.name
        + '">Open Jupyter notebook ↗</a>'
        + "".join(outputs)
        + "</article>"
    )
(root / "app/web/notebooks.js").write_text(
    'document.getElementById("notebook-content").innerHTML='
    + json.dumps("".join(blocks))
    + ";\n"
)
