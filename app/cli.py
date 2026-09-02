"""Dev CLI — talk to the agent without LINE. 90% of development happens here.

Interactive:  docker compose run --rm app python -m app.cli
Scripted:     docker compose run -T --rm app python -m app.cli --once "ข้อความ" [--img /srv/eval/receipts/01_7eleven.png]
Images: /img <path> [ข้อความแนบ]  (paths inside the container, e.g. /srv/eval/receipts/...)
"""
import argparse
import asyncio
import shutil
import sys
import uuid
from pathlib import Path

from app.agent import run_turn
from app.db import init_db

UPLOADS = Path("/data/uploads")


def stage_image(src: str) -> str:
    p = Path(src)
    if not p.exists():
        sys.exit(f"no such image: {src}")
    dest = UPLOADS / f"cli-{uuid.uuid4().hex[:8]}{p.suffix}"
    UPLOADS.mkdir(parents=True, exist_ok=True)
    shutil.copy(p, dest)
    return str(dest)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="cli:default")
    ap.add_argument("--once", help="single message then exit (for scripted tests)")
    ap.add_argument("--img", help="image path to attach")
    args = ap.parse_args()
    init_db()

    if args.once is not None or args.img:
        img = stage_image(args.img) if args.img else None
        print(await run_turn(args.user, text=args.once, image_path=img))
        return

    print("PBook CLI — พิมพ์คุยได้เลย | /img <path> [ข้อความ] | Ctrl-C ออก")
    while True:
        try:
            line = input("คุณ> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        img = None
        if line.startswith("/img"):
            _, rest = line.split(" ", 1)
            parts = rest.split(" ", 1)
            img = stage_image(parts[0])
            line = parts[1] if len(parts) > 1 else None
        print("บอท>", await run_turn(args.user, text=line, image_path=img))


if __name__ == "__main__":
    asyncio.run(main())
