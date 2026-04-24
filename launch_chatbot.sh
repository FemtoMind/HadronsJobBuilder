rm jobs.db #for now, don't persist jobs
uvicorn main.gui:app --host 0.0.0.0 --port 8050
