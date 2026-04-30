import streamlit as st
from agent.agent import run_agent
from agent.tools import (
    get_player_season_stats,
    get_player_bio,
    get_team_full_stats,
    get_team_rankings,
    get_player_shot_zones,
    get_player_photo_url,
    get_team_logo_url,
    get_team_colors,
    get_player_comparison_data,
    get_team_comparison_data,
    get_all_active_player_names,
    get_player_career_stats,
    get_player_accolades,
    get_team_game_log,
    get_full_standings,
)
from utils.parser import extract_single_player, extract_team, extract_teams, TEAM_MAP

# Unicode constants — avoids backslash-in-f-string errors on Python 3.9
DASH   = "\u2014"   # em dash  —
ENDASH = "\u2013"   # en dash  –
APOS   = "\u2019"   # right single quote  '

st.set_page_config(page_title="NBA Encyclopedia", layout="wide")

st.markdown("""
<style>
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
    def fmt(val):
        return f"{val}%" if val is not None else "—"

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

    # Fetch career stats for top 5 seasons (cached once per session via lru-style)
    _career = get_player_career_stats(name)
    _best_seasons_html = render_best_seasons(
        _career.get("top_seasons", []) if "error" not in _career else [],
        border, on_bg, bg
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
        + _best_seasons_html
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
# Team card
# ---------------------------------------------------------------------------

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
        + '</div>'
    )

    right_panel = (
        f'<div style="flex:1;padding:1.25rem;display:flex;flex-direction:column;gap:10px;background:{bg};">'
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 4px;font-weight:600;">Ranking Among Teams</p>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">{primary}</div>'
        f'<div class="stat-grid" style="grid-template-columns:repeat(5,1fr);">{shooting}</div>'
        + ratings_html
        + f'<div style="border-top:1px solid {border};padding-top:10px;">'
          f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};margin:0 0 6px;font-weight:600;">Best Performers</p>'
          f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">{performers_html}</div>'
          f'</div>'
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

def render_best_seasons(top_seasons, border, on_bg, bg):
    """Render top 5 seasons table with award badges."""
    if not top_seasons:
        return ""

    def badge(text, color):
        return (
            f'<span style="font-size:10px;font-weight:700;padding:1px 6px;border-radius:99px;'
            f'border:1px solid {color};color:{color};margin-right:3px;white-space:nowrap;">{text}</span>'
        )

    def fmt_pct(v):
        return f"{round(v*100,1)}%" if v else DASH

    rows_html = ""
    for s in top_seasons:
        badges = ""
        if s.get("ring"):       badges += badge("Ring", "#ca8a04")
        if s.get("finals_mvp"): badges += badge("FMVP", "#9333ea")
        if s.get("mvp"):        badges += badge("MVP",  "#1d4ed8")
        if s.get("all_star"):   badges += badge("All-Star", "#16a34a")
        if s.get("all_nba"):    badges += badge("All-NBA",  "#0891b2")
        if s.get("dpoy"):       badges += badge("DPOY",     "#dc2626")

        rows_html += (
            f'<tr style="border-bottom:0.5px solid {border};">'
            f'<td style="padding:7px 8px;font-size:12px;font-weight:600;color:{on_bg};white-space:nowrap;">'
            f'{s.get("season","")}</td>'
            f'<td style="padding:7px 6px;font-size:12px;color:#555;">{s.get("team","")}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:13px;font-weight:700;color:{on_bg};">'
            f'{s.get("ppg", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:#555;">'
            f'{s.get("reb", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:#555;">'
            f'{s.get("ast", DASH)}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:#555;">'
            f'{fmt_pct(s.get("fg_pct"))}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:#555;">'
            f'{fmt_pct(s.get("three_pct"))}</td>'
            f'<td style="padding:7px 6px;text-align:center;font-size:12px;color:#555;">'
            f'{s.get("ts_pct", DASH)}{"%" if s.get("ts_pct") else ""}</td>'
            f'<td style="padding:7px 8px;text-align:left;">{badges}</td>'
            f'</tr>'
        )

    return (
        f'<div style="border-top:1px solid {border};padding-top:10px;overflow-x:auto;">'
        f'<p style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:{on_bg};'
        f'margin:0 0 6px;font-weight:600;">Top 5 Seasons</p>'
        f'<table style="width:100%;border-collapse:collapse;background:{bg};">'
        f'<thead><tr style="border-bottom:1px solid {border};">'
        f'<th style="padding:5px 8px;font-size:10px;text-transform:uppercase;color:#888;'
        f'font-weight:600;text-align:left;">Season</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">Team</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">PPG</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">REB</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">AST</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">FG%</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">3PT%</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">TS%</th>'
        f'<th style="padding:5px 6px;font-size:10px;text-transform:uppercase;color:#888;font-weight:600;">Awards</th>'
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
        career.get("top_seasons", []), border, on_bg, bg
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
    """Render standings table with playoff markers, home/road records, ratings."""

    STATUS_LABEL = {"x": "Playoffs", "pi": "Play-In", "e": "Missed"}
    STATUS_COLOR = {"x": "#16a34a", "pi": "#d97706", "e": "#6b7280"}
    STATUS_DOT   = {"x": "#16a34a", "pi": "#f59e0b", "e": "#9ca3af"}

    def record(w, l):
        if w is None or l is None:
            return DASH
        return f"{w}{ENDASH}{l}"

    def net_fmt(v):
        if v is None:
            return DASH
        sign = "+" if v > 0 else ""
        color = "#16a34a" if v > 0 else ("#dc2626" if v < 0 else "#888")
        return f'<span style="color:{color};font-weight:600;">{sign}{v}</span>'

    def status_badge(s):
        color = STATUS_COLOR.get(s, "#888")
        label = STATUS_LABEL.get(s, "")
        return (
            f'<span style="font-size:10px;font-weight:600;padding:2px 7px;'
            f'border-radius:99px;border:1px solid {color};color:{color};">{label}</span>'
        )

    # Group rows
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

        header = (
            '<table style="width:100%;border-collapse:collapse;font-family:sans-serif;">'
            '<thead><tr style="border-bottom:2px solid #e0e0e0;background:#f7f7f7;">'
            '<th style="padding:8px 6px;text-align:left;font-size:11px;color:#888;font-weight:600;width:30px;">#</th>'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;color:#888;font-weight:600;">Team</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">W</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">L</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">PCT</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">Home</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">Road</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">ORTG</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">DRTG</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">NET RTG</th>'
            '<th style="padding:8px 6px;text-align:center;font-size:11px;color:#888;font-weight:600;">Status</th>'
            '</tr></thead><tbody>'
        )

        body = ""
        for i, r in enumerate(group):
            rank  = r.get(sort_key, "")
            dot   = STATUS_DOT.get(r.get("status",""), "#ccc")
            bg    = "#ffffff" if i % 2 == 0 else "#fafafa"
            ortg  = f"{r['ortg']:.1f}" if r.get("ortg") else DASH
            drtg  = f"{r['drtg']:.1f}" if r.get("drtg") else DASH

            # Dashed divider at playoff/play-in boundaries
            divider = ""
            conf_rank = r.get("conf_rank", 0)
            if view != "overall" and conf_rank in (7, 11):
                divider = (
                    f'<tr><td colspan="11" style="padding:0;">'
                    f'<div style="border-top:2px dashed #d1d5db;margin:2px 0;"></div>'
                    f'</td></tr>'
                )

            team_btn = (
                f'<span style="font-weight:600;font-size:13px;color:#111;">'
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                f'background:{dot};margin-right:6px;"></span>'
                f'{r["name"]}</span>'
            )

            body += (
                divider +
                f'<tr style="background:{bg};border-bottom:1px solid #f0f0f0;">'
                f'<td style="padding:9px 6px;color:#999;font-size:12px;">{rank}</td>'
                f'<td style="padding:9px 12px;">{team_btn}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:13px;color:#555;">{r["w"]}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:13px;color:#555;">{r["l"]}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:13px;color:#555;">{r["pct"]:.3f}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:12px;color:#555;">{record(r.get("w_home"), r.get("l_home"))}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:12px;color:#555;">{record(r.get("w_road"), r.get("l_road"))}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:12px;color:#555;">{ortg}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:12px;color:#555;">{drtg}</td>'
                f'<td style="padding:9px 6px;text-align:center;font-size:12px;">{net_fmt(r.get("net_rtg"))}</td>'
                f'<td style="padding:9px 6px;text-align:center;">{status_badge(r.get("status",""))}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<p style="font-size:13px;font-weight:700;color:#111;margin-bottom:6px;">{title}</p>'
            f'<div class="card" style="padding:0;overflow-x:auto;">'
            f'{header}{body}</tbody></table></div>',
            unsafe_allow_html=True
        )

    # Legend
    st.markdown(
        '<p style="font-size:11px;color:#888;margin-top:8px;">'
        '<span style="color:#16a34a;font-weight:600;">Playoffs</span> = Top 6 in conference &nbsp;|&nbsp; '
        '<span style="color:#d97706;font-weight:600;">Play-In</span> = Seed 7-10 &nbsp;|&nbsp; '
        '<span style="color:#6b7280;font-weight:600;">Missed</span> = Seed 11-15</p>',
        unsafe_allow_html=True
    )

    # Team detail picker
    st.markdown("---")
    st.markdown("**Click a team below to view their full stats card:**")
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

st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
  <div>
    <h1 style="margin:0;font-size:28px;font-weight:800;letter-spacing:-0.5px;">NBA Encyclopedia</h1>
    <p style="margin:0;font-size:13px;color:#888;">Stats · Analysis · History</p>
  </div>
</div>
""", unsafe_allow_html=True)

tab_lookup, tab_standings, tab_player_cmp, tab_team_cmp = st.tabs([
    "Search",
    "Standings",
    "Compare Players",
    "Compare Teams",
])


# ---------------------------------------------------------------------------
# Tab 1 — Lookup
# ---------------------------------------------------------------------------

with tab_lookup:

    st.markdown('<p style="font-size:13px;color:#888;margin-bottom:8px;">Try asking about...</p>',
                unsafe_allow_html=True)

    chip_cols = st.columns(4)
    for i, suggestion in enumerate(SUGGESTIONS):
        with chip_cols[i % 4]:
            if st.button(suggestion, key=f"chip_{i}", use_container_width=True):
                st.session_state["chip_query"] = suggestion
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    chip_q = st.session_state.pop("chip_query", None) if "chip_query" in st.session_state else None

    query = st.text_input(
        "Ask anything about players, teams, or stats:",
        value=chip_q or "",
        placeholder="e.g. 'Bring up Steph Curry’s stats' or 'Warriors vs Celtics'",
        key="main_query"
    )

    if query:
        query_lower = query.lower()
        player_name = extract_single_player(query)
        teams       = extract_teams(query)

        is_rankings = any(k in query_lower for k in [
            "ranking", "rankings", "best teams", "top teams",
            "league standings", "which team is best", "team ratings",
        ])
        is_opinion  = any(k in query_lower for k in OPINION_KEYWORDS)
        is_game_log = any(k in query_lower for k in GAME_LOG_KEYWORDS) and bool(teams)

        n_games = 5
        for word in query_lower.split():
            if word.isdigit():
                n_games = min(int(word), 10)
                break

        if is_rankings:
            with st.spinner("Loading league rankings..."):
                rankings = get_team_rankings()
            render_rankings_table(rankings)

        elif is_game_log and teams:
            team = teams[0]
            with st.spinner(f"Loading {team} last {n_games} games..."):
                log = get_team_game_log(team, n_games)
            if isinstance(log, list):
                render_game_log(team, log)
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
            else:
                career = get_player_career_stats(player_name)
                if "error" not in career:
                    bio    = get_player_bio(player_name)
                    acols  = get_player_accolades(player_name)
                    render_career_card(player_name, career, bio, acols)
                else:
                    st.warning(f"Could not find stats for {player_name}.")

        elif teams and not is_game_log:
            with st.spinner("Loading team data..."):
                stats = get_team_full_stats(teams[0])
            if "error" not in stats:
                render_team_card(stats)
            else:
                st.warning(stats["error"])

        elif not teams and any(k in query_lower for k in
                               ["season", "how is", "how are", "stats", "bring up",
                                "show me", "tell me about", "what are"]):
            team = extract_team(query)
            with st.spinner("Loading team data..."):
                stats = get_team_full_stats(team)
            if "error" not in stats:
                render_team_card(stats)
            else:
                st.warning(stats["error"])

        if not is_opinion:
            st.divider()

        with st.spinner("Analyzing..."):
            result, sources = run_agent(query)

        st.subheader("Analysis & Prediction" if is_opinion else "Analysis")
        st.write(result)

        # Sources panel — only shown when web search was used
        if sources:
            with st.expander(f"Sources ({len(sources)})", expanded=False):
                for s in sources:
                    domain = s.get("domain", "")
                    title  = s.get("title", domain)
                    url    = s.get("url", "")
                    if url:
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:10px;'
                            f'padding:6px 0;border-bottom:0.5px solid #f0f0f0;">'
                            f'<img src="https://www.google.com/s2/favicons?domain={domain}&sz=16" '
                            f'style="width:16px;height:16px;" onerror="this.style.display=\'none\'">'
                            f'<div>'
                            f'<a href="{url}" target="_blank" style="font-size:13px;font-weight:500;'
                            f'color:#2563eb;text-decoration:none;">{title}</a>'
                            f'<p style="font-size:11px;color:#888;margin:0;">{domain}</p>'
                            f'</div></div>',
                            unsafe_allow_html=True
                        )


# ---------------------------------------------------------------------------
# Tab 2 — Standings
# ---------------------------------------------------------------------------

with tab_standings:
    st.markdown("#### 2025-26 NBA Standings")

    with st.spinner("Loading standings..."):
        standing_rows = get_full_standings()

    view_opt = st.radio(
        "View",
        ["Overall", "Eastern Conference", "Western Conference"],
        horizontal=True,
        key="standings_view"
    )

    view_map = {
        "Overall":               "overall",
        "Eastern Conference":    "east",
        "Western Conference":    "west",
    }
    render_standings(standing_rows, view=view_map[view_opt])


# ---------------------------------------------------------------------------
# Tab 3 — Compare Players
# ---------------------------------------------------------------------------

with tab_player_cmp:
    st.markdown("#### Select two players to compare")
    all_players = get_all_active_player_names()

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
# Tab 4 — Compare Teams
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