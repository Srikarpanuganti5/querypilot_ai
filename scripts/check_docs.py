"""Validate local Markdown link targets, fragments and fences without network access."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def content(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def anchors(path: Path) -> set[str]:
    found, counts = set(), {}
    fenced = False
    for line in content(path).splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if fenced or not re.match(r"^#{1,6} ", line):
            continue
        heading = re.sub(r"^#{1,6} +", "", line).strip().lower()
        slug = re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")
        ordinal = counts.get(slug, 0)
        counts[slug] = ordinal + 1
        found.add(f"{slug}-{ordinal}" if ordinal else slug)
    return found


def check() -> list[str]:
    failures = []
    documents = sorted([*ROOT.glob("*.md"), *ROOT.joinpath("docs").glob("*.md")])
    for path in documents:
        text = content(path)
        if sum(line.startswith("```") for line in text.splitlines()) % 2:
            failures.append(f"{path.relative_to(ROOT)}: unbalanced code fences")
        # Ignore fenced examples; links in code blocks are not Markdown navigation.
        text = re.sub(r"^```[^\n]*\n.*?^```[^\n]*$", "", text, flags=re.M | re.S)
        for link in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", text):
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.exists():
                failures.append(f"{path.relative_to(ROOT)}: missing target {link}")
            elif url.fragment and target.suffix == ".md":
                if unquote(url.fragment) not in anchors(target):
                    failures.append(f"{path.relative_to(ROOT)}: missing anchor {link}")
    print(f"Checked {len(documents)} Markdown files (local links, anchors and fences).")
    return failures


if __name__ == "__main__":
    errors = check()
    for error in errors:
        print(error)
    raise SystemExit(bool(errors))
