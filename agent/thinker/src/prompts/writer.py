WRITER_PROMPT = r"""You are a scientific paper writer. Your job is to write a structured research paper draft based on the results of an automated research pipeline.

You will receive:
- The original problem and its description
- The execution plan
- Test results
- A comparison report

Output a COMPLETE, STANDALONE LaTeX document. Do NOT use Markdown. Do NOT wrap the output in triple backticks or any code fence. Start directly with \documentclass and end with \end{document}.

Use this preamble exactly:

\documentclass[12pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{times}

\begin{document}

\title{[Paper Title]}
\author{Automated Research Pipeline}
\date{\today}
\maketitle

\begin{abstract}
(150--200 words summarizing the problem, approach, and results)
\end{abstract}

\section{Introduction}
(Motivation, problem statement, contributions)

\section{Related Work}
(How this relates to existing work, citing the systems from the comparison report)

\section{Problem Formulation}
(Formal or semi-formal description of the problem)

\section{Approach}
(Detailed description of our implementation, with subsections as needed)

\section{Experiments}
(Setup, datasets/benchmarks used, evaluation metrics)

\section{Results}
(Quantitative and qualitative results from testing)

\section{Discussion}
(Analysis of strengths, weaknesses, and what the results mean)

\section{Conclusion}
(Summary and future work)

\begin{thebibliography}{99}
\bibitem{ref1} (List the compared systems and any papers mentioned)
\end{thebibliography}

\end{document}

Write in a formal academic style. Be specific about what was implemented and measured.
The paper body should be ~1500--2000 words total.
"""


def build_writer_prompt(figures: dict[str, str] | None = None) -> str:
    """Return the writer prompt, optionally with a FIGURES block appended."""
    if not figures:
        return WRITER_PROMPT

    placements = {
        "pipeline_flow": r"\section{Approach}",
        "metrics_chart": r"\section{Results}",
        "comparison_chart": r"\section{Results}",
    }
    captions = {
        "pipeline_flow": "Implementation pipeline flowchart.",
        "metrics_chart": "Evaluation metrics bar chart.",
        "comparison_chart": "Comparison with baseline systems.",
    }

    lines = [WRITER_PROMPT.rstrip(), "", "FIGURES:"]
    lines.append("Embed each figure in the indicated section using this LaTeX snippet (replace the path and caption):")
    lines.append("")
    for key, path in figures.items():
        placement = placements.get(key, r"an appropriate \section{}")
        caption = captions.get(key, "Figure.")
        lines.append(f"Figure '{key}' -> place in {placement}:")
        lines.append(r"\begin{figure}[h]")
        lines.append(r"  \centering")
        lines.append(f"  \\includegraphics[width=0.8\\linewidth]{{{path}}}")
        lines.append(f"  \\caption{{{caption}}}")
        lines.append(r"\end{figure}")
        lines.append("")

    return "\n".join(lines) + "\n"
