DROP TABLE IF EXISTS books;

CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    year INTEGER,
    genre TEXT,
    rating REAL,
    isbn TEXT,
    subjects TEXT,
    cover_url TEXT
);
