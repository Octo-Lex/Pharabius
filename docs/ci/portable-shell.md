# Portable Shell

Run Pharabius quality gate in any CI system using a portable shell script.

## Script

```bash
#!/usr/bin/env bash
set -euo pipefail

# Install Pharabius
pip install pharabius

# Initialize workspace if needed
if [ ! -d .ai-debt ]; then
    ai-debt init
fi

# Run full analysis
ai-debt run

# Quality gate — exits 0 on PASS, 1 on FAIL
ai-debt gate \
    --max-critical 0 \
    --max-high 10 \
    --max-total 50

echo "Quality gate passed."
```

## Usage

Save as `ci-debt-check.sh`, make executable, and run in any CI step:

```bash
chmod +x ci-debt-check.sh
./ci-debt-check.sh
```

## Customization

Override thresholds via environment variables:

```bash
#!/usr/bin/env bash
set -euo pipefail

pip install pharabius

[ -d .ai-debt ] || ai-debt init
ai-debt run

ai-debt gate \
    --max-critical "${MAX_CRITICAL:-0}" \
    --max-high "${MAX_HIGH:-10}" \
    --max-total "${MAX_TOTAL:-50}"
```

## Safety Notes

- No tokens or credentials required.
- All analysis is local and deterministic.
- `set -euo pipefail` ensures the script fails fast on errors.
