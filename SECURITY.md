# Security Notes

## Generated code is untrusted

LegacyPartBench asks models to generate Python/CadQuery code. This code must be treated as untrusted.

Do not execute model-generated code directly inside the main benchmark process after the Docker sandbox exists.

## Sandbox requirements

The execution sandbox should:

```text
run inside Docker
disable network access
use an execution timeout
mount only the generated code and output directory
limit CPU/memory if practical
capture stdout/stderr
always write execution_log.json
```

Suggested Docker flags:

```bash
python -m legacy_part_bench.sandbox.sandbox_runner --build-image \
  --code-file data/results/example/extracted_code.py \
  --output-dir data/results/example
```

Use an outer Python timeout as well.

The Docker runner mounts the generated code as a read-only file at
`/work/input.py` and mounts only the run output directory at `/work/output`.
It passes `--network none`, `--cpus 1`, and `--memory 2g` by default. The local
executor is still available for development, but model-generated code should use
the Docker runner once Docker is available. The sandbox also defaults to
`--platform linux/amd64` so CadQuery binary dependencies resolve reliably on
Apple Silicon Docker hosts.

## Do not expose secrets

The sandbox must not receive:

```text
OPENROUTER_API_KEY
.env files
SSH keys
cloud credentials
personal files
repo root unless necessary
```

Only mount the generated code file and output directory.

## Failure handling

The sandbox should fail closed.

If anything unexpected happens:

```text
success: false
error: clear error message
generated files: absent
scorecard: valid but low/zero
```

## Network access

Generated CAD code should never need network access.

Use:

```text
--network none
```

for Docker execution.

## Long-running code

Model-generated code may include infinite loops or expensive operations.

Use:

```text
timeout
CPU limits
memory limits
```

## File writes

Generated code should only be allowed to write inside the mounted output directory.

Do not allow writes to the repo root, home directory, or system directories.

## Manual review

For public demos, avoid displaying arbitrary raw model output as executable UI content. Show code as text only.
