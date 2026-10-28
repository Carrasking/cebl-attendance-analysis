# CEBL Attendance Report 2022–2026

**What actually fills arenas in Canadian pro basketball?**

This project analyzes five seasons of attendance data from the Canadian Elite Basketball League (CEBL) to understand which teams draw fans, how the league is trending, and whether winning actually brings people to the arena.

![Dashboard](dashboard.png)

## Key findings

- **League attendance peaked in 2024 and has dropped 15% since.** Average attendance per game went from 1,994 (2022) to 3,296 (2024), then fell to 2,803 (2026).
- **Winning doesn't fill arenas.** The correlation between win % and attendance index across all team-seasons is only 0.13. In 2026, Scarborough had the league's best record (20-4) but drew 31% below the league average, while Winnipeg (14-10) drew more than twice the league average.
- **Only 4 of 10 teams drew above the league average in 2026:** Winnipeg, Vancouver, Edmonton and Calgary.
- **Special events move the needle.** Calgary averaged 3,451 fans per game in 2024, but its biggest game drew 12,327, about 3.6x a normal night.

## Metrics

| Metric | Definition |
|---|---|
| `attendance_avg` | Average fans per home game |
| `league_avg` | League-wide average fans per game, weighted by number of games |
| `attendance_index` | Team average ÷ league average (1.0 = league average, 1.5 = 50% above) |
| `win_pct` | Wins ÷ games played |
| `yoy_change_pct` | Year-over-year change in average attendance, by franchise |
| `attendance_range` | Highest game minus lowest game in the season |

Teams that changed name or city are grouped under one `franchise` so they can be tracked over time (e.g. Saskatchewan Rattlers → Saskatoon Mamba).

## Project structure

```
├── cebl_attendance_database.py                    # Downloads, cleans and joins the data
├── CEBL_Attendance_Report_2022-2026_Template.pbit  # Power BI template (no data)
├── requirements.txt
├── dashboard.png
└── cebl_output/
    ├── cebl_team_attendance.csv      # Attendance by team and season
    ├── cebl_standings.csv            # Standings by team and season
    ├── cebl_team_season_base.csv     # Joined dataset + metrics (used in Power BI)
    ├── chart_league_average.png
    └── chart_teams_latest_season.png
```

## How to run

```bash
pip install -r requirements.txt
python cebl_attendance_database.py
```

Before running, change `OUTPUT_FOLDER` at the top of the script to a folder on your computer.

To open the dashboard, open the `.pbit` template in Power BI Desktop and point it to `cebl_output/cebl_team_season_base.csv`.

## Data notes and limitations

- Wikipedia only has attendance tables from 2022 onward, so 2019 and 2021 are not included. The 2020 season was played without fans.
- The dashboard excludes team-seasons with fewer than 8 home games because their data is incomplete.
- The data is aggregated by team and season. Game-by-game analysis (day, time, opponent, special events) is the next step.

## Tools

Python (pandas, requests, matplotlib) · Power BI · DAX

## Data source

Attendance and standings tables from the [CEBL season pages on Wikipedia](https://en.wikipedia.org/wiki/2026_CEBL_season), available under the [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).

## Author

**Jorge Carrasco** · Business Insights & Analytics, Humber Polytechnic
[LinkedIn](https://www.linkedin.com/in/jcarrascof) · [GitHub](https://github.com/Carrasking)
