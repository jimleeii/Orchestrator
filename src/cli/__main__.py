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
    # dispatch: execute a dispatch path using the runtime
    dispatch_parser = subparsers.add_parser("dispatch", help="Execute a dispatch path using the orchestrator runtime")
    dispatch_parser.add_argument("--dispatch-type", "-d", default="single-agent",
                                 choices=["direct", "single-agent", "multi-agent", "concurrent"],
                                 help="Dispatch path to execute")
    dispatch_parser.add_argument("--prompt", "-p", default="", help="Prompt to dispatch")
    dispatch_parser.add_argument("--user", "-u", default="runtime-user", help="User name")
    dispatch_parser.add_argument("--subagents", nargs="*", help="List of subagent ids/names")
    dispatch_parser.add_argument("--max-orchestration-cycles", type=int, help="Override max orchestration cycles")
    dispatch_parser.add_argument("--metadata", help="Structured JSON metadata to pass into the dispatch")
    dispatch_parser.add_argument("--json", action="store_true", help="Print full JSON output")

    # prepare-dispatch: prepare a dispatch payload (persistence + context) and print JSON
    prep_parser = subparsers.add_parser("prepare-dispatch", help="Prepare a dispatch payload (persistence + context) and print JSON")
    prep_parser.add_argument("--prompt", "-p", default="", help="Prompt to persist")
    prep_parser.add_argument("--user", "-u", default="runtime-user", help="User name")
    prep_parser.add_argument("--dispatch", "-d", default="single-agent",
                             choices=["direct", "single-agent", "multi-agent", "concurrent"],
                             help="Dispatch path to prepare for")
    prep_parser.add_argument("--subagent", help="Subagent name to prepare payload for")
    prep_parser.add_argument("--spawn-payload", help="JSON spawn payload to include in preparation")
    prep_parser.add_argument("--metadata", help="Structured JSON metadata to carry into the persistence step")

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

    if args.command == "dispatch":
        # Execute a dispatch path using the orchestrator runtime
        try:
            from src.orchestrator_runtime import execute_dispatch_by_type
        except Exception:
            from orchestrator_runtime import execute_dispatch_by_type  # type: ignore

        # parse metadata if supplied
        metadata = None
        if getattr(args, "metadata", None):
            try:
                metadata = json.loads(args.metadata)
            except Exception as exc:
                parser = _build_parser()
                parser.error(f"--metadata must be valid JSON: {exc}")

        result = execute_dispatch_by_type(
            dispatch_type=args.dispatch_type,
            prompt=args.prompt,
            metadata=metadata,
            subagents=args.subagents,
            max_orchestration_cycles=args.max_orchestration_cycles,
        )

        if args.json:
            _print_json(result)
        else:
            # Print a compact one-line summary
            print(json.dumps({
                "dispatch": result.get("dispatch"),
                "cycle_id": result.get("cycle_id"),
                "status": result.get("status"),
                "subagents": result.get("subagents"),
            }, ensure_ascii=False))

        return 0

    if args.command == "prepare-dispatch":
        try:
            from src.orchestrator_runtime import prepare_dispatch_payload
        except Exception:
            from orchestrator_runtime import prepare_dispatch_payload  # type: ignore

        metadata = None
        spawn_payload = None
        if getattr(args, "metadata", None):
            try:
                metadata = json.loads(args.metadata)
            except Exception as exc:
                parser = _build_parser()
                parser.error(f"--metadata must be valid JSON: {exc}")
        if getattr(args, "spawn_payload", None):
            try:
                spawn_payload = json.loads(args.spawn_payload)
            except Exception as exc:
                parser = _build_parser()
                parser.error(f"--spawn-payload must be valid JSON: {exc}")

        payload = prepare_dispatch_payload(
            prompt=args.prompt,
            user=args.user,
            dispatch=args.dispatch,
            subagent_name=args.subagent,
            spawn_payload=spawn_payload,
            metadata=metadata,
        )
        _print_json(payload)
        return 0

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