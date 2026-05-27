# Azure Pipelines

Run Pharabius quality gate in Azure Pipelines.

## Minimal Example

```yaml
trigger:
  - main
  - master

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.11"
    displayName: Set up Python

  - script: pip install pharabius
    displayName: Install Pharabius

  - script: |
      if [ ! -d .ai-debt ]; then ai-debt init; fi
      ai-debt run
    displayName: Run analysis

  - script: ai-debt gate --max-critical 0 --max-high 10 --max-total 50
    displayName: Quality gate

  - task: PublishBuildArtifacts@1
    condition: always()
    inputs:
      pathToPublish: .ai-debt/
      artifactName: pharabius-reports
    displayName: Publish reports
```

## Safety Notes

- No tokens or credentials required.
- All analysis is local and deterministic.
- Reports are published as Azure Pipelines build artifacts.
