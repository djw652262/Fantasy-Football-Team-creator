# Fantasy Football Team Creator

A FastAPI lineup assistant for Fantasy Premier League.

## V1 focus

- Manually maintain your 15-player squad
- Pull official FPL data for the next gameweek
- Rank your squad members for the next match
- Recommend a legal starting XI and bench order
- Let you override the recommendation and save your lineup
- Track saved lineups and their points over time

## Run locally

The easiest way on Windows is to double-click:

- `start-website.bat`

That starts the local server and opens the site in your browser.

You can also run it manually:

```bash
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open `http://127.0.0.1:8000`.

The one-click Windows launcher uses port `8010` to avoid conflicts with older local servers:

- `http://127.0.0.1:8010`

## Faster cached workflow

The app now loads from local cached FPL data so the pages open much faster.

1. Start the website
2. Click `Refresh FPL Data` once
3. Use the site normally from the cached data

That refresh only pulls the core FPL data plus detailed summaries for the players in your squad.
