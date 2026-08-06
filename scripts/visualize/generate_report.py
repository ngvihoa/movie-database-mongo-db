#!/usr/bin/env python3
import argparse
import html
import os
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient


def escape(value):
    return html.escape(str(value if value is not None else "N/A"))


def number(value, decimals=0):
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def table(headers, rows, classes=""):
    head = "".join(f"<th>{escape(label)}</th>" for label, _ in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(row.get(key, 'N/A'))}</td>" for _, key in headers) + "</tr>"
        for row in rows
    )
    return f'<div class="table-scroll"><table class="{classes}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def horizontal_bars(rows, label_key, value_key, maximum=None, formatter=lambda value: number(value, 4)):
    maximum = maximum or max((row.get(value_key) or 0 for row in rows), default=1)
    return "".join(
        f"""<div class="bar-row">
          <div class="bar-meta"><span>{escape(row[label_key])}</span><strong>{escape(formatter(row.get(value_key)))}</strong></div>
          <div class="bar-track"><span style="width:{min((row.get(value_key) or 0) / maximum * 100, 100):.2f}%"></span></div>
        </div>"""
        for row in rows
    )


def collect_data(database, person_name, limit, minimum_ratings, genre_name):
    q1 = list(database.movies.aggregate([
        {"$match": {"genres.genreName": "Action", "ratingStats.ratingCount": {"$gte": 50}}},
        {"$sort": {"ratingStats.averageRating": -1, "ratingStats.ratingCount": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "title": 1, "averageRating": "$ratingStats.averageRating", "ratingCount": "$ratingStats.ratingCount"}},
    ]))

    q2 = list(database.people.aggregate([
        {"$match": {"personName": person_name}},
        {"$lookup": {"from": "personCredits", "localField": "_id", "foreignField": "personId", "as": "credit"}},
        {"$unwind": "$credit"},
        {"$match": {"credit.roleName": {"$in": ["Actor", "Director"]}}},
        {"$group": {"_id": {"personId": "$_id", "movieId": "$credit.movieId"}, "personName": {"$first": "$personName"}, "roles": {"$addToSet": "$credit.roleName"}}},
        {"$lookup": {"from": "movies", "localField": "_id.movieId", "foreignField": "_id", "as": "movie"}},
        {"$set": {"movie": {"$first": "$movie"}}},
        {"$group": {"_id": "$_id.personId", "personName": {"$first": "$personName"}, "movies": {"$push": {"title": "$movie.title", "roles": "$roles", "revenue": {"$ifNull": ["$movie.revenue", 0]}}}, "totalRevenue": {"$sum": {"$ifNull": ["$movie.revenue", 0]}}}},
        {"$project": {"_id": 0, "personName": 1, "movies": 1, "totalRevenue": 1}},
    ], allowDiskUse=True))

    def ranking(role):
        return list(database.personCredits.aggregate([
            {"$match": {"roleName": role}},
            {"$group": {"_id": {"personId": "$personId", "movieId": "$movieId"}}},
            {"$lookup": {"from": "movies", "localField": "_id.movieId", "foreignField": "_id", "as": "movie"}},
            {"$set": {"movie": {"$first": "$movie"}}},
            {"$group": {"_id": "$_id.personId", "movieCount": {"$sum": 1}, "averageMovieRating": {"$avg": {"$cond": [{"$gt": [{"$ifNull": ["$movie.ratingStats.ratingCount", 0]}, 0]}, "$movie.ratingStats.averageRating", None]}}}},
            {"$lookup": {"from": "people", "localField": "_id", "foreignField": "_id", "as": "person"}},
            {"$set": {"person": {"$first": "$person"}}},
            {"$sort": {"movieCount": -1, "averageMovieRating": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "personName": "$person.personName", "movieCount": 1, "averageMovieRating": {"$round": ["$averageMovieRating", 4]}}},
        ], allowDiskUse=True))

    q3 = {
        "actors": ranking("Actor"),
        "directors": ranking("Director"),
    }

    q4 = list(database.demographicGenreStats.aggregate([
        {"$match": {"ratingCount": {"$gte": minimum_ratings}}},
        {"$sort": {"country": 1, "ageGroup": 1, "averageRating": -1, "ratingCount": -1}},
        {"$group": {"_id": {"country": "$country", "ageGroup": "$ageGroup"}, "topGenre": {"$first": "$genreName"}, "averageRating": {"$first": "$averageRating"}, "ratingCount": {"$first": "$ratingCount"}}},
        {"$project": {"_id": 0, "country": "$_id.country", "ageGroup": "$_id.ageGroup", "topGenre": 1, "averageRating": 1, "ratingCount": 1}},
        {"$sort": {"country": 1, "ageGroup": 1}},
    ]))

    q5 = list(database.ratings.aggregate([
        {"$match": {"movieSnapshot.genres.genreName": genre_name}},
        {"$facet": {
            "detail": [{"$group": {"_id": {"country": "$userSnapshot.country", "ageGroup": "$userSnapshot.ageGroup"}, "ratingCount": {"$sum": 1}, "averageRating": {"$avg": "$rating"}}}, {"$project": {"_id": 0, "level": "AGE_GROUP", "sortCountry": "$_id.country", "sortOrder": {"$literal": 1}, "country": "$_id.country", "ageGroup": "$_id.ageGroup", "ratingCount": 1, "averageRating": {"$round": ["$averageRating", 4]}}}],
            "countrySubtotal": [{"$group": {"_id": "$userSnapshot.country", "ratingCount": {"$sum": 1}, "averageRating": {"$avg": "$rating"}}}, {"$project": {"_id": 0, "level": "COUNTRY_SUBTOTAL", "sortCountry": "$_id", "sortOrder": {"$literal": 2}, "country": "$_id", "ageGroup": None, "ratingCount": 1, "averageRating": {"$round": ["$averageRating", 4]}}}],
            "grandTotal": [{"$group": {"_id": None, "ratingCount": {"$sum": 1}, "averageRating": {"$avg": "$rating"}}}, {"$project": {"_id": 0, "level": "GRAND_TOTAL", "sortCountry": "~~~~", "sortOrder": {"$literal": 3}, "country": None, "ageGroup": None, "ratingCount": 1, "averageRating": {"$round": ["$averageRating", 4]}}}],
        }},
        {"$project": {"rows": {"$concatArrays": ["$detail", "$countrySubtotal", "$grandTotal"]}}},
        {"$unwind": "$rows"}, {"$replaceWith": "$rows"},
        {"$sort": {"sortCountry": 1, "sortOrder": 1, "ageGroup": 1}},
        {"$unset": ["sortCountry", "sortOrder"]},
    ], allowDiskUse=True))

    top_genres = [row["_id"] for row in database.movies.aggregate([
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres.genreName", "totalRevenue": {"$sum": "$revenue"}}},
        {"$sort": {"totalRevenue": -1}}, {"$limit": 5},
    ])]
    q6 = list(database.companyGenreStats.aggregate([
        {"$match": {"genreName": {"$in": top_genres}}},
        {"$group": {"_id": "$companyId", "companyName": {"$first": "$companyName"}, "genreStats": {"$push": {"k": "$genreName", "v": {"ratio": "$overallRevenueBudgetRatio", "movieCount": "$movieCount", "totalBudget": "$totalBudget"}}}}},
        {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
        {"$set": {"company": {"$first": "$company"}}},
        {"$match": {"company.companyStats.totalRevenue": {"$gt": 1_000_000_000}, "company.companyStats.totalBudget": {"$gt": 0}}},
        {"$project": {"_id": 0, "companyName": 1, "genreStats": {"$arrayToObject": "$genreStats"}, "overallRevenueBudgetRatio": {"$round": ["$company.companyStats.revenueBudgetRatio", 4]}}},
        {"$sort": {"overallRevenueBudgetRatio": -1}}, {"$limit": 5},
    ], allowDiskUse=True))

    return q1, q2, q3, q4, q5, top_genres, q6


def render_report(data, database_name, person_name, limit, minimum_ratings, genre_name):
    q1, q2, q3, q4, q5, top_genres, q6 = data
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    person = q2[0] if q2 else {"personName": person_name, "movies": [], "totalRevenue": 0}
    movie_rows = [{"title": movie["title"], "roles": ", ".join(movie["roles"]), "revenue": number(movie["revenue"])} for movie in person["movies"]]
    grand_total = next((row for row in q5 if row["level"] == "GRAND_TOTAL"), {"ratingCount": 0, "averageRating": 0})

    q4_genres = list(dict.fromkeys(row["topGenre"] for row in q4))
    q4_palette = ["#d97706", "#0284c7", "#059669", "#dc2626", "#7c3aed", "#db2777", "#4f46e5", "#0f766e"]
    q4_genre_colors = {genre: q4_palette[index % len(q4_palette)] for index, genre in enumerate(q4_genres)}
    q4_body = []
    previous_country = None
    country_group = -1
    for row in q4:
        is_group_start = row["country"] != previous_country
        if is_group_start:
            country_group += 1
        row_classes = [f"country-band-{country_group % 2}"]
        if is_group_start:
            row_classes.append("country-start")
        q4_body.append(
            f'<tr class="{" ".join(row_classes)}"><td>{escape(row["country"])}</td>'
            f'<td>{escape(row["ageGroup"])}</td>'
            f'<td><span class="genre-badge" style="--genre-color:{q4_genre_colors[row["topGenre"]]}">{escape(row["topGenre"])}</span></td>'
            f'<td>{number(row["averageRating"], 4)}</td><td>{number(row["ratingCount"])}</td></tr>'
        )
        previous_country = row["country"]
    q4_body = "".join(q4_body)
    q5_body = "".join(
        f'<tr class="{row["level"].lower().replace("_", "-")}">'
        f'<td>{escape(row["level"].replace("_", " ").title())}</td>'
        f'<td>{escape(row.get("country") or "All countries")}</td>'
        f'<td>{escape(row.get("ageGroup") or ("Subtotal" if row["level"] == "COUNTRY_SUBTOTAL" else "All age groups"))}</td>'
        f'<td>{number(row["ratingCount"])}</td>'
        f'<td>{number(row["averageRating"], 4)}</td></tr>'
        for row in q5
    )

    genre_colors = ["#d97706", "#0284c7", "#059669", "#dc2626", "#7c3aed"]
    genre_styles = {genre: genre_colors[index % len(genre_colors)] for index, genre in enumerate(top_genres)}
    heatmap_headers = "".join(
        f'<th class="genre-heading" style="--genre-color:{genre_styles[genre]}">{escape(genre)}</th>'
        for genre in top_genres
    )
    heatmap_rows = []
    for company in q6:
        cells = []
        for genre in top_genres:
            stats = company["genreStats"].get(genre)
            if stats is None:
                cells.append('<td class="na">No movies</td>')
            elif stats["totalBudget"] <= 0:
                cells.append('<td class="na">Missing budget</td>')
            else:
                ratio = stats["ratio"]
                intensity = min(ratio / 20, 1)
                cells.append(f'<td class="heat" style="--genre-color:{genre_styles[genre]};--intensity:{intensity:.3f}">{number(ratio, 4)}</td>')
        heatmap_rows.append(f'<tr><td class="company">{escape(company["companyName"])}</td><td>{number(company["overallRevenueBudgetRatio"], 4)}</td>{"".join(cells)}</tr>')

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Movie analytics report</title>
  <style>
    :root {{ color-scheme: light dark; --ink:#18181b; --muted:#71717a; --line:rgba(24,24,27,.1); --paper:#fff; --well:#fafafa; --accent:#b45309; --accent-soft:#fef3c7; --green:#047857; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.55 Inter, ui-sans-serif, system-ui, sans-serif; }}
    header, main, footer {{ width:min(1180px, calc(100% - 32px)); margin-inline:auto; }}
    header {{ padding:64px 0 40px; border-bottom:1px solid var(--line); }}
    .eyebrow {{ margin:0 0 12px; color:var(--accent); font:600 12px/1.4 ui-monospace, monospace; letter-spacing:.12em; text-transform:uppercase; }}
    h1, h2, h3 {{ margin:0; font-weight:600; letter-spacing:-.025em; text-wrap:balance; }}
    h1 {{ max-width:18ch; font-size:clamp(38px,7vw,72px); }}
    h2 {{ font-size:clamp(26px,4vw,40px); }}
    h3 {{ font-size:20px; }}
    p {{ text-wrap:pretty; }}
    .lede {{ max-width:65ch; margin:18px 0 0; color:var(--muted); font-size:17px; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:10px 24px; margin-top:28px; color:var(--muted); }}
    nav {{ position:sticky; top:0; z-index:10; overflow:auto; background:color-mix(in srgb, var(--paper) 92%, transparent); border-bottom:1px solid var(--line); backdrop-filter:blur(12px); }}
    nav div {{ display:flex; width:min(1180px, calc(100% - 32px)); margin:auto; }}
    nav a {{ flex:0 0 auto; padding:14px 16px; color:var(--muted); text-decoration:none; }}
    nav a:hover {{ color:var(--ink); }}
    main {{ padding-bottom:80px; }}
    section {{ padding:64px 0; border-bottom:1px solid var(--line); scroll-margin-top:48px; }}
    .section-head {{ display:flex; align-items:end; justify-content:space-between; gap:24px; margin-bottom:32px; }}
    .section-head p {{ max-width:58ch; margin:8px 0 0; color:var(--muted); }}
    .query-label {{ flex:0 0 auto; color:var(--muted); font-family:ui-monospace, monospace; }}
    .stats {{ container-type:inline-size; display:grid; grid-template-columns:repeat(4,1fr); margin-top:40px; }}
    .stat {{ min-width:0; padding:0 24px; border-left:1px solid var(--line); }}
    .stat:first-child {{ padding-left:0; border:0; }}
    .stat span {{ display:block; overflow:hidden; color:var(--muted); text-overflow:ellipsis; white-space:nowrap; }}
    .stat strong {{ display:block; margin-top:6px; font-size:30px; font-weight:600; letter-spacing:-.03em; }}
    .split {{ container-type:inline-size; display:grid; grid-template-columns:1fr 1fr; gap:48px; }}
    .panel h3 {{ margin-bottom:20px; }}
    .bar-row + .bar-row {{ margin-top:16px; }}
    .bar-meta {{ display:flex; justify-content:space-between; gap:16px; margin-bottom:6px; }}
    .bar-meta span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .bar-meta strong {{ color:var(--muted); font-weight:500; font-variant-numeric:tabular-nums; }}
    .bar-track {{ height:8px; overflow:hidden; background:var(--accent-soft); border-radius:999px; }}
    .bar-track span {{ display:block; height:100%; background:var(--accent); border-radius:inherit; }}
    .table-scroll {{ width:100%; overflow-x:auto; white-space:nowrap; }}
    table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }}
    th {{ padding:12px 14px; color:var(--muted); font-weight:500; text-align:left; white-space:nowrap; }}
    td {{ padding:13px 14px; border-top:1px solid var(--line); }}
    tbody tr:hover {{ background:var(--well); }}
    th.genre-heading {{ box-shadow:inset 0 -3px var(--genre-color); color:var(--ink); }}
    td.heat {{ background:color-mix(in srgb, var(--genre-color) calc(10% + var(--intensity) * 30%), transparent); font-weight:600; }}
    td.na {{ color:var(--muted); font-style:italic; }}
    td.company {{ font-weight:600; }}
    tr.country-band-1 td {{ background:color-mix(in srgb, var(--ink) 3%, transparent); }}
    tr.country-start td {{ border-top:2px solid color-mix(in srgb, var(--ink) 18%, transparent); }}
    tr.country-start:first-child td {{ border-top:1px solid var(--line); }}
    .genre-badge {{ display:inline-block; padding:3px 9px; background:color-mix(in srgb, var(--genre-color) 14%, transparent); border-left:3px solid var(--genre-color); border-radius:4px; color:var(--ink); font-weight:600; }}
    tr.country-subtotal td {{ background:color-mix(in srgb, var(--accent) 9%, transparent); border-top-color:color-mix(in srgb, var(--accent) 35%, transparent); font-weight:600; }}
    tr.grand-total td {{ background:color-mix(in srgb, var(--green) 13%, transparent); border-top:2px solid color-mix(in srgb, var(--green) 55%, transparent); font-weight:700; }}
    tr.age-group td:first-child {{ color:var(--muted); }}
    .note {{ margin:24px 0 0; padding:18px 20px; background:var(--well); color:var(--muted); border-left:3px solid var(--accent); }}
    footer {{ padding:28px 0 48px; color:var(--muted); }}
    @container (max-width:700px) {{ .stats, .split {{ grid-template-columns:1fr; }} .stat {{ padding:18px 0; border-left:0; border-top:1px solid var(--line); }} .stat:first-child {{ padding-top:0; }} }}
    @media (max-width:700px) {{ header {{ padding-top:40px; }} section {{ padding:48px 0; }} .section-head {{ align-items:start; flex-direction:column; }} .split {{ grid-template-columns:1fr; }} body {{ font-size:16px; }} }}
    @media (prefers-color-scheme:dark) {{ :root {{ --ink:#f4f4f5; --muted:#a1a1aa; --line:rgba(255,255,255,.1); --paper:#09090b; --well:#18181b; --accent:#f59e0b; --accent-soft:#292524; --green:#34d399; }} nav {{ background:rgba(9,9,11,.9); }} }}
    @media print {{ nav {{ display:none; }} header, main, footer {{ width:100%; }} section {{ break-inside:avoid; }} }}
  </style>
</head>
<body>
  <header>
    <p class="eyebrow">MongoDB analytics / generated report</p>
    <h1>Movie data, made visible.</h1>
    <p class="lede">Six query-first analyses covering ratings, careers, demographics and production-company performance in the {escape(database_name)} database.</p>
    <div class="meta"><span>Generated {generated_at}</span><span>Source: MongoDB</span><span>Offline HTML</span></div>
    <div class="stats">
      <div class="stat"><span>Top Action rating</span><strong>{number(q1[0]['averageRating'] if q1 else 0, 2)}</strong></div>
      <div class="stat"><span>{escape(person_name)} movies</span><strong>{len(person['movies'])}</strong></div>
      <div class="stat"><span>{escape(genre_name)} ratings</span><strong>{number(grand_total['ratingCount'])}</strong></div>
      <div class="stat"><span>Top company ratio</span><strong>{number(q6[0]['overallRevenueBudgetRatio'] if q6 else 0, 2)}</strong></div>
    </div>
  </header>
  <nav><div>{''.join(f'<a href="#q{i}">Q{i}</a>' for i in range(1, 7))}</div></nav>
  <main>
    <section id="q1">
      <div class="section-head"><div><h2>Top Action movies</h2><p>Average MovieLens rating for Action films with at least 50 ratings.</p></div><span class="query-label">Q1</span></div>
      {horizontal_bars(q1, 'title', 'averageRating', 5)}
    </section>
    <section id="q2">
      <div class="section-head"><div><h2>{escape(person['personName'])}</h2><p>Actor and director credits with the total revenue of associated films.</p></div><span class="query-label">Q2</span></div>
      <div class="stats"><div class="stat"><span>Movies</span><strong>{len(person['movies'])}</strong></div><div class="stat"><span>Total revenue</span><strong>${number(person['totalRevenue'] / 1_000_000, 1)}M</strong></div></div>
      <div style="margin-top:32px">{table([('Movie','title'),('Roles','roles'),('Revenue (USD)','revenue')], movie_rows)}</div>
    </section>
    <section id="q3">
      <div class="section-head"><div><h2>Most active people</h2><p>Separate rankings for actors and directors, limited to {limit} people per role.</p></div><span class="query-label">Q3</span></div>
      <div class="split"><div class="panel"><h3>Actors</h3>{horizontal_bars(q3['actors'], 'personName', 'movieCount', formatter=lambda value: f'{value} films')}</div><div class="panel"><h3>Directors</h3>{horizontal_bars(q3['directors'], 'personName', 'movieCount', formatter=lambda value: f'{value} films')}</div></div>
    </section>
    <section id="q4">
      <div class="section-head"><div><h2>Top genre by demographic</h2><p>The highest-rated genre for each country and age group, requiring at least {minimum_ratings} ratings.</p></div><span class="query-label">Q4</span></div>
      <div class="table-scroll"><table><thead><tr><th>Country</th><th>Age group</th><th>Top genre</th><th>Average rating</th><th>Ratings</th></tr></thead><tbody>{q4_body}</tbody></table></div>
    </section>
    <section id="q5">
      <div class="section-head"><div><h2>{escape(genre_name)} rating report</h2><p>Country and age-group detail followed by country subtotals and a grand total.</p></div><span class="query-label">Q5</span></div>
      <div class="table-scroll"><table><thead><tr><th>Level</th><th>Country</th><th>Age group</th><th>Ratings</th><th>Average rating</th></tr></thead><tbody>{q5_body}</tbody></table></div>
    </section>
    <section id="q6">
      <div class="section-head"><div><h2>Company investment view</h2><p>Revenue-to-budget ratios across the five genres with the highest aggregate revenue.</p></div><span class="query-label">Q6</span></div>
      <div class="table-scroll"><table><thead><tr><th>Company</th><th>Overall ratio</th>{heatmap_headers}</tr></thead><tbody>{''.join(heatmap_rows)}</tbody></table></div>
      <p class="note"><strong>N/A meanings.</strong> “No movies” means the company has no film in that genre. “Missing budget” means films exist, but their source budget is zero, so the ratio cannot be calculated.</p>
    </section>
  </main>
  <footer>Generated from {escape(database_name)}. Rebuild with <code>make visualize</code>.</footer>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate an offline HTML report for movie analytics.")
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--database", default=os.getenv("MONGODB_DATABASE", "movie_analytics"))
    parser.add_argument("--output", type=Path, default=Path("reports/movie_analytics.html"))
    parser.add_argument("--person-name", default=os.getenv("PERSON_NAME", "Christopher Nolan"))
    parser.add_argument("--limit", type=int, default=int(os.getenv("LIMIT", "10")))
    parser.add_argument("--minimum-ratings", type=int, default=int(os.getenv("MIN_RATINGS", "20")))
    parser.add_argument("--genre-name", default=os.getenv("GENRE_NAME", "Action"))
    parser.add_argument("--open", action="store_true", help="Open the generated report in the default browser.")
    args = parser.parse_args()

    with MongoClient(args.uri) as client:
        database = client[args.database]
        data = collect_data(database, args.person_name, args.limit, args.minimum_ratings, args.genre_name)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(data, args.database, args.person_name, args.limit, args.minimum_ratings, args.genre_name), encoding="utf-8")
    print(f"HTML report generated: {args.output.resolve()}")
    if args.open:
        webbrowser.open(args.output.resolve().as_uri())


if __name__ == "__main__":
    main()
