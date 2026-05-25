from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
import sys

FONT_DIR = Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"
FONT_FILE_NAME = "MapleMonoNormalNL-NF-CN"
FONT_NAME = "Maple Mono Normal NL NF CN"


def find_font_file(font_dir: Path, font_file_name: str) -> Path | None:
    if not font_dir.exists() or not font_dir.is_dir():
        return None
    regular = sorted(font_dir.glob(f"{font_file_name}-Regular.*"))
    if regular:
        return regular[0]
    for ext in (".otf", ".ttf", ".ttc"):
        candidates = sorted(font_dir.glob(f"*{ext}"))
        if candidates:
            return candidates[0]
    return None


def make_header(header_path: Path, font_dir: Path, font_name: str, font_file: Path | None) -> None:
    font_path = font_dir.as_posix().rstrip("/") + "/"
    if font_file is None:
        font_face = font_name
        font_options = f"Path={font_path},Extension=ttf"
    else:
        font_face = font_file.name
        font_options = f"Path={font_path}"
        bold_file = font_file.with_name(
            font_file.name.replace("Regular", "Bold"))
        italic_file = font_file.with_name(
            font_file.name.replace("Regular", "Italic"))
        bold_italic_file = font_file.with_name(
            font_file.name.replace("Regular", "BoldItalic"))
        if bold_file.exists():
            font_options += f",BoldFont={bold_file.name}"
        if italic_file.exists():
            font_options += f",ItalicFont={italic_file.name}"
        if bold_italic_file.exists():
            font_options += f",BoldItalicFont={bold_italic_file.name}"
    header_text = fr"""% Generated font header for Pandoc -> XeLaTeX
\usepackage{{enumitem}}
\setlistdepth{{9}}
\renewlist{{itemize}}{{itemize}}{{9}}
\setlist[itemize,1]{{label=\textbullet}}
\setlist[itemize,2]{{label=\textbullet}}
\setlist[itemize,3]{{label=\textbullet}}
\setlist[itemize,4]{{label=\textbullet}}
\setlist[itemize,5]{{label=\textbullet}}
\setlist[itemize,6]{{label=\textbullet}}
\setlist[itemize,7]{{label=\textbullet}}
\setlist[itemize,8]{{label=\textbullet}}
\setlist[itemize,9]{{label=\textbullet}}
\usepackage[UTF8,fontset=none]{{ctex}}
\usepackage{{fontspec}}
\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{calc}}
\usepackage{{quoting}}
\usepackage{{mdframed}}
\usepackage{{ragged2e}}
\usepackage{{longtable}}
\usepackage[a4paper,margin=25.4mm]{{geometry}}
\definecolor{{codebg}}{{RGB}}{{240,240,240}}
\definecolor{{quotebg}}{{RGB}}{{248,248,248}}
\definecolor{{quoteborder}}{{RGB}}{{200,200,200}}
\newmdenv[
    linewidth=2pt,
    linecolor=quoteborder,
    backgroundcolor=quotebg,
    topline=false,
    rightline=false,
    bottomline=false,
    leftmargin=0pt,
    rightmargin=0pt,
    innerleftmargin=0.8em,
    innerrightmargin=0.8em,
    innertopmargin=0.45em,
    innerbottommargin=0.45em,
    skipabove=0.7em,
    skipbelow=0.7em
]{{quoteblock}}
\quotingsetup{{leftmargin=0pt,rightmargin=0pt,vskip=0pt}}
\renewenvironment{{quote}}{{\begin{{quoteblock}}\begin{{quoting}}}}{{\end{{quoting}}\end{{quoteblock}}}}
\lstset{{
	backgroundcolor=\color{{codebg}},
	basicstyle=\ttfamily\small,
	breaklines=true,
	columns=fullflexible,
	keepspaces=true,
	frame=single,
	framerule=0pt,
	framesep=6pt,
	xleftmargin=0.4em,
	xrightmargin=0.4em,
	aboveskip=0.8em,
	belowskip=0.8em
}}
\setlength{{\arrayrulewidth}}{{0.5pt}}
\setlength{{\tabcolsep}}{{0pt}}
\renewcommand{{\arraystretch}}{{1.2}}
\makeatletter
\@ifundefined{{LTleft}}{{}}{{\setlength{{\LTleft}}{{0pt}}}}
\@ifundefined{{LTright}}{{}}{{\setlength{{\LTright}}{{0pt}}}}
\renewcommand\paragraph{{\@startsection{{paragraph}}{{4}}{{\z@}}%
	{{3.25ex \@plus 1ex \@minus .2ex}}%
	{{1.5ex \@plus .2ex}}%
	{{\normalfont\normalsize\bfseries}}}}
\renewcommand\subparagraph{{\@startsection{{subparagraph}}{{5}}{{\z@}}%
	{{3.25ex \@plus 1ex \@minus .2ex}}%
	{{1.5ex \@plus .2ex}}%
	{{\normalfont\normalsize\bfseries}}}}
\makeatother
\defaultfontfeatures{{Ligatures=TeX,Scale=MatchLowercase}}
\setmainfont{{{font_face}}}[{font_options}]
\setsansfont{{{font_face}}}[{font_options}]
\setmonofont{{{font_face}}}[{font_options}]
\setCJKmainfont{{{font_face}}}[{font_options}]
\setCJKsansfont{{{font_face}}}[{font_options}]
\setCJKmonofont{{{font_face}}}[{font_options}]
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
"""
    header_path.write_text(header_text, encoding="utf-8")


def fix_hyperref_targets(tex_path: Path) -> None:
    content = tex_path.read_text(encoding="utf-8")
    content = re.sub(
        r"\\hyperref\[(?:[0-9]+-)([^]]+)\]", r"\\hyperref[\1]", content)
    content = re.sub(
        r"\\autoref\[(?:[0-9]+-)([^]]+)\]", r"\\autoref[\1]", content)
    # Pandoc metadata may emit \xmpquote{...} in pdfkeywords; fall back to plain text for compatibility.
    content = re.sub(r"\\xmpquote\{([^{}]*)\}", r"\1", content)
    tex_path.write_text(content, encoding="utf-8")


def style_inline_code(tex_path: Path) -> None:
    # Pandoc with --listings emits inline code as \passthrough{\lstinline!...!}.
    # Convert it to a simple gray inline code style that matches Markdown previews.
    content = tex_path.read_text(encoding="utf-8")

    def repl(match: re.Match[str]) -> str:
        code = match.group(1)
        code = code.replace(r"\_\allowbreak{}", r"\_")
        code = code.replace(r"\allowbreak{}", "")
        return r"\colorbox{codebg}{\strut\texttt{" + code + "}}"

    content = re.sub(r"\\passthrough\{\\lstinline!(.*?)!\}", repl, content)
    tex_path.write_text(content, encoding="utf-8")


def _normalize_table_text_block(block: str) -> str:
    block = block.replace(r"\_", r"\_\allowbreak{}")
    block = block.replace(r"\textless-\textgreater{}", "↔")
    block = block.replace(r"-\textgreater{}", "→")
    block = block.replace(r"\textgreater{}", "→")
    block = re.sub(r"0x([0-9a-fA-F]+)", r"0x\\allowbreak{}\1", block)
    return block


def _parse_columns(spec: str) -> list[str]:
    core = spec.strip()
    if core.startswith("@{}") and core.endswith("@{}"):
        core = core[3:-3]
    columns: list[str] = []
    i = 0
    while i < len(core):
        ch = core[i]
        if ch.isspace() or ch == "|":
            i += 1
            continue
        if ch in ">@<":
            j = i + 1
            if j < len(core) and core[j] == "{":
                brace = 1
                j += 1
                while j < len(core) and brace > 0:
                    if core[j] == "{":
                        brace += 1
                    elif core[j] == "}":
                        brace -= 1
                    j += 1
                i = j
                continue
        if ch in "lcrX":
            columns.append(ch)
            i += 1
            continue
        if ch in "pmb":
            j = i + 1
            if j < len(core) and core[j] == "{":
                brace = 1
                j += 1
                while j < len(core) and brace > 0:
                    if core[j] == "{":
                        brace += 1
                    elif core[j] == "}":
                        brace -= 1
                    j += 1
                columns.append(core[i:j])
                i = j
                continue
        columns.append(ch)
        i += 1
    return columns


def _measure_text_units(text: str) -> int:
    # For mono font layout: CJK/full-width chars count as 2, others count as 1.
    cleaned = re.sub(r"\\[a-zA-Z@]+", " ", text)
    cleaned = re.sub(r"\\([\\{}%_$&#])", r"\1", cleaned)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    total = 0
    for ch in cleaned:
        if ch.isspace():
            continue
        total += 2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1
    return max(1, total)


def _extract_word_units(text: str) -> list[int]:
    cleaned = re.sub(r"\\[a-zA-Z@]+", " ", text)
    cleaned = re.sub(r"\\([\\{}%_$&#])", r"\1", cleaned)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    tokens = re.findall(r"[A-Za-z0-9_./:+-]+|[\u3400-\u9fff]", cleaned)
    units: list[int] = []
    for token in tokens:
        if len(token) == 1 and unicodedata.east_asian_width(token) in {"W", "F"}:
            units.append(2)
        else:
            units.append(len(token))
    return units


def _estimate_column_metrics(table_block: str, column_count: int) -> tuple[list[int], list[int]]:
    if column_count <= 0:
        return [], []
    unit_counts = [1] * column_count
    longest_word_units = [1] * column_count
    for line in table_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if "&" not in line or r"\\" not in line:
            continue
        row_part = line.split(r"\\", 1)[0]
        cells = re.split(r"(?<!\\)&", row_part)
        for i in range(min(column_count, len(cells))):
            cell = cells[i]
            unit_counts[i] += _measure_text_units(cell)
            words = _extract_word_units(cell)
            if words:
                longest_word_units[i] = max(longest_word_units[i], max(words))
    return unit_counts, longest_word_units


def _bordered_colspec(
    spec: str,
    column_total_units: list[int] | None = None,
    column_longest_word_units: list[int] | None = None,
) -> str:
    columns = _parse_columns(spec)
    if not columns:
        return "!{\\vrule width 0.75pt}p{\\textwidth}!{\\vrule width 0.75pt}"
    count = len(columns)
    if column_total_units and len(column_total_units) == count:
        units = [max(1, value) for value in column_total_units]
        total_units = sum(units)
        widths: list[str] = []
        for index, unit in enumerate(units):
            proportional = (
                r"\dimexpr(\textwidth - 2\tabcolsep*%d - %d\arrayrulewidth)*%d/%d\relax"
                % (count, count + 1, unit, total_units)
            )
            if column_longest_word_units and len(column_longest_word_units) == count:
                # In mono fonts, 1 ASCII char ~= 0.5em and 1 CJK char ~= 1em (counted as 2 units).
                min_em = max(0.5, column_longest_word_units[index] / 2.0)
                widths.append(r"\maxof{%s}{%.2fem}" % (proportional, min_em))
            else:
                widths.append(proportional)
    else:
        widths = [
            r"\dimexpr(\textwidth - 2\tabcolsep*%d - %d\arrayrulewidth)/%d\relax"
            % (count, count + 1, count)
        ] * count
    rr = r">{\RaggedRight\arraybackslash\hspace{0pt}\sloppy}"
    rc = r">{\Centering\arraybackslash\hspace{0pt}\sloppy}"
    rl = r">{\RaggedLeft\arraybackslash\hspace{0pt}\sloppy}"
    converted: list[str] = []
    for index, column in enumerate(columns):
        width = widths[index]
        if column == "l":
            converted.append(f"{rr}p{{{width}}}")
        elif column == "c":
            converted.append(f"{rc}p{{{width}}}")
        elif column == "r":
            converted.append(f"{rl}p{{{width}}}")
        elif column == "X":
            converted.append(f"{rr}p{{{width}}}")
        elif column.startswith("p") or column.startswith("m") or column.startswith("b"):
            converted.append(f"{rr}p{{{width}}}")
        else:
            converted.append(f"{rr}p{{{width}}}")
    return r"!{\vrule width 0.75pt}" + "|".join(converted) + r"!{\vrule width 0.75pt}"


def _replace_table_begins_with_bordered(content: str) -> str:
    pattern = re.compile(r"\\begin\{(longtable|tabular)\}(?:\[[^]]*\])?")
    parts: list[str] = []
    cursor = 0
    for match in pattern.finditer(content):
        env_name = match.group(1)
        brace_start = match.end()
        if brace_start >= len(content) or content[brace_start] != "{":
            continue
        depth = 0
        brace_end = brace_start
        while brace_end < len(content):
            char = content[brace_end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            brace_end += 1
        if depth != 0:
            continue
        spec = content[brace_start + 1:brace_end]
        end_marker = f"\\end{{{env_name}}}"
        end_pos = content.find(end_marker, brace_end + 1)
        if end_pos == -1:
            continue
        table_block = content[match.start():end_pos + len(end_marker)]
        column_total_units, column_longest_word_units = _estimate_column_metrics(
            table_block, len(_parse_columns(spec)))
        parts.append(content[cursor:match.start()])
        parts.append(
            f"\\begin{{{env_name}}}{{{_bordered_colspec(spec, column_total_units, column_longest_word_units)}}}")
        cursor = brace_end + 1
    parts.append(content[cursor:])
    return "".join(parts)


def _add_row_hlines_to_longtable(block: str) -> str:
    marker = r"\endlastfoot"
    if marker not in block:
        return block
    head, rest = block.split(marker, 1)
    end_marker = r"\end{longtable}"
    if end_marker not in rest:
        return block
    body, tail = rest.rsplit(end_marker, 1)
    body = re.sub(r"(\\\\)\s*\n", r"\1\n\\hline\n", body)
    body = re.sub(r"(\\hline\s*\n)+\s*$", r"\\hline\n", body)
    return head + marker + body + end_marker + tail


def _bold_plain_header_row(line: str) -> str:
    if line.lstrip().startswith("\\"):
        return line
    cells = [cell.strip() for cell in line.split("&")]
    cells = [rf"\textbf{{{cell}}}" if cell else cell for cell in cells]
    return " " + " & ".join(cells)


def _style_table_frame_and_header(block: str) -> str:
    # Top outer border: thick
    block = re.sub(r"(\\begin\{longtable\}\{.*?\})\s*\n\\hline",
                   r"\1\n\\noalign{\\hrule height 0.75pt}", block, count=1, flags=re.DOTALL)
    # Header bottom border: keep only thick line
    block = block.replace(
        "\\hline\n\\noalign{\\hrule height 0.75pt}", "\\noalign{\\hrule height 0.75pt}")
    # Avoid stacking a thin line from endlastfoot with the thick bottom border.
    block = re.sub(r"\\endhead\s*\n\\hline\s*\n\\endlastfoot",
                   r"\\endhead\n\\endlastfoot", block)
    # Bottom outer border: thick
    block = re.sub(r"\\hline\s*\n\\end\{longtable\}",
                   r"\\noalign{\\hrule height 0.75pt}\n\\end{longtable}", block)

    if r"\endhead" not in block:
        return block
    head_part, tail_part = block.split(r"\endhead", 1)
    head_part = re.sub(
        r"(\\begin\{minipage\}\[b\]\{\\linewidth\}\\raggedright\s*\n)(.*?)(\n\\end\{minipage\})",
        lambda m: m.group(
            1) + r"\textbf{" + m.group(2).strip() + "}" + m.group(3),
        head_part,
        flags=re.DOTALL,
    )
    head_part = re.sub(r"\n([^\n]+?)\\\\", lambda m: "\n" +
                       _bold_plain_header_row(m.group(1)) + r"\\", head_part)
    return head_part + r"\endhead" + tail_part


def add_full_table_borders(tex_path: Path) -> None:
    content = tex_path.read_text(encoding="utf-8")
    content = _replace_table_begins_with_bordered(content)
    content = content.replace(r"\toprule\noalign{}", r"\hline")
    content = content.replace(r"\midrule\noalign{}",
                              "\\hline\n\\noalign{\\hrule height 0.75pt}")
    content = content.replace(r"\bottomrule\noalign{}", r"\hline")
    content = content.replace(
        r"\begin{longtable}", "\\begingroup\\footnotesize\n\\begin{longtable}")
    content = content.replace(
        r"\end{longtable}", "\\end{longtable}\n\\endgroup")
    content = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}",
                     lambda m: _normalize_table_text_block(m.group(0)), content, flags=re.DOTALL)
    content = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}",
                     lambda m: _add_row_hlines_to_longtable(m.group(0)), content, flags=re.DOTALL)
    content = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}",
                     lambda m: _style_table_frame_and_header(m.group(0)), content, flags=re.DOTALL)
    tex_path.write_text(content, encoding="utf-8")


def add_page_breaks_for_titles_and_subsections(tex_path: Path) -> None:
    content = tex_path.read_text(encoding="utf-8")

    # Insert a page break right after \maketitle when it exists and is not already followed by one.
    content = re.sub(r"(\\maketitle)(?!\s*\\newpage)",
                     r"\1\n\\newpage", content)

    lines = content.splitlines(keepends=True)
    new_lines: list[str] = []
    subsection_pattern = re.compile(r"^\s*\\subsection(?:\[[^\]]*\])?\{")

    for line in lines:
        if subsection_pattern.match(line):
            prev_nonempty: str | None = None
            for prev in reversed(new_lines):
                if prev.strip():
                    prev_nonempty = prev.strip()
                    break
            if prev_nonempty != r"\newpage":
                new_lines.append("\\newpage\n")
        new_lines.append(line)

    tex_path.write_text("".join(new_lines), encoding="utf-8")


def postprocess_tex(tex_path: Path) -> None:
    fix_hyperref_targets(tex_path)
    style_inline_code(tex_path)
    add_page_breaks_for_titles_and_subsections(tex_path)
    add_full_table_borders(tex_path)


def run_command(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR:", " ".join(command), file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)


def build_tex(input_path: Path, tex_path: Path, header_path: Path) -> None:
    if shutil.which("pandoc") is None:
        raise FileNotFoundError("Pandoc 未找到，请先安装 Pandoc 并将其加入 PATH。")
    pandoc_cmd = [
        "pandoc",
        str(input_path),
        "-s",
        "--listings",
        "-o",
        str(tex_path),
        "--include-in-header",
        str(header_path),
        "--pdf-engine=xelatex",
        "--from",
        "markdown+yaml_metadata_block+footnotes+table_captions+tex_math_dollars",
    ]
    run_command(pandoc_cmd)


def compile_pdf(tex_path: Path) -> None:
    if shutil.which("xelatex") is None:
        raise FileNotFoundError("xelatex 未找到，请先安装 XeLaTeX 并将其加入 PATH。")
    output_dir = tex_path.parent
    cmd = ["xelatex", "-interaction=nonstopmode",
           "-halt-on-error", "-synctex=1", tex_path.name]
    for _ in range(2):
        run_command(cmd, cwd=output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 Markdown 转换为 .tex（默认）；可选编译生成 PDF。")
    parser.add_argument("-i", "--input", default="服务器设计方案.md",
                        help="输入 Markdown 文件路径")
    parser.add_argument("-t", "--tex", help="输出 LaTeX 文件路径")
    parser.add_argument("-p", "--pdf", help="输出 PDF 文件路径")
    parser.add_argument("-d", "--out-dir", help="输出目录，若指定则 tex/pdf 文件使用该目录")
    parser.add_argument("--with-pdf", action="store_true",
                        help="额外编译并生成 PDF（默认不生成）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在：{input_path}")

    output_dir = Path(args.out_dir).expanduser(
    ).resolve() if args.out_dir else None
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    output_tex = Path(args.tex).expanduser(
    ) if args.tex else input_path.with_suffix(".tex")
    if not output_tex.is_absolute():
        output_tex = (
            output_dir / output_tex) if output_dir else (input_path.parent / output_tex)

    output_pdf = Path(args.pdf).expanduser(
    ) if args.pdf else input_path.with_suffix(".pdf")
    if not output_pdf.is_absolute():
        output_pdf = (
            output_dir / output_pdf) if output_dir else (input_path.parent / output_pdf)

    header_path = output_tex.with_name("pandoc_xelatex_header.tex")

    font_file = find_font_file(FONT_DIR, FONT_FILE_NAME)
    if font_file is None:
        print(
            f"WARNING: 未在 {FONT_DIR} 中找到 {FONT_FILE_NAME} 字体文件，将仅使用字体名注册。", file=sys.stderr)
    else:
        print(f"找到字体文件：{font_file}")

    make_header(header_path, FONT_DIR, FONT_NAME, font_file)
    build_tex(input_path, output_tex, header_path)
    postprocess_tex(output_tex)
    should_compile_pdf = args.with_pdf
    if should_compile_pdf:
        compile_pdf(output_tex)
        compiled_pdf = output_tex.with_suffix(".pdf")
        if not compiled_pdf.exists():
            raise FileNotFoundError(f"XeLaTeX 未生成 PDF: {compiled_pdf}")
        if output_pdf != compiled_pdf:
            if output_pdf.exists():
                output_pdf.unlink()
            shutil.copy(compiled_pdf, output_pdf)
    print(f"已生成：{output_tex}")
    if should_compile_pdf:
        print(f"已生成：{output_pdf}")


if __name__ == "__main__":
    main()
