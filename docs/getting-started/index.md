# Getting Started

Up and running in three commands:

```bash
pip install -r requirements.txt
python scripts/init_db.py          # build coffee_bi.duckdb (one-time)
streamlit run app/dashboard.py     # open the UI
```

Then, to run the agent from the command line:

```bash
python -m agent.run_agent
```

| Step | Page |
|---|---|
| 1. Install dependencies | [Installation](installation.md) |
| 2. Point to the dataset | [Configuration](configuration.md) |
| 3. Build the warehouse & run | [Running the App](running.md) |
