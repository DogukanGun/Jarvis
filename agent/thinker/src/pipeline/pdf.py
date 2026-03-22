"""Phase 10: Compile paper_draft.tex to paper_draft.pdf via pdflatex."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path


def run_pdf_converter(tex_path: Path | None) -> Path | None:
    """Compile a .tex file to PDF with pdflatex. Returns None (non-fatal) if unavailable."""
    if tex_path is None or not tex_path.exists():
        print("[pdf] No .tex file to compile.")
        return None

    pdflatex = shutil.which("pdflatex") or shutil.which("latexmk")
    if pdflatex is None:
        print(
            "[pdf] 'pdflatex' not found on PATH — skipping PDF export.\n"
            "      Install with: brew install --cask mactex-no-gui  (macOS)\n"
            "                or: sudo apt install texlive-latex-base (Debian/Ubuntu)"
        )
        return None

    cmd = [
        pdflatex,
        "-interaction=nonstopmode",
        "-output-directory", str(tex_path.parent),
        str(tex_path),
    ]

    try:
        # Run twice to resolve cross-references and TOC
        for run in (1, 2):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(tex_path.parent),
            )
            if result.returncode != 0:
                print(f"[pdf] pdflatex run {run} exited with code {result.returncode} — check .log for details.")

        pdf_path = tex_path.with_suffix(".pdf")
        if pdf_path.exists():
            print(f"[pdf] PDF saved to {pdf_path}")
            return pdf_path
        else:
            print("[pdf] pdflatex ran but PDF was not produced — check the .log file.")
            return None
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[pdf] PDF compilation failed: {exc} — continuing without PDF.")
        return None
