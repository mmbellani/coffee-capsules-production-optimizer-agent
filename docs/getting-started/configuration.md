# Configuration

## Dataset location

By default the app looks for the dataset in `../coffee_capsule_dataset`.
If it lives elsewhere, set `COFFEE_DATA_DIR`:

=== "Windows (PowerShell)"

    ```powershell
    $env:COFFEE_DATA_DIR = "C:\path\to\coffee_capsule_dataset"
    ```

=== "macOS / Linux"

    ```bash
    export COFFEE_DATA_DIR="/path/to/coffee_capsule_dataset"
    ```

Central settings live in `config.py`.

## Optional: LLM credentials

The agent runs **fully offline** on its deterministic engine.
If LLM credentials are available, it additionally produces an **executive narrative**.
See [LLM Narrative](../agent/llm.md).

!!! warning "Secrets"
    Never commit credentials. Keep them in environment variables or a local `.env`
    file that is listed in `.gitignore`.
