import requests
import sqlite3
import time
from datetime import datetime

TMDB_API_KEY = "ba7e4123d6f338e3c45f0ae8ffcce0b5"

import random

START_YEAR = 1950
END_YEAR = datetime.today().year

# pick 5 random unique years
sample_years = random.sample(range(START_YEAR, END_YEAR + 1), 5)

print("Selected years:", sample_years)



# -------- DB SETUP --------
conn = sqlite3.connect("film_cache.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY,
    title TEXT,
    overview TEXT,
    release_date TEXT,
    month INTEGER,
    day INTEGER,
    poster_path TEXT
)
""")

conn.commit()


# -------- FETCH AND CACHE --------
for year in sample_years:
    print(f"Fetching year {year}")

    page = 1
    while True:
        url = (
            f"https://api.themoviedb.org/3/discover/movie"
            f"?api_key={TMDB_API_KEY}"
            f"&primary_release_year={year}"
            f"&page={page}"
        )

        response = requests.get(url).json()
        results = response.get("results", [])

        if not results:
            break

        for film in results:
            release = film.get("release_date")
            if not release:
                continue

            try:
                dt = datetime.strptime(release, "%Y-%m-%d")
                month = dt.month
                day = dt.day

                c.execute("""
                INSERT OR IGNORE INTO films 
                (id, title, overview, release_date, month, day, poster_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    film["id"],
                    film["title"],
                    film.get("overview", ""),
                    release,
                    month,
                    day,
                    film.get("poster_path")
                ))

            except:
                pass

        conn.commit()

        page += 1
        time.sleep(0.25)  # avoid rate limit

conn.close()
print("Film cache complete.")