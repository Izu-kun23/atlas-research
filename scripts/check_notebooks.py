"""Validate notebook structure; optionally execute all notebooks in isolated kernels."""

import argparse, hashlib, json, os
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    records = []
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        cells = [c for c in notebook.cells if c.cell_type == "code"]
        for cell in cells:
            compile(cell.source, str(path), "exec")
        if args.execute:
            from nbclient import NotebookClient

            NotebookClient(
                notebook,
                timeout=180,
                kernel_name="python3",
                resources={"metadata": {"path": str(ROOT)}},
            ).execute()
        assert all(
            c.get("execution_count") for c in cells
        ), f"Unexecuted cells in {path.name}"
        assert not [
            o for c in cells for o in c.get("outputs", []) if o.output_type == "error"
        ], f"Notebook errors in {path.name}"
        records.append(
            {
                "notebook": path.name,
                "code_cells": len(cells),
                "source_sha256": hashlib.sha256(
                    "\n".join(c.source for c in notebook.cells).encode()
                ).hexdigest(),
                "executed_this_run": args.execute,
            }
        )
    output = ROOT / "artifacts/notebooks"
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation.json").write_text(json.dumps(records, indent=2))
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
