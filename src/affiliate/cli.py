"""CLI dispatch: `python -m affiliate.cli <command>`."""
from __future__ import annotations

import sys

from . import check, orchestrator, site_builder
from .config import Config


def _usage() -> int:
    print(
        "usage: python -m affiliate.cli <command>\n"
        "  run    - generate new articles and rebuild the site\n"
        "  build  - rebuild the static site from existing posts only\n"
        "  check  - validate environment configuration\n"
        "  ping   - notify search engines of the sitemap\n"
    )
    return 2


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return _usage()
    cmd = argv[1]
    if cmd == "run":
        return orchestrator.main()
    if cmd == "build":
        cfg = Config.from_env()
        site_builder.build(cfg)
        print("[cli] site built")
        return 0
    if cmd == "check":
        return check.main()
    if cmd == "ping":
        cfg = Config.from_env()
        site_builder.ping_sitemap(cfg)
        return 0
    return _usage()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
