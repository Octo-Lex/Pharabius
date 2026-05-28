# Pharabius v2.0 — Local CI Quality Gate

Product thesis: Pharabius v2.0 enters developer workflow through a local, deterministic CI quality gate without becoming infrastructure.

Core boundary:
- No server
- No database requirement
- No dashboard service
- No remote repository crawling
- No external API writes
- No issue creation
- No autonomous remediation
- No production code modification

Primary command target:

```bash
ai-debt gate
```

Primary outputs:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

## GitHub Actions

```yaml
name: Pharabius Quality Gate
on: [pull_request]
jobs:
  pharabius-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pharabius
      - run: |
          ai-debt init
          ai-debt profile
          ai-debt scan
          ai-debt analyze --no-ai
          ai-debt report
          ai-debt plan
          ai-debt gate --max-critical 0 --fail-on-blocking-gaps
```

## GitLab CI

```yaml
pharabius_gate:
  image: python:3.11
  script:
    - pip install pharabius
    - ai-debt init
    - ai-debt profile
    - ai-debt scan
    - ai-debt analyze --no-ai
    - ai-debt report
    - ai-debt plan
    - ai-debt gate --max-critical 0 --fail-on-blocking-gaps
  artifacts:
    when: always
    paths:
      - .ai-debt/reports/quality-gate.md
      - .ai-debt/reports/quality-gate.json
```

## Azure Pipelines

```yaml
pool:
  vmImage: ubuntu-latest
steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.11"
  - script: |
      pip install pharabius
      ai-debt init
      ai-debt profile
      ai-debt scan
      ai-debt analyze --no-ai
      ai-debt report
      ai-debt plan
      ai-debt gate --max-critical 0 --fail-on-blocking-gaps
    displayName: Run Pharabius quality gate
  - publish: .ai-debt/reports
    artifact: pharabius-reports
    condition: always()
```

## Jenkins

```groovy
pipeline {
  agent any
  stages {
    stage('Pharabius Gate') {
      steps {
        sh 'python -m pip install pharabius && ai-debt init && ai-debt profile && ai-debt scan && ai-debt analyze --no-ai && ai-debt report && ai-debt plan && ai-debt gate --max-critical 0 --fail-on-blocking-gaps'
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: '.ai-debt/reports/quality-gate.*', allowEmptyArchive: true
    }
  }
}
```

## Portable shell

```bash
#!/usr/bin/env bash
set -euo pipefail
ai-debt init
ai-debt profile
ai-debt scan
ai-debt analyze --no-ai
ai-debt report
ai-debt plan
ai-debt gate --max-critical 0 --fail-on-blocking-gaps
```

## Acceptance criteria

- CI examples are copy-pasteable.
- Examples do not require credentials.
- Examples archive quality-gate reports where practical.
- Examples do not call tracker APIs.
- Examples do not create issues or PR comments.
