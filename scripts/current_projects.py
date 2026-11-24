"""Fetch top 2 recent public repos and render SVG cards."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import re
import textwrap
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _build_request_headers(username: str) -> dict[str, str]:
    """Build safe request headers with optional GitHub token auth."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{username}-readme-updater",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@dataclass(frozen=True)
class RepoCardData:
    """Normalized data required to render a card."""

    name: str
    description: str
    language: str
    pushed_date: str
    stars: int
    html_url: str


class CurrentProjectsGenerator:
    """Fetches recent public repositories and generates matching SVG cards."""

    CARD_WIDTH = 415
    CARD_HEIGHT = 165
    CARD_BG = "#11111b"
    BORDER_COLOR = "#313244"
    TITLE_COLOR = "#cdd6f4"
    MUTED_COLOR = "#a6adc8"
    PURPLE_DARK = "#5b2c6f"
    PURPLE_MAUVE = "#cba6f7"
    ACCENT_WHITE = "#ffffff"

    README_START = "<!-- CURRENT_PROJECTS:START -->"
    README_END = "<!-- CURRENT_PROJECTS:END -->"

    def __init__(
        self,
        username: str,
        font_path: str = "assets/fonts/Grandstander-SemiBold.ttf",
        output_dir: str = "assets/projects",
        readme_path: str = "README.md",
        exclude_repos: set[str] | None = None,
    ) -> None:
        """Initialize API parameters, font encoding, and output path."""
        self.username = username
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.readme_path = Path(readme_path)
        self.exclude_repos = {repo.lower() for repo in (exclude_repos or set())}
        self.exclude_repos.add(username.lower())
        self.font_b64 = self._load_font_base64(Path(font_path))

    @staticmethod
    def _load_font_base64(font_file: Path) -> str:
        """Encode a ttf font file into Base64 for SVG embedding."""
        if not font_file.is_file():
            raise FileNotFoundError(f"Missing font file: {font_file}")
        return base64.b64encode(font_file.read_bytes()).decode("ascii")

    @staticmethod
    def _format_push_date(iso_timestamp: str) -> str:
        """Return a static YYYY-MM-DD date to avoid unnecessary commits."""
        if not iso_timestamp or len(iso_timestamp) < 10:
            return "unknown"
        return iso_timestamp[:10]

    @staticmethod
    def _truncate(text: str, max_chars: int = 28) -> str:
        """Shorten text cleanly with '...' so it fits inside the SVG card."""
        cleaned = " ".join(text.split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _wrap_description(
        text: str, line_width: int = 50, max_lines: int = 3
    ) -> list[str]:
        """Wrap description across up to max_lines and append '...' if needed."""
        cleaned = " ".join(text.split())
        if not cleaned:
            return ["Active public project."]

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
    def _sanitize_repo_url(url: str, fallback: str) -> str:
        """Allow only https://github.com/ URLs for README links."""
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc == "github.com":
            return url
        return fallback

    def fetch_latest_public_repos(self, count: int = 2) -> list[RepoCardData]:
        """Fetch the most recently pushed non-fork public repositories."""
        url = (
            f"https://api.github.com/users/{self.username}/repos"
            "?type=public&sort=pushed&direction=desc&per_page=30"
        )
        request = Request(
            url,
            headers=_build_request_headers(self.username),
        )

        try:
            with urlopen(request, timeout=15) as response:
                raw_items = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to fetch public repos: {exc}") from exc

        selected: list[RepoCardData] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            if not name or name.lower() in self.exclude_repos:
                continue
            if item.get("fork") or item.get("archived"):
                continue

            desc = str(item.get("description") or "Active public project.")
            lang = str(item.get("language") or "Code")
            fallback_url = f"https://github.com/{self.username}/{name}"
            repo_url = self._sanitize_repo_url(
                str(item.get("html_url", "")), fallback_url
            )

            selected.append(
                RepoCardData(
                    name=name,
                    description=desc,
                    language=lang,
                    pushed_date=self._format_push_date(
                        str(item.get("pushed_at", ""))
                    ),
                    stars=int(item.get("stargazers_count", 0)),
                    html_url=repo_url,
                )
            )
            if len(selected) >= count:
                break

        return selected

    def render_card_svg(self, repo: RepoCardData, slot_index: int) -> str:
        """Render a single Catppuccin Mocha SVG card for a repository."""
        safe_name = html.escape(self._truncate(repo.name, max_chars=28))
        desc_lines = self._wrap_description(repo.description)
        safe_lang = html.escape(repo.language)
        safe_date = html.escape(repo.pushed_date)
        slug = re.sub(r"[^a-zA-Z0-9]", "", repo.name.lower())
        uid = f"proj-{slot_index}-{slug}"

        tspans = []
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
    <linearGradient id="top-bar-{uid}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{self.PURPLE_DARK}" />
      <stop offset="65%" stop-color="{self.PURPLE_MAUVE}" />
      <stop offset="100%" stop-color="{self.ACCENT_WHITE}" />
    </linearGradient>
  </defs>

  <rect x="1" y="1" width="{self.CARD_WIDTH - 2}" height="{self.CARD_HEIGHT - 2}" rx="10"
        fill="{self.CARD_BG}" stroke="{self.BORDER_COLOR}" stroke-width="1.5" />

  <rect x="1" y="1" width="{self.CARD_WIDTH - 2}" height="4" rx="2"
        fill="url(#top-bar-{uid})" />

  <text x="20" y="38" class="repo-title">{safe_name}</text>
  <text x="20" y="65" class="repo-meta">
    {tspan_block}
  </text>

  <circle cx="26" cy="138" r="5" fill="{self.PURPLE_MAUVE}" />
  <text x="38" y="142" class="repo-meta">{safe_lang}</text>

  <text x="{self.CARD_WIDTH - 20}" y="142" text-anchor="end" class="repo-meta">
    ★ {repo.stars} · {safe_date}
  </text>
</svg>
"""

    def update_readme_links(self, repos: list[RepoCardData]) -> None:
        """Update direct repository links inside README markers if present."""
        if not self.readme_path.is_file():
            return

        content = self.readme_path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"{re.escape(self.README_START)}.*?{re.escape(self.README_END)}",
            re.DOTALL,
        )
        if not pattern.search(content):
            return

        cards_html = []
        for idx, repo in enumerate(repos, start=1):
            safe_url = html.escape(repo.html_url, quote=True)
            safe_alt = html.escape(repo.name, quote=True)
            img_path = f"{self.output_dir.as_posix()}/current-project-{idx}.svg"
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

    def generate_cards(self, count: int = 2) -> list[Path]:
        """Fetch latest public repos and save SVG cards to output_dir."""
        repos = self.fetch_latest_public_repos(count=count)
        written: list[Path] = []
        for idx, repo in enumerate(repos, start=1):
            out_file = self.output_dir / f"current-project-{idx}.svg"
            out_file.write_text(
                self.render_card_svg(repo, idx), encoding="utf-8"
            )
            written.append(out_file)
        self.update_readme_links(repos)
        return written


if __name__ == "__main__":
    generator = CurrentProjectsGenerator(username="astralamycal")
    saved = generator.generate_cards(count=2)
    for file_path in saved:
        print(f"Generated {file_path}")