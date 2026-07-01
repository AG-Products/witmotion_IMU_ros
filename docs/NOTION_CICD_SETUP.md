# Notion CI/CD Integration (AG-Products)

This repository uses the shared [AG-Products/notion-cicd](https://github.com/AG-Products/notion-cicd) templates.

Workflows sync GitHub Actions activity to the [Engineering Team OS](https://app.notion.com/p/38e19eeabe2c80c69cedf3caea1f7a54) Notion workspace under **AG → Engineering Team OS**.

## Organization secrets (set once)

These are configured at the **AG-Products** organization level and inherited by every repo:

| Secret | Value |
|---|---|
| `NOTION_TOKEN` | Notion integration secret |
| `NOTION_CICD_RUNS_DB_ID` | `38e19eea-be2c-817f-aa54-ff002eaeb15b` |
| `NOTION_PR_DB_ID` | `38e19eea-be2c-810e-a909-f1f3b8d43681` |
| `NOTION_DEPLOYMENTS_DB_ID` | `38e19eea-be2c-8171-a88e-e59229fd05f8` |
| `NOTION_EPIC_PAGE_ID` | `38e19eea-be2c-8194-98c1-c72211795b51` |
| `NOTION_PROJECT_PAGE_ID` | `38e19eea-be2c-8196-841e-c0ad1ec0f674` |

## Notion database access

Share these databases with your Notion integration:

- [CICD_Runs](https://app.notion.com/p/38e19eeabe2c817faa54ff002eaeb15b)
- [Pull_Request_Tracker](https://app.notion.com/p/38e19eeabe2c810ea909f1f3b8d43681)
- [Deployments](https://app.notion.com/p/38e19eeabe2c8171a88ee59229fd05f8)

## Workflows

- **ci.yml** — build (profile-specific) + sync CI run and PRs to Notion
- **deploy.yml** — manual deploy trigger → `Deployments` database

## Local test

```bash
export NOTION_TOKEN="secret_..."
export NOTION_CICD_RUNS_DB_ID="38e19eea-be2c-817f-aa54-ff002eaeb15b"
export GITHUB_REPOSITORY="AG-Products/<repo>"
export GITHUB_REF_NAME="main"
export GITHUB_SHA="abc123"
export GITHUB_RUN_ID="1"
export GITHUB_WORKFLOW="CI"
export GITHUB_ACTOR="you"
export CI_CONCLUSION="success"

python3 .github/scripts/notion_sync.py ci
```

## Maintenance

Do not edit `.github/workflows/ci.yml` or `.github/scripts/*` by hand. Update `AG-Products/notion-cicd` templates and re-run `scripts/rollout.py`.
