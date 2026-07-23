import argparse
import json
import sys

from .core import PackError, build_pack, verify_pack


def main() -> int:
    parser = argparse.ArgumentParser(prog="repair-event-pack")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build a local repair-event pack")
    build.add_argument("records")
    build.add_argument("--out", required=True)
    build.add_argument("--metadata", help="JSON metadata file")
    verify = sub.add_parser("verify", help="verify a generated pack")
    verify.add_argument("pack")
    args = parser.parse_args()
    try:
        if args.command == "build":
            metadata = json.loads(open(args.metadata, encoding="utf-8").read()) if args.metadata else {}
            record = build_pack(args.records, args.out, metadata)
            print(f"PASS: created {args.out} ({len(record['rows'])} repair records)")
            return 0
        errors = verify_pack(args.pack)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print("PASS: repair event pack verified")
        return 0
    except (PackError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
