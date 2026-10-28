"""
CEBL Attendance & Performance Database (by Team and Season)
===========================================================

What this script does:
  1. Downloads each CEBL season's ATTENDANCE table from Wikipedia
     (total, high, low and average per team).
  2. Downloads the STANDINGS table (wins, losses, points for/against).
  3. Joins both tables by team and season, and adds a franchise name so a team
     can be tracked even after it changed its name or city.
  4. Calculates business metrics (attendance index vs. league, year-over-year change).
  5. Saves everything as CSV (ready for Power BI) and creates two charts for LinkedIn.

Requirements (one time only, in the VS Code terminal):
    pip install pandas requests lxml matplotlib

How to run:
    python cebl_attendance_database.py

Output (saved in OUTPUT_FOLDER):
    cebl_team_attendance.csv     -> attendance by team and season
    cebl_standings.csv           -> standings by team and season
    cebl_team_season_base.csv    -> both joined + metrics (USE THIS ONE IN POWER BI)
    chart_league_average.png
    chart_teams_latest_season.png
"""

import io
import re
import time
from pathlib import Path

import pandas as pd
import requests
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------

# Folder on your PC where all results will be saved.
# The "r" before the quotes is needed on Windows so the backslashes are read correctly.
OUTPUT_FOLDER = Path(r"C:\Users\carra\OneDrive\Desktop\Idea\Canada Stadistics\CEBL") / "cebl_output"

# Seasons to download. 2020 was played in a bubble with no fans, so it is skipped.
SEASONS = [2019, 2021, 2022, 2023, 2024, 2025, 2026]

# Wikipedia asks scripts to identify themselves. You can replace the email with yours.
HEADERS = {"User-Agent": "CEBL-analytics-student-project/1.0 (contact: your_email@example.com)"}

# Some teams changed name or city. This dictionary groups those names under one
# "franchise" so they can be compared across seasons.
# If the script warns about a team without a franchise, add it here.
FRANCHISES = {
    "Guelph Nighthawks": "Nighthawks",  # separate team; played alongside Hamilton in 2022
    "Hamilton Honey Badgers": "Honey Badgers",
    "Newfoundland Growlers": "Growlers",
    "Brampton Honey Badgers": "Honey Badgers",
    "Fraser Valley Bandits": "Bandits",
    "Vancouver Bandits": "Bandits",
    "Saskatchewan Rattlers": "Saskatoon",
    "Saskatoon Mamba": "Saskatoon",
    "Edmonton Stingers": "Stingers",
    "Niagara River Lions": "River Lions",
    "Ottawa BlackJacks": "BlackJacks",
    "Scarborough Shooting Stars": "Shooting Stars",
    "Calgary Surge": "Surge",
    "Montreal Alliance": "Alliance",
    "Winnipeg Sea Bears": "Sea Bears",
}


# ---------------------------------------------------------------------------
# CLEANING FUNCTIONS
# ---------------------------------------------------------------------------

def clean_team(text):
    """Removes Wikipedia notes from a team name: [1], (H), 'x –', symbols, etc."""
    s = str(text)
    s = re.sub(r"\[.*?\]", "", s)              # footnotes like [1]
    s = re.sub(r"\(.*?\)", "", s)              # (H), (C), etc.
    s = re.sub(r"[†‡*^]", "", s)               # symbols
    s = re.sub(r"\s*[–-]\s*[a-zA-Z]$", "", s)  # "Team – x"
    s = re.sub(r"^[a-zA-Z]\s*[–-]\s*", "", s)  # "x – Team"
    return " ".join(s.split()).strip()


def clean_number(text):
    """Turns '78,375', '−14.9%†' or '+30.4%' into a number. Returns None if there is no number."""
    if pd.isna(text):
        return None
    s = str(text).replace("−", "-").replace(",", "")
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def flatten_columns(df):
    """Wikipedia sometimes uses two-level headers. Keep only the last level."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[-1]) for c in df.columns]
    df.columns = [re.sub(r"\[.*?\]", "", str(c)).strip() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# DOWNLOADING AND READING TABLES
# ---------------------------------------------------------------------------

def download_tables(season):
    """Downloads the season's Wikipedia page and returns all of its tables."""
    url = f"https://en.wikipedia.org/wiki/{season}_CEBL_season"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text))
    return [flatten_columns(t) for t in tables]


def extract_attendance(tables, season):
    """Finds the table that has Team + Total + Average columns."""
    for t in tables:
        cols = set(t.columns)
        if {"Team", "Total", "Average"}.issubset(cols):
            df = t.copy()
            df["Team"] = df["Team"].map(clean_team)
            df = df[~df["Team"].str.contains("total", case=False, na=False)]
            out = pd.DataFrame({
                "season": season,
                "team": df["Team"],
                "attendance_total": df["Total"].map(clean_number),
                "attendance_high": df["High"].map(clean_number) if "High" in cols else None,
                "attendance_low": df["Low"].map(clean_number) if "Low" in cols else None,
                "attendance_avg": df["Average"].map(clean_number),
            })
            return out.dropna(subset=["attendance_avg"])
    return pd.DataFrame()


def extract_standings(tables, season):
    """Finds the standings tables (Team + W + L). There is usually one per conference."""
    parts = []
    for t in tables:
        cols = set(t.columns)
        if {"Team", "W", "L"}.issubset(cols):
            df = t.copy()
            df["Team"] = df["Team"].map(clean_team)
            parts.append(pd.DataFrame({
                "season": season,
                "team": df["Team"],
                "wins": df["W"].map(clean_number),
                "losses": df["L"].map(clean_number),
                "points_for": df["PF"].map(clean_number) if "PF" in cols else None,
                "points_against": df["PA"].map(clean_number) if "PA" in cols else None,
            }))
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True).dropna(subset=["wins", "losses"])
    # If a team appears in more than one table (e.g. overall and conference), keep one row.
    return df.drop_duplicates(subset=["season", "team"])


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

def build_base(attendance, standings):
    """Joins attendance + standings and calculates business metrics."""
    base = attendance.merge(standings, on=["season", "team"], how="left")

    base["franchise"] = base["team"].map(FRANCHISES)
    missing = base.loc[base["franchise"].isna(), "team"].unique()
    if len(missing):
        print(f"  Warning: teams without a franchise (add them to FRANCHISES): {list(missing)}")
    base["franchise"] = base["franchise"].fillna(base["team"])

    # Approximate number of home games (total / average)
    base["home_games_approx"] = (base["attendance_total"] / base["attendance_avg"]).round()

    # Win percentage
    base["win_pct"] = base["wins"] / (base["wins"] + base["losses"])

    # League average per season, weighted by number of games
    league = base.groupby("season").agg(
        league_total=("attendance_total", "sum"),
        league_games=("home_games_approx", "sum"),
    )
    league["league_avg"] = league["league_total"] / league["league_games"]
    base = base.merge(league[["league_avg"]], on="season", how="left")

    # Attendance index: 1.00 = same as league average; 1.50 = 50% above the league
    base["attendance_index"] = base["attendance_avg"] / base["league_avg"]

    # Year-over-year change in average attendance, by franchise
    base = base.sort_values(["franchise", "season"])
    base["yoy_change_pct"] = base.groupby("franchise")["attendance_avg"].pct_change() * 100

    # Gap between the best and worst game: shows how "variable" the crowd is
    base["attendance_range"] = base["attendance_high"] - base["attendance_low"]

    return base.sort_values(["season", "attendance_avg"], ascending=[True, False]), league


def print_summary(base, league):
    print("\n=== League average attendance by season ===")
    table = league.copy()
    table["change_pct"] = table["league_avg"].pct_change() * 100
    print(table[["league_total", "league_avg", "change_pct"]].round(1).to_string())

    latest = base["season"].max()
    print(f"\n=== {latest} ranking (average per game) ===")
    cols = ["team", "attendance_avg", "attendance_index", "win_pct", "yoy_change_pct"]
    print(base[base["season"] == latest][cols].round(2).to_string(index=False))

    # Does winning bring in fans? Correlation between win % and attendance index
    data = base.dropna(subset=["win_pct", "attendance_index"])
    if len(data) > 5:
        r = data["win_pct"].corr(data["attendance_index"])
        print("\n=== Does winning bring in fans? ===")
        print(f"Correlation between win % and attendance index (all seasons): {r:.2f}")
        print("  Close to 0 = winning barely explains attendance; close to 1 = strong relationship.")


def make_charts(base, league):
    # 1) League average by season
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(league.index.astype(str), league["league_avg"], color="#1f4e79")
    for i, v in enumerate(league["league_avg"]):
        ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=9)
    ax.set_title("CEBL: Average Attendance per Game by Season")
    ax.set_ylabel("Fans per game")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / "chart_league_average.png", dpi=200)
    plt.close(fig)

    # 2) Teams in the latest season, with a league-average line
    latest = base["season"].max()
    d = base[base["season"] == latest].sort_values("attendance_avg")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(d["team"], d["attendance_avg"], color="#2e86c1")
    avg = d["league_avg"].iloc[0]
    ax.axvline(avg, color="#c0392b", linestyle="--", linewidth=1)
    ax.text(avg, len(d) - 0.4, f" League average: {avg:,.0f}", color="#c0392b", fontsize=9)
    ax.set_title(f"CEBL {latest}: Average Attendance by Team")
    ax.set_xlabel("Fans per game")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / "chart_teams_latest_season.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------------------------------

def main():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    all_attendance, all_standings = [], []

    for season in SEASONS:
        print(f"Downloading {season} season...")
        try:
            tables = download_tables(season)
        except Exception as e:
            print(f"  Could not download {season}: {e}")
            continue

        a = extract_attendance(tables, season)
        s = extract_standings(tables, season)
        print(f"  Attendance: {len(a)} teams | Standings: {len(s)} teams")
        if a.empty:
            print("  (This season has no attendance table on Wikipedia)")

        all_attendance.append(a)
        all_standings.append(s)
        time.sleep(1)  # short pause so we don't overload Wikipedia

    attendance = pd.concat(all_attendance, ignore_index=True) if all_attendance else pd.DataFrame()
    standings = pd.concat(all_standings, ignore_index=True) if all_standings else pd.DataFrame()

    if attendance.empty:
        print("No attendance data found. Check your internet connection or the Wikipedia page structure.")
        return

    base, league = build_base(attendance, standings)

    attendance.to_csv(OUTPUT_FOLDER / "cebl_team_attendance.csv", index=False)
    standings.to_csv(OUTPUT_FOLDER / "cebl_standings.csv", index=False)
    base.to_csv(OUTPUT_FOLDER / "cebl_team_season_base.csv", index=False)

    print_summary(base, league)
    make_charts(base, league)
    print(f"\nDone. Files saved in: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
