#!/usr/bin/env python3
"""Sync GitHub CI/CD activity to Engineering Team OS Notion databases."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

NOTION_VERSION = "2022-06-28"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def notion_request(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://api.notion.com/v1{path}"
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"Notion API {method} {path} failed ({exc.code}): {detail}") from exc


def rich_text(value: str) -> dict[str, Any]:
    return {"rich_text": [{"text": {"content": value[:2000]}}]}


def title(value: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": value[:2000]}}]}


def relation(page_ids: list[str]) -> dict[str, Any]:
    return {"relation": [{"id": page_id} for page_id in page_ids if page_id]}


def query_by_text_property(
    token: str,
    database_id: str,
    property_name: str,
    value: str,
) -> str | None:
    result = notion_request(
        "POST",
        f"/databases/{database_id}/query",
        token,
        {
            "filter": {
                "property": property_name,
                "rich_text": {"equals": value},
            },
            "page_size": 1,
        },
    )
    pages = result.get("results", [])
    return pages[0]["id"] if pages else None


def upsert_page(
    token: str,
    database_id: str,
    properties: dict[str, Any],
    lookup_property: str,
    lookup_value: str,
) -> str:
    page_id = query_by_text_property(token, database_id, lookup_property, lookup_value)
    if page_id:
        notion_request("PATCH", f"/pages/{page_id}", token, {"properties": properties})
        return page_id

    created = notion_request(
        "POST",
        "/pages",
        token,
        {"parent": {"database_id": database_id}, "properties": properties},
    )
    return created["id"]


def github_run_url() -> str:
    server = env("GITHUB_SERVER_URL", "https://github.com")
    repo = env("GITHUB_REPOSITORY")
    run_id = env("GITHUB_RUN_ID")
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return env("GITHUB_RUN_URL")


def map_ci_status(conclusion: str) -> str:
    mapping = {
        "success": "Success",
        "failure": "Failed",
        "cancelled": "Cancelled",
        "skipped": "Skipped",
        "neutral": "Neutral",
        "pending": "Pending",
        "in_progress": "In progress",
    }
    return mapping.get(conclusion, conclusion.capitalize() or "In progress")


def sync_ci(token: str) -> str:
    database_id = env("NOTION_CICD_RUNS_DB_ID")
    if not database_id:
        raise RuntimeError("NOTION_CICD_RUNS_DB_ID is required")

    repository = env("GITHUB_REPOSITORY")
    branch = env("GITHUB_REF_NAME", env("GITHUB_HEAD_REF", "main"))
    commit_sha = env("GITHUB_SHA")
    workflow = env("GITHUB_WORKFLOW", "CI")
    actor = env("GITHUB_ACTOR", "github-actions")
    conclusion = env("CI_CONCLUSION", env("GITHUB_JOB_STATUS", "in_progress"))
    run_url = github_run_url()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_name = env("CI_RUN_NAME", f"{workflow} — {branch}")

    properties = {
        "Run Name": title(run_name),
        "Status": rich_text(map_ci_status(conclusion)),
        "Repository": rich_text(f"https://github.com/{repository}"),
        "Branch": rich_text(branch),
        "Commit SHA": rich_text(commit_sha[:12] if commit_sha else ""),
        "Workflow": rich_text(workflow),
        "Job Type": rich_text(env("JOB_TYPE", "CI")),
        "Environment": rich_text(env("DEPLOY_ENVIRONMENT", "staging")),
        "GitHub Run URL": rich_text(run_url),
        "Triggered By": rich_text(actor),
        "Started At": rich_text(env("CI_STARTED_AT", now)),
        "Finished At": rich_text(env("CI_FINISHED_AT", now if conclusion else "")),
        "Notes": rich_text(env("CI_NOTES", "Synced from AG-Products GitHub Actions")),
    }

    return upsert_page(token, database_id, properties, "GitHub Run URL", run_url)


def sync_pr(token: str) -> str:
    database_id = env("NOTION_PR_DB_ID")
    if not database_id:
        raise RuntimeError("NOTION_PR_DB_ID is required")

    action = env("GITHUB_EVENT_NAME", "pull_request")
    pr_number = env("PR_NUMBER", env("GITHUB_REF_NAME", "").replace("refs/pull/", "").split("/")[0])
    pr_title = env("PR_TITLE", f"PR #{pr_number}")
    pr_url = env("PR_URL")
    if not pr_url and pr_number:
        repo = env("GITHUB_REPOSITORY")
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"

    status = env("PR_STATUS")
    if not status:
        gh_action = env("GITHUB_EVENT_ACTION", "opened")
        status_map = {
            "opened": "Open",
            "reopened": "Open",
            "ready_for_review": "Open",
            "converted_to_draft": "Draft",
            "closed": "Merged" if env("PR_MERGED", "false") == "true" else "Closed",
        }
        status = status_map.get(gh_action, "Open")

    properties = {
        "PR Title": title(pr_title),
        "Status": rich_text(status),
        "Repository": rich_text(env("GITHUB_REPOSITORY")),
        "Author": rich_text(env("PR_AUTHOR", env("GITHUB_ACTOR"))),
        "Branch": rich_text(env("PR_HEAD_BRANCH", env("GITHUB_HEAD_REF"))),
        "Target Branch": rich_text(env("PR_BASE_BRANCH", "main")),
        "PR URL": rich_text(pr_url),
        "CI Status": rich_text(env("PR_CI_STATUS", map_ci_status(env("CI_CONCLUSION", "pending")))),
        "Review Priority": rich_text(env("PR_REVIEW_PRIORITY", "Medium")),
        "Created Date": rich_text(env("PR_CREATED_AT", datetime.now(timezone.utc).strftime("%Y-%m-%d"))),
        "Merged Date": rich_text(env("PR_MERGED_AT", "")),
        "Notes": rich_text(env("PR_NOTES", f"Synced via GitHub {action}")),
    }

    epic_id = env("NOTION_EPIC_PAGE_ID")
    if epic_id:
        properties["Epics"] = relation([epic_id])

    lookup = pr_url or pr_title
    return upsert_page(token, database_id, properties, "PR URL", lookup)


def sync_deploy(token: str) -> str:
    database_id = env("NOTION_DEPLOYMENTS_DB_ID")
    if not database_id:
        raise RuntimeError("NOTION_DEPLOYMENTS_DB_ID is required")

    repository = env("GITHUB_REPOSITORY")
    environment = env("DEPLOY_ENVIRONMENT", "staging")
    version = env("DEPLOY_VERSION", env("GITHUB_REF_NAME", "latest"))
    deployment_name = env(
        "DEPLOYMENT_NAME",
        f"{repository.split('/')[-1]} — {environment} — {version}",
    )
    run_url = github_run_url()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    properties = {
        "Deployment Name": title(deployment_name),
        "Status": rich_text(env("DEPLOY_STATUS", "Completed")),
        "Environment": rich_text(environment),
        "Version / Tag": rich_text(version),
        "Commit SHA": rich_text(env("GITHUB_SHA", "")[:12]),
        "Branch": rich_text(env("GITHUB_REF_NAME", "main")),
        "Triggered By": rich_text(env("GITHUB_ACTOR", "github-actions")),
        "Deployment Date": rich_text(env("DEPLOY_DATE", now)),
        "CI Run URL": rich_text(run_url),
        "Release Notes": rich_text(env("DEPLOY_RELEASE_NOTES", "")),
        "Rollback Plan": rich_text(env("DEPLOY_ROLLBACK_PLAN", "Revert to previous tag")),
        "Post-Deployment Notes": rich_text(env("DEPLOY_POST_NOTES", "")),
    }

    repo_page_id = env("NOTION_REPO_PAGE_ID")
    if repo_page_id:
        properties["Repository / Service"] = relation([repo_page_id])

    project_id = env("NOTION_PROJECT_PAGE_ID")
    if project_id:
        properties["Projects"] = relation([project_id])

    cicd_run_id = env("NOTION_CICD_RUN_PAGE_ID")
    if cicd_run_id:
        properties["CICD_Runs"] = relation([cicd_run_id])

    return upsert_page(
        token,
        database_id,
        properties,
        "Deployment Name",
        deployment_name,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync GitHub events to Notion Team OS")
    parser.add_argument(
        "mode",
        choices=["ci", "pr", "deploy"],
        help="Which Engineering Team OS database to update",
    )
    args = parser.parse_args()

    token = env("NOTION_TOKEN")
    if not token:
        print("NOTION_TOKEN is required", file=sys.stderr)
        return 1

    try:
        if args.mode == "ci":
            page_id = sync_ci(token)
        elif args.mode == "pr":
            page_id = sync_pr(token)
        else:
            page_id = sync_deploy(token)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Notion page: {page_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
