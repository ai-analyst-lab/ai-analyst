"""Connected context commands; catalog/validate/plan never query the database."""
import argparse
import json

from .authoring import scaffold, review, migration_preview
from .store import Store, read_yaml
from .service import plan_request, execute_plan, validate_store


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", default=".")
    p.add_argument("--dataset", required=True)
    p.add_argument("--store", help="Explicit store for authoring/tests; otherwise resolve project config")
    sub = p.add_subparsers(dest="command", required=True)
    for cmd in ("catalog", "validate", "migration-preview"):
        sub.add_parser(cmd)
    load = sub.add_parser("load")
    load.add_argument("kind"); load.add_argument("id")
    load.add_argument("--hash", required=True); load.add_argument("--analysis-id", required=True)
    load.add_argument("--reason", required=True)
    create = sub.add_parser("scaffold")
    create.add_argument("kind"); create.add_argument("id"); create.add_argument("--template")
    approve = sub.add_parser("review")
    approve.add_argument("kind"); approve.add_argument("id")
    for name in ("reviewer", "approval-note", "reviewed-on", "review-after"):
        approve.add_argument("--"+name, required=True)
    for command in ("plan", "run"):
        c = sub.add_parser(command)
        c.add_argument("request", help="YAML/JSON structured metric/query request")
        c.add_argument("--analysis-id", required=command == "run")
    present = sub.add_parser("present", help="Execute a presentation-only wrapper around a saved maintained execution")
    present.add_argument("execution", help="Parent context-run directory returned by run")
    present.add_argument("presentation", help="YAML/JSON columns and optional order_by")
    present.add_argument("--analysis-id", required=True)
    args = p.parse_args()
    store = Store(args.store, args.dataset) if args.store else Store.from_project(args.project, args.dataset)
    if args.command == "catalog":
        result = store.catalog()
    elif args.command == "validate":
        result = validate_store(store)
    elif args.command == "migration-preview":
        result = migration_preview(store)
    elif args.command == "load":
        result = store.load(args.kind, args.id, args.hash, project=args.project, analysis_id=args.analysis_id, reason=args.reason)
    elif args.command == "scaffold":
        result = scaffold(store.root, args.dataset, args.kind, args.id, template=args.template)
    elif args.command == "review":
        result = review(store.root, args.dataset, args.kind, args.id, reviewer=args.reviewer,
                        approval_note=args.approval_note, reviewed_on=args.reviewed_on, review_after=args.review_after)
    else:
        from helpers.data.connection_manager import ConnectionManager
        conn = ConnectionManager(dataset_id=args.dataset)
        if args.command == "present":
            from .presentation import present_execution
            try:
                result = present_execution(store, args.execution, read_yaml(args.presentation), conn, project=args.project, analysis_id=args.analysis_id)
                result.pop("frame")
            finally:
                conn.close()
        elif args.command == "plan":
            plan = plan_request(store, read_yaml(args.request), conn)
            result = plan
        else:
            try:
                plan = plan_request(store, read_yaml(args.request), conn)
                result = execute_plan(store, plan, conn, project=args.project, analysis_id=args.analysis_id)
                result.pop("frame")
            finally:
                conn.close()
    print(json.dumps(result, indent=2, default=str))
    return 1 if args.command == "validate" and result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
