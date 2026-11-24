"""Render SVG highlight cards with stack and status metadata."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import html
from pathlib import Path
import re
import textwrap
from urllib.parse import urlparse


@dataclass(frozen=True)
class HighlightCardConfig:
    """Curated metadata used to render a highlight project card."""

    name: str
    description: str
    stack: str
    status: str
    repo_url: str


DEFAULT_HIGHLIGHTS: tuple[HighlightCardConfig, ...] = (
    HighlightCardConfig(
        name="kekommiam",
        description="Meal planner designed with phones in mind.",
        stack="Expo · TypeScript · SQLite",
        status="In Progress",
        repo_url="https://github.com/astralamycal/kekommiam",
    ),
    HighlightCardConfig(
        name="yapa-test",
        description="v1 build for Yet Another Productivity App.",
        stack="Django · PostgreSQL · JavaScript",
        status="v1 · Remake Planned",
        repo_url="https://github.com/astralamycal/yapa-test",
    ),
    HighlightCardConfig(
        name="CHU-Orleans",
        description="Polished enterprise project built for CHU Orléans.",
        stack="Django · PostgreSQL · Javascript",
        status="Completed",
        repo_url=(
            "https://github.com/astralamycal/"
            "done_Projet-Entreprise-CHU-Orleans"
        ),
    ),
)


class HighlightProjectsGenerator:
    """Renders SVG highlight cards using stack and status instead of stars."""

    CARD_WIDTH = 415
    CARD_HEIGHT = 165
    CARD_BG = "#11111b"
    BORDER_COLOR = "#313244"
    TITLE_COLOR = "#cdd6f4"
    MUTED_COLOR = "#a6adc8"
    PURPLE_DARK = "#5b2c6f"
    PURPLE_MAUVE = "#cba6f7"
    ACCENT_WHITE = "#ffffff"

    README_START = "<!-- HIGHLIGHT_PROJECTS:START -->"
    README_END = "<!-- HIGHLIGHT_PROJECTS:END -->"

    def __init__(
        self,
        highlights: tuple[HighlightCardConfig, ...]
        | list[HighlightCardConfig] = DEFAULT_HIGHLIGHTS,
        font_path: str = "assets/fonts/Grandstander-SemiBold.ttf",
        output_dir: str = "assets/highlights",
        readme_path: str = "README.md",
    ) -> None:
        """Initialize highlight items, font encoding, and output paths."""
        self.highlights = list(highlights)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.readme_path = Path(readme_path)
        self.font_b64 = self._load_font_base64(Path(font_path))

    @staticmethod
    def _load_font_base64(font_file: Path) -> str:
        """Encode a TTF font file into Base64 for SVG @font-face."""
        if not font_file.is_file():
            raise FileNotFoundError(f"Missing font file: {font_file}")
        return base64.b64encode(font_file.read_bytes()).decode("ascii")

    @staticmethod
    def _truncate(text: str, max_chars: int = 28) -> str:
        """Trim single-line text cleanly and append '...' when shortened."""
        cleaned = " ".join(text.split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _wrap_description(
        text: str, line_width: int = 50, max_lines: int = 3
    ) -> list[str]:
        """Wrap description across up to max_lines with '...' on overflow."""
        cleaned = " ".join(text.split())
        if not cleaned:
            return ["Highlighted repository."]

        lines = textwrap.wrap(
            cleaned,
            width=line_width,
            break_long_words=True,
            break_on_hyphens=True,
        )
        if len(lines) <= max_lines:
            return lines

        trimmed = lines[:max_lines]
        last_line = trimmed[-1]
        if len(last_line) > line_width - 3:
            last_line = last_line[: line_width - 3].rstrip()
        trimmed[-1] = f"{last_line}..."
        return trimmed

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Allow only HTTPS GitHub repository URLs."""
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc == "github.com":
            return url
        return "https://github.com/astralamycal"

    def render_card_svg(
        self, repo: HighlightCardConfig, slot_index: int
    ) -> str:
        """Render a single highlight SVG card with stack and status."""
        safe_title = html.escape(self._truncate(repo.name, max_chars=28))
        desc_lines = self._wrap_description(repo.description)
        safe_stack = html.escape(self._truncate(repo.stack, max_chars=34))
        safe_status = html.escape(self._truncate(repo.status, max_chars=24))
        slug = re.sub(r"[^a-zA-Z0-9]", "", repo.name.lower())
        grad_id = f"highlight-bar-{slot_index}-{slug}"

        tspans: list[str] = []
        for idx, line in enumerate(desc_lines):
            dy = "0" if idx == 0 else "17"
            tspans.append(
                f'<tspan x="20" dy="{dy}">{html.escape(line)}</tspan>'
            )
        tspan_block = "\n    ".join(tspans)

        return f"""<svg width="{self.CARD_WIDTH}" height="{self.CARD_HEIGHT}" viewBox="0 0 {self.CARD_WIDTH} {self.CARD_HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @font-face {{
        font-family: 'GrandstanderCard';
        src: url('data:font/ttf;base64,{self.font_b64}') format('truetype');
        font-weight: 600;
        font-style: normal;
      }}
      .repo-title {{
        font-family: 'GrandstanderCard', cursive, sans-serif;
        font-size: 20px;
        font-weight: 600;
        fill: {self.TITLE_COLOR};
      }}
      .repo-meta {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        font-size: 13px;
        fill: {self.MUTED_COLOR};
      }}
    </style>
    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{self.PURPLE_DARK}" />
      <stop offset="65%" stop-color="{self.PURPLE_MAUVE}" />
      <stop offset="100%" stop-color="{self.ACCENT_WHITE}" />
    </linearGradient>
  </defs>

  <rect x="1" y="1" width="{self.CARD_WIDTH - 2}" height="{self.CARD_HEIGHT - 2}" rx="10"
        fill="{self.CARD_BG}" stroke="{self.BORDER_COLOR}" stroke-width="1.5" />

  <rect x="1" y="1" width="{self.CARD_WIDTH - 2}" height="4" rx="2"
        fill="url(#{grad_id})" />

  <text x="20" y="38" class="repo-title">{safe_title}</text>
  <text x="20" y="65" class="repo-meta">
    {tspan_block}
  </text>

  <circle cx="26" cy="138" r="5" fill="{self.PURPLE_MAUVE}" />
  <text x="38" y="142" class="repo-meta">{safe_stack}</text>

  <text x="{self.CARD_WIDTH - 20}" y="142" text-anchor="end" class="repo-meta">
    {safe_status}
  </text>
</svg>
"""

    def update_readme_links(self, repos: list[HighlightCardConfig]) -> None:
        """Update highlight card links in README.md if markers are present."""
        if not self.readme_path.is_file():
            return

        content = self.readme_path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"{re.escape(self.README_START)}.*?{re.escape(self.README_END)}",
            re.DOTALL,
        )
        if not pattern.search(content):
            return

        cards_html: list[str] = []
        for idx, repo in enumerate(repos, start=1):
            safe_url = html.escape(self._sanitize_url(repo.repo_url), quote=True)
            safe_alt = html.escape(repo.name, quote=True)
            img_path = f"{self.output_dir.as_posix()}/highlight-{idx}.svg"
            cards_html.append(
                f'  <a href="{safe_url}">\n'
                f'    <img src="{img_path}" alt="{safe_alt}" />\n'
                "  </a>"
            )

        block = (
            f"{self.README_START}\n"
            '<div align="center">\n'
            + "\n".join(cards_html)
            + "\n</div>\n"
            f"{self.README_END}"
        )
        updated = pattern.sub(block, content, count=1)
        self.readme_path.write_text(updated, encoding="utf-8")

    def generate_cards(self) -> list[Path]:
        """Write highlight SVG files and sync README links."""
        written: list[Path] = []
        for idx, repo in enumerate(self.highlights, start=1):
            out_file = self.output_dir / f"highlight-{idx}.svg"
            out_file.write_text(
                self.render_card_svg(repo, idx), encoding="utf-8"
            )
            written.append(out_file)
        self.update_readme_links(self.highlights)
        return written


if __name__ == "__main__":
    generator = HighlightProjectsGenerator()
    for svg_path in generator.generate_cards():
        print(f"Generated {svg_path}")