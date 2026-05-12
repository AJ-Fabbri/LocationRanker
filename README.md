# Location Ranker

Ranks a list of named locations by estimated drive time from any starting address or coordinates. Includes the ranked list, a map, and a histogram of drive time distribution.

Built with Streamlit. No API keys required.

The included dataset is the [NH 52 With a View](https://www.trailspotting.com/p/nh52.html) trailhead list, but the app works with any CSV of named locations.

---

## How it works

1. Drop one or more CSV files into the `data/` folder — each becomes a selectable list in the app.
2. Enter a starting address or `lat, lon` coordinates.
3. The app returns every location ranked by estimated drive time.

Drive times come from [OSRM](http://project-osrm.org/) (free, no account needed) and are cached locally so repeated queries are instant. A correction factor slider lets you calibrate results against your own experience.

---

## CSV format

Each file in `data/` must have exactly these three columns:

```
name,lat,lon
Some Location,44.217,-71.411
Another Place,43.982,-71.203
```

- `name` — display name (any string)
- `lat` / `lon` — decimal degrees (WGS 84) — addresses are not supported here

The filename becomes the list name shown in the app. Coordinates for each location must be looked up in advance (Google Maps, Google Earth, etc.).

---

## Running the app

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## Notes

- Drive time estimates may be 10–20% higher than Google Maps on rural roads. Use the correction factor slider to tune.
- All routing results are cached in `cache.db` (excluded from version control).
- The `data/` folder is the only thing you need to version control alongside `app.py`.
