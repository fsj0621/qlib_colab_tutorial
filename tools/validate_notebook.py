from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

try:
    import nbformat
except ModuleNotFoundError:  # Keep validation usable in a clean Python install.
    nbformat = None


def read_notebook(notebook_path: Path):
    if nbformat is not None:
        notebook = nbformat.read(notebook_path, as_version=4)
        nbformat.validate(notebook)
        return notebook.cells

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise ValueError("expected a valid nbformat 4 notebook")
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") not in {"markdown", "code", "raw"}:
            raise ValueError(f"invalid cell_type in cell {index}")
        if not isinstance(cell.get("source"), list):
            raise ValueError(f"cell {index} source must be a list")
        if cell.get("cell_type") == "code" and not isinstance(cell.get("outputs"), list):
            raise ValueError(f"cell {index} outputs must be a list")
    return notebook["cells"]


def main() -> int:
    notebook_path = Path(sys.argv[1])
    cells = read_notebook(notebook_path)

    syntax_errors: list[tuple[int, str]] = []
    code_cells = 0
    output_count = 0

    for index, cell in enumerate(cells):
        cell_type = cell.cell_type if hasattr(cell, "cell_type") else cell["cell_type"]
        if cell_type != "code":
            continue
        code_cells += 1
        output_count += len(cell.get("outputs", []))
        source = cell.source if hasattr(cell, "source") else "".join(cell.get("source", []))
        try:
            ast.parse(source)
        except SyntaxError as error:
            syntax_errors.append((index, f"line {error.lineno}: {error.msg}"))

    print(
        f"nbformat OK | cells={len(cells)} | "
        f"code={code_cells} | outputs={output_count}"
    )
    if syntax_errors:
        for index, message in syntax_errors:
            print(f"syntax error in cell {index}: {message}")
        return 1

    print("all Python code cells parse successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
