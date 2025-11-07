import pandas as pd


class BookRecommender:
    """Very small, deterministic recommender used as a placeholder.

    Methods expected by `app.py`:
    - recommend_by_genre(books_df, genre)
    - recommend_by_author(books_df, author)
    - recommend_by_book(books_df, title)
    """

    def _safe_head(self, df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["Title", "Author", "Bookshelf", "Link"])
        return df.head(n)

    def recommend_by_genre(self, books_df: pd.DataFrame, genre: str) -> pd.DataFrame:
        if books_df is None or books_df.empty:
            return self._safe_head(books_df)
        filtered = books_df[books_df.get("Bookshelf") == genre]
        if filtered.empty:
            # fallback: top 5 by any means
            return self._safe_head(books_df.sample(frac=1, random_state=1))
        return self._safe_head(filtered.sort_values("Title"))

    def recommend_by_author(self, books_df: pd.DataFrame, author: str) -> pd.DataFrame:
        if books_df is None or books_df.empty:
            return self._safe_head(books_df)
        filtered = books_df[books_df.get("Author") == author]
        if filtered.empty:
            return self._safe_head(books_df.sample(frac=1, random_state=2))
        return self._safe_head(filtered.sort_values("Title"))

    def recommend_by_book(self, books_df: pd.DataFrame, title: str) -> pd.DataFrame:
        if books_df is None or books_df.empty:
            return self._safe_head(books_df)
        # Simple nearest-by-same-author fallback
        row = books_df[books_df.get("Title") == title]
        if row.empty:
            return self._safe_head(books_df.sample(frac=1, random_state=3))
        author = row.iloc[0].get("Author")
        if author:
            same_author = books_df[books_df.get("Author") == author]
            return self._safe_head(same_author[same_author.get("Title") != title])
        return self._safe_head(books_df.sample(frac=1, random_state=4))
