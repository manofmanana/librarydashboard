# Alejandro's Library Dashboard

A **Streamlit-powered data science dashboard** to track my reading journey across years, genres, and ideas.  
It combines **SQLite**, **Google Books API**, and **Plotly visualizations** to show insights into my reading habits.

---

## Features

- **Hero Banner with Overlay Text**  
  Displays a custom banner image with the project title and description.  

- **Dynamic Quotes**  
  A rotating inspirational quote at the top (auto-refresh every 60s).  

- **Visual Insights (Professional Charts)**  
  - Books read per year (clean bar chart).  
  - Genre distribution (modern donut chart).  
  - Ratings distribution & trends.  
  - Advanced insights on reading habits.  

- **KPIs (Key Metrics)**  
  - Total books read.  
  - Average rating.  
  - Most popular genre.  
  - Years covered.  

- **Interactive Table**  
  Filter by year, genre, or search by title.  

- **Book Covers**  
  Pulled dynamically from the **Google Books API** (with fallback placeholder).  

- **Random Recommendation**  
  A "🎲 Surprise Me!" button picks a random book from your library.  

- **Export Data**  
  Download your book collection as a CSV file.  

- **Password-Protected Add Book Form**  
  Add new books to your library (stored in SQLite).  

---

## Tech Stack

- [Python](https://www.python.org/)  
- [Streamlit](https://streamlit.io/)  
- [SQLite](https://www.sqlite.org/)  
- [Plotly Express](https://plotly.com/python/)  
- [Google Books API](https://developers.google.com/books)  
- HTML + CSS (custom styling for cards, banner, and animations)  

---

## Project Structure
my_dashboard/
│
├── librarydashboard.py # Main Streamlit app
├── books.db # SQLite database (auto-created)
├── schema.sql # Database schema
├── seed.sql # Initial book data
│
├── static/ # Static assets
│ ├── banner.jpg # Banner image
│ ├── styles.css # Custom CSS
│ └── scripts.js # Custom JS
│
└── README.md # Project documentation

---

## Setup

1. Clone the repository or move into your project folder:  
   ```bash
   cd my_dashboard
2. Create and activate a virtual environment:

bash
Copy code
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

3. Install dependencies:

bash
Copy code
pip install -r requirements.txt
(If you don’t have one, install manually: pip install streamlit plotly pandas requests)

4. Initialize the database (only once):

bash
Copy code
sqlite3 books.db < schema.sql
sqlite3 books.db < seed.sql

5. Launch the Dashboard:
streamlit run librarydashboard.py

6. Add Book Feature

The "Add a New Book" form requires a password.
Default password: JulietA
(You can change this inside librarydashboard.py.)