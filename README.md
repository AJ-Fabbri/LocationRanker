# Location Ranker

Ranks a list of named locations by estimated drive time from any starting address or coordinates. Includes the ranked list, a map, and a histogram of drive time distribution.

Built with Streamlit. No API keys required.

The main included dataset the [NH 52 With a View](https://www.trailspotting.com/p/nh52.html) trailhead list, but the app works with any CSV of named locations.
- I recently added the 48 NH 4000-foot peaks, but I don't have trailhead locations in one dataset, so this is somewhat less accurate because the backend attempts to route to the peaks. The rough order of which mountains are closest still works.

---

## How it works

1. Drop one or more CSV files into the `data/` folder — each becomes a selectable list in the app. Or upload your own CSV directly in the sidebar.
2. Enter a starting address or `lat, lon` coordinates.
3. The app returns every location ranked by estimated drive time.

Drive times come from [OSRM](http://project-osrm.org/) (free, no account needed) and are cached per session so repeated queries are instant. A correction factor slider lets you calibrate results against your own experience.

### Uploading your own list

Use the **Upload your own CSV** button in the sidebar to load a custom location list without touching the `data/` folder. The file must follow the same three-column format described below.

Uploaded files and search history are session-only — they exist only in your browser tab and are never stored on the server or shared with other users. Closing or refreshing the tab clears everything.

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
- All routing results and search history are cached in memory for the duration of your session only — nothing is written to disk or shared between users.
- The `data/` folder is the only thing you need to version control alongside `app.py`.
