from __future__ import annotations

import ast
import sys
from pathlib import Path

import nbformat


def main() -> int:
    notebook_path = Path(sys.argv[1])
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)

    syntax_errors: list[tuple[int, str]] = []
    code_cells = 0
    output_count = 0

    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        code_cells += 1
        output_count += len(cell.get("outputs", []))
        try:
            ast.parse(cell.source)
        except SyntaxError as error:
            syntax_errors.append((index, f"line {error.lineno}: {error.msg}"))

    print(
        f"nbformat OK | cells={len(notebook.cells)} | "
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

