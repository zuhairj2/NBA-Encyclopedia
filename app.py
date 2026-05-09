import streamlit as st
from agent.agent import run_agent
from agent.tools import (
    get_player_season_stats,
    get_player_bio,
    get_team_accolades,
    get_team_full_stats,
    get_team_rankings,
    get_player_shot_zones,
    get_player_photo_url,
    get_team_logo_url,
    get_team_colors,
    get_player_comparison_data,
    get_team_comparison_data,
    get_all_active_player_names,
    get_all_player_names_with_legends,
    get_player_career_stats,
    get_player_accolades,
    get_team_game_log,
    get_full_standings,
    get_team_schedule,
    search_game_boxscore,
    get_player_playoff_stats,
    get_player_stats_vs_team,
    get_games_on_date,
    get_boxscore_by_game_id,
    detect_season_type,
    get_todays_games,
)
from utils.parser import extract_single_player, extract_team, extract_teams, TEAM_MAP

# Unicode constants — avoids backslash-in-f-string errors on Python 3.9
DASH   = "\u2014"   # em dash  —
ENDASH = "\u2013"   # en dash  –
APOS   = "\u2019"   # right single quote  '

st.set_page_config(page_title="NBA Encyclopedia", layout="wide")


@st.cache_data(ttl=3600)
def _cached_all_players():
    """Player names including legends — cached 1hr."""
    try:
        return get_all_player_names_with_legends()
    except Exception:
        try:
            return get_all_active_player_names()
        except Exception:
            return []

@st.cache_data(ttl=60)
def _cached_todays_games(date_str):
    """Cache today's games for 60 seconds to avoid blocking reruns."""
    try:
        games = get_todays_games(date_str)
        return games if games else []
    except Exception:
        return []

@st.cache_data(ttl=1800)
def _cached_standings():
    """Standings cached 30 min — prevents re-fetching on every tab switch."""
    try:
        return get_full_standings()
    except Exception:
        return []

st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 0 !important; }

/* ── Tab bar → ESPN-style navbar ─────────────────── */
[data-testid="stTabs"] > div:first-child {
    background: #0f172a !important;
    border-bottom: 2px solid #1e293b !important;
    padding: 0 8px !important;
    gap: 0 !important;
    position: sticky;
    top: 0;
    z-index: 100;
}
/* Brand name injected before the tabs */
[data-testid="stTabs"] > div:first-child::before {
    content: "NBA Encyclopedia";
    color: #f1f5f9;
    font-weight: 900;
    font-size: 16px;
    letter-spacing: -0.3px;
    padding: 0 20px 0 4px;
    border-right: 1px solid #1e293b;
    margin-right: 8px;
    white-space: nowrap;
    display: flex;
    align-items: center;
    flex-shrink: 0;
}
[data-testid="stTabs"] button[role="tab"] {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    padding: 13px 18px !important;
    border: none !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    margin: 0 !important;
    white-space: nowrap !important;
    transition: all 0.15s !important;
}
[data-testid="stTabs"] button[role="tab"]:hover {
    color: #f1f5f9 !important;
    background: rgba(255,255,255,0.05) !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #fff !important;
    border-bottom: 3px solid #ef4444 !important;
    font-weight: 700 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

/* ── Component styles ────────────────────────────── */
.card{background:#fff;border:0.5px solid #e0e0e0;border-radius:12px;overflow:hidden;margin-bottom:1.5rem}
.left-panel{background:#f7f7f7;border-right:0.5px solid #e0e0e0;padding:1.5rem 1rem;display:flex;flex-direction:column;align-items:center;gap:10px;min-width:150px}
.stat-grid{display:grid;gap:6px}
.stat-box{text-align:center;background:#f2f2f2;border-radius:8px;padding:10px 6px;position:relative}
.stat-rank{position:absolute;top:4px;right:6px;font-size:11px;color:#333333;font-weight:600}
.stat-label{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#444444;margin:0 0 2px;font-weight:500}
.stat-val-lg{font-size:20px;font-weight:600;margin:0;color:#111}
.stat-val-sm{font-size:15px;font-weight:600;margin:0;color:#111}
.section-label{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#aaa;margin:0 0 8px}
.avatar{width:36px;height:36px;border-radius:50%;margin:0 auto 6px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600}
/* ── Suggestion chip buttons ─────────────────────── */
div[data-testid="stHorizontalBlock"] button,
div[data-testid="column"] button[kind="secondary"] {
    border-radius: 8px !important;
    border: 1px solid #1e293b !important;
    background: #111827 !important;
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
div[data-testid="column"] button[kind="secondary"]:hover {
    border-color: #3b82f6 !important;
    color: #f1f5f9 !important;
    background: #1e293b !important;
}
@keyframes livepulse{0%,100%{opacity:1}50%{opacity:0.3}}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#ef4444;margin-right:4px;animation:livepulse 1.5s infinite;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pct(val):
    try:
        return f"{round(float(val) * 100, 1)}%"
    except Exception:
        return "—"


def zone_chart_svg(zones=None):
    """
    Render a clean half-court shot chart with colored zones.
    Green = hot, yellow = average, orange/red = cold, dark = no data.
    """
    z = zones or {}

    def color_for(pct):
        if pct is None:
            return "#1e293b", "#334155", "#64748b"
        if pct >= 55:
            return "#14532d", "#22c55e", "#86efac"
        if pct >= 45:
            return "#166534", "#4ade80", "#d1fae5"
        if pct >= 38:
            return "#713f12", "#eab308", "#fef9c3"
        if pct >= 30:
            return "#7c2d12", "#f97316", "#fed7aa"
        return "#7f1d1d", "#ef4444", "#fee2e2"

    def get_zone(key):
        val = z.get(key)
        return val, color_for(val)

    def lbl(val):
        return f"{val}%" if val is not None else "—"

    def box(x, y, w, h, val, colors, title, rx=6):
        bg, bdr, txt = colors
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{bg}" stroke="{bdr}" stroke-width="1.5"/>' +
            (f'<text x="{x+w//2}" y="{y+h//2-9}" text-anchor="middle" font-size="10" '
             f'fill="{txt}" font-family="system-ui,sans-serif">{title}</text>'
             f'<text x="{x+w//2}" y="{y+h//2+10}" text-anchor="middle" font-size="17" '
             f'font-weight="700" fill="{txt}" font-family="system-ui,sans-serif">{lbl(val)}</text>'
             if title else
             f'<text x="{x+w//2}" y="{y+h//2+5}" text-anchor="middle" font-size="10" '
             f'fill="{txt}" font-family="system-ui,sans-serif">{lbl(val)}</text>')
        )

    paint_v,   paint_c   = get_zone("paint")
    lmid_v,    lmid_c    = get_zone("left_mid")
    rmid_v,    rmid_c    = get_zone("right_mid")
    l3_v,      l3_c      = get_zone("left_3")
    t3_v,      t3_c      = get_zone("top_3")
    r3_v,      r3_c      = get_zone("right_3")
    lc_v,      lc_c      = get_zone("left_corner")
    rc_v,      rc_c      = get_zone("right_corner")

    svg = (
        '<svg viewBox="0 0 500 365" width="100%" xmlns="http://www.w3.org/2000/svg" '
        'style="display:block;border-radius:10px;max-width:560px;">' +
        # Background
        '<rect width="500" height="365" fill="#0f172a" rx="10"/>' +
        # Court outline
        '<rect x="20" y="18" width="460" height="330" fill="none" stroke="#1e3a5f" stroke-width="1"/>' +
        # Paint
        '<rect x="175" y="178" width="150" height="165" fill="none" stroke="#1e3a5f" stroke-width="1"/>' +
        # FT circle
        '<ellipse cx="250" cy="178" rx="60" ry="45" fill="none" stroke="#1e3a5f" stroke-width="1" stroke-dasharray="5 4"/>' +
        # FT line
        '<line x1="175" y1="178" x2="325" y2="178" stroke="#1e3a5f" stroke-width="1"/>' +
        # 3pt lines
        '<line x1="42" y1="202" x2="42" y2="348" stroke="#1e3a5f" stroke-width="1"/>' +
        '<line x1="458" y1="202" x2="458" y2="348" stroke="#1e3a5f" stroke-width="1"/>' +
        '<path d="M 42 202 A 220 220 0 0 1 458 202" fill="none" stroke="#1e3a5f" stroke-width="1"/>' +
        # Restricted area
        '<path d="M 222 343 A 28 28 0 0 1 278 343" fill="none" stroke="#1e3a5f" stroke-width="1"/>' +
        # Backboard + basket
        '<rect x="218" y="10" width="64" height="6" rx="2" fill="none" stroke="#334155" stroke-width="1.5"/>' +
        '<circle cx="250" cy="24" r="9" fill="none" stroke="#334155" stroke-width="1.5"/>' +
        # Zone boxes
        box(178, 181, 144, 161, paint_v,  paint_c,  "Paint") +
        box(45,  180, 126, 98,  lmid_v,   lmid_c,   "Left Mid") +
        box(329, 180, 126, 98,  rmid_v,   rmid_c,   "Right Mid") +
        box(45,  58,  126, 118, l3_v,     l3_c,     "Left 3") +
        box(179, 20,  142, 112, t3_v,     t3_c,     "Top 3") +
        box(329, 58,  126, 118, r3_v,     r3_c,     "Right 3")
    )

    # Corner 3s as slim vertical strips
    bg, bdr, txt = lc_c
    svg += (
        f'<rect x="22" y="202" width="20" height="144" rx="3" fill="{bg}" stroke="{bdr}" stroke-width="1"/>' +
        f'<text x="32" y="285" text-anchor="middle" font-size="9" fill="{txt}" font-family="system-ui,sans-serif" ' +
        f'transform="rotate(-90 32 285)">C3 {lbl(lc_v)}</text>'
    )
    bg, bdr, txt = rc_c
    svg += (
        f'<rect x="458" y="202" width="20" height="144" rx="3" fill="{bg}" stroke="{bdr}" stroke-width="1"/>' +
        f'<text x="468" y="285" text-anchor="middle" font-size="9" fill="{txt}" font-family="system-ui,sans-serif" ' +
        f'transform="rotate(90 468 285)">C3 {lbl(rc_v)}</text>'
    )

    # Legend
    legend = [("#22c55e","45%+"),("#eab308","38-45%"),("#f97316","30-38%"),("#ef4444","<30%"),("#334155","No data")]
    lx = 20
    for color, label_txt in legend:
        svg += (
            f'<rect x="{lx}" y="353" width="8" height="8" rx="2" fill="{color}"/>' +
            f'<text x="{lx+10}" y="361" font-size="8" fill="#94a3b8" font-family="system-ui,sans-serif">{label_txt}</text>'
        )
        lx += 82
    svg += '</svg>'
    return svg


def _UNUSED_zone_chart_svg(zones=None):
    z = zones or {}
    paint        = fmt(z.get("paint"))
    left_mid     = fmt(z.get("left_mid"))
    right_mid    = fmt(z.get("right_mid"))
    left_3       = fmt(z.get("left_3"))
    right_3      = fmt(z.get("right_3"))
    top_3        = fmt(z.get("top_3"))
    left_corner  = fmt(z.get("left_corner"))
    right_corner = fmt(z.get("right_corner"))

    pb, pbo, pbt = "#1e3a5f", "#4a90d9", "#90c8f8"
    mb, mbo, mbt = "#1a3d28", "#4caf7d", "#7ed4a4"
    tb, tbo, tbt = "#3d2a0a", "#f5a623", "#f5c878"

    svg  = '<svg viewBox="0 0 500 340" width="75%" xmlns="http://www.w3.org/2000/svg" '
    svg += 'style="display:block;margin-top:8px;border-radius:8px;">'
    svg += '<rect x="0" y="0" width="500" height="340" rx="6" fill="#1a1a2e"/>'
    svg += '<rect x="175" y="170" width="150" height="165" fill="none" stroke="#fff" stroke-width="1.5"/>'
    svg += '<ellipse cx="250" cy="170" rx="50" ry="35" fill="none" stroke="#fff" stroke-width="1.5" stroke-dasharray="6 4"/>'
    svg += '<path d="M215 335 A35 35 0 0 1 285 335" fill="none" stroke="#fff" stroke-width="1.5"/>'
    svg += '<path d="M40 335 A215 215 0 0 1 460 335" fill="none" stroke="#fff" stroke-width="1.5"/>'
    svg += '<line x1="40" y1="205" x2="40" y2="335" stroke="#fff" stroke-width="1.5"/>'
    svg += '<line x1="460" y1="205" x2="460" y2="335" stroke="#fff" stroke-width="1.5"/>'
    svg += '<rect x="220" y="5" width="60" height="6" rx="2" fill="none" stroke="#fff" stroke-width="1.5"/>'
    svg += '<circle cx="250" cy="22" r="10" fill="none" stroke="#fff" stroke-width="1.5"/>'
    svg += f'<rect x="180" y="178" width="140" height="150" rx="6" fill="{pb}" stroke="{pbo}" stroke-width="1.5"/>'
    svg += f'<text x="250" y="245" text-anchor="middle" font-size="14" fill="{pbt}" font-family="sans-serif">Paint</text>'
    svg += f'<text x="250" y="268" text-anchor="middle" font-size="20" font-weight="700" fill="{pbt}" font-family="sans-serif">{paint}</text>'
    svg += f'<rect x="48" y="178" width="122" height="110" rx="6" fill="{mb}" stroke="{mbo}" stroke-width="1.5"/>'
    svg += f'<text x="109" y="228" text-anchor="middle" font-size="13" fill="{mbt}" font-family="sans-serif">Left mid</text>'
    svg += f'<text x="109" y="252" text-anchor="middle" font-size="20" font-weight="700" fill="{mbt}" font-family="sans-serif">{left_mid}</text>'
    svg += f'<rect x="330" y="178" width="122" height="110" rx="6" fill="{mb}" stroke="{mbo}" stroke-width="1.5"/>'
    svg += f'<text x="391" y="228" text-anchor="middle" font-size="13" fill="{mbt}" font-family="sans-serif">Right mid</text>'
    svg += f'<text x="391" y="252" text-anchor="middle" font-size="20" font-weight="700" fill="{mbt}" font-family="sans-serif">{right_mid}</text>'
    svg += f'<rect x="48" y="60" width="118" height="108" rx="6" fill="{tb}" stroke="{tbo}" stroke-width="1.5"/>'
    svg += f'<text x="107" y="108" text-anchor="middle" font-size="13" fill="{tbt}" font-family="sans-serif">Left 3</text>'
    svg += f'<text x="107" y="133" text-anchor="middle" font-size="20" font-weight="700" fill="{tbt}" font-family="sans-serif">{left_3}</text>'
    svg += f'<rect x="180" y="18" width="140" height="95" rx="6" fill="{tb}" stroke="{tbo}" stroke-width="1.5"/>'
    svg += f'<text x="250" y="58" text-anchor="middle" font-size="13" fill="{tbt}" font-family="sans-serif">Top 3</text>'
    svg += f'<text x="250" y="84" text-anchor="middle" font-size="20" font-weight="700" fill="{tbt}" font-family="sans-serif">{top_3}</text>'
    svg += f'<rect x="334" y="60" width="118" height="108" rx="6" fill="{tb}" stroke="{tbo}" stroke-width="1.5"/>'
    svg += f'<text x="393" y="108" text-anchor="middle" font-size="13" fill="{tbt}" font-family="sans-serif">Right 3</text>'
    svg += f'<text x="393" y="133" text-anchor="middle" font-size="20" font-weight="700" fill="{tbt}" font-family="sans-serif">{right_3}</text>'
    svg += f'<rect x="4" y="210" width="32" height="118" rx="4" fill="{tb}" stroke="{tbo}" stroke-width="1"/>'
    svg += f'<text x="20" y="268" text-anchor="middle" font-size="9" fill="{tbt}" font-family="sans-serif" transform="rotate(-90 20 268)">C3 {left_corner}</text>'
    svg += f'<rect x="464" y="210" width="32" height="118" rx="4" fill="{tb}" stroke="{tbo}" stroke-width="1"/>'
    svg += f'<text x="480" y="268" text-anchor="middle" font-size="9" fill="{tbt}" font-family="sans-serif" transform="rotate(90 480 268)">C3 {right_corner}</text>'
    svg += '</svg>'
    return svg


def stat_box_html(label, value, rank=None):
    rank_html = f'<span class="stat-rank">#{rank}</span>' if rank else ""
    return (
        f'<div class="stat-box">'
        f'{rank_html}'
        f'<p class="stat-label">{label}</p>'
        f'<p class="stat-val-lg">{value}</p>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Player card
# ---------------------------------------------------------------------------

def render_player_card(stats, bio, zones=None):
    name   = stats["name"]
    team   = stats["team"]
    age    = bio.get("age", "—")
    pos    = bio.get("position", "")
    school = bio.get("school", "") or "—"
    jersey = bio.get("jersey", "")
    is_active = bio.get("is_active", True)

    # Badge: active shows team + number, retired shows career span
    if is_active and team and team != "RET":
        badge = f"{team} · #{jersey}" if jersey else team
    else:
        from_yr = str(bio.get("from_year", ""))[:4]
        to_yr   = str(bio.get("to_year",   ""))[:4]
        badge   = f"{from_yr}{ENDASH}{to_yr}" if from_yr and to_yr else "Retired"

    # Extra bio fields
    height     = bio.get("height", "")
    weight     = bio.get("weight", "")
    country    = bio.get("country", "")
    draft_year = bio.get("draft_year", "")
    draft_rd   = bio.get("draft_round", "")
    draft_pick = bio.get("draft_number", "")
    draft_str  = ""
    if draft_year and draft_rd and draft_pick:
        draft_str = f"{draft_year} · Rd {draft_rd} Pick #{draft_pick}"
    elif draft_year:
        draft_str = str(draft_year)

    # For retired players use a neutral color scheme
    if not is_active or team == "RET":
        colors = get_team_colors("San Antonio Spurs")  # neutral silver/black
    else:
        colors = get_team_colors(team)

    bg          = colors["pastel_bg"]
    border      = colors["pastel_border"]
    on_bg       = colors["on_bg"]
    on_bg_muted = colors["on_bg_muted"]

    photo_url  = get_player_photo_url(name)
    photo_html = (
        f'<img src="{photo_url}" style="width:90px;height:110px;object-fit:cover;'
        f'border-radius:10px;border:2px solid {border};" onerror="this.style.display=\'none\'">'
        if photo_url else
        f'<div style="width:90px;height:110px;background:rgba(0,0,0,0.1);border-radius:10px;'
        f'border:2px solid {border};"></div>'
    )

    def bio_row(label, val):
        if not val:
            return ""
        return (
            f'<div style="display:flex;justify-content:space-between;padding:2px 0;'
            f'border-bottom:0.5px solid {border};">'
            f'<span style="font-size:11px;color:{on_bg_muted};">{label}</span>'
            f'<span style="font-size:11px;font-weight:600;color:{on_bg};">{val}</span>'
            f'</div>'
        )

    primary = "".join(stat_box_html(l, v, r) for l, v, r in [
        ("GP",  stats["gp"],  None),
        ("PTS", stats["ppg"], stats.get("rank_pts")),
        ("REB", stats["reb"], stats.get("rank_reb")),
        ("AST", stats["ast"], stats.get("rank_ast")),
        ("STL", stats["stl"], stats.get("rank_stl")),
        ("BLK", stats["blk"], stats.get("rank_blk")),
    ])

    fta  = stats.get("fta_pg", "—")
    fg3a = stats.get("fg3a_pg", "—")
    ts   = f"{stats['ts_pct']}%" if stats.get("ts_pct") else "—"
    usg  = f"{stats['usg_pct']}%" if stats.get("usg_pct") else "—"
    shooting = "".join([
        stat_box_html("FG%",   pct(stats["fg_pct"]),    stats.get("rank_fg")),
        stat_box_html("3PT%",  pct(stats["three_pct"]), stats.get("rank_3fg")),
        stat_box_html("3FGA",  fg3a,                    stats.get("rank_3fga")),
        stat_box_html("FT%",   pct(stats["ft_pct"]),    stats.get("rank_ft")),
        stat_box_html("FTA",   fta,                     stats.get("rank_fta")),
        stat_box_html("TS%",   ts,                      None),
        stat_box_html("USG%",  usg,                     None),
        stat_box_html("MIN/G", stats.get("min_pg") or "—", None),
    ])

    ortg    = stats.get("ortg")
    drtg    = stats.get("drtg")
    net_rtg = stats.get("net_rtg")
    ratings_html = ""
    if any(v is not None for v in [ortg, drtg, net_rtg]):
        net_color = "#16a34a" if (net_rtg or 0) > 0 else "#dc2626"
        ratings_html = (
            f'<div style="border-top:1px solid {border};padding-top:10px;">'
            f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 6px;font-weight:600;">Advanced ratings</p>'
            '<div class="stat-grid" style="grid-template-columns:repeat(3,1fr);">'
            + stat_box_html("ORTG", ortg or "—", stats.get("rank_ortg"))
            + stat_box_html("DRTG", drtg or "—", stats.get("rank_drtg"))
            + f'<div class="stat-box"><p class="stat-label">NET RTG</p>'
              f'<p class="stat-val-lg" style="color:{net_color};">'
              f'{("+" if (net_rtg or 0) > 0 else "")}{net_rtg or "—"}</p></div>'
            + '</div></div>'
        )

    zone_svg = zone_chart_svg(zones)

    # Career stats for top 5 seasons
    _career = get_player_career_stats(name)
    _reg_top5 = _career.get("top_seasons", []) if "error" not in _career else []

    # Playoff stats — top 5 postseasons
    _po = get_player_playoff_stats(name)
    _po_top5 = _po.get("top_po_seasons", []) if "error" not in _po else []

    # Convert po seasons to same format as reg seasons (no award flags)
    _po_top5_fmt = []
    for s in _po_top5:
        _po_top5_fmt.append({
            "season":    s.get("season", ""),
            "team":      s.get("team", ""),
            "gp":        s.get("gp"),
            "ppg":       s.get("ppg"),
            "reb":       s.get("reb"),
            "ast":       s.get("ast"),
            "fg_pct":    (s.get("fg_pct") / 100) if s.get("fg_pct") else None,
            "three_pct": (s.get("three_pct") / 100) if s.get("three_pct") else None,
            "ts_pct":    s.get("ts_pct"),
        })
    _po_html = ""
    if "error" not in _po and _po.get("career_games", 0) > 0:
        def _po_box(label, val, fmt=None):
            v = fmt(val) if (fmt and val is not None) else (val if val is not None else DASH)
            return stat_box_html(label, v)

        # Current season playoffs (if available and different from career)
        curr = _po.get("current_season")
        curr_html = ""
        if curr and curr.get("gp", 0) > 0:
            curr_html = (
                f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;'
                f'color:{on_bg};margin:8px 0 6px;font-weight:600;">'
                f'2025{ENDASH}26 Playoffs '
                f'<span style="font-size:10px;font-weight:400;color:{on_bg_muted};">({curr["gp"]} GP)</span></p>'
                f'<div class="stat-grid" style="grid-template-columns:repeat(5,1fr);">'
                + _po_box("PPG", curr.get("ppg"))
                + _po_box("REB", curr.get("reb"))
                + _po_box("AST", curr.get("ast"))
                + _po_box("STL", curr.get("stl"))
                + _po_box("BLK", curr.get("blk"))
                + '</div>'
            )

        _po_html = (
            f'<div style="border-top:1px solid {border};padding-top:10px;">'
            + curr_html
            + f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;'
              f'color:{on_bg};margin:{"8px" if curr_html else "0"} 0 6px;font-weight:600;">Career Playoff Averages '
              f'<span style="font-size:10px;font-weight:400;color:{on_bg_muted};">({_po["career_games"]} GP, {_po.get("seasons",0)} seasons)</span></p>'
            f'<div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">'
            + _po_box("PPG",  _po.get("career_ppg"))
            + _po_box("REB",  _po.get("career_reb"))
            + _po_box("AST",  _po.get("career_ast"))
            + _po_box("STL",  _po.get("career_stl"))
            + _po_box("BLK",  _po.get("career_blk"))
            + _po_box("TS%",  _po.get("career_ts_pct"), fmt=lambda x: f"{x}%")
            + '</div>'
            f'<div class="stat-grid" style="grid-template-columns:repeat(3,1fr);margin-top:6px;">'
            + _po_box("FG%",  _po.get("career_fg_pct"), fmt=lambda x: f"{round(x*100,1)}%")
            + _po_box("3PT%", _po.get("career_3_pct"),  fmt=lambda x: f"{round(x*100,1)}%")
            + _po_box("FT%",  _po.get("career_ft_pct"), fmt=lambda x: f"{round(x*100,1)}%")
            + '</div></div>'
        )

    # Accolades for left panel
    ac = stats.get("_accolades", {})

    def ac_item(label, val):
        if not val:
            return ""
        return (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:3px 0;border-bottom:0.5px solid {border};">'
            f'<span style="font-size:11px;color:{on_bg_muted};">{label}</span>'
            f'<span style="font-size:12px;font-weight:700;color:{on_bg};">{val}</span>'
            f'</div>'
        )

    ac_html = ""
    if ac:
        ac_html = (
            f'<div style="width:100%;margin-top:8px;">'
            f'<p style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;'
            f'color:{on_bg_muted};margin:0 0 6px;font-weight:600;">Accolades</p>'
            + ac_item("Rings",         ac.get("rings"))
            + ac_item("MVPs",          ac.get("mvps"))
            + ac_item("Finals MVPs",   ac.get("finals_mvp"))
            + ac_item("All-NBA",       ac.get("all_nba"))
            + ac_item("All-Star",      ac.get("all_star"))
            + ac_item("All-Defense",   ac.get("all_defense"))
            + ac_item("Scoring Titles",ac.get("scoring"))
            + ac_item("DPOY",          ac.get("dpoy"))
            + ac_item("ROY",           ac.get("roty"))
            + '</div>'
        )

    left_panel = (
        f'<div class="left-panel" style="background:{bg};border-right:1px solid {border};">'
        + photo_html
        + f'<div style="text-align:center;">'
          f'<p style="font-size:16px;font-weight:700;margin:0;color:{on_bg};">{name}</p>'
          f'<p style="font-size:13px;font-weight:500;color:{on_bg_muted};margin:4px 0 2px;">{pos}</p>'
          f'</div>'
        + f'<span style="font-size:12px;padding:4px 14px;border-radius:99px;'
          f'background:{colors["badge_bg"]};color:{colors["badge_text"]};'
          f'border:1px solid {colors["badge_border"]};font-weight:600;">{badge}</span>'
        + f'<div style="width:100%;margin-top:4px;">'
          + bio_row("Age",     str(age) if age else "")
          + bio_row("Height",  height)
          + bio_row("Weight",  f"{weight} lbs" if weight else "")
          + bio_row("College", school)
          + bio_row("Country", country)
          + bio_row("Draft",   draft_str)
          + '</div>'
        + ac_html
        + '</div>'
    )

    right_panel = (
        f'<div style="flex:1;padding:1.25rem;display:flex;flex-direction:column;gap:10px;background:{bg};">'
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 4px;font-weight:600;">2025{ENDASH}26 Season Averages</p>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">{primary}</div>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(4,1fr);">{shooting}</div>'
        + ratings_html
        + f'<div style="border-top:1px solid {border};padding-top:10px;">'
          f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 6px;font-weight:600;">Shot Zones</p>'
          + zone_svg
          + '</div>'
        + _po_html
        + '</div>'
    )

    st.markdown(
        f'<div class="card" style="border:1px solid {border};">'
        '<div style="display:flex;align-items:stretch;">'
        + left_panel + right_panel
        + '</div></div>',
        unsafe_allow_html=True
    )

    # ── Top 5 Seasons toggle ──────────────────────────────────────────────
    has_po = bool(_po_top5_fmt)
    toggle_options = ["Regular Season", "Postseason"] if has_po else ["Regular Season"]
    season_type_toggle = st.radio(
        "seasons_view",
        toggle_options,
        horizontal=True,
        key=f"seasons_toggle_{name.replace(' ','_')}",
        label_visibility="collapsed"
    )
    if season_type_toggle == "Regular Season":
        st.markdown(
            render_best_seasons(_reg_top5, border, on_bg, bg, on_bg_muted),
            unsafe_allow_html=True
        )
    else:
        if _po_top5_fmt:
            st.markdown(
                render_best_seasons(_po_top5_fmt, border, on_bg, bg, on_bg_muted),
                unsafe_allow_html=True
            )
        else:
            st.caption("No postseason data available.")

def render_team_card(stats):
    team      = stats["team"]
    abbr      = stats.get("abbr", team[:3].upper())
    record    = f"{stats['wins']}\u2013{stats['losses']}"
    conf      = stats.get("conf", "")
    div       = stats.get("div", "")
    conf_rank = stats.get("conf_rank", "\u2014")
    div_rank  = stats.get("div_rank",  "\u2014")

    colors      = get_team_colors(team)
    bg          = colors["pastel_bg"]
    border      = colors["pastel_border"]
    primary_c   = colors["primary"]
    on_bg       = colors["on_bg"]
    on_bg_muted = colors["on_bg_muted"]

    logo_url  = get_team_logo_url(team)
    logo_html = (
        f'<img src="{logo_url}" style="width:80px;height:80px;object-fit:contain;" '
        f'onerror="this.style.display=\'none\'">'
        if logo_url else
        f'<div style="width:80px;height:80px;border-radius:50%;background:{primary_c};'
        f'display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff;">{abbr}</div>'
    )

    def ordinal(n):
        if not isinstance(n, int):
            return str(n)
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th")
        return f"{n}{suffix}"

    primary = "".join(stat_box_html(l, v, r) for l, v, r in [
        ("GP",  stats["gp"],  None),
        ("PTS", stats["ppg"], stats.get("rank_pts")),
        ("REB", stats["reb"], stats.get("rank_reb")),
        ("AST", stats["ast"], stats.get("rank_ast")),
        ("STL", stats["stl"], stats.get("rank_stl")),
        ("BLK", stats["blk"], stats.get("rank_blk")),
    ])

    fta  = stats.get("fta_pg", "\u2014")
    fg3a = stats.get("fg3a_pg", "\u2014")
    shooting = "".join([
        stat_box_html("FG%",  pct(stats["fg_pct"]),    stats.get("rank_fg")),
        stat_box_html("3PT%", pct(stats["three_pct"]), stats.get("rank_3fg")),
        stat_box_html("3FGA", fg3a,                    stats.get("rank_3fga")),
        stat_box_html("FT%",  pct(stats["ft_pct"]),    stats.get("rank_ft")),
        stat_box_html("FTA",  fta,                     stats.get("rank_fta")),
    ])

    ortg    = stats.get("ortg")
    drtg    = stats.get("drtg")
    net_rtg = stats.get("net_rtg")
    ratings_html = ""
    if any(v is not None for v in [ortg, drtg, net_rtg]):
        net_color = "#16a34a" if (net_rtg or 0) > 0 else "#dc2626"
        ratings_html = (
            f'<div style="border-top:1px solid {border};padding-top:10px;">'
            f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 6px;font-weight:600;">Advanced Ratings</p>'
            '<div class="stat-grid" style="grid-template-columns:repeat(3,1fr);">'
            + stat_box_html("ORTG", ortg or DASH, stats.get("rank_ortg"))
            + stat_box_html("DRTG", drtg or DASH, stats.get("rank_drtg"))
            + f'<div class="stat-box"><p class="stat-label">NET RTG</p>'
              f'<p class="stat-val-lg" style="color:{net_color};">'
              f'{("+" if (net_rtg or 0) > 0 else "")}{net_rtg or DASH}</p></div>'
            + '</div></div>'
        )

    def performer_card(title, player, p_bg, p_color):
        if not player:
            return ""
        return (
            f'<div style="background:#ffffff;border:1px solid #e0e0e0;border-radius:8px;padding:10px;'
            f'display:flex;flex-direction:column;align-items:center;gap:6px;">'
            f'<p style="font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#555;margin:0;font-weight:500;">{title}</p>'
            f'<div class="avatar" style="background:{p_bg};color:{p_color};">{player["initials"]}</div>'
            f'<div style="text-align:center;">'
            f'<p style="font-size:12px;font-weight:600;margin:0;color:#111;">{player["name"]}</p>'
            f'<p style="font-size:13px;font-weight:700;margin:3px 0 0;color:#111;">{player["stat_val"]} '
            f'<span style="font-size:10px;font-weight:400;color:#666;">{player["stat_lbl"]}</span></p>'
            '</div></div>'
        )

    performers_html = "".join([
        performer_card("Top Scorer",    stats.get("best_scorer"),    "#dbeafe", "#1e40af"),
        performer_card("Top Rebounder", stats.get("best_rebounder"), "#fef3c7", "#92400e"),
        performer_card("Top Blocker",   stats.get("best_blocker"),   "#dcfce7", "#166534"),
    ])

    conf_label = f"{conf}ern Conference" if conf in ("East", "West") else conf

    # Fetch team accolades
    acols = get_team_accolades(team)
    champs = acols.get("championships", 0)
    playoff_apps = acols.get("playoff_appearances", 0)

    acol_html = ""
    if champs or playoff_apps:
        acol_html = (
            f'<div style="width:100%;margin-top:10px;border-top:1px solid {border};padding-top:10px;">'
            f'<p style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;'
            f'color:{on_bg_muted};margin:0 0 8px;font-weight:600;">Franchise History</p>'
        )
        if champs:
            acol_html += (
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
                f'border-bottom:0.5px solid {border};">'
                f'<span style="font-size:11px;color:{on_bg_muted};">🏆 Championships</span>'
                f'<span style="font-size:12px;font-weight:700;color:{on_bg};">{champs}</span>'
                f'</div>'
            )
        if playoff_apps:
            acol_html += (
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;">'
                f'<span style="font-size:11px;color:{on_bg_muted};">Playoff Appearances</span>'
                f'<span style="font-size:12px;font-weight:700;color:{on_bg};">{playoff_apps}</span>'
                f'</div>'
            )
        acol_html += '</div>'

    left_panel = (
        f'<div class="left-panel" style="background:{bg};border-right:1px solid {border};">'
        + logo_html
        + f'<div style="text-align:center;">'
          f'<p style="font-size:15px;font-weight:700;margin:0 0 6px;color:{on_bg};">{team}</p>'
          f'<p style="font-size:14px;font-weight:600;color:{on_bg};margin:0 0 8px;">{record}</p>'
          f'<p style="font-size:13px;font-weight:600;color:{on_bg_muted};margin:0 0 3px;">'
          f'<span style="font-size:15px;font-weight:700;color:{on_bg};">{ordinal(conf_rank)}</span> {conf_label}</p>'
          f'<p style="font-size:13px;font-weight:600;color:{on_bg_muted};margin:0;">'
          f'<span style="font-size:15px;font-weight:700;color:{on_bg};">{ordinal(div_rank)}</span> {div} Division</p>'
          f'</div>'
        + acol_html
        + '</div>'
    )

    # Fetch recent schedule (last 8 games)
    recent_log = get_team_game_log(team, 8)
    schedule_html = ""
    if isinstance(recent_log, list) and recent_log:
        rows_s = ""
        for g in recent_log:
            res      = g.get("result", "")
            rc       = "#22c55e" if res == "W" else ("#ef4444" if res == "L" else "#888")
            res_bg   = "rgba(34,197,94,0.12)" if res == "W" else "rgba(239,68,68,0.12)"
            opp      = g.get("opponent", "")
            pts      = g.get("pts")
            opp_pts  = g.get("opp_pts")
            is_home  = g.get("home", False)
            ha       = "vs" if is_home else "@"
            ha_c     = "#3b82f6" if is_home else "#8b5cf6"

            # Pretty date
            try:
                from datetime import datetime as _dtp
                d = _dtp.strptime(str(g.get("date", "")), "%Y-%m-%d")
                date_str = d.strftime("%b %-d")
            except Exception:
                date_str = str(g.get("date", ""))[-5:]

            # Score
            if pts is not None and opp_pts is not None:
                if res == "W":
                    score_str = (f'<span style="color:#22c55e;font-weight:700;">{pts}</span>'
                                 f'<span style="color:{on_bg_muted};">–{opp_pts}</span>')
                else:
                    score_str = (f'<span style="color:{on_bg_muted};">{pts}–</span>'
                                 f'<span style="color:#ef4444;font-weight:700;">{opp_pts}</span>')
            else:
                score_str = str(pts) if pts else "—"

            # Opponent logo
            opp_logo = ""
            try:
                opp_url = get_team_logo_url(opp)
                if opp_url:
                    opp_logo = (f'<img src="{opp_url}" style="width:18px;height:18px;'
                               f'object-fit:contain;vertical-align:middle;margin-right:5px;" '
                               f'onerror="this.style.display=\'none\'">')
            except Exception:
                pass

            rows_s += (
                f'<tr style="border-bottom:0.5px solid {border};">'
                f'<td style="padding:6px 8px;font-size:11px;color:{on_bg_muted};white-space:nowrap;">{date_str}</td>'
                f'<td style="padding:6px 8px;font-size:11px;">'
                f'<span style="color:{ha_c};font-size:10px;font-weight:600;margin-right:4px;">{ha}</span>'
                + opp_logo +
                f'<span style="color:{on_bg};font-size:12px;">{opp.split()[-1]}</span></td>'
                f'<td style="padding:6px 8px;text-align:center;">'
                f'<span style="font-size:11px;font-weight:800;padding:2px 7px;border-radius:5px;'
                f'background:{res_bg};color:{rc};">{res or "—"}</span></td>'
                f'<td style="padding:6px 8px;text-align:center;font-size:12px;">{score_str}</td>'
                f'</tr>'
            )

        schedule_html = (
            f'<div style="border-top:1px solid {border};padding-top:10px;">'
            f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;'
            f'color:{on_bg};margin:0 0 6px;font-weight:600;">Recent Games</p>'
            f'<div style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr style="border-bottom:1px solid {border};">'
            f'<th style="padding:4px 8px;font-size:10px;text-transform:uppercase;color:{on_bg_muted};text-align:left;">Date</th>'
            f'<th style="padding:4px 8px;font-size:10px;text-transform:uppercase;color:{on_bg_muted};text-align:left;">Opponent</th>'
            f'<th style="padding:4px 8px;font-size:10px;text-transform:uppercase;color:{on_bg_muted};text-align:center;">W/L</th>'
            f'<th style="padding:4px 8px;font-size:10px;text-transform:uppercase;color:{on_bg_muted};text-align:center;">Score</th>'
            f'</tr></thead><tbody>{rows_s}</tbody></table></div></div>'
        )

    right_panel = (
        f'<div style="flex:1;padding:1.25rem;display:flex;flex-direction:column;gap:10px;background:{bg};">'
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 4px;font-weight:600;">Ranking Among Teams</p>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">{primary}</div>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(5,1fr);">{shooting}</div>'
        + ratings_html
        + schedule_html
        + '</div>'
    )

    st.markdown(
        f'<div class="card" style="border:1px solid {border};">'
        '<div style="display:flex;align-items:stretch;">'
        + left_panel + right_panel
        + '</div></div>',
        unsafe_allow_html=True
    )



# ---------------------------------------------------------------------------
# Best seasons renderer (shared by both active + career cards)
# ---------------------------------------------------------------------------

def render_best_seasons(top_seasons, border, on_bg, bg, on_bg_muted=None):
    """Render top 5 seasons table with award badges. Uses theme colors for readability."""
    if not top_seasons:
        return ""
    muted = on_bg_muted or on_bg

    def badge(text, bg, text_color="#fff"):
        return (
            f'<span style="font-size:10px;font-weight:800;padding:2px 7px;border-radius:4px;'
            f'background:{bg};color:{text_color};margin-right:3px;white-space:nowrap;'
            f'letter-spacing:.03em;">{text}</span>'
        )

    def fmt_pct(v):
        return f"{round(v*100,1)}%" if v else DASH

    rows_html = ""
    for s in top_seasons:
        badges = ""
        if s.get("ring"):       badges += badge("🏆 Ring",   "#92400e", "#fbbf24")
        if s.get("finals_mvp"): badges += badge("FMVP",      "#6b21a8", "#e9d5ff")
        if s.get("mvp"):        badges += badge("MVP",        "#1e3a8a", "#93c5fd")
        if s.get("all_star"):   badges += badge("All-Star",   "#14532d", "#86efac")
        if s.get("all_nba"):    badges += badge("All-NBA",    "#164e63", "#67e8f9")
        if s.get("dpoy"):       badges += badge("DPOY",       "#7f1d1d", "#fca5a5")

        rows_html += (
            f'<tr style="border-bottom:0.5px solid {border};">'
            f'<td style="padding:7px 8px;font-size:12px;font-weight:600;color:{on_bg};white-space:nowrap;">{s.get("season","")}</td>'
            f'<td style="padding:7px 6px;font-size:12px;color:{muted};">{s.get("team","")}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:{muted};">{s.get("gp", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:13px;font-weight:700;color:{on_bg};">{s.get("ppg", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:{muted};">{s.get("reb", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:{muted};">{s.get("ast", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:{muted};">{fmt_pct(s.get("fg_pct"))}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:{muted};">{fmt_pct(s.get("three_pct"))}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:{muted};">{s.get("ts_pct", DASH)}{"%" if s.get("ts_pct") else ""}</td>'
            f'<td style="padding:7px 8px;text-align:left;">{badges}</td>'
            f'</tr>'
        )

    header_style = f'font-size:10px;text-transform:uppercase;color:{muted};font-weight:600;'
    return (
        f'<div style="border-top:1px solid {border};padding-top:10px;overflow-x:auto;">'
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 6px;font-weight:600;">Top 5 Seasons</p>'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:1px solid {border};">'
        f'<th style="padding:5px 8px;{header_style}text-align:left;">Season</th>'
        f'<th style="padding:5px 6px;{header_style}">Team</th>'
        f'<th style="padding:5px 6px;{header_style}">GP</th>'
        f'<th style="padding:5px 6px;{header_style}">PPG</th>'
        f'<th style="padding:5px 6px;{header_style}">REB</th>'
        f'<th style="padding:5px 6px;{header_style}">AST</th>'
        f'<th style="padding:5px 6px;{header_style}">FG%</th>'
        f'<th style="padding:5px 6px;{header_style}">3PT%</th>'
        f'<th style="padding:5px 6px;{header_style}">TS%</th>'
        f'<th style="padding:5px 6px;{header_style}">Awards</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>'
    )


# ---------------------------------------------------------------------------
# Career card (retired / legend players)
# ---------------------------------------------------------------------------

def render_career_card(player_name, career, bio, accolades):
    """Full card for retired players using career averages."""
    # Use neutral silver color scheme for retired players
    colors      = get_team_colors("San Antonio Spurs")
    bg          = colors["pastel_bg"]
    border      = colors["pastel_border"]
    on_bg       = colors["on_bg"]
    on_bg_muted = colors["on_bg_muted"]

    # Bio
    age    = bio.get("age", DASH)
    pos    = bio.get("position", "")
    school = bio.get("school", "") or DASH
    height = bio.get("height", "")
    weight = bio.get("weight", "")
    country= bio.get("country", "")
    from_yr= str(bio.get("from_year", ""))[:4]
    to_yr  = str(bio.get("to_year",   ""))[:4]
    draft_year  = bio.get("draft_year", "")
    draft_rd    = bio.get("draft_round", "")
    draft_pick  = bio.get("draft_number", "")
    draft_str   = f"{draft_year} · Rd {draft_rd} Pick #{draft_pick}" \
                  if (draft_year and draft_rd and draft_pick) else str(draft_year or "")
    career_span = f"{from_yr}{ENDASH}{to_yr}" if from_yr and to_yr else "Retired"

    # Photo
    photo_url  = get_player_photo_url(player_name)
    photo_html = (
        f'<img src="{photo_url}" style="width:90px;height:110px;object-fit:cover;'
        f'border-radius:10px;border:2px solid {border};" onerror="this.style.display=\'none\'">'
        if photo_url else
        f'<div style="width:90px;height:110px;background:rgba(0,0,0,0.1);border-radius:10px;'
        f'border:2px solid {border};"></div>'
    )

    def bio_row(label, val):
        if not val:
            return ""
        return (
            f'<div style="display:flex;justify-content:space-between;padding:2px 0;'
            f'border-bottom:0.5px solid {border};">'
            f'<span style="font-size:11px;color:{on_bg_muted};">{label}</span>'
            f'<span style="font-size:11px;font-weight:600;color:{on_bg};">{val}</span>'
            f'</div>'
        )

    def ac_item(label, val):
        if not val:
            return ""
        return (
            f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
            f'border-bottom:0.5px solid {border};">'
            f'<span style="font-size:11px;color:{on_bg_muted};">{label}</span>'
            f'<span style="font-size:12px;font-weight:700;color:{on_bg};">{val}</span>'
            f'</div>'
        )

    ac_html = ""
    if accolades:
        ac_html = (
            f'<div style="width:100%;margin-top:8px;">'
            f'<p style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;'
            f'color:{on_bg_muted};margin:0 0 6px;font-weight:600;">Accolades</p>'
            + ac_item("Rings",          accolades.get("rings"))
            + ac_item("MVPs",           accolades.get("mvps"))
            + ac_item("Finals MVPs",    accolades.get("finals_mvp"))
            + ac_item("All-NBA",        accolades.get("all_nba"))
            + ac_item("All-Star",       accolades.get("all_star"))
            + ac_item("All-Defense",    accolades.get("all_defense"))
            + ac_item("Scoring Titles", accolades.get("scoring"))
            + ac_item("DPOY",           accolades.get("dpoy"))
            + ac_item("ROY",            accolades.get("roty"))
            + ac_item("Olympic Medals", accolades.get("olympic"))
            + '</div>'
        )

    left_panel = (
        f'<div class="left-panel" style="background:{bg};border-right:1px solid {border};min-width:170px;">'
        + photo_html
        + f'<div style="text-align:center;">'
          f'<p style="font-size:16px;font-weight:700;margin:0;color:{on_bg};">{player_name}</p>'
          f'<p style="font-size:13px;font-weight:500;color:{on_bg_muted};margin:4px 0 2px;">{pos}</p>'
          f'</div>'
        + f'<span style="font-size:12px;padding:4px 14px;border-radius:99px;'
          f'background:{colors["badge_bg"]};color:{colors["badge_text"]};'
          f'border:1px solid {colors["badge_border"]};font-weight:600;">{career_span}</span>'
        + f'<div style="width:100%;margin-top:4px;">'
          + bio_row("Age at Retirement", str(age) if age else "")
          + bio_row("Height",  height)
          + bio_row("Weight",  f"{weight} lbs" if weight else "")
          + bio_row("College", school)
          + bio_row("Country", country)
          + bio_row("Draft",   draft_str)
          + '</div>'
        + ac_html
        + '</div>'
    )

    # Career stat boxes
    def cbox(label, val, fmt=None):
        v = fmt(val) if (fmt and val is not None) else (val if val is not None else DASH)
        return stat_box_html(label, v)

    primary = "".join([
        cbox("GP",  career.get("career_games")),
        cbox("PPG", career.get("career_ppg")),
        cbox("REB", career.get("career_reb")),
        cbox("AST", career.get("career_ast")),
        cbox("STL", career.get("career_stl")),
        cbox("BLK", career.get("career_blk")),
    ])

    shooting = "".join([
        cbox("FG%",  career.get("career_fg_pct"),  fmt=lambda x: f"{round(x*100,1)}%"),
        cbox("3PT%", career.get("career_3_pct"),   fmt=lambda x: f"{round(x*100,1)}%"),
        cbox("FT%",  career.get("career_ft_pct"),  fmt=lambda x: f"{round(x*100,1)}%"),
        cbox("TS%",  career.get("career_ts_pct"),  fmt=lambda x: f"{x}%"),
        cbox("Seasons", career.get("seasons")),
    ])

    # Teams played for
    teams = career.get("teams", [])
    teams_html = ""
    if teams:
        pills = "".join(
            f'<span style="font-size:11px;font-weight:600;padding:2px 8px;border-radius:99px;'
            f'background:#ffffff;border:1px solid #e0e0e0;color:#333;margin:2px;">{t}</span>'
            for t in teams
        )
        teams_html = (
            f'<div style="border-top:1px solid {border};padding-top:10px;margin-top:4px;">'
            f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};'
            f'margin:0 0 6px;font-weight:600;">Teams</p>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{pills}</div>'
            f'</div>'
        )

    best_seasons_html = render_best_seasons(
        career.get("top_seasons", []), border, on_bg, bg, on_bg_muted
    )

    right_panel = (
        f'<div style="flex:1;padding:1.25rem;display:flex;flex-direction:column;gap:10px;background:{bg};">'
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};'
        f'margin:0 0 4px;font-weight:600;">Career Averages</p>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">{primary}</div>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(5,1fr);">{shooting}</div>'
        + teams_html
        + best_seasons_html
        + '</div>'
    )

    st.markdown(
        f'<div class="card" style="border:1px solid {border};">'
        '<div style="display:flex;align-items:stretch;">'
        + left_panel + right_panel
        + '</div></div>',
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Game log
# ---------------------------------------------------------------------------

def render_game_log(team_name, log):
    colors = get_team_colors(team_name)
    on_bg  = colors["on_bg"]

    st.markdown(
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;'
        f'color:{"#ffffff" if on_bg == "#ffffff" else "#666"};font-weight:600;margin-bottom:8px;">'
        f'Last {len(log)} games {DASH} {team_name}</p>',
        unsafe_allow_html=True
    )

    for i, game in enumerate(log):
        win = game["result"] == "W"
        label = (
            f"{'W' if win else 'L'}  {game['date']} \u00b7 {game['matchup']} \u00b7 "
            f"**{game['pts']} pts** \u00b7 "
            f"FG {game['fg_pct']}% \u00b7 3PT {game['three_pct']}% \u00b7 "
            f"REB {game['reb']} \u00b7 AST {game['ast']} \u00b7 TOV {game['tov']}"
        )
        with st.expander(label, expanded=(i == 0)):
            if game["players"]:
                header = "| Player | MIN | PTS | REB | AST | STL | BLK | FG | 3PT | FT | +/- |"
                sep    = "|---|---|---|---|---|---|---|---|---|---|---|"
                rows   = "\n".join(
                    f"| {p['name']} | {p['min']} | {p['pts']} | {p['reb']} | "
                    f"{p['ast']} | {p['stl']} | {p['blk']} | {p['fg']} | "
                    f"{p['fg3']} | {p['ft']} | {'+' if p['plus_minus'] >= 0 else ''}{p['plus_minus']} |"
                    for p in game["players"]
                )
                st.markdown(f"{header}\n{sep}\n{rows}")
            else:
                st.info("Box score not available for this game.")


# ---------------------------------------------------------------------------
# Rankings table
# ---------------------------------------------------------------------------

def render_rankings_table(rankings):
    rows_html = ""
    for t in rankings:
        rank      = t.get("rank", "")
        name      = t.get("TEAM_NAME", "")
        abbr      = t.get("TEAM_ABBREVIATION", "")
        w         = t.get("W", "\u2014")
        l         = t.get("L", "\u2014")
        ortg      = t.get("OFF_RATING")
        drtg      = t.get("DEF_RATING")
        net       = t.get("NET_RATING")
        net_str   = f"{'+' if (net or 0) > 0 else ''}{net:.1f}" if net is not None else "\u2014"
        ortg_str  = f"{ortg:.1f}" if ortg is not None else "\u2014"
        drtg_str  = f"{drtg:.1f}" if drtg is not None else "\u2014"
        net_color = "#16a34a" if (net or 0) > 0 else "#dc2626"

        rows_html += (
            f'<tr style="border-bottom:0.5px solid #f0f0f0;">'
            f'<td style="padding:8px 6px;color:#999;font-size:12px;width:32px;">{rank}</td>'
            f'<td style="padding:8px 6px;font-weight:500;font-size:13px;color:#111;">{name}'
            f'<span style="font-size:11px;color:#aaa;margin-left:4px;">{abbr}</span></td>'
            f'<td style="padding:8px 6px;text-align:center;font-size:13px;color:#555;">{w}{ENDASH}{l}</td>'
            f'<td style="padding:8px 6px;text-align:center;font-size:13px;color:#555;">{ortg_str}</td>'
            f'<td style="padding:8px 6px;text-align:center;font-size:13px;color:#555;">{drtg_str}</td>'
            f'<td style="padding:8px 6px;text-align:center;font-size:13px;font-weight:600;color:{net_color};">{net_str}</td>'
            f'</tr>'
        )

    st.markdown(f"""
<div class="card" style="padding:0;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="border-bottom:1px solid #e0e0e0;background:#f7f7f7;">
        <th style="padding:8px 6px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#aaa;font-weight:500;">#</th>
        <th style="padding:8px 6px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#aaa;font-weight:500;">Team</th>
        <th style="padding:8px 6px;text-align:center;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#aaa;font-weight:500;">W\u2013L</th>
        <th style="padding:8px 6px;text-align:center;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#aaa;font-weight:500;">ORTG</th>
        <th style="padding:8px 6px;text-align:center;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#aaa;font-weight:500;">DRTG</th>
        <th style="padding:8px 6px;text-align:center;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#aaa;font-weight:500;">NET RTG</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _cmp_color(v1, v2, higher_is_better=True):
    try:
        f1, f2 = float(v1), float(v2)
        if f1 == f2:
            return "#ffffff", "#ffffff"
        if higher_is_better:
            return ("#d1fae5", "#fde8e8") if f1 > f2 else ("#fde8e8", "#d1fae5")
        else:
            return ("#d1fae5", "#fde8e8") if f1 < f2 else ("#fde8e8", "#d1fae5")
    except Exception:
        return "#ffffff", "#ffffff"


def cmp_row(label, v1, v2, higher_is_better=True, fmt=None):
    d1 = fmt(v1) if fmt and v1 not in (None, "\u2014") else (v1 if v1 is not None else "\u2014")
    d2 = fmt(v2) if fmt and v2 not in (None, "\u2014") else (v2 if v2 is not None else "\u2014")
    c1, c2 = _cmp_color(
        v1 if v1 not in (None, "\u2014") else None,
        v2 if v2 not in (None, "\u2014") else None,
        higher_is_better
    )
    return (
        f'<div style="display:grid;grid-template-columns:1fr auto 1fr;'
        f'align-items:center;gap:4px;margin-bottom:5px;">'
        f'<div style="text-align:center;background:{c1};border-radius:6px;padding:8px 4px;'
        f'font-size:16px;font-weight:600;color:#111;">{d1}</div>'
        f'<div style="text-align:center;font-size:10px;text-transform:uppercase;'
        f'letter-spacing:.06em;color:#888;font-weight:600;min-width:60px;">{label}</div>'
        f'<div style="text-align:center;background:{c2};border-radius:6px;padding:8px 4px;'
        f'font-size:16px;font-weight:600;color:#111;">{d2}</div>'
        f'</div>'
    )


def accolade_row(label, v1, v2):
    c1, c2 = _cmp_color(v1, v2, higher_is_better=True)
    win1 = " *" if v1 > v2 else ""
    win2 = " *" if v2 > v1 else ""
    return (
        f'<div style="display:grid;grid-template-columns:1fr auto 1fr;'
        f'align-items:center;gap:4px;margin-bottom:5px;">'
        f'<div style="text-align:center;background:{c1};border-radius:6px;padding:8px 4px;'
        f'font-size:16px;font-weight:600;color:#111;">{v1}{win1}</div>'
        f'<div style="text-align:center;font-size:10px;text-transform:uppercase;'
        f'letter-spacing:.06em;color:#888;font-weight:600;min-width:90px;">{label}</div>'
        f'<div style="text-align:center;background:{c2};border-radius:6px;padding:8px 4px;'
        f'font-size:16px;font-weight:600;color:#111;">{v2}{win2}</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Player comparison
# ---------------------------------------------------------------------------

def render_player_compare(p1, p2):
    s1, s2   = p1["stats"], p2["stats"]
    ac1, ac2 = p1["accolades"], p2["accolades"]
    c1, c2   = p1["colors"], p2["colors"]

    col1, col2 = st.columns(2)

    def player_header(col, data, colors):
        with col:
            photo = data["photo"]
            bg    = colors["pastel_bg"]
            on_bg = colors["on_bg"]
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:20px;text-align:center;">'
                + (f'<img src="{photo}" style="width:110px;height:130px;object-fit:cover;'
                   f'border-radius:10px;margin-bottom:10px;">' if photo else "")
                + f'<p style="font-size:18px;font-weight:700;color:{on_bg};margin:0;">{data["stats"].get("name","")}</p>'
                  f'<p style="font-size:13px;color:{colors["on_bg_muted"]};margin:4px 0 0;">'
                  f'Age {data["bio"].get("age","—")} · {data["bio"].get("position","")}</p>'
                  f'<p style="font-size:13px;color:{colors["on_bg_muted"]};margin:2px 0;">'
                  f'{data["bio"].get("school","—")}</p>'
                  f'<span style="font-size:12px;padding:3px 12px;border-radius:99px;'
                  f'background:{colors["badge_bg"]};color:{colors["badge_text"]};'
                  f'border:1px solid {colors["badge_border"]};font-weight:600;">'
                  f'{data["stats"].get("team","")} · #{data["bio"].get("jersey","")}</span>'
                + '</div>',
                unsafe_allow_html=True
            )

    player_header(col1, p1, c1)
    player_header(col2, p2, c2)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Season Stats")
    rows = ""
    rows += cmp_row("PPG",     s1.get("ppg"),       s2.get("ppg"))
    rows += cmp_row("REB",     s1.get("reb"),        s2.get("reb"))
    rows += cmp_row("AST",     s1.get("ast"),        s2.get("ast"))
    rows += cmp_row("STL",     s1.get("stl"),        s2.get("stl"))
    rows += cmp_row("BLK",     s1.get("blk"),        s2.get("blk"))
    rows += cmp_row("FG%",     s1.get("fg_pct"),     s2.get("fg_pct"),     fmt=lambda x: f"{x*100:.1f}%")
    rows += cmp_row("3FG%",    s1.get("three_pct"),  s2.get("three_pct"),  fmt=lambda x: f"{x*100:.1f}%")
    rows += cmp_row("3FGA",    s1.get("fg3a_pg"),    s2.get("fg3a_pg"))
    rows += cmp_row("FT%",     s1.get("ft_pct"),     s2.get("ft_pct"),     fmt=lambda x: f"{x*100:.1f}%")
    rows += cmp_row("FTA",     s1.get("fta_pg"),     s2.get("fta_pg"))
    rows += cmp_row("ORTG",    s1.get("ortg"),       s2.get("ortg"))
    rows += cmp_row("DRTG",    s1.get("drtg"),       s2.get("drtg"),       higher_is_better=False)
    rows += cmp_row("NET RTG", s1.get("net_rtg"),    s2.get("net_rtg"))
    st.markdown(f'<div style="max-width:700px;margin:0 auto;">{rows}</div>', unsafe_allow_html=True)

    st.markdown("### Career Accolades")
    ac_rows = ""
    ac_rows += accolade_row("Rings",               ac1.get("rings",0),       ac2.get("rings",0))
    ac_rows += accolade_row("Finals MVPs",          ac1.get("finals_mvp",0),  ac2.get("finals_mvp",0))
    ac_rows += accolade_row("Regular Season MVPs",  ac1.get("mvps",0),        ac2.get("mvps",0))
    ac_rows += accolade_row("All-NBA",              ac1.get("all_nba",0),     ac2.get("all_nba",0))
    ac_rows += accolade_row("All-Defense",          ac1.get("all_defense",0), ac2.get("all_defense",0))
    ac_rows += accolade_row("All-Star",             ac1.get("all_star",0),    ac2.get("all_star",0))
    ac_rows += accolade_row("Scoring Titles",       ac1.get("scoring",0),     ac2.get("scoring",0))
    ac_rows += accolade_row("DPOY",                 ac1.get("dpoy",0),        ac2.get("dpoy",0))
    ac_rows += accolade_row("ROY",                  ac1.get("roty",0),        ac2.get("roty",0))
    ac_rows += accolade_row("Olympic Medals",       ac1.get("olympic",0),     ac2.get("olympic",0))
    st.markdown(f'<div style="max-width:700px;margin:0 auto;">{ac_rows}</div>', unsafe_allow_html=True)

    ca1 = p1.get("career", {})
    ca2 = p2.get("career", {})
    if ca1 and ca2 and "error" not in ca1 and "error" not in ca2:
        st.markdown("### Career Averages")
        car_rows = ""
        car_rows += cmp_row("Career PPG",  ca1.get("career_ppg"),    ca2.get("career_ppg"))
        car_rows += cmp_row("Career REB",  ca1.get("career_reb"),    ca2.get("career_reb"))
        car_rows += cmp_row("Career AST",  ca1.get("career_ast"),    ca2.get("career_ast"))
        car_rows += cmp_row("Career STL",  ca1.get("career_stl"),    ca2.get("career_stl"))
        car_rows += cmp_row("Career BLK",  ca1.get("career_blk"),    ca2.get("career_blk"))
        car_rows += cmp_row("Career FG%",  ca1.get("career_fg_pct"), ca2.get("career_fg_pct"), fmt=lambda x: f"{x*100:.1f}%")
        car_rows += cmp_row("Career 3PT%", ca1.get("career_3_pct"),  ca2.get("career_3_pct"),  fmt=lambda x: f"{x*100:.1f}%")
        car_rows += cmp_row("Career FT%",  ca1.get("career_ft_pct"), ca2.get("career_ft_pct"), fmt=lambda x: f"{x*100:.1f}%")
        car_rows += cmp_row("Career TS%",  ca1.get("career_ts_pct"), ca2.get("career_ts_pct"), fmt=lambda x: f"{x}%")
        car_rows += cmp_row("Seasons",     ca1.get("seasons"),        ca2.get("seasons"))
        car_rows += cmp_row("Career GP",   ca1.get("career_games"),   ca2.get("career_games"))
        st.markdown(f'<div style="max-width:700px;margin:0 auto;">{car_rows}</div>', unsafe_allow_html=True)

    st.markdown("### Shot Zones")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"**{s1.get('name','')}**")
        st.markdown(zone_chart_svg(p1["zones"]), unsafe_allow_html=True)
    with sc2:
        st.markdown(f"**{s2.get('name','')}**")
        st.markdown(zone_chart_svg(p2["zones"]), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Team comparison
# ---------------------------------------------------------------------------

def render_team_compare(t1, t2):
    s1, s2   = t1["stats"], t2["stats"]
    ac1, ac2 = t1["accolades"], t2["accolades"]
    c1, c2   = t1["colors"], t2["colors"]

    col1, col2 = st.columns(2)

    def team_header(col, data, colors):
        with col:
            bg    = colors["pastel_bg"]
            on_bg = colors["on_bg"]
            logo  = data["logo"]
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:20px;text-align:center;">'
                + (f'<img src="{logo}" style="width:80px;height:80px;object-fit:contain;margin-bottom:10px;">'
                   if logo else "")
                + f'<p style="font-size:18px;font-weight:700;color:{on_bg};margin:0;">{data["name"]}</p>'
                  f'<p style="font-size:14px;font-weight:600;color:{on_bg};margin:4px 0 0;">'
                  f'{data["stats"].get("wins", DASH)}{ENDASH}{data["stats"].get("losses", DASH)}</p>'
                + '</div>',
                unsafe_allow_html=True
            )

    team_header(col1, t1, c1)
    team_header(col2, t2, c2)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Season Stats")
    rows = ""
    rows += cmp_row("PPG",     s1.get("ppg"),       s2.get("ppg"))
    rows += cmp_row("REB",     s1.get("reb"),        s2.get("reb"))
    rows += cmp_row("AST",     s1.get("ast"),        s2.get("ast"))
    rows += cmp_row("STL",     s1.get("stl"),        s2.get("stl"))
    rows += cmp_row("BLK",     s1.get("blk"),        s2.get("blk"))
    rows += cmp_row("FG%",     s1.get("fg_pct"),     s2.get("fg_pct"),     fmt=lambda x: f"{x*100:.1f}%")
    rows += cmp_row("3FG%",    s1.get("three_pct"),  s2.get("three_pct"),  fmt=lambda x: f"{x*100:.1f}%")
    rows += cmp_row("3FGA",    s1.get("fg3a_pg"),    s2.get("fg3a_pg"))
    rows += cmp_row("FT%",     s1.get("ft_pct"),     s2.get("ft_pct"),     fmt=lambda x: f"{x*100:.1f}%")
    rows += cmp_row("FTA",     s1.get("fta_pg"),     s2.get("fta_pg"))
    rows += cmp_row("ORTG",    s1.get("ortg"),       s2.get("ortg"))
    rows += cmp_row("DRTG",    s1.get("drtg"),       s2.get("drtg"),       higher_is_better=False)
    rows += cmp_row("NET RTG", s1.get("net_rtg"),    s2.get("net_rtg"))
    st.markdown(f'<div style="max-width:700px;margin:0 auto;">{rows}</div>', unsafe_allow_html=True)

    st.markdown("### Franchise History")
    ac_rows = ""
    ac_rows += accolade_row("Championships",      ac1.get("championships",0),      ac2.get("championships",0))
    ac_rows += accolade_row("Playoff Appearances",ac1.get("playoff_appearances",0), ac2.get("playoff_appearances",0))
    st.markdown(f'<div style="max-width:700px;margin:0 auto;">{ac_rows}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Suggestion chips
# ---------------------------------------------------------------------------

SUGGESTIONS = [
    "Bring up the Warriors stats",
    "What are SGA's stats this season?",
    "Compare Luka vs Giannis",
    "Who leads the league in scoring?",
    "Show me the Celtics last 5 games",
    "Who do you think wins the MVP?",
    "What are the Lakers season stats?",
    "Show me the team rankings",
]

OPINION_KEYWORDS = [
    "who do you think", "who wins", "predict", "prediction", "your opinion",
    "who will win", "mvp race", "finals prediction", "playoff prediction",
    "best player", "goat", "greatest", "who is better", "draft lottery",
]

GAME_LOG_KEYWORDS = ["last", "games", "game log", "recent games", "box score"]


# ---------------------------------------------------------------------------
# Standings renderer
# ---------------------------------------------------------------------------

def render_standings(rows, view="overall"):
    """Render standings with team logos, color bars, and clean layout."""

    STATUS_LABEL = {"x": "Playoffs", "pi": "Play-In", "e": "Missed"}
    STATUS_BG    = {"x": "#dcfce7", "pi": "#fef3c7", "e": "#f3f4f6"}
    STATUS_COLOR = {"x": "#16a34a", "pi": "#d97706", "e": "#6b7280"}

    def record(w, l):
        return f"{w}–{l}" if (w is not None and l is not None) else DASH

    def net_fmt(v):
        if v is None: return DASH
        sign  = "+" if v > 0 else ""
        color = "#16a34a" if v > 0 else ("#dc2626" if v < 0 else "#6b7280")
        return f'<span style="color:{color};font-weight:700;">{sign}{v}</span>'

    def status_pill(s):
        bg    = STATUS_BG.get(s, "#f3f4f6")
        color = STATUS_COLOR.get(s, "#888")
        label = STATUS_LABEL.get(s, "")
        return (
            f'<span style="font-size:10px;font-weight:700;padding:2px 8px;'
            f'border-radius:99px;background:{bg};color:{color};">{label}</span>'
        )

    if view == "east":
        groups = [("Eastern Conference", [r for r in rows if r["conf"] == "East"])]
        sort_key = "conf_rank"
    elif view == "west":
        groups = [("Western Conference", [r for r in rows if r["conf"] == "West"])]
        sort_key = "conf_rank"
    else:
        groups = [("Overall Standings", rows)]
        sort_key = "overall_rank"

    for title, group in groups:
        group = sorted(group, key=lambda r: r.get(sort_key, 99))

        th = ('padding:9px 10px;font-size:10px;font-weight:700;text-transform:uppercase;'
              'letter-spacing:.05em;color:#94a3b8;text-align:center;white-space:nowrap;'
              'border-bottom:1px solid #1e293b;')

        header = (
            f'<div style="background:#0f172a;border-radius:12px;overflow:hidden;'
            f'box-shadow:0 2px 12px rgba(0,0,0,0.2);">'
            f'<table style="width:100%;border-collapse:collapse;font-family:system-ui,sans-serif;">'
            f'<thead><tr>'
            f'<th style="{th}text-align:left;padding-left:16px;width:28px;">#</th>'
            f'<th style="{th}text-align:left;min-width:180px;">Team</th>'
            f'<th style="{th}">W</th>'
            f'<th style="{th}">L</th>'
            f'<th style="{th}">PCT</th>'
            f'<th style="{th}">Home</th>'
            f'<th style="{th}">Road</th>'
            f'<th style="{th}">ORTG</th>'
            f'<th style="{th}">DRTG</th>'
            f'<th style="{th}">NET RTG</th>'
            f'<th style="{th}">Status</th>'
            f'</tr></thead><tbody>'
        )

        body = ""
        for i, r in enumerate(group):
            rank     = r.get(sort_key, "")
            status   = r.get("status", "")
            colors   = get_team_colors(r["name"])
            primary  = colors["primary"]
            logo_url = get_team_logo_url(r["name"])
            logo_html = (
                f'<img src="{logo_url}" style="width:28px;height:28px;object-fit:contain;'
                f'vertical-align:middle;margin-right:10px;" onerror="this.style.display=\'none\'">'
                if logo_url else ""
            )
            ortg = f"{r['ortg']:.1f}" if r.get("ortg") else DASH
            drtg = f"{r['drtg']:.1f}" if r.get("drtg") else DASH
            bg   = "#0f172a" if i % 2 == 0 else "#111827"

            # Section dividers
            divider = ""
            conf_rank = r.get("conf_rank", 0)
            if view != "overall" and conf_rank in (7, 11):
                divider = (
                    f'<tr><td colspan="11" style="padding:0;background:#0f172a;">'
                    f'<div style="border-top:1px dashed #334155;margin:0;"></div>'
                    f'</td></tr>'
                )

            # Color bar + rank
            td = 'padding:10px 10px;text-align:center;font-size:13px;color:#cbd5e1;'

            body += (
                divider +
                f'<tr style="background:{bg};border-bottom:1px solid #1e293b;" '
                f'onmouseover="this.style.background=\'#1e293b\'" '
                f'onmouseout="this.style.background=\'{bg}\'">'
                f'<td style="padding:10px 6px 10px 0;text-align:center;">'
                f'<div style="display:flex;align-items:center;gap:0;">'
                f'<div style="width:3px;height:36px;background:{primary};border-radius:0 2px 2px 0;margin-right:10px;"></div>'
                f'<span style="font-size:12px;color:#64748b;font-weight:600;">{rank}</span>'
                f'</div></td>'
                f'<td style="padding:10px 12px;">'
                f'<div style="display:flex;align-items:center;">'
                + logo_html +
                f'<span style="font-size:13px;font-weight:600;color:#f1f5f9;">{r["name"]}</span>'
                f'</div></td>'
                f'<td style="{td}font-weight:700;color:#f1f5f9;">{r["w"]}</td>'
                f'<td style="{td}color:#94a3b8;">{r["l"]}</td>'
                f'<td style="{td}color:#94a3b8;">{r["pct"]:.3f}</td>'
                f'<td style="{td}font-size:12px;">{record(r.get("w_home"), r.get("l_home"))}</td>'
                f'<td style="{td}font-size:12px;">{record(r.get("w_road"), r.get("l_road"))}</td>'
                f'<td style="{td}font-size:12px;color:#94a3b8;">{ortg}</td>'
                f'<td style="{td}font-size:12px;color:#94a3b8;">{drtg}</td>'
                f'<td style="{td}">{net_fmt(r.get("net_rtg"))}</td>'
                f'<td style="padding:10px 10px;text-align:center;">{status_pill(status)}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<p style="font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">{title}</p>'
            f'{header}{body}</tbody></table></div>',
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

    # Legend
    st.markdown(
        '<p style="font-size:11px;color:#888;margin-top:4px;">'
        '<span style="color:#16a34a;font-weight:600;">● Playoffs</span> — Top 6 in conference &nbsp;|&nbsp; '
        '<span style="color:#d97706;font-weight:600;">● Play-In</span> — Seeds 7–10 &nbsp;|&nbsp; '
        '<span style="color:#6b7280;font-weight:600;">● Missed</span> — Seeds 11–15</p>',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("**Select a team to view their full stats card:**")
    team_names = [r["name"] for r in sorted(rows, key=lambda r: r["name"])]
    selected = st.selectbox("Select team", [""] + team_names, key=f"standings_team_{view}")
    if selected:
        with st.spinner(f"Loading {selected}..."):
            team_stats = get_team_full_stats(selected)
        if "error" not in team_stats:
            render_team_card(team_stats)


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

tab_lookup, tab_standings, tab_schedule, tab_boxscore, tab_player_cmp, tab_team_cmp, tab_draft = st.tabs([
    "Search",
    "Standings",
    "Schedule",
    "Games",
    "Compare Players",
    "Compare Teams",
    "Draft Lottery",
])


# ---------------------------------------------------------------------------
# Tab 1 — Lookup
# ---------------------------------------------------------------------------

with tab_lookup:

    # ── Live / Today's Games strip ────────────────────────────────────────
    import datetime as _dt
    _today_str   = _dt.date.today().strftime("%Y-%m-%d")
    _today_games = _cached_todays_games(_today_str)

    if _today_games:
        live_games   = [g for g in _today_games if g.get("is_live")]
        final_games  = [g for g in _today_games if g.get("is_final")]
        upcoming     = [g for g in _today_games if not g.get("is_live") and not g.get("is_final")]
        has_live     = bool(live_games)

        section_label = (
            '<span class="live-dot"></span><span style="color:#ef4444;font-weight:700;font-size:13px;">Live Now</span>'
            if has_live else
            '<span style="font-size:13px;font-weight:700;color:#f1f5f9;">Today\'s Games</span>'
        )

        tiles_html = ""
        for g in _today_games:
            is_live  = g.get("is_live", False)
            is_final = g.get("is_final", False)
            a_pts = g.get("away_pts")
            h_pts = g.get("home_pts")
            a_won = is_final and a_pts is not None and h_pts is not None and a_pts > h_pts
            h_won = is_final and a_pts is not None and h_pts is not None and h_pts > a_pts

            a_logo = get_team_logo_url(g["away_name"]) or ""
            h_logo = get_team_logo_url(g["home_name"]) or ""
            a_name = g["away_name"].split()[-1]
            h_name = g["home_name"].split()[-1]

            if is_live:
                status_txt  = g.get("status_txt", "LIVE")
                status_html = (f'<div style="font-size:9px;font-weight:800;color:#ef4444;'
                               f'letter-spacing:.05em;margin-bottom:8px;">'
                               f'<span class="live-dot"></span>{status_txt}</div>')
                tile_border = "border:1px solid rgba(239,68,68,0.35);"
                top_glow    = "box-shadow:0 0 0 1px rgba(239,68,68,0.15);"
            elif is_final:
                status_html = ('<div style="font-size:9px;font-weight:600;color:#475569;'
                               'letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px;">Final</div>')
                tile_border = "border:1px solid #1e293b;"
                top_glow    = ""
            else:
                status_html = (f'<div style="font-size:9px;color:#475569;margin-bottom:8px;">'
                               f'{g.get("status_txt","TBD")}</div>')
                tile_border = "border:1px solid #1e293b;"
                top_glow    = ""

            def _logo(url, sz=24):
                return (f'<img src="{url}" style="width:{sz}px;height:{sz}px;object-fit:contain;" '
                        f'onerror="this.style.display:\'none\'">') if url else ""

            def _row(logo, name, pts, won):
                nc = "#f1f5f9" if won else "#94a3b8"
                fw = "700" if won else "400"
                sc = "#ffffff" if won else "#64748b"
                sf = "700" if won else "400"
                score = f'<span style="font-size:15px;font-weight:{sf};color:{sc};min-width:28px;text-align:right;">{pts}</span>' if pts is not None else '<span style="min-width:28px;"></span>'
                return (
                    f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                    f'{_logo(logo)}'
                    f'<span style="font-size:13px;font-weight:{fw};color:{nc};flex:1;">{name}</span>'
                    f'{score}</div>'
                )

            tiles_html += (
                f'<div style="background:#111827;{tile_border}{top_glow}'
                f'border-radius:10px;padding:12px 14px;min-width:170px;flex:1;max-width:210px;">'
                + status_html
                + _row(a_logo, a_name, a_pts, a_won)
                + _row(h_logo, h_name, h_pts, h_won)
                + '</div>'
            )

        today_label = (
            '<span class="live-dot"></span>'
            '<span style="font-size:12px;font-weight:800;color:#ef4444;letter-spacing:.04em;text-transform:uppercase;">Live Now</span>'
            if has_live else
            f'<span style="font-size:12px;font-weight:700;color:#94a3b8;">'
            f'{_dt.date.today().strftime("%A, %B %-d")}</span>'
        )

        st.markdown(
            f'<div style="margin-bottom:22px;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">'
            f'<div style="display:flex;align-items:center;gap:6px;">{today_label}</div>'
            f'<span style="font-size:11px;color:#334155;">{_dt.date.today().strftime("%A, %B %-d") if has_live else ""}</span>'
            f'</div>'
            f'<div style="display:flex;gap:10px;flex-wrap:wrap;">{tiles_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Init chat history ─────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # ── Suggestion chips (only when chat is empty) ────────────────────────
    if not st.session_state["chat_history"]:
        st.markdown(
            '<p style="font-size:11px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.08em;color:#334155;margin-bottom:10px;">Try asking about</p>',
            unsafe_allow_html=True
        )
        chip_cols = st.columns(4)
        for i, suggestion in enumerate(SUGGESTIONS):
            with chip_cols[i % 4]:
                if st.button(suggestion, key=f"chip_{i}", use_container_width=True):
                    st.session_state["pending_query"] = suggestion
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Render existing chat history ──────────────────────────────────────
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg["content"])
            else:
                if msg.get("card"):
                    msg["card"]()
                if msg.get("content"):
                    st.write(msg["content"])
                if msg.get("sources"):
                    with st.expander(f"Sources ({len(msg['sources'])})", expanded=False):
                        for s in msg["sources"]:
                            domain = s.get("domain", "")
                            title  = s.get("title", domain)
                            url    = s.get("url", "")
                            if url:
                                st.markdown(
                                    f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:0.5px solid #f0f0f0;">' +
                                    f'<img src="https://www.google.com/s2/favicons?domain={domain}&sz=16" style="width:16px;height:16px;" onerror="this.style.display=\'none\'">\n' +
                                    f'<a href="{url}" target="_blank" style="font-size:13px;font-weight:500;color:#2563eb;text-decoration:none;">{title}</a></div>',
                                    unsafe_allow_html=True
                                )

    # ── Chat input ────────────────────────────────────────────────────────
    pending = st.session_state.pop("pending_query", None)
    query   = st.chat_input("Ask anything about players, teams, or stats...") or pending

    if query:
        st.session_state["chat_history"].append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Build LLM history for context (text only, last 6 turns)
        llm_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["chat_history"][:-1]
            if m.get("content")
        ][-6:]

        query_lower = query.lower()
        player_name = extract_single_player(query)
        teams       = extract_teams(query)

        is_rankings = any(k in query_lower for k in [
            "ranking", "rankings", "best teams", "top teams",
            "league standings", "which team is best", "team ratings",
        ])
        is_game_log = any(k in query_lower for k in GAME_LOG_KEYWORDS) and bool(teams)

        n_games = 5
        for word in query_lower.split():
            if word.isdigit():
                n_games = min(int(word), 10)
                break

        card_fn  = None
        analysis = ""
        sources  = []

        with st.chat_message("assistant"):
            if is_rankings:
                with st.spinner("Loading league rankings..."):
                    rankings = get_team_rankings()
                render_rankings_table(rankings)
                card_fn = lambda: render_rankings_table(get_team_rankings())

            elif is_game_log and teams:
                team = teams[0]
                with st.spinner(f"Loading {team} last {n_games} games..."):
                    log = get_team_game_log(team, n_games)
                if isinstance(log, list):
                    render_game_log(team, log)
                    _t, _l = team, log
                    card_fn = lambda t=_t, l=_l: render_game_log(t, l)
                else:
                    st.warning(log.get("error", "Could not load game log."))

            elif player_name:
                with st.spinner(f"Loading {player_name}..."):
                    stats = get_player_season_stats(player_name)
                    bio   = get_player_bio(player_name)
                    zones = get_player_shot_zones(player_name)
                    acols = get_player_accolades(player_name)
                if "error" not in stats:
                    stats["_accolades"] = acols
                    render_player_card(stats, bio, zones)
                    _s, _b, _z = stats, bio, zones
                    card_fn = lambda s=_s, b=_b, z=_z: render_player_card(s, b, z)
                else:
                    with st.spinner(f"Looking up career stats for {player_name}..."):
                        career = get_player_career_stats(player_name)
                        if "error" not in career:
                            bio   = get_player_bio(player_name)
                            acols = get_player_accolades(player_name)
                        else:
                            parts = player_name.split()
                            alt   = f"{parts[0]} {parts[-1]}" if len(parts) >= 2 else None
                            if alt and alt != player_name:
                                career = get_player_career_stats(alt)
                                if "error" not in career:
                                    bio, acols = get_player_bio(alt), get_player_accolades(alt)
                                    player_name = alt
                    if "error" not in career:
                        render_career_card(player_name, career, bio, acols)
                        _p, _c, _b, _a = player_name, career, bio, acols
                        card_fn = lambda p=_p, c=_c, b=_b, a=_a: render_career_card(p, c, b, a)
                    else:
                        st.warning(f"Could not find stats for {player_name}. Try the full name.")

            elif teams and not is_game_log:
                with st.spinner("Loading team data..."):
                    stats = get_team_full_stats(teams[0])
                if "error" not in stats:
                    render_team_card(stats)
                    _s = stats
                    card_fn = lambda s=_s: render_team_card(s)
                else:
                    st.warning(stats["error"])

            # Always run agent for analysis
            if not is_rankings:
                st.divider()
                with st.spinner("Analyzing..."):
                    analysis, sources = run_agent(query, history=llm_history)
                st.write(analysis)
                if sources:
                    with st.expander(f"Sources ({len(sources)})", expanded=False):
                        for s in sources:
                            domain = s.get("domain", "")
                            title  = s.get("title", domain)
                            url    = s.get("url", "")
                            if url:
                                st.markdown(
                                    f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:0.5px solid #f0f0f0;">' +
                                    f'<img src="https://www.google.com/s2/favicons?domain={domain}&sz=16" style="width:16px;height:16px;" onerror="this.style.display=\'none\'">\n' +
                                    f'<a href="{url}" target="_blank" style="font-size:13px;font-weight:500;color:#2563eb;text-decoration:none;">{title}</a></div>',
                                    unsafe_allow_html=True
                                )

        # Save to history
        st.session_state["chat_history"].append({
            "role":    "assistant",
            "content": analysis,
            "sources": sources,
            "card":    card_fn,
        })

    # Clear button
    if st.session_state["chat_history"]:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()

    # Live game refresh — manual only to avoid blocking all other tabs
    if _today_games and any(g.get("is_live") for g in _today_games):
        if st.button("⟳ Refresh scores", key="home_refresh_live"):
            st.rerun()


# Tab 2 — Standings
# ---------------------------------------------------------------------------

with tab_standings:
    st.markdown("#### 2025-26 NBA Standings")

    with st.spinner("Loading standings..."):
        standing_rows = _cached_standings()

    if standing_rows:
        view_opt = st.radio(
            "View",
            ["Overall", "Eastern Conference", "Western Conference"],
            horizontal=True,
            key="standings_view"
        )
        view_map = {
            "Overall":            "overall",
            "Eastern Conference": "east",
            "Western Conference": "west",
        }
        render_standings(standing_rows, view=view_map[view_opt])
    else:
        st.warning("Could not load standings. Check your connection and refresh.")


# ---------------------------------------------------------------------------
# Tab 3 — Schedule
# ---------------------------------------------------------------------------

with tab_schedule:
    st.markdown("#### Team Schedule")
    all_teams_sched = sorted(list(set(TEAM_MAP.values())))
    sched_col1, sched_col2 = st.columns([2, 1])
    with sched_col1:
        sched_team = st.selectbox("Select team", all_teams_sched, key="sched_team")
    with sched_col2:
        sched_season = st.selectbox("Season", [
            "2025-26", "2024-25", "2023-24", "2022-23", "2021-22"
        ], key="sched_season")

    if st.button("Load Schedule", key="btn_sched"):
        with st.spinner(f"Loading {sched_team} schedule..."):
            sched = get_team_schedule(sched_team, sched_season)

        if isinstance(sched, dict) and "error" in sched:
            st.warning(sched["error"])
        elif sched:
            wins      = sum(1 for g in sched if g.get("result") == "W")
            losses    = sum(1 for g in sched if g.get("result") == "L")
            po_games  = [g for g in sched if g.get("playoffs")]
            reg_games = [g for g in sched if not g.get("playoffs")]

            # Team colors for header
            sc = get_team_colors(sched_team)
            primary_c = sc["primary"]
            on_bg_c   = sc["on_bg"]
            logo_url  = get_team_logo_url(sched_team)
            logo_tag  = (f'<img src="{logo_url}" style="width:44px;height:44px;object-fit:contain;" '
                         f'onerror="this.style.display=\'none\'">' if logo_url else "")

            # Season header card
            st.markdown(
                f'<div style="background:{primary_c};border-radius:12px;padding:16px 20px;'
                f'display:flex;align-items:center;gap:16px;margin-bottom:16px;">'
                + logo_tag +
                f'<div>'
                f'<p style="font-size:16px;font-weight:700;color:{on_bg_c};margin:0;">{sched_team}</p>'
                f'<p style="font-size:13px;color:rgba(255,255,255,0.7);margin:0;">'
                f'{sched_season} · {wins}W – {losses}L · {len(sched)} games</p>'
                f'</div></div>',
                unsafe_allow_html=True
            )

            for section_label, games in [("Regular Season", reg_games), ("Playoffs", po_games)]:
                if not games:
                    continue

                is_po = section_label == "Playoffs"
                games_sorted = sorted(games, key=lambda x: x["date"])

                th = ('padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;'
                      'letter-spacing:.05em;color:#94a3b8;text-align:center;'
                      'border-bottom:1px solid #1e293b;')

                header = (
                    f'<div style="background:#0f172a;border-radius:12px;overflow:hidden;'
                    f'margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.2);">'
                    f'<div style="padding:10px 16px;border-bottom:1px solid #1e293b;">'
                    f'<span style="font-size:12px;font-weight:700;color:#f1f5f9;'
                    f'text-transform:uppercase;letter-spacing:.06em;">'
                    f'{"🏆 " if is_po else ""}{section_label}</span>'
                    f'</div>'
                    f'<div style="overflow-x:auto;">'
                    f'<table style="width:100%;border-collapse:collapse;">'
                    f'<thead><tr>'
                    f'<th style="{th}text-align:left;padding-left:16px;">Date</th>'
                    f'<th style="{th}text-align:left;">Opponent</th>'
                    f'<th style="{th}">H/A</th>'
                    f'<th style="{th}">W/L</th>'
                    f'<th style="{th}">Score</th>'
                    f'<th style="{th}">Record</th>'
                    f'</tr></thead><tbody>'
                )

                rows_html = ""
                for i, g in enumerate(games_sorted):
                    result  = g.get("result", "")
                    is_home = g.get("home", False)
                    ha_label = "Home" if is_home else "Away"
                    ha_color = "#3b82f6" if is_home else "#8b5cf6"
                    opp     = g.get("opponent", "")
                    opp_abbr = g.get("opp_abbr", "")
                    pts     = g.get("pts")
                    opp_pts = g.get("opp_pts")
                    cum_w   = g.get("cum_w")
                    cum_l   = g.get("cum_l")
                    rec_s   = f"{cum_w}–{cum_l}" if cum_w is not None else ""

                    # Pretty date: "Mon, Apr 28"
                    try:
                        from datetime import datetime as _dtp
                        d = _dtp.strptime(str(g.get("date", "")), "%Y-%m-%d")
                        date_str = d.strftime("%a, %b %-d")
                    except Exception:
                        date_str = str(g.get("date", ""))

                    # Score string
                    if pts is not None and opp_pts is not None:
                        if result == "W":
                            score_str = f'<span style="color:#22c55e;font-weight:700;">{pts}</span><span style="color:#64748b;">–{opp_pts}</span>'
                        else:
                            score_str = f'<span style="color:#94a3b8;">{pts}</span><span style="color:#ef4444;font-weight:700;">–{opp_pts}</span>'
                    elif pts is not None:
                        score_str = str(pts)
                    else:
                        score_str = "—"

                    res_color = "#22c55e" if result == "W" else ("#ef4444" if result == "L" else "#94a3b8")
                    res_bg    = "rgba(34,197,94,0.1)" if result == "W" else ("rgba(239,68,68,0.1)" if result == "L" else "transparent")
                    row_bg    = "#0f172a" if i % 2 == 0 else "#111827"

                    # Opponent logo
                    opp_logo = ""
                    try:
                        opp_url = get_team_logo_url(opp)
                        if opp_url:
                            opp_logo = (f'<img src="{opp_url}" style="width:22px;height:22px;'
                                       f'object-fit:contain;vertical-align:middle;margin-right:8px;" '
                                       f'onerror="this.style.display=\'none\'">')
                    except Exception:
                        pass

                    td = 'padding:10px 12px;text-align:center;'
                    rows_html += (
                        f'<tr style="background:{row_bg};border-bottom:1px solid #1e293b;">'
                        f'<td style="{td}text-align:left;padding-left:16px;font-size:12px;color:#94a3b8;white-space:nowrap;">{date_str}</td>'
                        f'<td style="{td}text-align:left;">'
                        f'{opp_logo}<span style="font-size:13px;font-weight:500;color:#f1f5f9;">{opp}</span></td>'
                        f'<td style="{td}">'
                        f'<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:99px;'
                        f'background:rgba({("59,130,246" if is_home else "139,92,246")},0.15);color:{ha_color};">'
                        f'{ha_label}</span></td>'
                        f'<td style="{td}">'
                        f'<span style="font-size:13px;font-weight:800;padding:3px 10px;border-radius:6px;'
                        f'background:{res_bg};color:{res_color};">{result or "—"}</span></td>'
                        f'<td style="{td}font-size:13px;">{score_str}</td>'
                        f'<td style="{td}font-size:12px;font-weight:600;color:#64748b;">{rec_s}</td>'
                        f'</tr>'
                    )

                st.markdown(
                    header + rows_html +
                    '</tbody></table></div></div>',
                    unsafe_allow_html=True
                )


# ---------------------------------------------------------------------------
# Tab 4 — Games (Calendar + Box Score)
# ---------------------------------------------------------------------------

with tab_boxscore:
    import datetime as _dt

    st.markdown("#### Games")

    # ── Date picker ───────────────────────────────────────────────────────
    gcol1, gcol2 = st.columns([3, 1])
    with gcol1:
        selected_date = st.date_input(
            "Select date",
            value=_dt.date.today(),
            min_value=_dt.date(2024, 10, 1),
            max_value=_dt.date(2026, 9, 1),
            key="games_date",
        )
    with gcol2:
        games_season = st.selectbox(
            "Season", ["2025-26", "2024-25", "2023-24"], key="games_season"
        )

    date_str   = selected_date.strftime("%Y-%m-%d")
    is_today  = selected_date == _dt.date.today()
    is_future = selected_date > _dt.date.today()

    # Auto-detect season type from date
    games_stype = detect_season_type(selected_date)

    badge_color = {
        "Playoffs":       "#1d4ed8",
        "PlayIn":         "#d97706",
        "Regular Season": "#16a34a",
    }.get(games_stype, "#888")

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">' +
        f'<p style="font-size:16px;font-weight:700;margin:0;">{selected_date.strftime("%A, %B %d, %Y")}</p>' +
        f'<span style="font-size:11px;font-weight:700;padding:2px 10px;border-radius:99px;' +
        f'background:{badge_color};color:#fff;">{games_stype}</span>' +
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Load games ────────────────────────────────────────────────────────
    if is_today:
        rc1, rc2 = st.columns([5, 1])
        with rc2:
            if st.button("⟳ Refresh", key="refresh_games", use_container_width=True):
                st.rerun()

    with st.spinner("Loading games..."):
        if is_today:
            # Live API for today
            day_games = get_todays_games(date_str)
            if not day_games:
                day_games = get_games_on_date(date_str, games_season, games_stype)
        else:
            # get_games_on_date handles both past (leaguegamefinder) and future (scoreboardv2)
            day_games = get_games_on_date(date_str, games_season, games_stype)

    if not day_games:
        st.info("No games found for this date." + (" Check back closer to tip-off." if is_future else ""))
    else:
        st.markdown(f"*{len(day_games)} game{'s' if len(day_games)!=1 else ''}*")

        # Show game tiles — click to load box score
        game_cols = st.columns(min(len(day_games), 3))
        selected_game_id = st.session_state.get("selected_game_id")
        selected_game    = st.session_state.get("selected_game_meta")

        for i, g in enumerate(day_games):
            with game_cols[i % 3]:
                is_live   = g.get("is_live", False)
                is_final  = g.get("finished", False)
                status_txt = g.get("status_txt", "")

                away_logo = get_team_logo_url(g["away_name"])
                home_logo = get_team_logo_url(g["home_name"])
                away_name = g["away_name"].split()[-1]
                home_name = g["home_name"].split()[-1]

                a_pts = g.get("away_pts")
                h_pts = g.get("home_pts")
                has_score = (is_final or is_live) and a_pts is not None
                away_won  = is_final and has_score and a_pts > (h_pts or 0)
                home_won  = is_final and has_score and (h_pts or 0) > a_pts

                # Series score
                away_sw = g.get("away_series_wins", 0) or 0
                home_sw = g.get("home_series_wins", 0) or 0
                series_str = g.get("series_text") or (f"{away_sw}–{home_sw}" if (away_sw or home_sw) else "")
                is_po = games_stype == "Playoffs"

                # Status line
                if is_live:
                    status_html = (
                        f'<span style="font-size:9px;font-weight:800;color:#ef4444;'
                        f'letter-spacing:.04em;"><span class="live-dot"></span>{status_txt}</span>'
                        + (f' <span style="font-size:9px;color:#475569;margin-left:6px;">{series_str}</span>' if is_po and series_str else "")
                    )
                    tile_border = "border:1px solid rgba(239,68,68,0.4);"
                elif is_final:
                    status_html = (
                        '<span style="font-size:9px;font-weight:600;color:#475569;'
                        'text-transform:uppercase;letter-spacing:.06em;">Final</span>'
                        + (f' <span style="font-size:9px;color:#475569;margin-left:6px;">{series_str}</span>' if is_po and series_str else "")
                    )
                    tile_border = "border:1px solid #1e293b;"
                else:
                    status_html = f'<span style="font-size:9px;color:#475569;">{status_txt or "Upcoming"}</span>'
                    tile_border = "border:1px solid #1e293b;"

                def _logo(url):
                    return (f'<img src="{url}" style="width:24px;height:24px;object-fit:contain;" '
                            f'onerror="this.style.display=\'none\'">') if url else ""

                def _row(logo, name, pts, won):
                    nc = "#f1f5f9" if won else "#94a3b8"
                    fw = "700" if won else "400"
                    sc = "#ffffff" if won else "#64748b"
                    sf = "700" if won else "400"
                    score = (f'<span style="font-size:15px;font-weight:{sf};color:{sc};'
                             f'min-width:28px;text-align:right;">{pts}</span>') if pts is not None else '<span style="min-width:28px;"></span>'
                    return (
                        f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;">'
                        f'{logo}{chr(10)}'
                        f'<span style="font-size:13px;font-weight:{fw};color:{nc};flex:1;">{name}</span>'
                        f'{score}</div>'
                    )

                tile_html = (
                    f'<div style="background:#111827;{tile_border}border-radius:10px;'
                    f'padding:12px 14px;margin-bottom:4px;">'
                    f'<div style="margin-bottom:8px;">{status_html}</div>'
                    + _row(away_logo and _logo(away_logo), away_name, a_pts if has_score else None, away_won)
                    + _row(home_logo and _logo(home_logo), home_name, h_pts if has_score else None, home_won)
                    + '</div>'
                )
                st.markdown(tile_html, unsafe_allow_html=True)

                btn_label    = "View Box Score" if (is_final or is_live) else "Scheduled"
                btn_disabled = not (is_final or is_live)
                if st.button(btn_label, key=f"game_btn_{g['game_id']}", use_container_width=True, disabled=btn_disabled):
                    st.session_state["selected_game_id"]   = g["game_id"]
                    st.session_state["selected_game_meta"] = g
                    st.session_state["selected_stype"]     = games_stype
                    st.rerun()

        # Live refresh — manual button to avoid blocking tab switches
        has_live = any(g.get("is_live") for g in day_games)
        if has_live and is_today:
            if st.button("⟳ Refresh live scores", key="games_live_refresh", use_container_width=False):
                st.rerun()
            st.caption("🔴 Live game in progress — click to refresh")

    # ── Box score display ─────────────────────────────────────────────────
    if st.session_state.get("selected_game_id"):
        g       = st.session_state.get("selected_game_meta", {})
        game_id = st.session_state["selected_game_id"]
        stype   = st.session_state.get("selected_stype", "Regular Season")

        with st.spinner("Loading box score..."):
            from agent.tools import ABBR_TO_TEAM
            # Use game_id directly — avoids re-searching by team/date which can miss
            result_bs = get_boxscore_by_game_id(game_id, season_type=stype)

            # Patch in known meta from the tile
            if "error" not in result_bs:
                if not result_bs.get("home_abbr") and g.get("home_abbr"):
                    result_bs["home_abbr"] = g["home_abbr"]
                if not result_bs.get("away_abbr") and g.get("away_abbr"):
                    result_bs["away_abbr"] = g["away_abbr"]
                if not result_bs.get("date") and g.get("date"):
                    result_bs["date"] = g["date"]

        if "error" in result_bs:
            st.warning(result_bs["error"])
        else:
            teams_data      = result_bs.get("teams", {})
            home_abbr       = result_bs.get("home_abbr", "").strip().upper()
            away_abbr       = result_bs.get("away_abbr", "").strip().upper()
            game_number     = result_bs.get("game_number", 0)
            away_series_w   = result_bs.get("series_away_wins", 0)
            home_series_w   = result_bs.get("series_home_wins", 0)
            home_seed       = result_bs.get("home_seed")
            away_seed       = result_bs.get("away_seed")
            is_playoffs     = result_bs.get("season_type","") == "Playoffs"
            game_date       = result_bs.get("date", "")
            arena           = result_bs.get("arena", "")
            attendance      = result_bs.get("attendance", "")

            home_full = ABBR_TO_TEAM.get(home_abbr, home_abbr)
            away_full = ABBR_TO_TEAM.get(away_abbr, away_abbr)
            home_c    = get_team_colors(home_full)
            away_c    = get_team_colors(away_full)

            scores     = {a.strip().upper(): teams_data[a]["total_pts"] for a in teams_data}
            home_score = scores.get(home_abbr, 0)
            away_score = scores.get(away_abbr, 0)
            home_wins  = home_score > away_score

            def _logo(name, sz=44):
                url = get_team_logo_url(name)
                return (f'<img src="{url}" style="width:{sz}px;height:{sz}px;object-fit:contain;" ' +
                        'onerror="this.style.display=\'none\'">') if url else ""

            # ── Scoreboard ───────────────────────────────────────────────
            # Date + game info line
            game_label = ""
            if is_playoffs and game_number:
                game_label = f"Game {game_number}"
            meta_parts = [game_date]
            if arena:      meta_parts.append(arena)
            if attendance: meta_parts.append(f"Att: {attendance}")

            def scoreboard_side(full, abbr, score, seed, series_w, colors, is_home, won):
                primary = colors["primary"]
                on_bg   = colors["on_bg"]
                logo    = _logo(full, 44)
                align   = "right" if is_home else "left"
                seed_badge = (
                    f'<span style="font-size:11px;font-weight:800;padding:2px 8px;border-radius:99px;' +
                    f'background:rgba(255,255,255,0.18);color:#fff;">#{seed}</span>'
                ) if seed else ""
                series_block = (
                    f'<div style="text-align:center;padding:0 12px;">' +
                    f'<p style="font-size:30px;font-weight:900;color:rgba(255,255,255,0.95);margin:0;line-height:1;">{series_w}</p>' +
                    f'<p style="font-size:9px;color:rgba(255,255,255,0.55);margin:0;text-transform:uppercase;letter-spacing:.06em;">wins</p>' +
                    f'</div>'
                ) if (is_playoffs and game_number) else ""
                return (
                    f'<div style="flex:1;background:{primary};padding:18px 22px;' +
                    f'display:flex;flex-direction:{"row-reverse" if is_home else "row"};' +
                    f'align-items:center;gap:14px;">' +
                    logo +
                    f'<div style="flex:1;text-align:{align};">' +
                    f'<p style="font-size:10px;font-weight:600;color:rgba(255,255,255,0.55);margin:0;text-transform:uppercase;">{"Home" if is_home else "Away"}</p>' +
                    f'<div style="display:flex;align-items:center;gap:8px;{"flex-direction:row-reverse;" if is_home else ""}margin:2px 0;">' +
                    f'<p style="font-size:17px;font-weight:700;color:{on_bg};margin:0;">{full}</p>' +
                    seed_badge +
                    f'</div>' +
                    f'<p style="font-size:44px;font-weight:{"900" if won else "600"};' +
                    f'color:{"#fff" if won else "rgba(255,255,255,0.4)"};margin:0;line-height:1;">{score}</p>' +
                    f'</div>' +
                    series_block +
                    f'</div>'
                )

            mid_html = (
                f'<div style="background:#111;padding:14px 18px;text-align:center;' +
                f'min-width:130px;display:flex;flex-direction:column;justify-content:center;gap:6px;">' +
                (f'<p style="font-size:14px;font-weight:800;color:#fff;margin:0;letter-spacing:.02em;">{game_label}</p>' if game_label else "") +
                f'<p style="font-size:11px;color:#666;margin:0;">{game_date}</p>' +
                (f'<p style="font-size:22px;font-weight:900;color:#fff;margin:0;letter-spacing:.02em;">{away_series_w}–{home_series_w}</p>' +
                 f'<p style="font-size:9px;color:#555;margin:0;text-transform:uppercase;">series</p>'
                 if is_playoffs and game_number else "") +
                f'</div>'
            )

            st.markdown(
                f'<div style="display:flex;border-radius:14px;overflow:hidden;' +
                f'box-shadow:0 4px 24px rgba(0,0,0,0.3);margin-bottom:22px;">' +
                scoreboard_side(away_full, away_abbr, away_score, away_seed, away_series_w, away_c, False, not home_wins) +
                mid_html +
                scoreboard_side(home_full, home_abbr, home_score, home_seed, home_series_w, home_c, True, home_wins) +
                f'</div>',
                unsafe_allow_html=True
            )

            # ── Box scores ───────────────────────────────────────────────
            def build_bs_card(abbr, tdata, colors):
                players = tdata["players"]
                if not players:
                    return ""
                full    = ABBR_TO_TEAM.get(abbr.upper(), abbr)
                primary = colors["primary"]
                on_bg   = colors["on_bg"]
                bg      = colors["pastel_bg"]
                muted   = colors["on_bg_muted"]
                border  = colors["pastel_border"]

                th = f'font-size:9px;text-transform:uppercase;font-weight:600;color:{muted};padding:6px 5px;text-align:center;'
                head = (
                    f'<tr style="background:{primary}22;border-bottom:1px solid {border};">' +
                    f'<th style="{th}text-align:left;min-width:90px;">Player</th>' +
                    f'<th style="{th}">MIN</th><th style="{th}">PTS</th><th style="{th}">REB</th>' +
                    f'<th style="{th}">AST</th><th style="{th}">STL</th><th style="{th}">BLK</th>' +
                    f'<th style="{th}">TOV</th><th style="{th}">FG</th><th style="{th}">3PT</th>' +
                    f'<th style="{th}">FT</th><th style="{th}">+/-</th></tr>'
                )
                max_pts = max(p["pts"] for p in players)
                rows = ""
                for p in players:
                    pm   = p["plus_minus"]
                    pms  = f'{"+" if pm>=0 else ""}{pm}'
                    pmc  = "#16a34a" if pm>0 else ("#dc2626" if pm<0 else muted)
                    top  = p["pts"] == max_pts
                    td   = f'padding:7px 5px;text-align:center;font-size:12px;color:{muted};'
                    rows += (
                        f'<tr style="border-bottom:0.5px solid {border};">' +
                        f'<td style="padding:7px 8px;font-size:12px;font-weight:{"700" if top else "500"};color:{on_bg};">{p["name"]}</td>' +
                        f'<td style="{td}font-size:11px;">{p["min"]}</td>' +
                        f'<td style="{td}font-size:13px;font-weight:{"700" if top else "500"};color:{on_bg};">{p["pts"]}</td>' +
                        f'<td style="{td}color:{on_bg};">{p["reb"]}</td>' +
                        f'<td style="{td}color:{on_bg};">{p["ast"]}</td>' +
                        f'<td style="{td}">{p["stl"]}</td>' +
                        f'<td style="{td}">{p["blk"]}</td>' +
                        f'<td style="{td}">{p["tov"]}</td>' +
                        f'<td style="{td}">{p["fg"]}</td>' +
                        f'<td style="{td}">{p["fg3"]}</td>' +
                        f'<td style="{td}">{p["ft"]}</td>' +
                        f'<td style="{td}font-weight:600;color:{pmc};">{pms}</td>' +
                        f'</tr>'
                    )
                return (
                    f'<div style="border:1px solid {border};border-radius:10px;overflow:hidden;">' +
                    f'<div style="background:{primary};padding:10px 14px;display:flex;align-items:center;gap:10px;">' +
                    _logo(full, 26) +
                    f'<span style="font-size:14px;font-weight:700;color:{on_bg};flex:1;">{full}</span>' +
                    f'<span style="font-size:22px;font-weight:800;color:{on_bg};">{tdata["total_pts"]}</span>' +
                    f'</div>' +
                    f'<div style="overflow-x:auto;background:{bg};">' +
                    f'<table style="width:100%;border-collapse:collapse;">' +
                    f'<thead>{head}</thead><tbody>{rows}</tbody></table></div></div>'
                )

            all_keys   = list(teams_data.keys())
            away_key   = next((a for a in all_keys if a.strip().upper()==away_abbr), all_keys[0])
            home_key   = next((a for a in all_keys if a.strip().upper()==home_abbr), all_keys[-1])
            left_html  = build_bs_card(away_key, teams_data[away_key], away_c)
            right_html = build_bs_card(home_key, teams_data[home_key], home_c)

            st.markdown(
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">' +
                left_html + right_html + '</div>',
                unsafe_allow_html=True
            )

        if st.button("Back to games", key="back_to_games"):
            del st.session_state["selected_game_id"]
            if "selected_game_meta" in st.session_state:
                del st.session_state["selected_game_meta"]
            st.rerun()

# Tab 5 — Draft Lottery Simulator
# ---------------------------------------------------------------------------

with tab_draft:
    import random

    # Official 2026 NBA lottery odds (per NBA.com — top 3 teams ALL share 14%)
    # Combinations out of 1000 (1001 total, one unused)
    LOTTERY_COMBOS = [140, 140, 140, 125, 105, 90, 75, 60, 45, 30, 20, 15, 10, 5]
    LOTTERY_PCT    = [14.0, 14.0, 14.0, 12.5, 10.5, 9.0, 7.5, 6.0, 4.5, 3.0, 2.0, 1.5, 1.0, 0.5]

    # 2025-26 confirmed play-in losers: Golden State, LA Clippers (West), Miami, Charlotte (East)
    # Traded pick situations (source: Tankathon / Hoops Rumors)
    TRADED_PICKS = {
        "Indiana Pacers":       {"owner": "LA Clippers",          "protected": "1-4,10-30",
                                 "note": "→ LAC if pick #5-9; IND keeps if top-4 or #10+"},
        "New Orleans Pelicans": {"owner": "Atlanta Hawks",         "protected": None,
                                 "note": "→ ATL (Hawks get better of NOP/MIL picks)"},
        "LA Clippers":          {"owner": "Oklahoma City Thunder", "protected": None,
                                 "note": "→ OKC (best of OKC/HOU/LAC three-way deal)"},
        "Washington Wizards":   {"owner": "New York Knicks",       "protected": 8,
                                 "note": "→ NYK if pick #9-14; WAS keeps if top-8"},
        "Phoenix Suns":         {"owner": "Washington Wizards",    "protected": None,
                                 "note": "WAS has swap rights (Brad Beal trade)"},
    }

    def run_lottery_sim(teams):
        """
        Simulate the NBA lottery using weighted combination draws.
        Returns list of (pick, team_dict) tuples in order 1-14.
        """
        names   = [t["name"] for t in teams]
        weights = LOTTERY_PCT[:len(names)]
        pool_n  = list(names)
        pool_w  = list(weights)
        lottery_picks = {}   # pick -> name

        # Draw picks 1-4
        for pick in range(1, 5):
            tot    = sum(pool_w)
            norm   = [w / tot for w in pool_w]
            idx    = random.choices(range(len(pool_n)), weights=norm, k=1)[0]
            winner = pool_n.pop(idx)
            pool_w.pop(idx)
            lottery_picks[pick] = winner

        # Remaining teams fill 5-14 in standing order (worst first = lowest seed)
        remaining = [n for n in names if n not in lottery_picks.values()]
        for i, name in enumerate(remaining, 5):
            lottery_picks[i] = name

        return [(p, lottery_picks[p]) for p in range(1, 15)]

    def compute_odds_matrix(teams, n_sim=50000):
        """
        Monte Carlo: probability of each team landing each pick.
        Returns dict: team_name -> [pct_pick1, pct_pick2, ..., pct_pick14]
        """
        counts = {t["name"]: [0]*14 for t in teams}
        for _ in range(n_sim):
            result = run_lottery_sim(teams)
            for pick, name in result:
                counts[name][pick-1] += 1
        pcts = {}
        for name, c in counts.items():
            pcts[name] = [round(v / n_sim * 100, 1) for v in c]
        return pcts

    st.markdown("#### 2026 NBA Draft Lottery Simulator")

    # Load lottery teams
    if "lottery_teams_cache" not in st.session_state:
        with st.spinner("Loading lottery teams..."):
            try:
                rows = _cached_standings()

                PLAYIN_LOSERS_2026 = {
                    "Golden State Warriors",
                    "LA Clippers",
                    "Miami Heat",
                    "Charlotte Hornets",
                }
                PLAYIN_WINNERS = {
                    "Portland Trail Blazers",
                    "Philadelphia 76ers",
                    "Orlando Magic",
                }

                eliminated = sorted(
                    [r for r in rows
                     if r.get("status") == "e"
                     and r["name"] not in PLAYIN_WINNERS
                     and r["name"] not in PLAYIN_LOSERS_2026],
                    key=lambda r: (r["w"], -r["l"])
                )
                west_losers = sorted(
                    [r for r in rows if r["name"] in {"Golden State Warriors", "LA Clippers"}],
                    key=lambda r: (r["w"], -r["l"])
                )
                heat    = next((r for r in rows if r["name"] == "Miami Heat"), None)
                hornets = next((r for r in rows if r["name"] == "Charlotte Hornets"), None)
                playin_losers_ordered = west_losers
                if heat:    playin_losers_ordered = playin_losers_ordered + [heat]
                if hornets: playin_losers_ordered = playin_losers_ordered + [hornets]
                lottery_teams = (eliminated + playin_losers_ordered)[:14]
                st.session_state["lottery_teams_cache"] = lottery_teams
            except Exception as _lottery_err:
                st.session_state["lottery_teams_cache"] = []
                st.warning(f"Could not load standings for lottery: {_lottery_err}")

    lottery_teams = st.session_state["lottery_teams_cache"]

    if not lottery_teams:
        st.info("Could not load standings. Please check your NBA API connection.")
    else:
        n = len(lottery_teams)
        odds_pcts = LOTTERY_PCT[:n]

        # ── Lottery Odds Table ────────────────────────────────────────────────
        th = ('padding:9px 12px;font-size:10px;font-weight:700;text-transform:uppercase;'
              'letter-spacing:.05em;color:#94a3b8;text-align:center;'
              'border-bottom:1px solid #1e293b;')

        rows_html = ""
        for i, team in enumerate(lottery_teams):
            odds_pct = odds_pcts[i] if i < len(odds_pcts) else 0
            color    = get_team_colors(team["name"])
            primary  = color["primary"]
            on_bg    = color["on_bg"]
            logo_url = get_team_logo_url(team["name"])
            logo_tag = (f'<img src="{logo_url}" style="width:28px;height:28px;object-fit:contain;'
                        f'vertical-align:middle;margin-right:10px;" onerror="this.style.display=\'none\'">'
                        if logo_url else "")

            # Bar width relative to max (14%)
            bar_pct = int(odds_pct / 14.0 * 100)

            # Trade annotation
            trade_info = TRADED_PICKS.get(team["name"])
            trade_html = ""
            if trade_info:
                trade_html = (
                    f'<div style="font-size:10px;color:#f59e0b;margin-top:2px;font-weight:500;">'
                    f'⇒ {trade_info["note"]}</div>'
                )

            # Play-in badge
            is_playin = team["name"] in {
                "Golden State Warriors", "LA Clippers", "Miami Heat", "Charlotte Hornets"
            }
            badge = (
                '<span style="font-size:9px;font-weight:700;padding:1px 6px;border-radius:99px;'
                'background:rgba(245,158,11,0.2);color:#f59e0b;margin-left:8px;">Play-In</span>'
            ) if is_playin else ""

            row_bg = "#0f172a" if i % 2 == 0 else "#111827"
            rows_html += (
                f'<tr style="background:{row_bg};border-bottom:1px solid #1e293b;">'
                f'<td style="padding:10px 8px 10px 0;text-align:center;">'
                f'<div style="display:flex;align-items:center;">'
                f'<div style="width:3px;height:36px;background:{primary};border-radius:0 2px 2px 0;margin-right:10px;"></div>'
                f'<span style="font-size:12px;color:#64748b;font-weight:600;">{i+1}</span>'
                f'</div></td>'
                f'<td style="padding:10px 12px;">'
                f'<div style="display:flex;align-items:center;">'
                + logo_tag +
                f'<div>'
                f'<span style="font-size:13px;font-weight:600;color:#f1f5f9;">{team["name"]}</span>'
                f'{badge}'
                + trade_html +
                f'</div></div></td>'
                f'<td style="padding:10px 12px;text-align:center;font-size:13px;color:#94a3b8;">'
                f'{team["w"]}–{team["l"]}</td>'
                f'<td style="padding:10px 16px;">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<div style="flex:1;background:#1e293b;border-radius:4px;height:8px;overflow:hidden;">'
                f'<div style="width:{bar_pct}%;height:100%;background:{primary};border-radius:4px;"></div>'
                f'</div>'
                f'<span style="font-size:13px;font-weight:700;color:#f1f5f9;min-width:38px;">{odds_pct}%</span>'
                f'</div></td>'
                f'</tr>'
            )

        st.markdown(
            f'<div style="background:#0f172a;border-radius:12px;overflow:hidden;'
            f'box-shadow:0 2px 12px rgba(0,0,0,0.2);margin-bottom:8px;">'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr>'
            f'<th style="{th}text-align:left;padding-left:16px;width:28px;">#</th>'
            f'<th style="{th}text-align:left;">Team</th>'
            f'<th style="{th}">Record</th>'
            f'<th style="{th}text-align:left;padding-left:16px;">Odds (#1 Pick)</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True
        )
        st.caption("Top 3 seeds share equal 14.0% odds per 2019 lottery reform · Odds reflect #1 pick probability")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Odds matrix ───────────────────────────────────────────────────────
        if st.checkbox("Show full odds matrix (all pick positions)", key="show_matrix"):
            if "odds_matrix" not in st.session_state:
                with st.spinner("Computing odds matrix (50,000 simulations)..."):
                    st.session_state["odds_matrix"] = compute_odds_matrix(lottery_teams)
            matrix = st.session_state["odds_matrix"]

            pick_headers = "".join(
                f'<th style="padding:6px 4px;text-align:center;font-size:10px;font-weight:700;'
                f'color:#94a3b8;min-width:40px;border-bottom:1px solid #1e293b;">#{p}</th>'
                for p in range(1, n+1)
            )
            matrix_rows = ""
            for i, team in enumerate(lottery_teams):
                color    = get_team_colors(team["name"])
                primary  = color["primary"]
                logo_url = get_team_logo_url(team["name"])
                logo_tag = (f'<img src="{logo_url}" style="width:20px;height:20px;object-fit:contain;'
                            f'vertical-align:middle;margin-right:8px;" onerror="this.style.display=\'none\'">'
                            if logo_url else "")
                cells    = ""
                row_pcts = matrix.get(team["name"], [0]*n)
                row_bg   = "#0f172a" if i % 2 == 0 else "#111827"
                for p_idx, pct_val in enumerate(row_pcts[:n]):
                    if pct_val == 0:
                        cell_bg = "transparent"; cell_fg = "#334155"; fw = "400"
                    elif pct_val >= 20:
                        cell_bg = primary; cell_fg = "#fff"; fw = "700"
                    elif pct_val >= 10:
                        cell_bg = f"{primary}44"; cell_fg = "#f1f5f9"; fw = "600"
                    elif pct_val >= 5:
                        cell_bg = f"{primary}22"; cell_fg = "#94a3b8"; fw = "500"
                    else:
                        cell_bg = "transparent"; cell_fg = "#475569"; fw = "400"
                    cells += (
                        f'<td style="padding:6px 4px;text-align:center;font-size:11px;'
                        f'font-weight:{fw};background:{cell_bg};color:{cell_fg};'
                        f'border-bottom:1px solid #1e293b;">'
                        f'{"—" if pct_val==0 else f"{pct_val}%"}</td>'
                    )
                matrix_rows += (
                    f'<tr style="background:{row_bg};">'
                    f'<td style="padding:7px 12px;white-space:nowrap;border-bottom:1px solid #1e293b;">'
                    f'<div style="display:flex;align-items:center;">'
                    + logo_tag +
                    f'<span style="font-size:12px;font-weight:600;color:#f1f5f9;">{team["name"].split()[-1]}</span>'
                    f'</div></td>'
                    + cells + '</tr>'
                )

            st.markdown(
                f'<div style="overflow-x:auto;background:#0f172a;border-radius:12px;'
                f'box-shadow:0 2px 12px rgba(0,0,0,0.2);">'
                f'<table style="width:100%;border-collapse:collapse;">'
                f'<thead><tr style="background:#0f172a;">'
                f'<th style="padding:8px 12px;text-align:left;font-size:10px;font-weight:700;'
                f'color:#94a3b8;border-bottom:1px solid #1e293b;">Team</th>'
                f'{pick_headers}</tr></thead>'
                f'<tbody>{matrix_rows}</tbody></table></div>',
                unsafe_allow_html=True
            )
            st.caption("Probabilities via 50,000 Monte Carlo simulations · Darker = higher probability")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Run Simulation ────────────────────────────────────────────────────
        sim_col1, sim_col2 = st.columns([1, 3])
        with sim_col1:
            run_sim = st.button("🎲  Run Lottery", key="btn_lottery", use_container_width=True)
        with sim_col2:
            if "lottery_result" in st.session_state:
                st.caption("Showing last result — click Run Lottery to re-simulate.")

        if run_sim:
            result = run_lottery_sim(lottery_teams)
            st.session_state["lottery_result"] = result
            if "odds_matrix" in st.session_state:
                del st.session_state["odds_matrix"]

        if "lottery_result" in st.session_state:
            result = st.session_state["lottery_result"]
            name_to_seed = {t["name"]: i+1 for i, t in enumerate(lottery_teams)}

            st.markdown(
                '<p style="font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:10px;">Results</p>',
                unsafe_allow_html=True
            )

            reveal_html = ""
            for pick, team_name in result:
                seed    = name_to_seed.get(team_name, pick)
                jumped  = pick < seed
                fell    = pick > seed
                color   = get_team_colors(team_name)
                primary = color["primary"]
                on_bg   = color["on_bg"]
                logo_url = get_team_logo_url(team_name)
                is_top4 = pick <= 4

                # Trade logic
                trade      = TRADED_PICKS.get(team_name)
                owner_note = ""
                if trade:
                    protected = trade.get("protected")
                    conveys   = False
                    if protected is None:
                        conveys = True
                    elif isinstance(protected, int):
                        conveys = pick > protected
                    elif isinstance(protected, str):
                        kept = False
                        for part in protected.split(","):
                            part = part.strip()
                            if "-" in part:
                                lo, hi = part.split("-")
                                if int(lo) <= pick <= int(hi):
                                    kept = True; break
                            elif int(part) == pick:
                                kept = True; break
                        conveys = not kept
                    if conveys:
                        owner_note = (f'<span style="font-size:10px;font-weight:700;'
                                      f'padding:2px 8px;border-radius:99px;'
                                      f'background:rgba(245,158,11,0.2);color:#f59e0b;margin-left:8px;">'
                                      f'→ {trade["owner"]}</span>')
                    else:
                        owner_note = (f'<span style="font-size:10px;color:#22c55e;margin-left:8px;">'
                                      f'✓ Protected</span>')

                # Jump/fall indicator
                if jumped:
                    move_html = (f'<span style="color:#22c55e;font-size:11px;font-weight:700;">'
                                 f'▲ {seed-pick} jump</span>')
                elif fell:
                    move_html = (f'<span style="color:#ef4444;font-size:11px;font-weight:700;">'
                                 f'▼ {pick-seed} fall</span>')
                else:
                    move_html = f'<span style="color:#64748b;font-size:11px;">stayed</span>'

                logo_img = (f'<img src="{logo_url}" style="width:{"36px" if is_top4 else "28px"};'
                            f'height:{"36px" if is_top4 else "28px"};object-fit:contain;" '
                            f'onerror="this.style.display=\'none\'">'
                            if logo_url else "")

                pick_bg = f"{primary}18" if is_top4 else "#111827"
                border_l = f"border-left:4px solid {primary};" if is_top4 else "border-left:4px solid #1e293b;"

                reveal_html += (
                    f'<div style="display:flex;align-items:center;gap:14px;'
                    f'padding:{"14px" if is_top4 else "10px"} 18px;'
                    f'{border_l}background:{pick_bg};border-bottom:1px solid #1e293b;">'
                    f'<div style="font-size:{"24px" if is_top4 else "16px"};font-weight:900;'
                    f'color:{"#f1f5f9" if is_top4 else "#475569"};min-width:44px;text-align:center;">'
                    f'#{pick}</div>'
                    + logo_img +
                    f'<div style="flex:1;">'
                    f'<div style="font-size:{"15px" if is_top4 else "13px"};'
                    f'font-weight:{"700" if is_top4 else "500"};color:#f1f5f9;">'
                    f'{team_name}{owner_note}'
                    + (f' <span style="font-size:9px;font-weight:800;padding:2px 8px;'
                       f'border-radius:99px;background:{primary};color:{on_bg};">LOTTERY PICK</span>'
                       if is_top4 else "")
                    + f'</div>'
                    f'<div style="font-size:11px;color:#64748b;margin-top:2px;">'
                    f'Seed #{seed} · {move_html}</div>'
                    f'</div>'
                    f'<div style="text-align:right;font-size:11px;color:#475569;">'
                    f'{odds_pcts[seed-1] if seed-1<len(odds_pcts) else 0}% odds</div>'
                    f'</div>'
                )

            st.markdown(
                f'<div style="background:#0f172a;border-radius:12px;overflow:hidden;'
                f'box-shadow:0 2px 16px rgba(0,0,0,0.3);">'
                + reveal_html + '</div>',
                unsafe_allow_html=True
            )

            # Lottery jumps summary
            jumped_teams = [(pick, name) for pick, name in result
                           if pick <= 4 and pick < name_to_seed.get(name, pick)]
            if jumped_teams:
                st.markdown(
                    '<div style="margin-top:12px;padding:10px 16px;background:#0f172a;'
                    'border-radius:8px;border-left:3px solid #22c55e;">'
                    '<span style="font-size:12px;font-weight:700;color:#22c55e;">🎉 Lottery Jumps: </span>'
                    '<span style="font-size:12px;color:#94a3b8;">'
                    + ", ".join(f'{name} (#{pick})' for pick, name in jumped_teams)
                    + '</span></div>',
                    unsafe_allow_html=True
                )
            st.caption("Picks 1–4 determined by weighted lottery · Picks 5–14 follow reverse standings order")




# ---------------------------------------------------------------------------
# Tab 6 — Compare Players
# ---------------------------------------------------------------------------

with tab_player_cmp:
    st.markdown("#### Select two players to compare")
    all_players = _cached_all_players()

    if not all_players:
        st.warning("Could not load player list. Check your connection and refresh the page.")
    else:
        pc1, pc2 = st.columns(2)
        with pc1:
            default_p1 = all_players.index("LeBron James") if "LeBron James" in all_players else 0
            p1_select  = st.selectbox("Player 1", all_players, index=default_p1, key="cmp_p1")
        with pc2:
            default_p2 = all_players.index("Stephen Curry") if "Stephen Curry" in all_players else 1
            p2_select  = st.selectbox("Player 2", all_players, index=default_p2, key="cmp_p2")

        if st.button("Compare Players", key="btn_player_cmp"):
            with st.spinner(f"Loading {p1_select} vs {p2_select}..."):
                p1_data, p2_data = get_player_comparison_data(p1_select, p2_select)

            def _fallback_to_career(data, name, default_team):
                if "error" not in data["stats"]:
                    return data
                career = data.get("career", {})
                if career and "error" not in career:
                    st.info(f"{name} is not in the current season — showing career averages.")
                    data["stats"] = {
                        "name": name, "team": "RET",
                        "ppg": career.get("career_ppg"), "reb": career.get("career_reb"),
                        "ast": career.get("career_ast"), "stl": career.get("career_stl"),
                        "blk": career.get("career_blk"), "fg_pct": career.get("career_fg_pct"),
                        "three_pct": career.get("career_3_pct"), "ft_pct": career.get("career_ft_pct"),
                        "ts_pct": career.get("career_ts_pct"),
                        "fg3a_pg": None, "fta_pg": None, "usg_pct": None,
                        "ortg": None, "drtg": None, "net_rtg": None,
                    }
                    data["colors"] = get_team_colors(default_team)
                return data

            p1_data = _fallback_to_career(p1_data, p1_select, "Los Angeles Lakers")
            p2_data = _fallback_to_career(p2_data, p2_select, "Boston Celtics")

            if "error" not in p1_data["stats"] and "error" not in p2_data["stats"]:
                render_player_compare(p1_data, p2_data)
            else:
                st.warning("Could not load data for one or both players.")


# ---------------------------------------------------------------------------
# Tab 7 — Compare Teams
# ---------------------------------------------------------------------------

with tab_team_cmp:
    st.markdown("#### Select two teams to compare")
    all_teams = sorted(list(set(TEAM_MAP.values())))

    tc1, tc2 = st.columns(2)
    with tc1:
        default_t1 = all_teams.index("Los Angeles Lakers") if "Los Angeles Lakers" in all_teams else 0
        t1_select  = st.selectbox("Team 1", all_teams, index=default_t1, key="cmp_t1")
    with tc2:
        default_t2 = all_teams.index("Boston Celtics") if "Boston Celtics" in all_teams else 1
        t2_select  = st.selectbox("Team 2", all_teams, index=default_t2, key="cmp_t2")

    if st.button("Compare Teams", key="btn_team_cmp"):
        with st.spinner(f"Loading {t1_select} vs {t2_select}..."):
            t1_data, t2_data = get_team_comparison_data(t1_select, t2_select)
        if "error" not in t1_data["stats"] and "error" not in t2_data["stats"]:
            render_team_compare(t1_data, t2_data)
        else:
            st.warning("Could not load data for one or both teams.")