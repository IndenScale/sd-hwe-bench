#!/usr/bin/env python3
"""Extract a filesystem-safe slug from a sections directory's meta.yaml.

Usage: slug-from-meta.py <sections_dir>
Output: the slug printed to stdout.
"""
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required", file=sys.stderr)
    sys.exit(1)


def slugify(text: str) -> str:
    """Create a filesystem-safe slug from a paper title.

    - Keeps CJK han characters, Latin letters, digits, and spaces.
    - Replaces everything else with a hyphen.
    - Collapses multiple hyphens and trims leading/trailing hyphens.
    - Lowercases ASCII letters (CJK is unaffected).
    """
    text = text.strip()
    if text.startswith('#'):
        text = text.lstrip('#').strip()

    text = re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z\s]+', '-', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text.lower()


def main() -> None:
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <sections_dir>', file=sys.stderr)
        sys.exit(1)

    sections_dir = sys.argv[1]
    meta_path = os.path.join(sections_dir, 'meta.yaml')
    if not os.path.isfile(meta_path):
        print(f'ERROR: missing {meta_path}', file=sys.stderr)
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = yaml.safe_load(f)

    title = meta.get('title', '') if isinstance(meta, dict) else ''
    if not title:
        print('ERROR: empty title in meta.yaml', file=sys.stderr)
        sys.exit(1)

    print(slugify(title))


if __name__ == '__main__':
    main()
