# Build Monitor (GitHub Action)

Composite GitHub Action (implemented in Python) to:

- record build start time
- compute total build time on completion
- optionally health-check a URL
- optionally POST a JSON report to a webhook

## Inputs

- `action` (required): `start` or `end`
- `project_name` (optional, default: `unknown`)
- `webhook_url` (optional): webhook endpoint to receive a JSON report
- `health_check_url` (optional): URL to check on `end`
- `job_status` (optional, recommended): pass `${{ job.status }}` so the action can report success/failure

## Outputs (when `action=end`)

- `build_time`: seconds
- `build_status`: `success|failure|cancelled|unknown`
- `health_status`: `ok|fail|skipped`
- `health_http_status`: HTTP status code (string)
- `health_latency_ms`: latency in ms (string)

## Example workflow

```yaml
name: CI
on:
  push:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start monitoring
        uses: ./. 
        with:
          action: start
          project_name: my-service

      - name: Build
        run: |
          echo "do build..."
          sleep 2

      - name: End monitoring (always)
        id: monitor_end
        if: ${{ always() }}
        uses: ./. 
        with:
          action: end
          project_name: my-service
          job_status: ${{ job.status }}
          # webhook_url: ${{ secrets.BUILD_MONITOR_WEBHOOK }}
          # health_check_url: https://example.com/health

      - name: Show outputs
        if: ${{ always() }}
        run: |
          echo "build_time=${{ steps.monitor_end.outputs.build_time }}"
          echo "build_status=${{ steps.monitor_end.outputs.build_status }}"
          echo "health_status=${{ steps.monitor_end.outputs.health_status }}"
```

Note: when using `end`, call the step with `if: ${{ always() }}` so it runs even on failures.

## Using from another repo

```yaml
- uses: ghkdqhrbals/build-monitoring@v1
  with:
    action: start
    project_name: my-service
```

## Marketplace publish checklist

1. Push this repo to GitHub as a **public** repository.
2. Ensure the action metadata file is at repo root: `action.yml`.
3. Add a release tag, e.g.:
   - `v1.0.0` (immutable)
   - and optionally a moving major tag `v1` (recommended for users)
4. Create a GitHub Release for the tag.
5. In the GitHub UI: **Settings → Actions → General** (optional hardening).
6. Marketplace listing typically appears once the repo is public and contains a valid `action.yml` + README.

### Recommended tagging

- Tag a specific version: `v1.0.0`
- Also create/update a major tag: `v1` pointing to the latest compatible `v1.x.y`
