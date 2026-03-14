from __future__ import annotations

from datetime import datetime
from io import StringIO
from urllib.parse import quote_plus

import folium
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium

from smartpark.client import (
    API_BASE_URL,
    add_camera,
    add_lot,
    create_alert,
    healthcheck,
    load_alerts,
    load_analytics,
    load_cameras,
    load_lots,
    update_spot_status,
)


st.set_page_config(
    page_title="SmartPark AI",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)


DRIVER_PAGES = ["Find Parking"]
OWNER_PAGES = ["Admin", "Analytics", "Settings", "Alerts Log"]


def inject_styles(theme_mode: str) -> None:
    dark = theme_mode == "Night"
    palette = {
        "bg": "#08131d" if dark else "#efe8da",
        "bg2": "#0f2230" if dark else "#f8f3e9",
        "panel": "rgba(12, 24, 36, 0.82)" if dark else "rgba(255, 252, 246, 0.86)",
        "panel_strong": "rgba(15, 34, 48, 0.95)" if dark else "rgba(255, 255, 255, 0.9)",
        "text": "#eef6f7" if dark else "#16302b",
        "muted": "#91a9b4" if dark else "#56716a",
        "accent": "#18b67e",
        "warm": "#ffc857",
        "danger": "#f05f57",
        "border": "rgba(255,255,255,0.08)" if dark else "rgba(22,48,43,0.08)",
    }
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: "Avenir Next", "Trebuchet MS", sans-serif;
            color: {palette["text"]};
        }}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(255, 200, 87, 0.14), transparent 28%),
                radial-gradient(circle at top right, rgba(24, 182, 126, 0.16), transparent 24%),
                linear-gradient(180deg, {palette["bg2"]} 0%, {palette["bg"]} 100%);
        }}
        .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
        }}
        .top-shell {{
            padding: 1rem 1.15rem;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(10, 34, 57, 0.96), rgba(21, 88, 122, 0.85));
            color: #f6f7f2;
            box-shadow: 0 22px 50px rgba(10, 34, 57, 0.22);
            margin-bottom: 1rem;
        }}
        .top-grid {{
            display: grid;
            grid-template-columns: 2fr 1.2fr 1fr 1fr 1fr;
            gap: 0.8rem;
            align-items: center;
        }}
        .top-brand {{
            font-size: 1.9rem;
            font-weight: 700;
            line-height: 1.05;
        }}
        .top-kicker {{
            color: rgba(246, 247, 242, 0.72);
            font-size: 0.88rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .top-stat {{
            padding: 0.85rem 1rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.09);
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .top-stat-label {{
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: rgba(246,247,242,0.68);
        }}
        .top-stat-value {{
            font-size: 1.45rem;
            font-weight: 700;
            margin-top: 0.2rem;
        }}
        .shell {{
            padding: 1rem;
            border-radius: 24px;
            background: {palette["panel"]};
            border: 1px solid {palette["border"]};
            box-shadow: 0 16px 38px rgba(0, 0, 0, 0.12);
            backdrop-filter: blur(10px);
        }}
        .subshell {{
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: {palette["panel_strong"]};
            border: 1px solid {palette["border"]};
        }}
        .search-hero {{
            padding: 1.15rem;
            border-radius: 26px;
            background: linear-gradient(145deg, rgba(255,255,255,0.98), rgba(247,250,252,0.92));
            color: #152a24;
            border: 1px solid rgba(22,48,43,0.08);
            box-shadow: 0 20px 40px rgba(7, 24, 39, 0.08);
            margin-bottom: 1rem;
        }}
        .search-title {{
            font-size: 2.1rem;
            font-weight: 700;
            line-height: 1.05;
            margin-bottom: 0.3rem;
        }}
        .search-subtitle {{
            color: #537069;
            font-size: 1rem;
            max-width: 44rem;
        }}
        .callout-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.75rem;
            margin-top: 1rem;
        }}
        .callout {{
            background: rgba(21, 42, 36, 0.04);
            border: 1px solid rgba(21, 42, 36, 0.08);
            border-radius: 18px;
            padding: 0.85rem 0.95rem;
        }}
        .finder-toolbar {{
            padding: 0.85rem 1rem;
            border-radius: 20px;
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(22,48,43,0.08);
            margin-bottom: 1rem;
        }}
        .callout strong {{
            display: block;
            font-size: 1rem;
            margin-bottom: 0.2rem;
        }}
        .metric-card {{
            padding: 1rem;
            border-radius: 20px;
            background: {palette["panel_strong"]};
            border: 1px solid {palette["border"]};
            min-height: 118px;
        }}
        .metric-label {{
            font-size: 0.82rem;
            color: {palette["muted"]};
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.35rem;
            color: {palette["text"]};
        }}
        .metric-note {{
            margin-top: 0.25rem;
            color: {palette["muted"]};
            font-size: 0.92rem;
        }}
        .banner {{
            padding: 0.85rem 1rem;
            border-radius: 18px;
            background: rgba(24, 182, 126, 0.16);
            color: {palette["text"]};
            border: 1px solid rgba(24, 182, 126, 0.28);
            margin-bottom: 0.8rem;
        }}
        .mini-chip {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            margin-right: 0.4rem;
            font-size: 0.78rem;
            background: rgba(255,255,255,0.08);
            border: 1px solid {palette["border"]};
            color: {palette["muted"]};
        }}
        .spot-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
            gap: 0.8rem;
        }}
        .spot-card {{
            position: relative;
            border-radius: 18px;
            padding: 0.95rem;
            color: white;
            overflow: hidden;
            min-height: 132px;
        }}
        .spot-card.free {{
            background: linear-gradient(135deg, #14b86f, #0d8f59);
            box-shadow: 0 0 0 rgba(20, 184, 111, 0.35);
            animation: pulse 2.2s infinite;
        }}
        .spot-card.occupied {{
            background: linear-gradient(135deg, #f05f57, #d94840);
        }}
        .spot-card p, .spot-card h4 {{
            margin: 0;
        }}
        .spot-card .meta {{
            color: rgba(255,255,255,0.82);
            margin-top: 0.3rem;
            font-size: 0.9rem;
        }}
        .badge {{
            display: inline-block;
            padding: 0.18rem 0.45rem;
            border-radius: 999px;
            font-size: 0.72rem;
            margin-top: 0.45rem;
            background: rgba(255,255,255,0.16);
        }}
        .list-card {{
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: {palette["panel_strong"]};
            border: 1px solid {palette["border"]};
            margin-bottom: 0.75rem;
        }}
        .alert-critical {{ border-left: 4px solid #f05f57; }}
        .alert-warning {{ border-left: 4px solid #ffc857; }}
        .alert-info {{ border-left: 4px solid #54c7ec; }}
        .recommend-card {{
            padding: 1rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #0c8256, #16ad72);
            color: white;
            box-shadow: 0 20px 38px rgba(12, 130, 86, 0.24);
        }}
        .recommend-card h3, .recommend-card p {{
            margin: 0;
        }}
        .recommend-meta {{
            margin-top: 0.65rem;
            color: rgba(255,255,255,0.88);
        }}
        .soft-panel {{
            padding: 0.95rem;
            border-radius: 20px;
            background: rgba(255,255,255,0.62);
            border: 1px solid rgba(22,48,43,0.08);
            color: #16302b;
        }}
        .result-list {{
            display: grid;
            gap: 0.85rem;
        }}
        .result-card {{
            padding: 1rem;
            border-radius: 20px;
            background: rgba(255,255,255,0.92);
            border: 1px solid rgba(22,48,43,0.08);
            box-shadow: 0 14px 24px rgba(7, 24, 39, 0.06);
            color: #16302b;
        }}
        .result-card.free {{
            border-left: 5px solid #16ad72;
        }}
        .result-card.occupied {{
            border-left: 5px solid #f05f57;
            opacity: 0.88;
        }}
        .result-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.75rem;
        }}
        .result-title {{
            font-size: 1.05rem;
            font-weight: 700;
        }}
        .result-subtitle {{
            color: #56716a;
            margin-top: 0.18rem;
            font-size: 0.92rem;
        }}
        .status-pill {{
            display: inline-block;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .status-pill.free {{
            background: rgba(22, 173, 114, 0.12);
            color: #0d8f59;
        }}
        .status-pill.occupied {{
            background: rgba(240, 95, 87, 0.12);
            color: #c7463f;
        }}
        .result-chip-row {{
            margin-top: 0.7rem;
        }}
        .result-chip {{
            display: inline-block;
            margin-right: 0.42rem;
            margin-bottom: 0.42rem;
            padding: 0.28rem 0.6rem;
            border-radius: 999px;
            font-size: 0.78rem;
            color: #45625b;
            background: rgba(21, 42, 36, 0.06);
        }}
        .driver-note {{
            margin-top: 0.65rem;
            color: #56716a;
            font-size: 0.92rem;
        }}
        .sticky-cta {{
            position: fixed;
            left: 50%;
            transform: translateX(-50%);
            bottom: 18px;
            width: min(720px, calc(100vw - 28px));
            z-index: 999;
            border-radius: 22px;
            background: rgba(12, 130, 86, 0.96);
            color: white;
            box-shadow: 0 18px 36px rgba(12, 130, 86, 0.28);
            border: 1px solid rgba(255,255,255,0.14);
            overflow: hidden;
        }}
        .sticky-cta a {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            text-decoration: none;
            color: white;
            padding: 1rem 1.1rem;
            font-weight: 700;
        }}
        .sticky-cta small {{
            display: block;
            color: rgba(255,255,255,0.82);
            font-weight: 500;
            margin-top: 0.15rem;
        }}
        .owner-badge {{
            display: inline-block;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.75rem;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.08);
            color: #91a9b4;
        }}
        .mini-stat {{
            padding: 0.85rem 0.95rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.88);
            border: 1px solid rgba(22,48,43,0.08);
            color: #16302b;
            min-height: 92px;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(20, 184, 111, 0.4); }}
            70% {{ transform: scale(1.01); box-shadow: 0 0 0 14px rgba(20, 184, 111, 0.0); }}
            100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(20, 184, 111, 0.0); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def navigation_url(spot: dict) -> str | None:
    latitude = spot.get("lat")
    longitude = spot.get("lng")
    if latitude is None or longitude is None:
        return None
    destination = quote_plus(f"{latitude},{longitude}")
    return f"https://www.google.com/maps/dir/?api=1&destination={destination}"


def count_stats(lots: list[dict]) -> dict:
    all_spots = [spot for lot in lots for spot in lot["spots"]]
    free = sum(1 for spot in all_spots if spot["status"] == "free")
    total = len(all_spots)
    occupied = total - free
    return {
        "lots": len(lots),
        "spots": total,
        "free": free,
        "occupied": occupied,
        "occupancy_pct": round((occupied / total) * 100, 1) if total else 0,
    }


def render_top_bar(selected_lot: dict, analytics: dict, refresh_seconds: int) -> None:
    free_count = selected_lot["free_count"]
    total_count = len(selected_lot["spots"])
    occupancy_pct = round(((total_count - free_count) / max(total_count, 1)) * 100, 1)
    st.markdown(
        f"""
        <div class="top-shell">
            <div class="top-grid">
                <div>
                    <div class="top-kicker">Local-first parking command center</div>
                    <div class="top-brand">SmartPark AI Dashboard</div>
                </div>
                <div class="top-stat">
                    <div class="top-stat-label">Lot</div>
                    <div class="top-stat-value" style="font-size:1.05rem;">{selected_lot['name']}</div>
                </div>
                <div class="top-stat">
                    <div class="top-stat-label">Live Free</div>
                    <div class="top-stat-value">{free_count} / {total_count}</div>
                </div>
                <div class="top-stat">
                    <div class="top-stat-label">Occupied</div>
                    <div class="top-stat-value">{occupancy_pct}%</div>
                </div>
                <div class="top-stat">
                    <div class="top-stat-label">Refreshing</div>
                    <div class="top-stat-value">{refresh_seconds}s</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_search_hero(selected_lot: dict, analytics: dict) -> None:
    free_count = selected_lot["free_count"]
    total_count = len(selected_lot["spots"])
    wait = analytics["summary"]["avg_wait_minutes"]
    st.markdown(
        f"""
        <div class="search-hero">
            <div class="search-title">Find the fastest spot, not just any spot.</div>
            <div class="search-subtitle">
                Live parking availability for {selected_lot['name']}. Pick the best space,
                open navigation in one tap, and skip the circling.
            </div>
            <div class="callout-row">
                <div class="callout">
                    <strong>{free_count} spots open now</strong>
                    Updated every few seconds from local cameras.
                </div>
                <div class="callout">
                    <strong>{wait:.1f} min average time to park</strong>
                    Current estimate based on recent turnover.
                </div>
                <div class="callout">
                    <strong>{total_count - free_count} spots occupied</strong>
                    Use filters to find EV, wide, covered, or accessible bays.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_spots(spots: list[dict], preference: str, spot_filter: str) -> list[dict]:
    filtered = spots
    if spot_filter == "EV only":
        filtered = [spot for spot in filtered if spot["spot_type"] == "ev"]
    elif spot_filter == "Wide only":
        filtered = [spot for spot in filtered if spot["width_class"] == "wide"]
    elif spot_filter == "Accessible only":
        filtered = [spot for spot in filtered if spot["spot_type"] == "accessible"]
    elif spot_filter == "Covered only":
        filtered = [spot for spot in filtered if spot["is_covered"]]

    if preference == "Nearest entrance":
        filtered = sorted(filtered, key=lambda spot: spot.get("distance_rank", 999))
    elif preference == "First free":
        filtered = sorted(filtered, key=lambda spot: (spot["status"] != "free", spot.get("distance_rank", 999)))
    elif preference == "Covered first":
        filtered = sorted(filtered, key=lambda spot: (not spot["is_covered"], spot.get("distance_rank", 999)))
    return filtered


def render_outdoor_map(spots: list[dict], center: dict) -> None:
    park_map = folium.Map(
        location=[center["lat"], center["lng"]],
        zoom_start=18,
        control_scale=True,
        tiles="CartoDB positron",
    )
    for spot in spots:
        color = "#18b67e" if spot["status"] == "free" else "#f05f57"
        popup_lines = [
            f"<strong>{spot['label']}</strong>",
            f"Status: {spot['status'].title()}",
            f"Zone: {spot['zone']}",
            f"Type: {spot['spot_type'].title()}",
        ]
        nav_link = navigation_url(spot)
        if nav_link:
            popup_lines.append(f"<a href='{nav_link}' target='_blank'>Navigate Here</a>")
        folium.CircleMarker(
            location=[spot["lat"], spot["lng"]],
            radius=12 if spot["status"] == "free" else 10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=f"{spot['label']} · {spot['status']}",
            popup=folium.Popup("<br>".join(popup_lines), max_width=240),
        ).add_to(park_map)
    st_folium(park_map, width=None, height=560, returned_objects=[])


def render_indoor_grid(spots: list[dict]) -> None:
    cards = []
    for spot in spots:
        cards.append(
            f"""
            <div class="spot-card {spot['status']}">
                <h4>{spot['label']}</h4>
                <p class="meta">{spot['zone']} · LED {spot.get('led_channel', 'n/a')}</p>
                <p class="meta">{spot['status'].title()} · {spot['spot_type'].title()}</p>
                <div class="badge">{spot['width_class'].title()} bay</div>
            </div>
            """
        )
    html(f"<div class='spot-grid'>{''.join(cards)}</div>", height=max(320, ((len(spots) + 2) // 3) * 150))


def fresh_free_spot_banner(selected_lot: dict) -> None:
    previous = st.session_state.get("previous_statuses", {})
    current = {spot["label"]: spot["status"] for spot in selected_lot["spots"]}
    freed = [label for label, status in current.items() if status == "free" and previous.get(label) == "occupied"]
    st.session_state["previous_statuses"] = current
    if freed:
        st.markdown(
            f"<div class='banner'>Spot just freed: <strong>{', '.join(freed[:3])}</strong>. "
            "Share it or send drivers there now.</div>",
            unsafe_allow_html=True,
        )


def build_spot_dataframe(spots: list[dict]) -> pd.DataFrame:
    rows = []
    for spot in spots:
        rows.append(
            {
                "Spot": spot["label"],
                "Zone": spot["zone"],
                "Status": spot["status"].title(),
                "Type": spot["spot_type"].title(),
                "Width": spot["width_class"].title(),
                "Covered": "Yes" if spot["is_covered"] else "No",
                "Distance Rank": spot["distance_rank"],
                "Updated": spot["updated_at"],
                "Navigate": navigation_url(spot) or "Indoor route",
            }
        )
    return pd.DataFrame(rows)


def render_spot_cards(spots: list[dict]) -> None:
    cards = []
    for spot in spots:
        covered = "Covered" if spot["is_covered"] else "Open air"
        cards.append(
            f"""
            <div class="result-card {spot['status']}">
                <div class="result-header">
                    <div>
                        <div class="result-title">{spot['label']}</div>
                        <div class="result-subtitle">{spot['zone']} · {spot['spot_type'].title()} · {spot['width_class'].title()} bay</div>
                    </div>
                    <div class="status-pill {spot['status']}">{spot['status']}</div>
                </div>
                <div class="result-chip-row">
                    <span class="result-chip">Entrance rank {spot['distance_rank']}</span>
                    <span class="result-chip">{covered}</span>
                    <span class="result-chip">Updated {spot['updated_at'][-8:-3]}</span>
                </div>
                <div class="driver-note">
                    {"Tap navigate to route straight to this spot." if spot["status"] == "free" else "Currently unavailable, but still visible for context."}
                </div>
            </div>
            """
        )
    html(f"<div class='result-list'>{''.join(cards)}</div>", height=max(360, len(spots) * 168))


def render_sticky_cta(spot: dict | None) -> None:
    if not spot:
        return
    nav_link = navigation_url(spot)
    if not nav_link:
        return
    st.markdown(
        f"""
        <div class="sticky-cta">
            <a href="{nav_link}" target="_blank">
                <div>
                    Navigate to {spot['label']}
                    <small>{spot['zone']} · {spot['spot_type'].title()} · rank {spot['distance_rank']}</small>
                </div>
                <div>Open Maps</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def export_csv(dataframe: pd.DataFrame, file_name: str) -> None:
    buffer = StringIO()
    dataframe.to_csv(buffer, index=False)
    st.download_button("Export Report", buffer.getvalue(), file_name=file_name, mime="text/csv")


def render_dashboard(selected_lot: dict, analytics: dict, alerts: list[dict]) -> None:
    all_spots = selected_lot["spots"]
    fresh_free_spot_banner(selected_lot)
    render_search_hero(selected_lot, analytics)

    st.markdown("<div class='finder-toolbar'>", unsafe_allow_html=True)
    controls_left, controls_mid, controls_right, controls_extra = st.columns([1.3, 1, 1, 1])
    with controls_left:
        preference = st.selectbox("What matters most?", ["Nearest entrance", "First free", "Covered first"])
    with controls_mid:
        spot_filter = st.selectbox("Filter spots", ["All spots", "EV only", "Wide only", "Accessible only", "Covered only"])
    with controls_right:
        view_mode = st.segmented_control("View", ["Auto", "Map", "Grid"], default="Auto")
    with controls_extra:
        indoor_outdoor = st.toggle("Garage view", value=selected_lot["kind"] == "indoor")
    st.markdown("</div>", unsafe_allow_html=True)

    filtered_spots = filter_spots(all_spots, preference, spot_filter)
    free_spots = [spot for spot in filtered_spots if spot["status"] == "free"]
    best_spot = free_spots[0] if free_spots else None

    stats_cols = st.columns(4)
    with stats_cols[0]:
        st.markdown(f"<div class='mini-stat'><div class='metric-label'>Free Spots</div><div class='metric-value'>{selected_lot['free_count']}</div><div class='metric-note'>Ready right now</div></div>", unsafe_allow_html=True)
    with stats_cols[1]:
        st.markdown(f"<div class='mini-stat'><div class='metric-label'>Avg Wait</div><div class='metric-value'>{analytics['summary']['avg_wait_minutes']:.1f} min</div><div class='metric-note'>From arrival to parked</div></div>", unsafe_allow_html=True)
    with stats_cols[2]:
        st.markdown(f"<div class='mini-stat'><div class='metric-label'>Turnover Today</div><div class='metric-value'>{analytics['summary']['turnover_today']}</div><div class='metric-note'>Cars moved through recently</div></div>", unsafe_allow_html=True)
    with stats_cols[3]:
        peak = analytics["summary"]["peak_hour"] or "n/a"
        st.markdown(f"<div class='mini-stat'><div class='metric-label'>Peak Hour</div><div class='metric-value'>{peak[-8:-3] if peak != 'n/a' else 'n/a'}</div><div class='metric-note'>Usually busiest time</div></div>", unsafe_allow_html=True)

    main_left, main_right = st.columns([1.75, 1.05])
    with main_left:
        st.markdown("<div class='shell'>", unsafe_allow_html=True)
        st.subheader("Choose Your Spot")
        st.caption("Tap a green marker for details, or switch to grid mode for garage-style guidance.")
        should_show_grid = view_mode == "Grid" or indoor_outdoor or selected_lot["kind"] == "indoor"
        if view_mode == "Map" and selected_lot["kind"] == "indoor":
            st.info("Garages read better in grid mode, so we automatically mirror the indoor guidance view.")
            should_show_grid = True
        if should_show_grid:
            render_indoor_grid(filtered_spots)
        else:
            render_outdoor_map(filtered_spots, selected_lot["map_center"])
        st.markdown("</div>", unsafe_allow_html=True)

    with main_right:
        st.markdown("<div class='recommend-card'>", unsafe_allow_html=True)
        if best_spot:
            st.markdown(
                f"""
                <h3>Best pick right now: {best_spot['label']}</h3>
                <p class='recommend-meta'>{best_spot['zone']} · {best_spot['spot_type'].title()} · {best_spot['width_class'].title()} bay</p>
                <p class='recommend-meta'>Shortest route based on your current preference.</p>
                """,
                unsafe_allow_html=True,
            )
            nav_link = navigation_url(best_spot)
            if nav_link:
                st.link_button("Open Navigation", nav_link, width="stretch")
            share_link = f"http://localhost:8501/?lot={selected_lot['id']}&spot={best_spot['label']}"
            st.text_input("Share this live spot link", value=share_link)
        else:
            st.markdown("<p>No spot matches the current filter right now. Try widening the search.</p>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
        st.markdown("### Why this suggestion")
        if best_spot:
            st.markdown(f"<span class='mini-chip'>Entrance rank {best_spot['distance_rank']}</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='mini-chip'>{best_spot['spot_type'].title()}</span>", unsafe_allow_html=True)
            if best_spot["is_covered"]:
                st.markdown("<span class='mini-chip'>Covered</span>", unsafe_allow_html=True)
        for label in ["Hybrid indoor/outdoor", "100% local", "No video leaves the Mac"]:
            st.markdown(f"<span class='mini-chip'>{label}</span>", unsafe_allow_html=True)

        st.markdown("### Heads up")
        for alert in alerts[:3]:
            st.markdown(
                f"<div class='list-card alert-{alert['severity']}'><strong>{alert['category'].title()}</strong><br>{alert['message']}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns([1.4, 1])
    with lower_left:
        st.markdown("### Matching Spots")
        render_spot_cards(filtered_spots[:8])
        st.markdown("### Spot Details")
        for spot in filtered_spots[:6]:
            title = f"{spot['label']} · {spot['zone']} · {spot['status'].title()}"
            with st.expander(title, expanded=(best_spot is not None and spot["label"] == best_spot["label"])):
                chip_cols = st.columns(4)
                chip_cols[0].metric("Type", spot["spot_type"].title())
                chip_cols[1].metric("Width", spot["width_class"].title())
                chip_cols[2].metric("Covered", "Yes" if spot["is_covered"] else "No")
                chip_cols[3].metric("Rank", str(spot["distance_rank"]))
                st.caption(f"Last updated {spot['updated_at']}")
                nav_link = navigation_url(spot)
                button_cols = st.columns([1, 1, 1.2])
                if nav_link and spot["status"] == "free":
                    button_cols[0].link_button("Navigate", nav_link, width="stretch")
                else:
                    button_cols[0].button("Unavailable", disabled=True, key=f"disabled-{spot['label']}", width="stretch")
                share_link = f"http://localhost:8501/?lot={selected_lot['id']}&spot={spot['label']}"
                button_cols[1].text_input("Share link", value=share_link, key=f"share-{spot['label']}")
                if spot["status"] != "free":
                    if button_cols[2].button("Report incorrect status", key=f"feedback-{spot['label']}", width="stretch"):
                        create_alert(
                            {
                                "lot_id": selected_lot["id"],
                                "severity": "info",
                                "category": "user_feedback",
                                "message": f"Driver flagged {spot['label']} as incorrectly marked {spot['status']}.",
                                "status": "open",
                            }
                        )
                        st.success(f"Feedback logged for {spot['label']}.")
                        st.rerun()
                else:
                    button_cols[2].markdown("<span class='mini-chip'>Looks good</span>", unsafe_allow_html=True)
    with lower_right:
        st.markdown("### Quick Compare")
        df = build_spot_dataframe(filtered_spots)
        st.dataframe(df, width="stretch", hide_index=True)
        export_csv(df, f"{selected_lot['id']}-live-report.csv")
    render_sticky_cta(best_spot)


def render_admin(lots: list[dict]) -> None:
    st.subheader("Add New Lot")
    with st.form("add_lot_form", clear_on_submit=True):
        name = st.text_input("Lot name", placeholder="Santa Monica Mall North")
        kind = st.selectbox("Lot type", ["outdoor", "indoor"])
        description = st.text_area("Description", placeholder="Five-minute setup pilot with live wayfinding.")
        zone = st.text_input("Default zone", value="General")
        spot_type = st.selectbox("Primary spot type", ["standard", "ev", "accessible"])
        width_class = st.selectbox("Width class", ["standard", "wide", "compact"])
        camera_count = st.number_input("Expected camera count", min_value=1, max_value=100, value=4)
        latitude = st.number_input("Center latitude", value=34.0195, format="%.6f")
        longitude = st.number_input("Center longitude", value=-118.4912, format="%.6f")
        spot_labels = st.text_area("Spot labels", placeholder="A1,A2,A3,A4")
        submitted = st.form_submit_button("Save lot")
    if submitted:
        labels = [label.strip() for label in spot_labels.split(",") if label.strip()]
        if not name or not labels:
            st.error("Lot name and at least one spot label are required.")
        else:
            add_lot(
                {
                    "name": name,
                    "kind": kind,
                    "description": description,
                    "camera_count": int(camera_count),
                    "map_center": {"lat": latitude, "lng": longitude},
                    "spots": labels,
                    "zone": zone,
                    "spot_type": spot_type,
                    "width_class": width_class,
                }
            )
            st.success(f"{name} is live.")
            st.rerun()

    st.subheader("Live Simulator")
    selected_lot_name = st.selectbox("Choose lot", [lot["name"] for lot in lots], key="admin_lot")
    selected_lot = next(lot for lot in lots if lot["name"] == selected_lot_name)
    chosen_spot = st.selectbox("Spot", [spot["label"] for spot in selected_lot["spots"]])
    chosen_status = st.radio("Status", ["free", "occupied"], horizontal=True)
    if st.button("Apply status", width="stretch"):
        update_spot_status(selected_lot["id"], chosen_spot, chosen_status)
        st.success(f"{chosen_spot} set to {chosen_status}.")
        st.rerun()

    st.subheader("Fast Setup Notes")
    st.info(
        "Keep the one-click parking polygon workflow, but avoid building photo upload and GUI launching inside "
        "Streamlit for now. That step belongs in the local operator workflow because it depends on Ultralytics desktop tooling."
    )


def render_analytics(selected_lot: dict, analytics: dict) -> None:
    st.subheader("Occupancy Analytics")
    hourly = pd.DataFrame(analytics["hourly"])
    if hourly.empty:
        st.warning("No analytics yet.")
        return
    hourly["timestamp"] = pd.to_datetime(hourly["timestamp"])
    st.line_chart(hourly.set_index("timestamp")[["occupancy_pct", "avg_wait_minutes"]], width="stretch")
    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        st.bar_chart(hourly.set_index("timestamp")["turnover_count"], width="stretch")
    with bottom_right:
        summary = analytics["summary"]
        render_metric_card("Peak Occupancy", f"{summary['peak_occupancy_pct']}%", "Highest recent load")
        render_metric_card("Avg Wait", f"{summary['avg_wait_minutes']:.1f} min", "Current estimated delay")
        render_metric_card("Turnover", str(summary["turnover_today"]), "Most recent operating window")
    export_csv(hourly, f"{selected_lot['id']}-analytics.csv")


def render_settings(lots: list[dict], cameras: list[dict]) -> None:
    st.subheader("Camera Stream Manager")
    left, right = st.columns([1.2, 1])
    with left:
        camera_df = pd.DataFrame(cameras)
        if not camera_df.empty:
            st.dataframe(camera_df.rename(columns={"rtsp_url": "RTSP URL", "last_seen": "Last Seen"}), width="stretch", hide_index=True)
        else:
            st.info("No cameras configured yet.")
    with right:
        with st.form("add_camera_form", clear_on_submit=True):
            lot_name = st.selectbox("Assign to lot", [lot["name"] for lot in lots])
            lot_id = next(lot["id"] for lot in lots if lot["name"] == lot_name)
            name = st.text_input("Camera name", placeholder="North Pole Cam 03")
            rtsp_url = st.text_input("RTSP URL", placeholder="rtsp://192.168.1.99:554/stream1")
            status = st.selectbox("Initial status", ["online", "warning", "offline"])
            if st.form_submit_button("Add camera"):
                add_camera({"lot_id": lot_id, "name": name, "rtsp_url": rtsp_url, "status": status})
                st.success(f"{name} added.")
                st.rerun()

    st.subheader("LED Controller")
    indoor_lots = [lot for lot in lots if lot["kind"] == "indoor"]
    if indoor_lots:
        chosen_lot = st.selectbox("Indoor lot", [lot["name"] for lot in indoor_lots], key="led_lot")
        lot = next(lot for lot in indoor_lots if lot["name"] == chosen_lot)
        spot = st.selectbox("LED target spot", [item["label"] for item in lot["spots"]], key="led_spot")
        led_color = st.radio("Send color", ["green", "red"], horizontal=True)
        if st.button("Send LED test", width="stretch"):
            severity = "info" if led_color == "green" else "warning"
            create_alert(
                {
                    "lot_id": lot["id"],
                    "severity": severity,
                    "category": "led_test",
                    "message": f"LED test sent to {spot}: {led_color}.",
                    "status": "resolved",
                }
            )
            st.success(f"LED test queued for {spot}.")
    else:
        st.info("Add an indoor lot to unlock LED controls.")

    st.subheader("Product Judgment")
    st.write("Included now: analytics, alerts, filters, camera management, shareable links, and indoor/outdoor parity.")
    st.write("Avoided for now: reservations and predictive holds. They need policy rules, abuse prevention, and real historical confidence before they are worth shipping.")


def render_alerts(alerts: list[dict], lots: list[dict]) -> None:
    st.subheader("Alerts Log")
    lot_lookup = {lot["id"]: lot["name"] for lot in lots}
    severity_filter = st.multiselect("Severity", ["critical", "warning", "info"], default=["critical", "warning", "info"])
    status_filter = st.multiselect("Status", ["open", "resolved"], default=["open", "resolved"])
    filtered = [alert for alert in alerts if alert["severity"] in severity_filter and alert["status"] in status_filter]
    if not filtered:
        st.success("No alerts match the current filters.")
        return
    for alert in filtered:
        lot_name = lot_lookup.get(alert["lot_id"], "Global")
        st.markdown(
            f"""
            <div class="list-card alert-{alert['severity']}">
                <strong>{alert['severity'].upper()} · {alert['category'].title()}</strong><br>
                {alert['message']}<br>
                <span class='mini-chip'>{lot_name}</span>
                <span class='mini-chip'>{alert['status']}</span>
                <span class='mini-chip'>{alert['created_at']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def fetch_all_data(selected_lot_id: str | None) -> tuple[list[dict], list[dict], list[dict], dict]:
    lots = load_lots()
    alerts = load_alerts()
    cameras = load_cameras()
    chosen_lot = next((lot for lot in lots if lot["id"] == selected_lot_id), lots[0])
    analytics = load_analytics(chosen_lot["id"])
    return lots, alerts, cameras, analytics


def main() -> None:
    refresh_seconds = 3
    st_autorefresh(interval=refresh_seconds * 1000, key="smartpark_live_refresh")

    if not healthcheck():
        st.error("SmartPark API is offline. Start it with `uvicorn smartpark.api:app --reload` and reload this page.")
        st.stop()

    with st.sidebar:
        st.title("SmartPark")
        owner_mode = st.toggle("Owner mode", value=False, help="Turn this on for admin, analytics, camera, and alert tools.")
        pages = DRIVER_PAGES + OWNER_PAGES if owner_mode else DRIVER_PAGES
        page = st.radio("Navigate", pages, label_visibility="collapsed")
        theme_mode = st.segmented_control("Theme", ["Day", "Night"], default="Night")
        st.caption(f"API: {API_BASE_URL}")
        if owner_mode:
            st.markdown("<span class='owner-badge'>Owner tools enabled</span>", unsafe_allow_html=True)
        st.caption("The periodic rerun logs are expected. They come from live refresh every few seconds.")

    inject_styles(theme_mode)

    selected_query_lot = st.query_params.get("lot")
    lots, alerts, cameras, initial_analytics = fetch_all_data(selected_query_lot)
    selected_lot_id = st.sidebar.selectbox(
        "Lot",
        options=[lot["id"] for lot in lots],
        index=next((i for i, lot in enumerate(lots) if lot["id"] == (selected_query_lot or lots[0]["id"])), 0),
        format_func=lambda lot_id: next(lot["name"] for lot in lots if lot["id"] == lot_id),
    )
    selected_lot = next(lot for lot in lots if lot["id"] == selected_lot_id)
    st.query_params["lot"] = selected_lot_id
    analytics = initial_analytics if selected_lot["id"] == (selected_query_lot or selected_lot["id"]) else load_analytics(selected_lot["id"])
    selected_alerts = [alert for alert in alerts if alert["lot_id"] in (None, selected_lot["id"])]

    render_top_bar(selected_lot, analytics, refresh_seconds)

    if page == "Find Parking":
        render_dashboard(selected_lot, analytics, selected_alerts)
    elif page == "Admin":
        render_admin(lots)
    elif page == "Analytics":
        render_analytics(selected_lot, analytics)
    elif page == "Settings":
        render_settings(lots, cameras)
    else:
        render_alerts(alerts, lots)

    st.caption(f"Last refresh: {datetime.now().strftime('%b %d, %Y %I:%M:%S %p')} · Local-only mode active")


if __name__ == "__main__":
    main()
