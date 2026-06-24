#!/usr/bin/env python3
r"""
Post-process Pandoc-generated LaTeX to make wide longtables fit the page.

Strategy:
- Detect \begin{longtable} environments and their column specifiers.
- Replace plain l/c/r columns with ragged-right p{width} columns whose widths
  are proportional to the text width.
- Wrap very wide tables (>= 6 columns) in \footnotesize to reduce overfull
  hbox pressure.

For FSE (ACM acmart sigconf), longtable is unsupported in two-column mode.
Pass --fse to convert longtables into table* (spanning single-page wide tables).
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


def rewrite_longtable_fse(match: re.Match) -> str:
    r"""Convert a longtable environment into an ACM table* environment.

    Pandoc emits longtables with repeated header blocks and (sometimes) a
    trailing footer block.  We extract the single header row and the data
    rows, then rebuild the table as a booktabs-style tabular with explicit
    \toprule / \midrule / \bottomrule so the horizontal rules survive the
    conversion.
    """
    spec = match.group(2)
    body = match.group(3)

    # Extract caption and label if present at the beginning.
    caption = ''
    label = ''
    body = body.lstrip()
    cap_match = re.match(
        r'\\caption\{([^}]*)\}(?:\\label\{([^}]*)\})?\\tabularnewline\s*',
        body,
    )
    if cap_match:
        caption = cap_match.group(1)
        label = cap_match.group(2) or ''
        body = body[cap_match.end():]

    # Extract the header row from the first header block before stripping it.
    header_match = re.search(
        r'\\toprule\\noalign\{\}\s*(.*?)\s*\\midrule\\noalign\{\}',
        body,
        flags=re.DOTALL,
    )
    header = header_match.group(1).strip() if header_match else ''

    # Strip the repeated-header block(s) and the footer block.
    body = re.sub(
        r'(?:\\toprule\\noalign\{\}\s*.*?\\midrule\\noalign\{\}\s*\\endfirsthead\s*)?'
        r'\\toprule\\noalign\{\}\s*.*?\\midrule\\noalign\{\}\s*\\endhead\s*',
        '',
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r'\\bottomrule\\noalign\{\}\s*\\endlastfoot\s*',
        '',
        body,
        flags=re.DOTALL,
    )
    # Drop any stray longtable markers.
    body = re.sub(
        r'\\endfirsthead|\\endhead|\\endfoot|\\endlastfoot',
        '',
        body,
    )
    # Remove remaining \noalign{} and \tabularnewline artifacts.
    body = re.sub(r'\\noalign\{\}', '', body)
    body = re.sub(r'\\tabularnewline', '', body)
    # Trim blank lines.
    body = body.strip()

    # Build new column spec (keep existing p{width} if already rewritten).
    if 'p{' in spec:
        new_spec = spec
    else:
        cols = parse_col_spec(spec)
        new_spec = build_p_spec(cols) if cols else spec

    cap_label = ''
    if caption:
        cap_label += f'\\caption{{{caption}}}'
    if label:
        cap_label += f'\\label{{{label}}}'
    if cap_label:
        cap_label += '\n'

    # Ensure header row ends with a line break without duplicating it.
    header = header.rstrip()
    if not header.endswith('\\\\'):
        header += ' \\\\'
    header_line = header + '\n'

    table = (
        f'\\begin{{table*}}\n'
        f'\\centering\n'
        f'{cap_label}'
        f'\\begin{{tabular}}{{{new_spec}}}\n'
        f'\\toprule\n'
        f'{header_line}'
        f'\\midrule\n'
        f'{body}\n'
        f'\\bottomrule\n'
        f'\\end{{tabular}}\n'
        f'\\end{{table*}}'
    )
    return table


def main():
    args = sys.argv[1:]
    fse_mode = False
    if '--fse' in args:
        fse_mode = True
        args.remove('--fse')

    if len(args) != 1:
        print(f'Usage: {sys.argv[0]} [--fse] <file.tex>', file=sys.stderr)
        sys.exit(1)

    path = args[0]
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = re.compile(
        r'\\begin\{longtable\}(\[.*?\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}(.*?)\\end\{longtable\}',
        re.DOTALL
    )

    if fse_mode:
        new_text = pattern.sub(rewrite_longtable_fse, text)
    else:
        new_text = pattern.sub(rewrite_longtable, text)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_text)

    count = len(pattern.findall(text))
    print(f'Fixed {count} longtable(s) in {path} (fse={fse_mode})')


if __name__ == '__main__':
    main()
