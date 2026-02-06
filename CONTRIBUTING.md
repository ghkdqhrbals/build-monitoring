# Contributing

## Quick test (recommended)

This repository includes CI workflows to validate the action.

- Smoke test: runs the action end-to-end on each push/PR
- Lint: runs `actionlint` against workflow YAML

You can also run them manually:

1. Go to **Actions** tab
2. Select **Smoke Test** or **Lint**
3. Click **Run workflow**

## Release tags (for Marketplace users)

Recommended:

- Create immutable version tags like `v1.0.0`
- Maintain a moving major tag `v1` that points to the latest `v1.x.y`
