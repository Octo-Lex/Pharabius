# GitLab CI

Run Pharabius quality gate in GitLab CI/CD.

## Minimal Example

```yaml
stages:
  - quality

debt-analysis:
  stage: quality
  image: python:3.11
  script:
    - pip install pharabius
    - if [ ! -d .ai-debt ]; then ai-debt init; fi
    - ai-debt run
    - ai-debt gate --max-critical 0 --max-high 10 --max-total 50
  artifacts:
    when: always
    paths:
      - .ai-debt/
    expire_in: 30 days
```

## Full Pipeline with SARIF Export

```yaml
stages:
  - quality

debt-analysis:
  stage: quality
  image: python:3.11
  script:
    - pip install pharabius
    - if [ ! -d .ai-debt ]; then ai-debt init; fi
    - ai-debt run
    - ai-debt gate --max-critical 0 --max-high 10
    - ai-debt export --format sarif --output-dir sarif-output
  artifacts:
    when: always
    paths:
      - .ai-debt/
      - sarif-output/
    expire_in: 30 days
```

## Safety Notes

- No tokens or credentials required.
- All analysis is local and deterministic.
- Reports are archived as GitLab CI artifacts.
