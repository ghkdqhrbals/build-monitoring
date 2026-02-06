# Build Monitor (GitHub Action)

## Example workflow

- `start`: 빌드/배포 시작 시간을 기록합니다.
- `end`: (권장) `if: ${{ always() }}`로 실패해도 실행되게 하고, `build_time_ms` 등 결과를 outputs로 남깁니다.
- `health_check_url`: 지정하면 헬스체크를 수행합니다.
- `health_wait_seconds`: 0이면 1회만 체크, 0보다 크면 최대 N초 동안 1초 간격으로 재시도합니다.

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