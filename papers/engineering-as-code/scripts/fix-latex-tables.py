#!/usr/bin/env python3
r"""
Post-process Pandoc-generated LaTeX to make wide longtables fit the page.

Strategy:
- Detect \begin{longtable} environments and their column specifiers.
- Replace plain l/c/r columns with ragged-right p{width} columns whose widths
  are proportional to the text width.
- Wrap very wide tables (>= 6 columns) in \footnotesize to reduce overfull
  hbox pressure.
"""
import re
import sys


def parse_col_spec(spec: str) -> list[str]:
    """Extract simple l/c/r column letters from a longtable column spec."""
    spec = re.sub(r'@\{[^}]*\}', '', spec)
    spec = re.sub(r'\|', '', spec)
    return [ch for ch in spec if ch in 'lcr']


def build_p_spec(cols: list[str]) -> str:
    n = len(cols)
    if n == 0:
        return ''
    slack = 0.12
    usable = 1.0 - slack
    if n >= 3:
        first = min(0.16, usable / n)
        rest = (usable - first) / (n - 1)
        widths = [first] + [rest] * (n - 1)
    else:
        widths = [usable / n] * n

    new_cols = [
        f'>{{\\raggedright\\arraybackslash}}p{{{w:.3f}\\textwidth}}'
        for w in widths
    ]
    return '@{}' + ' '.join(new_cols) + '@{}'


def rewrite_longtable(match: re.Match) -> str:
    optional = match.group(1) or ''      # e.g. [c] or []
    spec = match.group(2)
    body = match.group(3)

    cols = parse_col_spec(spec)
    new_spec = build_p_spec(cols)
    if not new_spec:
        return match.group(0)

    table = f'\\begin{{longtable}}{optional}{{{new_spec}}}{body}\\end{{longtable}}'
    # Very wide tables benefit from a smaller font size.
    if len(cols) >= 6:
        table = f'{{\\footnotesize\n{table}\n}}'
    return table


def main():
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <file.tex>', file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = re.compile(
        r'\\begin\{longtable\}(\[.*?\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}(.*?)\\end\{longtable\}',
        re.DOTALL
    )
    new_text = pattern.sub(rewrite_longtable, text)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_text)

    count = len(pattern.findall(text))
    print(f'Fixed {count} longtable(s) in {path}')


if __name__ == '__main__':
    main()
