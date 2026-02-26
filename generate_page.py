import requests
from datetime import datetime
from jinja2 import Template
# from flask import Flask, render_template_string
import re
import subprocess

def push_to_git():
    subprocess.run(["git", "add", "index.html"], check=True)

    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )

    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", "Daily update"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Pushed to GitHub.")
    else:
        print("No changes to push.")
today_str = datetime.now().strftime("%B %d, %Y")
# app = Flask(__name__)

TMDB_API_KEY = "ba7e4123d6f338e3c45f0ae8ffcce0b5"
NEWS_API_KEY = "6398714c5240472a8c20922180668acb"

import sqlite3
import random

# -----------------------------
# DATA SOURCES
# -----------------------------
import ollama

OLLAMA_HOST = "http://ser4988-a.tjh.tju.edu:11434"
MODEL_NAME = "llama3.3:latest"

client = ollama.Client(host=OLLAMA_HOST)

SYSTEM_PROMPT = """
You are a sarcastic, sharp political film commentator.

Pick ONE film that symbolically or ironically matches today's political news.

Style:
- Dry
- Intelligent
- Cynical but not hateful
- Under 120 words

Output EXACTLY in this format:

Film Title: <title>
Commentary: <2-4 sentences>
"""

def llm_recommend(news_text, films):

    film_list = "\n".join(
        [f"{f['title']} ({f['release_date']}): {f['overview']}" for f in films]
    )

    prompt = f"""
{SYSTEM_PROMPT}

Today's News:
{news_text}

Films Released Today:
{film_list}
"""

    response = client.generate(
        model=MODEL_NAME,
        prompt=prompt,
        options={
            "temperature": 0.7,
            "num_predict": 512
        }
    )

    return response["response"]

def get_today_news():
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(url).json()
    articles = response.get("articles", [])
    headlines = [a["title"] for a in articles if a["title"]]
    return headlines

def get_films_today():
    today = datetime.today()
    month = today.month
    day = today.day

    conn = sqlite3.connect("film_cache.db")
    c = conn.cursor()

    c.execute("""
        SELECT id, title, overview, release_date, poster_path
        FROM films
        WHERE month=? AND day=?
    """, (month, day))

    rows = c.fetchall()
    conn.close()

    films =[]
    for r in rows:
        films.append({
            "id": r[0],
            "title": r[1],
            "overview": r[2] if r[2] else "No overview available.",
            "release_date": r[3],
            "poster_path": r[4]
        })

    # FALLBACK: If your database has absolutely no films for today
    if not films:
        films =[{
            "title": "Idiocracy", 
            "overview": "A completely average human awakens in a dystopian future...", 
            "release_date": "2006-09-01"
        }]

    # LIMITER: Limit to 25 random films so the LLM doesn't get confused by massive text
    if len(films) > 25:
        films = random.sample(films, 25)

    return films

# -----------------------------
# POSTER FETCH
# -----------------------------

def fetch_poster(title):
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }
    r = requests.get(url, params=params).json()

    if r["results"]:
        poster_path = r["results"][0]["poster_path"]
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None

def parse_llm_output(text):
    # Regex finds the strings even if surrounded by **markdown** or spaces
    title_match = re.search(r'Film Title:\s*\*?([^\*\n]+)\*?', text, re.IGNORECASE)
    commentary_match = re.search(r'Commentary:\s*\*?(.*)', text, re.IGNORECASE | re.DOTALL)

    title = title_match.group(1).strip() if title_match else ""
    commentary = commentary_match.group(1).strip() if commentary_match else "The LLM was speechless today."

    # Strip out the year if the LLM hallucinated it (e.g. "Title (1999)" -> "Title")
    title = re.sub(r'\s*\(\d{4}\)$', '', title)

    return title, commentary

# -----------------------------
# HTML TEMPLATE
# -----------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="21600">
<title>Daily Political Film Calendar</title>

<style>
body {
    margin: 0;
    background: #111;
    color: white;
    font-family: Arial, sans-serif;
    overflow: hidden;
}
.header {
    position: absolute;
    top: 15px;
    right: 20px;
    font-size: 20px;
    color: #ccc;
}

.release-date {
    font-size: 18px;
    margin-bottom: 15px;
    color: #cccccc;
}

.today-date {
    font-size: 28px;
    color: #ffcc00;
    margin-bottom: 10px;
}
.container {
    width: 800px;
    height: 480px;
    display: flex;
    padding: 20px;
    box-sizing: border-box;
}

.poster {
    width: 300px;
    animation: fadeIn 1.5s ease-in-out;
}

.poster img {
    width: 100%;
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(255,255,255,0.3);
}

.content {
    flex: 1;
    padding-left: 30px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.title {
    font-size: 42px;
    font-weight: bold;
    margin-bottom: 20px;
    animation: slideIn 1s ease-out;
}

.commentary {
    font-size: 22px;
    line-height: 1.4;
    animation: fadeIn 2s ease-in;
}

.news {
    position: absolute;
    bottom: 20px;
    left: 20px;
    right: 20px;
    font-size: 14px;
    color: #66ccff;
    animation: ticker 15s linear infinite;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0 }
    to { opacity: 1 }
}

@keyframes slideIn {
    from { transform: translateX(50px); opacity: 0 }
    to { transform: translateX(0); opacity: 1 }
}

@keyframes ticker {
    0% { transform: translateX(100%) }
    100% { transform: translateX(-100%) }
}
</style>
</head>

<body>
<div class="header">
    <div class="today-date">
        {{ today_date }}
    </div>
</div>

<div class="container">

    <div class="poster">
        <img src="{{ poster_url }}">
        <div class="release-date">
            Released: {{ film_release_date }}
        </div>
    </div>

    <div class="content">
        <div class="title">{{ film_title }}</div>
        <div class="commentary">{{ commentary }}</div>
    </div>

</div>

<div class="news">
    {{ news }}
</div>

</body>
</html>
"""

# -----------------------------
# GENERATOR
# -----------------------------

def generate_page():
    news = get_today_news()
    films = get_films_today()

    # Safely attempt to generate commentary
    try:
        raw_output = llm_recommend(news, films)
        film_title, commentary = parse_llm_output(raw_output)
    except Exception as e:
        print(f"LLM Error: {e}")
        film_title, commentary = "", ""

    # ROBUST MATCHING (Case-insensitive & Partial Match)
    selected_film = None
    if film_title:
        for f in films:
            if film_title.lower() in f["title"].lower() or f["title"].lower() in film_title.lower():
                selected_film = f
                film_title = f["title"]  # Standardize the title exactly as it is in DB
                break

    # FALLBACK: If LLM failed or made up a title, pick a random film to keep the site alive
    if not selected_film:
        print(f"Warning: Could not match '{film_title}'. Selecting a random film.")
        selected_film = random.choice(films)
        film_title = selected_film["title"]
        if commentary == "The LLM was speechless today." or not commentary:
            commentary = "Today's political theater is too absurd to comment on, but this film speaks volumes."

    film_release_date = selected_film.get("release_date", "Unknown")
    poster_url = fetch_poster(film_title)

    # Poster fallback just in case TMDB can't find it
    if not poster_url:
        poster_url = "https://via.placeholder.com/500x750/111111/FFFFFF/?text=No+Poster+Found"

    # Format news properly for the HTML marquee ticker (Item 1 • Item 2 • Item 3)
    news_ticker = " • ".join(news) if news else "No news available today."

    template = Template(HTML_TEMPLATE)
    html = template.render(
        film_title=film_title,
        commentary=commentary,
        poster_url=poster_url,
        news=news_ticker,  
        today_date=today_str,
        film_release_date=film_release_date
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Page generated successfully.")

if __name__ == "__main__":
    generate_page()
    push_to_git()