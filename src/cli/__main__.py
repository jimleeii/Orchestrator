#!/usr/bin/env python3
"""Top-level dispatcher for the Orchestrator CLI."""

from __future__ import annotations

import argparse
import json

from src import health_monitor


def _normalize_log_command(level: str) -> str:
    level = (level or '').strip()
    if not level.startswith('/'):
        level = '/' + level
    return level


def _format_health_snapshot(snapshot) -> str:
    payload = snapshot.to_dict()
    lines = [
        f"workspace_id: {payload['workspace_id']}",
        f"generated_at: {payload['generated_at']}",
        f"records: {len(payload['records'])}",
    ]
    for record in payload['records']:
        scope = record['scope']
        state = record['state']
        lines.append(
            f"- {scope['agent_id']}: {state['status']} "
            f"(failures={state['failure_count']}, successes={state['success_count']})"
        )
    return "\n".join(lines)


def _format_health_decision(decision) -> str:
    payload = decision.to_dict()
    lines = [
        f"workspace_id: {payload['workspace_id']}",
        f"session_id: {payload['session_id']}",
        f"task_family: {payload['task_family']}",
        f"state: {payload['state']}",
        f"action: {payload['action']}",
        f"reason: {payload['reason']}",
        f"selected_candidates: {', '.join(payload['selected_candidates']) or '-'}",
        f"suppressed_candidates: {', '.join(payload['suppressed_candidates']) or '-'}",
        f"probe_candidate: {payload['probe_candidate'] or '-'}",
    ]
    if payload.get('model_id'):
        lines.append(f"model_id: {payload['model_id']}")
    if payload.get('failure_kind'):
        lines.append(f"failure_kind: {payload['failure_kind']}")
    if payload.get('failure_message'):
        lines.append(f"failure_message: {payload['failure_message']}")
    return "\n".join(lines)


def _print_json(payload) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _run_health_snapshot(args):
    registry = health_monitor.get_workspace_health_registry(args.workspace_id)
    snapshot = registry.snapshot()

    if args.json:
        _print_json(snapshot.to_dict())
    else:
        print(_format_health_snapshot(snapshot))

    return 0


def _run_health_route(args):
    scope = health_monitor.build_health_scope(
        {
            "workspace_id": args.workspace_id,
            "session_id": args.session_id,
            "task_family": args.task_family,
            "model_id": args.model_id,
        },
        args.candidates[0],
        dispatch_type=args.task_family,
        workspace_id=args.workspace_id,
    )
    registry = health_monitor.get_workspace_health_registry(scope.workspace_id)
    decision = registry.route_candidates(
        args.candidates,
        session_id=scope.session_id,
        task_family=scope.task_family,
        model_id=scope.model_id,
    )

    if args.json:
        _print_json(decision.to_dict())
    else:
        print(_format_health_decision(decision))

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("request", help="Route to scripts.handle_request:main")
    subparsers.add_parser("package", help="Route to package_orchestrator:main")
    models_parser = subparsers.add_parser("models", help="Route to scripts.discover_models:main and scripts.refresh_model_catalog:main")
    models_subparsers = models_parser.add_subparsers(dest="action", required=True)
    models_subparsers.add_parser("discover", help="Route to scripts.discover_models:main")
    models_subparsers.add_parser("refresh", help="Route to scripts.refresh_model_catalog:main")
    validate_parser = subparsers.add_parser("validate", help="Route to validation helper scripts")
    validate_subparsers = validate_parser.add_subparsers(dest="check", required=True)
    validate_subparsers.add_parser("prompts", help="Route to scripts.validate_prompt_mappings:main")
    validate_subparsers.add_parser("api-contract", help="Route to scripts.validate_api_contract:main")
    validate_subparsers.add_parser("parity", help="Route to scripts.check_parity:main")
    wiki_parser = subparsers.add_parser("wiki", help="Route to wiki maintenance and synthesis scripts")
    wiki_subparsers = wiki_parser.add_subparsers(dest="action", required=True)
    wiki_subparsers.add_parser("analyze", help="Route to scripts.analyze_logs:main")
    wiki_subparsers.add_parser("lint", help="Route to scripts.lint_wiki:main")
    wiki_subparsers.add_parser("search", help="Route to scripts.search_wiki:main")
    wiki_subparsers.add_parser("synthesize", help="Route to scripts.synthesize_wiki:main")
    wiki_subparsers.add_parser("normalize-links", help="Route to scripts.normalize_log_links:main")
    health_parser = subparsers.add_parser("health", help="Route to health snapshot and routing helpers")
    health_subparsers = health_parser.add_subparsers(dest="action", required=True)
    health_snapshot_parser = health_subparsers.add_parser("snapshot", help="Print the current workspace health snapshot")
    health_snapshot_parser.add_argument("--workspace-id", help="Workspace id to inspect")
    health_snapshot_parser.add_argument("--json", action="store_true", help="Print JSON output")
    health_route_parser = health_subparsers.add_parser("route", help="Route candidates through the health registry")
    health_route_parser.add_argument("candidates", nargs="+", help="Candidate agent ids")
    health_route_parser.add_argument("--workspace-id", help="Workspace id to inspect")
    health_route_parser.add_argument("--session-id", help="Session id for the routing decision")
    health_route_parser.add_argument("--task-family", help="Task family for the routing decision")
    health_route_parser.add_argument("--model-id", help="Model id for the routing decision")
    health_route_parser.add_argument("--json", action="store_true", help="Print JSON output")
    log_parser = subparsers.add_parser("log", help="Route to scripts.log_prompt:main")
    log_parser.add_argument(
        "level",
        help="Logging level or prompt command name (for example: full-log, info, debug, warning, error, trace, cleanup)",
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    args, remainder = parser.parse_known_args(argv)

    if args.command == "request":
        from scripts.handle_request import main as request_main

        return request_main(remainder)

    if args.command == "package":
        from package_orchestrator import main as package_main

        return package_main(remainder)

    if args.command == "models":
        if args.action == "discover":
            from scripts.discover_models import main as discover_models_main

            return discover_models_main(remainder)
        if args.action == "refresh":
            from scripts.refresh_model_catalog import main as refresh_model_catalog_main

            return refresh_model_catalog_main(remainder)

    if args.command == "validate":
        if args.check == "prompts":
            from scripts.validate_prompt_mappings import main as validate_prompt_mappings_main

            return validate_prompt_mappings_main(remainder)
        if args.check == "api-contract":
            from scripts.validate_api_contract import main as validate_api_contract_main

            return validate_api_contract_main(remainder)
        if args.check == "parity":
            from scripts.check_parity import main as check_parity_main

            return check_parity_main(remainder)

    if args.command == "wiki":
        if args.action == "analyze":
            from scripts.analyze_logs import main as analyze_logs_main

            return analyze_logs_main(remainder)
        if args.action == "lint":
            from scripts.lint_wiki import main as lint_wiki_main

            return lint_wiki_main(remainder)
        if args.action == "search":
            from scripts.search_wiki import main as search_wiki_main

            return search_wiki_main(remainder)
        if args.action == "synthesize":
            from scripts.synthesize_wiki import main as synthesize_wiki_main

            return synthesize_wiki_main(remainder)
        if args.action == "normalize-links":
            from scripts.normalize_log_links import main as normalize_log_links_main

            return normalize_log_links_main(remainder)

    if args.command == "health":
        if args.action == "snapshot":
            return _run_health_snapshot(args)
        if args.action == "route":
            return _run_health_route(args)

    if args.command == "log":
        from scripts.log_prompt import main as log_main

        return log_main([_normalize_log_command(args.level), *remainder])

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()