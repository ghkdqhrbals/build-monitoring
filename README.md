# Build Monitor (GitHub Action)

This is a simple workflow for someone who need **build time calculation** and **readinessProbe status**.

- `start`: saves the start time.
- `end`: calculates duration and writes outputs (e.g. `build_time_ms`).
- `health_check_url`: optional health check URL.
- `health_wait_seconds`: `0` = check once, `>0` = retry every 1s for up to N seconds.

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

      - name: server deploy monitoring start
        uses: ghkdqhrbals/build-monitoring@v1.0.3
        with:
          action: start
          project_name: guestbook

      - name: Building And Deploy Step
        run: ...

      - name: server deploy monitoring end
        uses: ghkdqhrbals/build-monitoring@v1.0.3
        id: deploy-stats
        if: ${{ always() }}
        with:
          action: end
          project_name: guestbook
          job_status: ${{ job.status }}
          health_check_url: https://lowfidev.cloud/health
          health_wait_seconds: 60

      - name: Show outputs
        if: ${{ always() }}
        run: |
          echo "build_time_ms=${{ steps.deploy-stats.outputs.build_time_ms }}"
          echo "build_time=${{ steps.deploy-stats.outputs.build_time }}"
          echo "build_status=${{ steps.deploy-stats.outputs.build_status }}"
          echo "health_status=${{ steps.deploy-stats.outputs.health_status }}"
          echo "health_http_status=${{ steps.deploy-stats.outputs.health_http_status }}"
          echo "health_latency_ms=${{ steps.deploy-stats.outputs.health_latency_ms }}"
```