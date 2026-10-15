# FAQ

??? question "Do I need an LLM to run the agent?"
    No. The agent runs fully offline. An LLM only adds an executive narrative.

??? question "Is the data real?"
    No — it is a synthetic dataset of a coffee-capsule plant.

??? question "Where does the warehouse live?"
    In a local DuckDB file, `coffee_bi.duckdb`, created by `scripts/init_db.py`.

??? question "The app can't find the dataset."
    Set `COFFEE_DATA_DIR` to the dataset folder. See [Configuration](getting-started/configuration.md).

??? question "How do I add a new metric?"
    Add a `.sql` file to `sql/analytics/`, then expose it in the dashboard and/or as an agent tool.

??? question "How do I preview these docs locally?"
    ```bash
    pip install -r requirements-docs.txt
    mkdocs serve
    ```
    Then open <http://127.0.0.1:8000>.
