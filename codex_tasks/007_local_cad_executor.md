# Codex Task 007 — Local CadQuery Executor

Implement local execution of generated CadQuery code.

## Requirements

- Input: Python code file
- Expects variable named `result`
- Exports `generated.step`
- Exports `generated.stl`
- Writes `execution_log.json`
- Handles syntax errors and missing `result`

## Acceptance criteria

Valid code succeeds. Broken code fails cleanly with logs.
