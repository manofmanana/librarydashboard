import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import random
import requests
import sqlite3
import os
import base64
from streamlit_autorefresh import st_autorefresh
from scipy.stats import gaussian_kde  # ok to keep even if not used now
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
import re
from difflib import SequenceMatcher

# =====================
# App/Theme Settings
# =====================
st.set_page_config(
    page_title="Alejandro's Library",
    layout="wide",
    initial_sidebar_state="expanded"
)

DARK_BROWN = "#2c1b0c"
MID_BROWN = "#3a2414"
COPPER = "#b87333"
COPPER_LIGHT = "#d28b47"

# =====================
# SQLite Setup
# =====================
conn = sqlite3.connect("books.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    year INTEGER,
    genre TEXT,
    rating REAL,
    isbn TEXT,
    subjects TEXT,
    cover_url TEXT
)
""")
conn.commit()

def reload_df() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM books", conn)

df = reload_df()

# =====================
# Quotes
# =====================
quotes = [
    ("The darker the night, the brighter the stars.", "Fyodor Dostoevsky"),
    ("Blessed are the hearts that can bend; they shall never be broken.", "Albert Camus"),
    ("He who has a why to live can bear almost any how.", "Viktor Frankl"),
    ("The only way to deal with fear is to face it head on.", "Haruki Murakami"),
    ("The more sand has escaped from the hourglass of our life, the clearer we should see through it.", "Niccolò Machiavelli"),
    ("In order to write about life, first you must live it.", "Ernest Hemingway"),
    ("If you are always trying to be normal, you will never know how amazing you can be.", "Maya Angelou"),
    ("Freeing yourself was one thing, claiming ownership of that freed self was another.", "Toni Morrison"),
    ("The world is before you, and you need not take it or leave it as it was when you came in.", "James Baldwin"),
    ("A mind that is stretched by a new experience can never go back to its old dimensions.", "Oliver Wendell Holmes"),
]
st_autorefresh(interval=60*1000, limit=None, key="quote_refresh")

# =====================
# CSS (theme + cover hover)
# =====================
st.markdown(
    f"""
    <style>
        body, .stApp {{ background-color: {DARK_BROWN}; color: #ffffff; }}
        section[data-testid="stSidebar"] {{ background-color: {MID_BROWN}; }}
        h1, h2, h3, h4, h5, h6 {{ color: #ffffff !important; }}

        .copper-card {{
            background-color:{COPPER};
            padding:15px;
            border-radius:12px;
            margin:15px 0;
            font-size:1.1em;
            color:#ffffff;
            font-weight:500;
            text-align:center;
        }}

        .book-cover {{
            margin-bottom: 14px;
        }}
        .book-cover img {{
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.35);
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }}
        .book-cover img:hover {{
            transform: translateY(-4px) scale(1.04);
            box-shadow: 0 10px 20px rgba(184,115,51,0.5);
            cursor: pointer;
        }}
        .book-link {{ text-decoration: none; }}
        .genre-label {{
            color: #fff; opacity: 0.8; font-size: 0.9rem; margin-bottom: 6px;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# Hero Banner
# =====================
banner_path = os.path.join(os.path.dirname(__file__), "static", "banner.jpg")
if os.path.exists(banner_path):
    with open(banner_path, "rb") as f:
        banner_bytes = f.read()
    banner_base64 = base64.b64encode(banner_bytes).decode()
    st.markdown(
        f"""
        <div style="position: relative; width: 100%; margin-top: -70px; overflow: hidden;">
            <img src="data:image/jpg;base64,{banner_base64}"
                 style="width:100%; height:auto; border-radius: 0 0 12px 12px; filter: brightness(60%);">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                        color: white; text-align: center; padding: 0 20px;">
                <h1 style="font-size: 3em; margin-bottom: 0.3em;">Alejandro's Library 📚</h1>
                <p style="font-size: 1.2em; margin: 0;">A dashboard tracking my reading journey across years, genres, and ideas.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =====================
# Quote Block (under banner)
# =====================
q, a = random.choice(quotes)
st.markdown(f"<div class='copper-card'>{q} — {a}</div>", unsafe_allow_html=True)

# =====================
# Helpers (matching + links)
# =====================
def normalize_text(s: str) -> str:
    s = s or ""
    s = s.strip().lower()
    s = re.sub(r"[’'`]", "'", s)
    s = re.sub(r"[^a-z0-9\s:,-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def strip_subtitle(title: str) -> str:
    return title.split(":", 1)[0].strip() if title else title

def author_tokens(author: Optional[str]) -> List[str]:
    if not author:
        return []
    return [p.strip() for p in re.split(r",| and ", author) if p.strip()]

def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

def author_score(cand_authors: List[str], query_author: Optional[str]) -> float:
    if not query_author:
        return 0.0
    qa = set([normalize_text(x) for x in author_tokens(query_author)])
    ca = set([normalize_text(x) for x in (cand_authors or [])])
    if not qa or not ca:
        return 0.0
    inter = len(qa & ca)
    union = len(qa | ca) if (qa | ca) else 1
    return inter / union

def openlibrary_link(title: Optional[str], author: Optional[str], isbn: Optional[str]) -> str:
    if isbn and str(isbn).strip():
        return f"https://openlibrary.org/isbn/{str(isbn).strip()}"
    q = " ".join([x for x in [(title or "").strip(), (author or "").strip()] if x])
    return f"https://openlibrary.org/search?q={quote_plus(q)}"

# =====================
# Tiered Cover Fetching (ISBN → Open Library fuzzy → Google Books)
# =====================
@st.cache_data(show_spinner=False)
def fetch_cover_by_isbn(isbn: str) -> Optional[str]:
    if not isbn:
        return None
    try:
        r = requests.get(f"https://openlibrary.org/isbn/{isbn}.json", timeout=10)
        if r.status_code == 200:
            js = r.json()
            if isinstance(js, dict) and "covers" in js and js["covers"]:
                cover_id = js["covers"][0]
                return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    except Exception:
        pass
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

def _best_doc_from_openlibrary(docs: List[Dict[str, Any]], title: str, author: Optional[str]) -> Optional[Dict[str, Any]]:
    if not docs: return None
    best, best_score = None, -1.0
    t_base = strip_subtitle(title)
    for d in docs:
        cand_title = d.get("title", "") or ""
        cand_authors = d.get("author_name", []) or []
        ts = max(title_similarity(cand_title, title), title_similarity(cand_title, t_base))
        ascore = author_score(cand_authors, author)
        score = 0.75 * ts + 0.25 * ascore
        ed = d.get("edition_count", 0) or 0
        score += min(ed, 20) / 200.0
        if score > best_score:
            best_score, best = score, d
    return best if best_score >= 0.55 else None

@st.cache_data(show_spinner=False)
def fetch_openlibrary_best(title: str, author: Optional[str]) -> Dict[str, Optional[str]]:
    attempts = []
    a_tok = author_tokens(author)
    if a_tok: attempts.append({"title": title, "author": a_tok[0]})
    attempts.append({"title": title, "author": author} if author else {"title": title})
    base = strip_subtitle(title)
    if a_tok: attempts.append({"title": base, "author": a_tok[0]})
    attempts.append({"title": base})
    attempts.append({"q": f"{title} {author or ''}".strip()})
    for params in attempts:
        try:
            r = requests.get("https://openlibrary.org/search.json", params=params, timeout=10)
            if r.status_code != 200: continue
            docs = (r.json() or {}).get("docs", []) or []
            if not docs: continue
            best = _best_doc_from_openlibrary(docs, title, author)
            if not best: continue
            cover_url = f"https://covers.openlibrary.org/b/id/{best['cover_i']}-L.jpg" if "cover_i" in best else None
            isbn = (best.get("isbn") or [None])[0]
            subjects = ", ".join((best.get("subject") or [])[:5]) if best.get("subject") else None
            return {"cover_url": cover_url, "isbn": isbn, "subjects": subjects}
        except Exception:
            continue
    return {"cover_url": None, "isbn": None, "subjects": None}

@st.cache_data(show_spinner=False)
def fetch_cover_google_books(title: str, author: Optional[str]) -> Optional[str]:
    q = f'intitle:"{title}"'
    if author: q += f'+inauthor:"{author}"'
    try:
        r = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q": q, "maxResults": 5}, timeout=10)
        items = (r.json() or {}).get("items", [])
        for it in items:
            links = (it.get("volumeInfo") or {}).get("imageLinks") or {}
            for key in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                if links.get(key): return links[key]
    except Exception:
        pass
    return None

@st.cache_data(show_spinner=False)
def fetch_book_data(title: str, author: Optional[str], isbn: Optional[str]) -> Dict[str, Optional[str]]:
    if isbn and str(isbn).strip():
        cover_isbn = fetch_cover_by_isbn(str(isbn).strip())
        if cover_isbn:
            return {"cover_url": cover_isbn, "isbn": isbn, "subjects": None}
    ol = fetch_openlibrary_best(title, author)
    if ol.get("cover_url"): return ol
    gb = fetch_cover_google_books(title, author)
    if gb: return {"cover_url": gb, "isbn": isbn, "subjects": None}
    return {"cover_url": None, "isbn": isbn, "subjects": None}

def get_or_fetch_cover_for_row(row: pd.Series) -> str:
    current = (row.get("cover_url") or "").strip()
    if current:
        return current
    fetched = fetch_book_data(row.get("title") or "", row.get("author"), row.get("isbn"))
    cover_url = (fetched.get("cover_url") or "").strip()
    if cover_url:
        isbn_final = fetched.get("isbn") or row.get("isbn")
        subjects = fetched.get("subjects") or row.get("subjects")
        try:
            c.execute(
                "UPDATE books SET cover_url=?, isbn=?, subjects=? WHERE id=?",
                (cover_url, isbn_final, subjects, int(row["id"]))
            ); conn.commit()
        except Exception:
            pass
        return cover_url
    return "https://via.placeholder.com/256x384.png?text=No+Cover"

# =====================
# KPIs
# =====================
total_books = len(df)
avg_rating = f"{df['rating'].mean():.2f}" if total_books > 0 else "0.00"
genre_series = df["genre"].fillna("Unknown") if total_books > 0 else pd.Series([])
most_genre = genre_series.mode()[0] if total_books > 0 and not genre_series.dropna().empty else "N/A"
valid_years = df.loc[(df["year"].fillna(0) > 0), "year"]
years_covered = f"{int(valid_years.min())}–{int(valid_years.max())}" if not valid_years.empty else "N/A"

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f"<div class='copper-card'>Total Books<br><h2>{total_books}</h2></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='copper-card'>Avg. Rating<br><h2>{avg_rating}</h2></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='copper-card'>Most Popular Genre<br><h2>{most_genre}</h2></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='copper-card'>Years Covered<br><h2>{years_covered}</h2></div>", unsafe_allow_html=True)

# =====================
# Visual Insights
# =====================
st.subheader("Visual Insights")
if total_books > 0:
    by_year = df[(df["year"].fillna(0) > 0)].groupby("year", as_index=False).size().rename(columns={"size": "Books"})
    fig1 = px.bar(by_year, x="year", y="Books", text="Books", color="Books",
                  color_continuous_scale=["#5c3820", COPPER, COPPER_LIGHT])
    fig1.update_traces(textposition="outside")

    genre_series = df["genre"].fillna("Unknown")
    by_genre = genre_series.groupby(genre_series).size().reset_index(name="Books").sort_values("Books", ascending=True)
    by_genre = by_genre.rename(columns={"genre": "genre"})
    fig2 = px.bar(by_genre, x="Books", y="genre", orientation="h",
                  text="Books", color="Books",
                  color_continuous_scale=["#5c3820", COPPER, COPPER_LIGHT])
    fig2.update_traces(textposition="outside")

    fig3 = px.histogram(df, x="rating", nbins=15, opacity=0.85, color_discrete_sequence=[COPPER_LIGHT])

    c_1, c_2 = st.columns(2)
    with c_1: st.plotly_chart(fig1, use_container_width=True)
    with c_2: st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Add some books to unlock visual insights!")

# =====================
# Book Covers (with Genre Filter) — simple 5-column layout
# =====================
st.subheader("Book Covers")

if not df.empty:
    all_genres = ["All"] + sorted([str(g) for g in df["genre"].fillna("Unknown").unique().tolist()])
    selected_genre = st.selectbox("Filter by Genre", all_genres, index=0)
    if selected_genre != "All":
        df_covers = df[df["genre"].fillna("Unknown") == selected_genre]
    else:
        df_covers = df

    if df_covers.empty:
        st.warning("No books match this filter.")
    else:
        cols = st.columns(5, gap="small")
        for i, (_, row) in enumerate(df_covers.iterrows()):
            with cols[i % 5]:
                cover_url = get_or_fetch_cover_for_row(row)
                link = openlibrary_link(row.get("title"), row.get("author"), row.get("isbn"))
                st.markdown(
                    f"""
                    <div class='book-cover'>
                        <a href="{link}" target="_blank" class="book-link">
                            <img src="{cover_url}" alt="cover"/>
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
else:
    st.info("No books yet — add your first one below!")

# =====================
# Add / Edit / Delete Books (+ optional admin rebuild)
# =====================
st.subheader("Add, Edit, or Delete Books")
password = st.text_input("Enter password:", type="password")

if password == "JulietA":
    # Add
    with st.form("add_book", clear_on_submit=True):
        title = st.text_input("Book Title")
        author = st.text_input("Author(s) — comma-separated if multiple")
        year_read = st.number_input("Year Read", min_value=0, max_value=datetime.datetime.now().year,
                                    value=datetime.datetime.now().year)
        rating = st.slider("Rating", 0.0, 5.0, 4.0, 0.1)
        isbn_in = st.text_input("ISBN (optional)").strip()
        submitted = st.form_submit_button("Add Book")
        if submitted:
            fetched = fetch_book_data(title, author, isbn_in if isbn_in else None)
            subjects = fetched.get("subjects")
            genre = subjects.split(",")[0] if subjects else "Unknown"
            cover_url = fetched.get("cover_url")
            isbn_final = fetched.get("isbn") or (isbn_in if isbn_in else None)
            c.execute(
                """INSERT INTO books (title, author, year, genre, rating, isbn, subjects, cover_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, author, int(year_read), genre, float(rating),
                 isbn_final, subjects, cover_url)
            )
            conn.commit()
            st.success(f"Book '{title}' added!")
            st.rerun()

    st.markdown("---")
    st.markdown("**Edit a Book**")
    df = reload_df()
    if not df.empty:
        book_to_edit = st.selectbox("Select a book", df["title"].tolist())
        if book_to_edit:
            row = df[df["title"] == book_to_edit].iloc[0]
            with st.form("edit_book"):
                new_title = st.text_input("Edit Title", value=row["title"])
                new_author = st.text_input("Edit Author(s)", value=row["author"] or "")
                default_year = int(row["year"]) if pd.notnull(row["year"]) and row["year"] else datetime.datetime.now().year
                new_year = st.number_input("Edit Year Read", min_value=0, max_value=datetime.datetime.now().year,
                                           value=default_year)
                new_rating = st.slider("Edit Rating", 0.0, 5.0,
                                       float(row["rating"]) if pd.notnull(row["rating"]) else 4.0, 0.1)
                new_isbn = st.text_input("Edit ISBN (optional)", value=row["isbn"] or "")
                do_refetch = st.checkbox("Re-fetch cover automatically", value=True)
                save_changes = st.form_submit_button("Save Changes")
                if save_changes:
                    cover_url = (row["cover_url"] or "").strip()
                    subjects = row["subjects"]
                    isbn_final = new_isbn.strip() if new_isbn.strip() else None
                    if do_refetch:
                        fetched = fetch_book_data(new_title, new_author, isbn_final)
                        cover_url = fetched.get("cover_url") or cover_url
                        subjects = fetched.get("subjects") or subjects
                        isbn_final = fetched.get("isbn") or isbn_final
                    c.execute(
                        """UPDATE books
                           SET title=?, author=?, year=?, rating=?, isbn=?, subjects=?, cover_url=?
                           WHERE id=?""",
                        (new_title, new_author, int(new_year), float(new_rating),
                         isbn_final, subjects, cover_url, int(row["id"]))
                    )
                    conn.commit()
                    st.success(f"Updated '{new_title}'")
                    st.rerun()
    else:
        st.info("No books available to edit.")

    st.markdown("---")
    st.markdown("**Delete a Book**")
    df = reload_df()
    if not df.empty:
        book_to_delete = st.selectbox("Select book to delete", df["title"].tolist(), key="del_select")
        if st.button("Delete", type="primary"):
            row = df[df["title"] == book_to_delete].iloc[0]
            c.execute("DELETE FROM books WHERE id=?", (int(row["id"]),))
            conn.commit()
            st.success(f"Deleted '{book_to_delete}'.")
            st.rerun()
    else:
        st.info("No books available to delete.")

    st.markdown("---")
    st.markdown("**Admin: Rebuild All Book Covers**")
    if st.button("🔄 Rebuild All Book Covers"):
        rows = pd.read_sql("SELECT * FROM books", conn)
        updated = 0
        for _, r in rows.iterrows():
            fetched = fetch_book_data(r["title"], r["author"], r["isbn"])
            cover_url = (fetched.get("cover_url") or "").strip()
            if cover_url:
                isbn_final = fetched.get("isbn") or r["isbn"]
                subjects = fetched.get("subjects") or r["subjects"]
                c.execute(
                    "UPDATE books SET cover_url=?, isbn=?, subjects=? WHERE id=?",
                    (cover_url, isbn_final, subjects, r["id"])
                )
                updated += 1
        if updated:
            conn.commit()
        st.success(f"Rebuilt covers for {updated} book(s).")
        st.rerun()
else:
    if password:
        st.error("Incorrect password")
