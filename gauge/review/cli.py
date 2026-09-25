"""Command-line tools for searching companies and resolving review items.

    python -m gauge.review.cli search RECORDS.json "acme" [--town Hoboken]
    python -m gauge.review.cli link RECORDS.json
    python -m gauge.review.cli dedupe RECORDS.json
    python -m gauge.review.cli list [--status open]
    python -m gauge.review.cli show ITEM_ID
    python -m gauge.review.cli approve ITEM_ID --by "Your Name" [--note "..."]
    python -m gauge.review.cli reject ITEM_ID --by "Your Name"
    python -m gauge.review.cli uncertain ITEM_ID --by "Your Name"

The queue lives in ``--store`` (default ``data/local/review.json``).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from gauge.core.serialize import load_records
from gauge.review.dedupe import find_duplicate_companies, merge_approved_duplicates
from gauge.review.linking import link_records
from gauge.review.models import Action, ActorType, ReviewItem, ReviewStatus
from gauge.review.search import describe, search_companies
from gauge.review.store import JsonReviewStore, UnknownReviewItem

DEFAULT_STORE = "data/local/review.json"
_ACTIONS = {
    "approve": Action.APPROVE_MERGE,
    "reject": Action.REJECT_MERGE,
    "uncertain": Action.LEAVE_UNCERTAIN,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gauge.review.cli", description=__doc__.split("\n")[0])
    parser.add_argument("--store", default=DEFAULT_STORE, help="review queue JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="search linked companies")
    s.add_argument("records")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--town")
    s.add_argument("--limit", type=int, default=25)

    for name, text in (
        ("link", "link records, opening review items"),
        ("dedupe", "find duplicate companies"),
    ):
        p = sub.add_parser(name, help=text)
        p.add_argument("records")

    ls = sub.add_parser("list", help="list review items")
    ls.add_argument("--status", choices=[s.value for s in ReviewStatus])

    sh = sub.add_parser("show", help="show one review item and its history")
    sh.add_argument("item_id")

    for name in _ACTIONS:
        d = sub.add_parser(name, help=f"{name} a review item")
        d.add_argument("item_id")
        d.add_argument("--by", required=True, help="who is making this decision")
        d.add_argument("--note", default="")

    args = parser.parse_args(argv)
    store = JsonReviewStore(args.store)

    if args.command in ("search", "link", "dedupe"):
        linking = link_records(load_records(args.records), store)
        profiles = merge_approved_duplicates(linking.profiles, store)
        if args.command == "search":
            for hit in search_companies(
                profiles.values(), args.query, town=args.town, limit=args.limit
            ):
                print(f"[{hit.score:.2f} {hit.matched_on}]")
                print("\n".join(describe(hit.profile)))
            return 0
        if args.command == "link":
            pending = [i for i in store.items() if i.status is ReviewStatus.OPEN]
            print(
                f"{len(linking.links)} records -> {len(profiles)} companies; "
                f"{len(pending)} open review items"
            )
            return 0
        opened = find_duplicate_companies(profiles.values(), store)
        print(f"{len(opened)} open duplicate-company review items")
        for item in opened:
            _print_item(item)
        return 0

    if args.command == "list":
        status = ReviewStatus(args.status) if args.status else None
        for item in store.items(status):
            _print_item(item)
        return 0

    try:
        if args.command == "show":
            item = store.get(args.item_id)
            _print_item(item, full=True)
            return 0
        item = store.decide(
            args.item_id, _ACTIONS[args.command], args.by, ActorType.HUMAN, args.note
        )
    except UnknownReviewItem:
        print(f"no review item {args.item_id}", file=sys.stderr)
        return 1
    print(f"{item.item_id} is now {item.status.value} (by {args.by})")
    return 0


def _print_item(item: ReviewItem, full: bool = False) -> None:
    print(
        f"{item.item_id}  {item.status.value:<9}  {item.kind.value}  "
        f"{item.subject} -> {item.candidate_company_id}  score={item.score:.2f}"
    )
    if not full:
        return
    for reason in item.reasons:
        print(f"  reason: {reason}")
    for p in item.evidence:
        print(f"  evidence: {p.source_type.value} {p.source_id} {p.source_date} {p.source_url}")
    for d in item.decisions:
        line = f"  {d.at.isoformat()} {d.actor_type.value}:{d.actor} {d.action.value}"
        print(line + (f" ({d.note})" if d.note else ""))
        for key, value in d.details.items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
