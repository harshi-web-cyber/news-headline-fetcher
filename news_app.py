import os
import threading
import io
import json
from datetime import datetime

import requests
import customtkinter as ctk
from PIL import Image
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv()
API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2/top-headlines"
EVERYTHING_URL = "https://newsapi.org/v2/everything"
FAVORITES_FILE = "favorites.json"

CATEGORIES = ["general", "business", "entertainment", "health",
              "science", "sports", "technology"]

ctk.set_appearance_mode("dark")       # "dark" or "light"
ctk.set_default_color_theme("blue")   # theme accent color


# ---------- APP CLASS ----------
class NewsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PyNews — Headline Fetcher")
        self.geometry("950x700")
        self.minsize(800, 600)

        self.favorites = self.load_favorites()
        self.current_articles = []

        self.build_ui()

    # ---------- UI LAYOUT ----------
    def build_ui(self):
        # Top control bar
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill="x", padx=15, pady=15)

        self.keyword_entry = ctk.CTkEntry(control_frame, placeholder_text="Search keyword...", width=250)
        self.keyword_entry.grid(row=0, column=0, padx=10, pady=10)
        self.keyword_entry.bind("<Return>", lambda e: self.fetch_news())

        self.category_menu = ctk.CTkOptionMenu(control_frame, values=["All"] + CATEGORIES)
        self.category_menu.set("All")
        self.category_menu.grid(row=0, column=1, padx=10, pady=10)

        search_btn = ctk.CTkButton(control_frame, text="🔍 Search", command=self.fetch_news)
        search_btn.grid(row=0, column=2, padx=10, pady=10)

        fav_btn = ctk.CTkButton(control_frame, text="⭐ Favorites", command=self.show_favorites,
                                 fg_color="#8a6d00")
        fav_btn.grid(row=0, column=3, padx=10, pady=10)

        theme_btn = ctk.CTkButton(control_frame, text="🌗 Toggle Theme", command=self.toggle_theme)
        theme_btn.grid(row=0, column=4, padx=10, pady=10)

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Enter a keyword or pick a category, then search.",
                                          font=("Segoe UI", 13))
        self.status_label.pack(pady=(0, 5))

        # Scrollable article area
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=900, height=550)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    # ---------- THEME ----------
    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if current == "Dark" else "dark")

    # ---------- FETCH (threaded so UI doesn't freeze) ----------
    def fetch_news(self):
        self.status_label.configure(text="Fetching latest headlines...")
        threading.Thread(target=self._fetch_news_thread, daemon=True).start()

    def _fetch_news_thread(self):
        keyword = self.keyword_entry.get().strip()
        category = self.category_menu.get()

        params = {"apiKey": API_KEY, "pageSize": 20}

        if keyword:
            url = EVERYTHING_URL
            params["q"] = keyword
            params["sortBy"] = "publishedAt"
        else:
            url = BASE_URL
            params["country"] = "us"
            if category != "All":
                params["category"] = category

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if response.status_code != 200:
                self.status_label.configure(text=f"Error: {data.get('message', 'Unknown error')}")
                return

            articles = data.get("articles", [])
            self.current_articles = articles
            self.status_label.configure(text=f"Found {len(articles)} articles.")
            self.render_articles(articles)

        except requests.exceptions.RequestException as e:
            self.status_label.configure(text=f"Network error: {e}")

    # ---------- RENDER ARTICLES ----------
    def render_articles(self, articles):
        # Clear previous results
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not articles:
            ctk.CTkLabel(self.scroll_frame, text="No articles found.").pack(pady=20)
            return

        for article in articles:
            self.create_article_card(article)

    def create_article_card(self, article):
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        card.pack(fill="x", pady=8, padx=5)

        # Thumbnail (if available)
        img_label = ctk.CTkLabel(card, text="")
        img_label.grid(row=0, column=0, rowspan=4, padx=10, pady=10)
        self.load_thumbnail(article.get("urlToImage"), img_label)

        title = article.get("title") or "No title"
        source = article.get("source", {}).get("name", "Unknown source")
        published = article.get("publishedAt", "")
        try:
            published = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %Y %H:%M")
        except Exception:
            pass
        description = article.get("description") or ""

        ctk.CTkLabel(card, text=title, font=("Segoe UI", 15, "bold"),
                     wraplength=600, justify="left").grid(row=0, column=1, sticky="w", padx=10, pady=(10, 0))

        ctk.CTkLabel(card, text=f"{source} • {published}", font=("Segoe UI", 11),
                     text_color="gray70").grid(row=1, column=1, sticky="w", padx=10)

        ctk.CTkLabel(card, text=description, font=("Segoe UI", 12),
                     wraplength=600, justify="left").grid(row=2, column=1, sticky="w", padx=10, pady=(5, 5))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=3, column=1, sticky="w", padx=10, pady=(0, 10))

        open_btn = ctk.CTkButton(btn_frame, text="Read More", width=100,
                                  command=lambda url=article.get("url"): self.open_link(url))
        open_btn.pack(side="left", padx=(0, 10))

        fav_btn = ctk.CTkButton(btn_frame, text="⭐ Save", width=100, fg_color="#8a6d00",
                                 command=lambda a=article: self.add_favorite(a))
        fav_btn.pack(side="left")

    def load_thumbnail(self, url, label_widget):
        if not url:
            return
        try:
            resp = requests.get(url, timeout=5)
            img_data = Image.open(io.BytesIO(resp.content))
            img_data = img_data.resize((120, 90))
            ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(120, 90))
            label_widget.configure(image=ctk_img)
            label_widget.image = ctk_img  # keep reference
        except Exception:
            pass  # skip broken images silently

    # ---------- LINKS ----------
    def open_link(self, url):
        if url:
            import webbrowser
            webbrowser.open(url)

    # ---------- FAVORITES ----------
    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_favorites(self):
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, indent=2)

    def add_favorite(self, article):
        if article not in self.favorites:
            self.favorites.append(article)
            self.save_favorites()
            self.status_label.configure(text="Saved to favorites.")

    def show_favorites(self):
        self.status_label.configure(text=f"Showing {len(self.favorites)} saved favorites.")
        self.render_articles(self.favorites)


# ---------- RUN ----------
if __name__ == "__main__":
    app = NewsApp()
    app.mainloop()