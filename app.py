from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

OSRM_BASE = "http://router.project-osrm.org/table/v1/driving"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"


def init_session_cache():
    if "geocode_cache" not in st.session_state:
        st.session_state.geocode_cache = {}
    if "drive_cache" not in st.session_state:
        st.session_state.drive_cache = {}
    if "uploaded_list" not in st.session_state:
        st.session_state.uploaded_list = None  # (name, records) or None


def round_coord(v: float) -> float:
    # snap coords to ~11m grid so nearby queries share cache entries
    return round(v, 4)


def origin_key(lat: float, lon: float) -> str:
    return f"osrm:{round_coord(lat)},{round_coord(lon)}"


def cached_addresses() -> list[str]:
    return sorted(st.session_state.geocode_cache.keys())


@st.cache_data
def available_lists() -> list[str]:
    return sorted(p.stem for p in DATA_DIR.glob("*.csv"))


@st.cache_data
def load_locations(list_name: str) -> list[dict]:
    path = DATA_DIR / f"{list_name}.csv"
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def geocode(address: str):
    # look up an address string and return its (lat, lon) via Nominatim, caching the result
    cache = st.session_state.geocode_cache
    if address in cache:
        return cache[address]

    resp = requests.get(
        NOMINATIM_BASE,
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "LocationRanker/1.0"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None, None
    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    cache[address] = (lat, lon)
    return lat, lon


def get_drive_times(origin_lat, origin_lon, locations):
    key = origin_key(origin_lat, origin_lon)
    cache = st.session_state.drive_cache
    # only return a hit if every location in the list is cached
    if key in cache and len(cache[key]) == len(locations):
        return cache[key]

    # build a single OSRM table request: origin at index 0, locations at 1..n
    coords = f"{origin_lon},{origin_lat}"
    for loc in locations:
        coords += f";{loc['lon']},{loc['lat']}"
    destinations = ";".join(str(i + 1) for i in range(len(locations)))
    url = f"{OSRM_BASE}/{coords}?sources=0&destinations={destinations}&annotations=duration"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    durations = resp.json()["durations"][0]

    result = {loc["name"]: durations[i] for i, loc in enumerate(locations)}
    cache[key] = result
    return result


def fmt_duration(seconds, factor=1.0):
    if seconds is None:
        return "N/A"
    m = int((seconds * factor) // 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def show_results(origin_lat, origin_lon, times, locations, factor=1.0):
    rows = []
    for loc in locations:
        d = times.get(loc["name"])
        rows.append(
            {
                "Location": loc["name"],
                "Drive Time": fmt_duration(d, factor),
                "_seconds": (d * factor) if d is not None else float("inf"),
                "lat": loc["lat"],
                "lon": loc["lon"],
                "Coordinates": f"{loc['lat']:.5f}, {loc['lon']:.5f}",
            }
        )

    df = pd.DataFrame(rows).sort_values("_seconds").reset_index(drop=True)
    df.index += 1

    tab1, tab2, tab3 = st.tabs(["Ranked List", "Map", "Drive Time Distribution"])

    with tab1:
        st.dataframe(df[["Location", "Drive Time", "Coordinates"]], use_container_width=True)

    with tab2:
        origin_df = pd.DataFrame([{
            "lat": origin_lat, "lon": origin_lon,
            "name": "Origin", "drive_time": "—",
            "color": [220, 50, 50],
        }])
        points_df = pd.DataFrame([{
            "lat": r["lat"], "lon": r["lon"],
            "name": r["Location"], "drive_time": r["Drive Time"],
            "color": [30, 120, 200],
        } for _, r in df.iterrows()])
        all_points = pd.concat([origin_df, points_df], ignore_index=True)

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=all_points,
            get_position=["lon", "lat"],
            get_fill_color="color",
            get_radius=1500,
            pickable=True,
        )
        view = pdk.ViewState(
            latitude=all_points["lat"].mean(),
            longitude=all_points["lon"].mean(),
            zoom=7,
        )
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"text": "{name}\n{drive_time}"},
            ),
            use_container_width=True,
        )

    with tab3:
        hist_df = df[df["_seconds"] < float("inf")].copy()
        hist_df["minutes"] = (hist_df["_seconds"] / 60).round().astype(int)
        chart = (
            alt.Chart(hist_df)
            .mark_bar()
            .encode(
                x=alt.X("minutes:Q", bin=alt.Bin(step=15), title="Drive time (minutes)"),
                y=alt.Y("count()", title="Number of locations"),
                tooltip=[alt.Tooltip("count()", title="Count")],
            )
            .properties(height=350)
        )
        st.altair_chart(chart, use_container_width=True)


st.set_page_config(page_title="Location Ranker", layout="wide")
st.title("Location Ranker")
st.caption("Ranks a list of locations by estimated drive time from any starting point.")

init_session_cache()
lists = available_lists()

with st.sidebar:
    st.header("Settings")

    uploaded_file = st.file_uploader("Upload your own CSV", type="csv")
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            missing = [c for c in ("name", "lat", "lon") if c not in df.columns]
            if missing:
                st.error(f"CSV missing columns: {', '.join(missing)}")
            else:
                st.session_state.uploaded_list = (uploaded_file.name.removesuffix(".csv"), df.to_dict(orient="records"))
                st.success(f"Loaded {len(df)} locations from {uploaded_file.name}")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    all_lists = lists.copy()
    if st.session_state.uploaded_list:
        all_lists = [st.session_state.uploaded_list[0]] + all_lists

    if not all_lists:
        st.error("No location lists found. Upload a CSV or add one to the data/ folder.")
        st.stop()

    list_name = st.selectbox("Location list", options=all_lists)
    if st.session_state.uploaded_list and list_name == st.session_state.uploaded_list[0]:
        locations = st.session_state.uploaded_list[1]
    else:
        locations = load_locations(list_name)
    st.caption(f"{len(locations)} locations loaded")

    st.divider()

    factor = st.slider(
        "Drive time correction factor",
        min_value=0.70,
        max_value=1.10,
        value=0.85,
        step=0.01,
        help=(
            "OSRM tends to overestimate drive times on rural roads by ~15–20% "
            "vs Google Maps. 0.85 is a good starting point."
        ),
    )
    st.caption(
        f"OSRM times × **{factor:.2f}** before display. "
        "Changing this is instant — raw times stay cached."
    )

past = cached_addresses()

col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
with col1:
    raw_input = st.text_input(
        "Enter a starting location",
        placeholder="e.g. 123 Main St, Concord NH  or  43.2081,-71.5376",
    )
with col2:
    go = st.button("Rank Locations", type="primary", use_container_width=True)

use_history = False
history_choice = None
if past:
    st.caption("Or choose a recent search:")
    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1:
        history_choice = st.selectbox(
            "Recent searches",
            options=past,
            label_visibility="collapsed",
        )
    with col2:
        use_history = st.button("Use This", use_container_width=True)

active_query = None
if use_history and history_choice:
    active_query = history_choice
elif go and raw_input.strip():
    active_query = raw_input.strip()
elif go:
    st.warning("Enter a starting location above.")

if active_query:
    origin_lat = origin_lon = None

    # try parsing as raw lat,lon before hitting the geocoder
    parts = active_query.replace(" ", "").split(",")
    if len(parts) == 2:
        try:
            origin_lat, origin_lon = float(parts[0]), float(parts[1])
        except ValueError:
            pass

    if origin_lat is None:
        with st.spinner("Geocoding address…"):
            origin_lat, origin_lon = geocode(active_query)
        if origin_lat is None:
            st.error("Could not geocode that address. Try being more specific or use lat,lon.")
            st.stop()

    st.success(f"Origin: {origin_lat:.5f}, {origin_lon:.5f}")

    with st.spinner("Fetching drive times…"):
        times = get_drive_times(origin_lat, origin_lon, locations)

    show_results(origin_lat, origin_lon, times, locations, factor)
