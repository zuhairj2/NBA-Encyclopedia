import time
import unicodedata
from nba_api.stats.endpoints import (
    leaguegamefinder,
    boxscoretraditionalv2,
    leaguedashteamstats,
    leaguedashplayerstats,
    commonplayerinfo,
    teaminfocommon,
    shotchartdetail,
    playerawards,
    teamyearbyyearstats,
    playercareerstats,
    leaguestandingsv3,
    teamgamelog,
    boxscoresummaryv2,
    scoreboardv2,
)
from nba_api.stats.static import players as nba_static_players
from nba_api.stats.static import teams as nba_static_teams

CURRENT_SEASON = "2025-26"
NBA_TIMEOUT = 60

# ── In-memory caches ──────────────────────────────────────────────────────────
_PLAYER_STATS_CACHE    = None
_TEAM_STATS_CACHE      = None
_TEAM_ADV_CACHE        = None
_PLAYER_ADV_CACHE      = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nba_call(fn, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise e


def _normalize(text):
    """Strip accents, hyphens, and punctuation for fuzzy name matching."""
    import re
    t = unicodedata.normalize("NFD", str(text)).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[-'.]", " ", t)          # hyphen/apostrophe → space
    t = re.sub(r"[^a-z0-9 ]", "", t)     # strip remaining punctuation
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _get_player_id(player_name):
    norm = _normalize(player_name)
    for p in nba_static_players.get_active_players():
        if _normalize(p["full_name"]) == norm:
            return p["id"]
    for p in nba_static_players.get_active_players():
        if norm in _normalize(p["full_name"]):
            return p["id"]
    return None


def _get_team_id(team_name):
    norm = _normalize(team_name)
    for t in nba_static_teams.get_teams():
        if _normalize(t["full_name"]) == norm:
            return t["id"]
    return None


def _rank_of(series, value):
    """1-based rank of value in series (higher value = better = lower rank number)."""
    return int((series > value).sum()) + 1


# ── Team colors (primary, secondary) — used for pastel card theming ───────────
TEAM_COLORS = {
    "Atlanta Hawks":          ("#C8102E", "#C1D32F"),
    "Boston Celtics":         ("#007A33", "#BA9653"),
    "Brooklyn Nets":          ("#000000", "#FFFFFF"),
    "Charlotte Hornets":      ("#1D1160", "#00788C"),
    "Chicago Bulls":          ("#CE1141", "#000000"),
    "Cleveland Cavaliers":    ("#860038", "#FDBB30"),
    "Dallas Mavericks":       ("#00538C", "#002B5E"),
    "Denver Nuggets":         ("#0E2240", "#FEC524"),
    "Detroit Pistons":        ("#C8102E", "#006BB6"),
    "Golden State Warriors":  ("#1D428A", "#FFC72C"),
    "Houston Rockets":        ("#CE1141", "#000000"),
    "Indiana Pacers":         ("#002D62", "#FDBB30"),
    "LA Clippers":            ("#C8102E", "#1D428A"),
    "Los Angeles Lakers":     ("#552583", "#FDB927"),
    "Memphis Grizzlies":      ("#5D76A9", "#12173F"),
    "Miami Heat":             ("#98002E", "#F9A01B"),
    "Milwaukee Bucks":        ("#00471B", "#EEE1C6"),
    "Minnesota Timberwolves": ("#0C2340", "#236192"),
    "New Orleans Pelicans":   ("#0C2340", "#C8102E"),
    "New York Knicks":        ("#006BB6", "#F58426"),
    "Oklahoma City Thunder":  ("#007AC1", "#EF3B24"),
    "Orlando Magic":          ("#0077C0", "#C4CED4"),
    "Philadelphia 76ers":     ("#006BB6", "#ED174C"),
    "Phoenix Suns":           ("#1D1160", "#E56020"),
    "Portland Trail Blazers": ("#E03A3E", "#000000"),
    "Sacramento Kings":       ("#5A2D81", "#63727A"),
    "San Antonio Spurs":      ("#C4CED4", "#000000"),
    "Toronto Raptors":        ("#CE1141", "#000000"),
    "Utah Jazz":              ("#002B5C", "#00471B"),
    "Washington Wizards":     ("#002B5C", "#E31837"),
}


def _pastel(hex_color, mix=0.35):
    """Blend a hex color toward white to create a pastel version."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = int(r + (255 - r) * (1 - mix))
    g = int(g + (255 - g) * (1 - mix))
    b = int(b + (255 - b) * (1 - mix))
    return f"#{r:02x}{g:02x}{b:02x}"


# Abbreviation → full team name for player card color lookup
ABBR_TO_TEAM = {v[:3].upper(): v for v in TEAM_COLORS}
ABBR_TO_TEAM.update({
    "ATL": "Atlanta Hawks",       "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",       "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",       "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",     "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",     "IND": "Indiana Pacers",
    "LAC": "LA Clippers",         "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",   "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",     "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans","NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder","ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",  "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers","SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",   "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",           "WAS": "Washington Wizards",
})


def _luminance(hex_color):
    """Return relative luminance 0–1 for a hex color."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16) / 255, int(hex_color[2:4], 16) / 255, int(hex_color[4:6], 16) / 255
    def c(x):
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


def get_team_colors(team_name_or_abbr):
    """
    Return color theme for a team. Stat boxes always white.
    Left panel / section label text is auto-selected for readability.
    """
    if len(team_name_or_abbr) <= 3:
        team_name = ABBR_TO_TEAM.get(team_name_or_abbr.upper(), team_name_or_abbr)
    else:
        team_name = team_name_or_abbr

    primary, secondary = TEAM_COLORS.get(team_name, ("#4a5568", "#718096"))

    pastel_bg = _pastel(primary, 0.82)

    # Decide text color based on luminance of the pastel bg
    lum = _luminance(pastel_bg)
    if lum < 0.35:          # dark background → white text
        on_bg       = "#ffffff"
        on_bg_muted = "rgba(255,255,255,0.75)"
        badge_bg    = "rgba(255,255,255,0.18)"
        badge_border= "rgba(255,255,255,0.35)"
        badge_text  = "#ffffff"
    else:                   # light background → dark text
        on_bg       = "#111111"
        on_bg_muted = "#444444"
        badge_bg    = "rgba(0,0,0,0.10)"
        badge_border= "rgba(0,0,0,0.20)"
        badge_text  = "#111111"

    return {
        "primary":       primary,
        "secondary":     secondary,
        "pastel_bg":     pastel_bg,
        "pastel_border": _pastel(primary, 0.55),
        "text_accent":   primary,          # section labels on right panel bg
        "on_bg":         on_bg,            # main text on left panel / card bg
        "on_bg_muted":   on_bg_muted,      # secondary text on card bg
        "badge_bg":      badge_bg,
        "badge_border":  badge_border,
        "badge_text":    badge_text,
        # stat boxes always white — these stay constant
        "text_value":    "#111111",
        "text_label":    "#444444",
    }


def get_player_photo_url(player_name):
    """Return NBA CDN headshot URL for a player (active or retired), or None."""
    player_id = _get_player_id_all(player_name)
    if player_id:
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    return None


def get_team_logo_url(team_name):
    """Return NBA CDN logo URL for a team, or None if not found."""
    team_id = _get_team_id(team_name)
    if team_id:
        return f"https://cdn.nba.com/logos/nba/{team_id}/global/L/logo.svg"
    return None

def get_league_player_stats():
    """All player season stats, per-game (cached for session)."""
    global _PLAYER_STATS_CACHE
    if _PLAYER_STATS_CACHE is not None:
        return _PLAYER_STATS_CACHE

    def _fetch():
        return leaguedashplayerstats.LeagueDashPlayerStats(
            season=CURRENT_SEASON,
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0]

    stats = _nba_call(_fetch)

    for col in ["PTS", "AST", "REB", "STL", "BLK", "TOV"]:
        if col in stats.columns:
            stats[col] = (stats[col] / stats["GP"]).round(1)

    _PLAYER_STATS_CACHE = stats
    return stats


def _get_team_stats():
    """All team season stats, per-game (cached for session)."""
    global _TEAM_STATS_CACHE
    if _TEAM_STATS_CACHE is not None:
        return _TEAM_STATS_CACHE

    def _fetch():
        return leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0]

    stats = _nba_call(_fetch)

    for col in ["PTS", "AST", "REB", "STL", "BLK", "TOV"]:
        if col in stats.columns:
            stats[col] = (stats[col] / stats["GP"]).round(1)

    _TEAM_STATS_CACHE = stats
    return stats


def _get_team_advanced_stats():
    """ORTG, DRTG, NET_RATING for all teams (cached)."""
    global _TEAM_ADV_CACHE
    if _TEAM_ADV_CACHE is not None:
        return _TEAM_ADV_CACHE

    try:
        def _fetch():
            return leaguedashteamstats.LeagueDashTeamStats(
                season=CURRENT_SEASON,
                measure_type_detailed_defense="Advanced",
                timeout=NBA_TIMEOUT
            ).get_data_frames()[0]
        _TEAM_ADV_CACHE = _nba_call(_fetch)
    except Exception:
        _TEAM_ADV_CACHE = None

    return _TEAM_ADV_CACHE


def _get_player_advanced_stats():
    """ORTG, DRTG, NET_RATING for all players (cached)."""
    global _PLAYER_ADV_CACHE
    if _PLAYER_ADV_CACHE is not None:
        return _PLAYER_ADV_CACHE

    try:
        def _fetch():
            return leaguedashplayerstats.LeagueDashPlayerStats(
                season=CURRENT_SEASON,
                measure_type_detailed_defense="Advanced",
                timeout=NBA_TIMEOUT
            ).get_data_frames()[0]
        _PLAYER_ADV_CACHE = _nba_call(_fetch)
    except Exception:
        _PLAYER_ADV_CACHE = None

    return _PLAYER_ADV_CACHE


def get_team_rankings():
    """All 30 teams ranked by NET_RATING. Falls back to PPG if advanced unavailable."""
    adv  = _get_team_advanced_stats()
    base = _get_team_stats()

    if adv is not None and "NET_RATING" in adv.columns:
        # adv may not have TEAM_ABBREVIATION — merge it from base
        cols = ["TEAM_NAME", "OFF_RATING", "DEF_RATING", "NET_RATING"]
        if "TEAM_ABBREVIATION" in adv.columns:
            cols.insert(1, "TEAM_ABBREVIATION")
        merged = adv[cols].copy()

        if "TEAM_ABBREVIATION" not in merged.columns:
            abbr_map = base.set_index("TEAM_NAME")["TEAM_ABBREVIATION"].to_dict() \
                       if "TEAM_ABBREVIATION" in base.columns else {}
            merged["TEAM_ABBREVIATION"] = merged["TEAM_NAME"].map(abbr_map).fillna("")

        wl = base[["TEAM_NAME", "W", "L"]].copy()
        merged = merged.merge(wl, on="TEAM_NAME", how="left")
        merged = merged.sort_values("NET_RATING", ascending=False).reset_index(drop=True)
        merged["rank"] = merged.index + 1
        return merged.to_dict(orient="records")

    # Fallback: rank by PPG
    fallback = base[["TEAM_NAME", "W", "L", "PTS"]].copy()
    if "TEAM_ABBREVIATION" in base.columns:
        fallback["TEAM_ABBREVIATION"] = base["TEAM_ABBREVIATION"]
    else:
        fallback["TEAM_ABBREVIATION"] = ""
    fallback = fallback.sort_values("PTS", ascending=False).reset_index(drop=True)
    fallback["rank"]       = fallback.index + 1
    fallback["NET_RATING"] = None
    fallback["OFF_RATING"] = None
    fallback["DEF_RATING"] = None
    return fallback.to_dict(orient="records")


def get_full_standings():
    """
    Complete standings for all 30 teams with NBA tiebreaker logic:
    1. Overall W-L pct
    2. Head-to-head record (between tied teams)
    3. Division record (if same division)
    4. Conference record
    5. Point differential (capped ±10/game)
    """
    base = _get_team_stats()
    adv  = _get_team_advanced_stats()

    # Pull full season game log once — used for home/road, conf record, h2h, point diff
    games_df = None
    try:
        games_df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
            season_nullable=CURRENT_SEASON,
            league_id_nullable="00",
            season_type_nullable="Regular Season",
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0])
    except Exception:
        pass

    # Build per-team records from game log
    home_road   = {}   # name -> {wh, lh, wr, lr}
    conf_record = {}   # name -> {w, l}
    div_record  = {}   # name -> {w, l}
    h2h_record  = {}   # (name_a, name_b) -> {w_a, w_b}
    point_diff  = {}   # name -> total capped diff

    if games_df is not None and not games_df.empty:
        for _, g in games_df.iterrows():
            name    = g.get("TEAM_NAME", "")
            wl      = g.get("WL", "")
            matchup = g.get("MATCHUP", "")
            pts     = g.get("PTS", 0) or 0
            plus    = g.get("PLUS_MINUS", 0) or 0
            if not name or not wl:
                continue

            # Home/Road
            is_home = " vs. " in matchup
            if name not in home_road:
                home_road[name] = {"wh": 0, "lh": 0, "wr": 0, "lr": 0}
            if is_home:
                home_road[name]["wh" if wl == "W" else "lh"] += 1
            else:
                home_road[name]["wr" if wl == "W" else "lr"] += 1

            # Point differential capped at ±10 per game
            capped = max(-10, min(10, int(plus)))
            point_diff[name] = point_diff.get(name, 0) + capped

            # Conference & division record
            my_conf, my_div = _TEAM_CONF_DIV.get(name, ("", ""))

            # Opponent name from matchup: "TEAM vs. OPP" or "TEAM @ OPP"
            opp_name = matchup.split(" vs. ")[-1] if " vs. " in matchup \
                       else matchup.split(" @ ")[-1]
            opp_name = opp_name.strip()
            # Try to find full team name matching opp
            opp_full = next(
                (t for t in _TEAM_CONF_DIV if t.endswith(opp_name) or
                 opp_name in t or t[:3].upper() == opp_name[:3].upper()),
                None
            )
            if opp_full:
                opp_conf, opp_div = _TEAM_CONF_DIV.get(opp_full, ("", ""))

                # Conference record
                if my_conf and opp_conf == my_conf:
                    if name not in conf_record:
                        conf_record[name] = {"w": 0, "l": 0}
                    conf_record[name]["w" if wl == "W" else "l"] += 1

                # Division record
                if my_div and opp_div == my_div:
                    if name not in div_record:
                        div_record[name] = {"w": 0, "l": 0}
                    div_record[name]["w" if wl == "W" else "l"] += 1

                # Head-to-head (canonical key: alphabetical order)
                key = tuple(sorted([name, opp_full]))
                if key not in h2h_record:
                    h2h_record[key] = {key[0]: 0, key[1]: 0}
                if wl == "W":
                    h2h_record[key][name] = h2h_record[key].get(name, 0) + 1

    def h2h_pct(name_a, name_b):
        key = tuple(sorted([name_a, name_b]))
        rec = h2h_record.get(key, {})
        wa  = rec.get(name_a, 0)
        wb  = rec.get(name_b, 0)
        tot = wa + wb
        return wa / tot if tot > 0 else 0.5

    def conf_pct(name):
        r = conf_record.get(name, {})
        w, l = r.get("w", 0), r.get("l", 0)
        return w / (w + l) if (w + l) > 0 else 0.0

    def div_pct(name):
        r = div_record.get(name, {})
        w, l = r.get("w", 0), r.get("l", 0)
        return w / (w + l) if (w + l) > 0 else 0.0

    # Build rows
    rows = []
    for _, row in base.iterrows():
        name = row["TEAM_NAME"]
        conf, div = _TEAM_CONF_DIV.get(name, ("", ""))
        w = int(row.get("W", 0))
        l = int(row.get("L", 0))
        hr = home_road.get(name, {})

        ortg = drtg = net = None
        if adv is not None and not adv.empty:
            ar = adv[adv["TEAM_NAME"] == name]
            if not ar.empty:
                a = ar.iloc[0]
                ortg = round(float(a.get("OFF_RATING") or 0), 1) or None
                drtg = round(float(a.get("DEF_RATING") or 0), 1) or None
                net  = round(float(a.get("NET_RATING")  or 0), 1)

        rows.append({
            "name":    name,
            "abbr":    row.get("TEAM_ABBREVIATION", ""),
            "conf":    conf,
            "div":     div,
            "w":       w,
            "l":       l,
            "pct":     round(w / (w + l), 3) if (w + l) > 0 else 0,
            "w_home":  hr.get("wh"),
            "l_home":  hr.get("lh"),
            "w_road":  hr.get("wr"),
            "l_road":  hr.get("lr"),
            "conf_w":  conf_record.get(name, {}).get("w", 0),
            "conf_l":  conf_record.get(name, {}).get("l", 0),
            "conf_pct":conf_pct(name),
            "div_pct": div_pct(name),
            "pt_diff": point_diff.get(name, 0),
            "ortg":    ortg,
            "drtg":    drtg,
            "net_rtg": net,
        })

    def tiebreak_sort(group):
        """
        Sort a group of tied teams using NBA tiebreaker rules.
        Works recursively: break ties within sub-groups if needed.
        """
        if len(group) <= 1:
            return group

        # Step 1: overall win pct (already equal in a tie group, but sort anyway)
        group = sorted(group, key=lambda r: r["pct"], reverse=True)

        # Step 2: head-to-head (only meaningful for 2-team ties)
        if len(group) == 2:
            a, b = group[0]["name"], group[1]["name"]
            h = h2h_pct(a, b)
            if h != 0.5:
                return group if h > 0.5 else [group[1], group[0]]

        # Step 3: division record (only if same division)
        divs = set(r["div"] for r in group)
        if len(divs) == 1:
            by_div = sorted(group, key=lambda r: r["div_pct"], reverse=True)
            # Only apply if it actually breaks the tie
            div_pcts = [r["div_pct"] for r in by_div]
            if div_pcts[0] != div_pcts[-1]:
                group = by_div

        # Step 4: conference record
        by_conf = sorted(group, key=lambda r: r["conf_pct"], reverse=True)
        conf_pcts = [r["conf_pct"] for r in by_conf]
        if conf_pcts[0] != conf_pcts[-1]:
            group = by_conf

        # Step 5: point differential (capped ±10/game)
        group = sorted(group, key=lambda r: r["pt_diff"], reverse=True)

        return group

    # Sort each conference with tiebreakers, assign conf_rank + status
    for conf_name in ("East", "West"):
        conf_teams = [r for r in rows if r["conf"] == conf_name]

        # Group by win pct, then apply tiebreakers within each group
        from itertools import groupby
        conf_teams.sort(key=lambda r: r["pct"], reverse=True)

        final_order = []
        for _, tied in groupby(conf_teams, key=lambda r: r["pct"]):
            tied_list = list(tied)
            final_order.extend(tiebreak_sort(tied_list))

        for rank, r in enumerate(final_order, 1):
            r["conf_rank"] = rank
            r["status"]    = "x" if rank <= 6 else ("pi" if rank <= 10 else "e")

    # Overall rank with same tiebreaker logic
    rows.sort(key=lambda r: r["pct"], reverse=True)
    final_rows = []
    from itertools import groupby
    for _, tied in groupby(rows, key=lambda r: r["pct"]):
        tied_list = list(tied)
        final_rows.extend(tiebreak_sort(tied_list))

    for rank, r in enumerate(final_rows, 1):
        r["overall_rank"] = rank

    return final_rows


# ── Player functions ──────────────────────────────────────────────────────────

def get_player_bio(player_name):
    """Fetch age, position, college, jersey number from commonplayerinfo.
    Works for both active and retired players."""
    player_id = _get_player_id_all(player_name)
    if not player_id:
        return {}

    try:
        info = _nba_call(lambda: commonplayerinfo.CommonPlayerInfo(
            player_id=player_id,
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0].iloc[0])

        from datetime import date
        birthdate = str(info.get("BIRTHDATE", ""))
        age = None
        if birthdate and len(birthdate) >= 4:
            try:
                birth_year = int(birthdate[:4])
                age = date.today().year - birth_year
                # More precise: subtract 1 if birthday hasn't happened yet this year
                birth_month = int(birthdate[5:7]) if len(birthdate) >= 7 else 1
                birth_day   = int(birthdate[8:10]) if len(birthdate) >= 10 else 1
                if (date.today().month, date.today().day) < (birth_month, birth_day):
                    age -= 1
            except Exception:
                pass

        # For retired players, team will be empty string — show "Retired"
        team_abbr = info.get("TEAM_ABBREVIATION", "") or ""
        is_active = bool(team_abbr)

        return {
            "position":  info.get("POSITION", ""),
            "jersey":    info.get("JERSEY", "") or "",
            "school":    info.get("SCHOOL", "") or "",
            "age":       age,
            "team_abbr": team_abbr,
            "is_active": is_active,
            "from_year": info.get("FROM_YEAR", ""),
            "to_year":   info.get("TO_YEAR", ""),
            "height":    info.get("HEIGHT", ""),
            "weight":    info.get("WEIGHT", ""),
            "country":   info.get("COUNTRY", ""),
            "draft_year":info.get("DRAFT_YEAR", ""),
            "draft_round":info.get("DRAFT_ROUND", ""),
            "draft_number":info.get("DRAFT_NUMBER", ""),
        }
    except Exception:
        return {}


def get_player_shot_zones(player_name):
    """Return FG% per shot zone for a player this season."""
    player_id = _get_player_id(player_name)
    if not player_id:
        return None

    try:
        def _fetch():
            return shotchartdetail.ShotChartDetail(
                team_id=0,
                player_id=player_id,
                season_nullable=CURRENT_SEASON,
                season_type_all_star="Regular Season",
                context_measure_simple="FGA",
                timeout=NBA_TIMEOUT
            ).get_data_frames()[0]

        shots = _nba_call(_fetch)
        if shots is None or shots.empty:
            return None

        # Use SHOT_ZONE_AREA + SHOT_ZONE_BASIC to classify
        zones = {k: {"made": 0, "att": 0} for k in
                 ["paint", "left_mid", "right_mid",
                  "left_3", "right_3", "top_3",
                  "left_corner", "right_corner"]}

        for _, shot in shots.iterrows():
            basic = shot.get("SHOT_ZONE_BASIC", "")
            area  = shot.get("SHOT_ZONE_AREA", "")
            made  = 1 if shot.get("SHOT_MADE_FLAG") == 1 else 0
            loc_x = float(shot.get("LOC_X", 0))

            if basic in ("Restricted Area", "In The Paint (Non-RA)"):
                key = "paint"
            elif basic == "Mid-Range":
                key = "left_mid" if loc_x < 0 else "right_mid"
            elif basic == "Left Corner 3":
                key = "left_corner"
            elif basic == "Right Corner 3":
                key = "right_corner"
            elif basic == "Above the Break 3":
                if loc_x < -80:
                    key = "left_3"
                elif loc_x > 80:
                    key = "right_3"
                else:
                    key = "top_3"
            else:
                continue

            zones[key]["att"]  += 1
            zones[key]["made"] += made

        def fg(z):
            a = zones[z]["att"]
            return round(zones[z]["made"] / a * 100, 1) if a > 0 else None

        return {k: fg(k) for k in zones}

    except Exception:
        return None


def get_player_season_stats(player_name):
    """Per-game stats with league rank for every stat."""
    stats = get_league_player_stats()
    norm_search = _normalize(player_name)  # strip accents from input too

    rows = stats[stats["PLAYER_NAME"].apply(
        lambda n: norm_search in _normalize(n)
    )]

    if rows.empty:
        return {"error": f"Player not found: {player_name}"}

    row = rows.iloc[0]

    min_pg = None
    if "MIN" in stats.columns and row["GP"] > 0:
        min_pg = round(row["MIN"] / row["GP"], 1)

    # Pull advanced metrics for this player
    adv = _get_player_advanced_stats()
    ortg = drtg = net_rtg = None
    rank_ortg = rank_drtg = rank_net = None
    if adv is not None and not adv.empty:
        adv_row = adv[adv["PLAYER_NAME"].apply(
            lambda n: norm_search in _normalize(n)
        )]
        if not adv_row.empty:
            ar = adv_row.iloc[0]
            if "OFF_RATING" in adv.columns:
                ortg = round(ar["OFF_RATING"], 1)
                rank_ortg = _rank_of(adv["OFF_RATING"], ar["OFF_RATING"])
            if "DEF_RATING" in adv.columns:
                drtg = round(ar["DEF_RATING"], 1)
                # lower DRTG = better, so flip rank
                rank_drtg = int((adv["DEF_RATING"] < ar["DEF_RATING"]).sum()) + 1
            if "NET_RATING" in adv.columns:
                net_rtg = round(ar["NET_RATING"], 1)
                rank_net = _rank_of(adv["NET_RATING"], ar["NET_RATING"])

    # shooting ranks — filter to players with meaningful attempts (min 100 FGA)
    qualified  = stats[stats["GP"] >= 20]
    fta_pg     = round(row["FTA"] / row["GP"], 1) if "FTA" in stats.columns and row["GP"] > 0 else None
    fg3a_pg    = round(row["FG3A"] / row["GP"], 1) if "FG3A" in stats.columns and row["GP"] > 0 else None
    fta_series = qualified["FTA"] / qualified["GP"] if "FTA" in qualified.columns else None
    fg3a_series= qualified["FG3A"] / qualified["GP"] if "FG3A" in qualified.columns else None

    # True Shooting %: PTS / (2 * (FGA + 0.44 * FTA))
    # NOTE: PTS was divided by GP in cache, but FGA/FTA were not — use raw totals
    pts_total = row["PTS"] * row["GP"]                          # reconstruct total
    fga_total = row["FGA"] if "FGA" in row.index else 0         # already a season total
    fta_total = row["FTA"] if "FTA" in row.index else 0         # already a season total
    ts_pct = round(pts_total / (2 * (fga_total + 0.44 * fta_total)) * 100, 1) \
             if (fga_total + fta_total) > 0 else None

    # Usage % if available in advanced stats
    usg_pct = None
    adv = _get_player_advanced_stats()
    if adv is not None and not adv.empty:
        adv_row2 = adv[adv["PLAYER_NAME"].apply(lambda n: norm_search in _normalize(n))]
        if not adv_row2.empty and "USG_PCT" in adv_row2.columns:
            usg_pct = round(float(adv_row2.iloc[0]["USG_PCT"]) * 100, 1)

    return {
        "name":       row["PLAYER_NAME"],
        "team":       row["TEAM_ABBREVIATION"],
        "gp":         int(row["GP"]),
        "ppg":        round(row["PTS"], 1),
        "reb":        round(row["REB"], 1),
        "ast":        round(row["AST"], 1),
        "stl":        round(row["STL"], 1),
        "blk":        round(row["BLK"], 1),
        "tov":        round(row["TOV"], 1),
        "fg_pct":     round(row["FG_PCT"], 3),
        "three_pct":  round(row["FG3_PCT"], 3),
        "ft_pct":     round(row.get("FT_PCT", 0), 3),
        "fta_pg":     fta_pg,
        "fg3a_pg":    fg3a_pg,
        "ts_pct":     ts_pct,
        "usg_pct":    usg_pct,
        "min_pg":     min_pg,
        "rank_pts":   _rank_of(stats["PTS"], row["PTS"]),
        "rank_reb":   _rank_of(stats["REB"], row["REB"]),
        "rank_ast":   _rank_of(stats["AST"], row["AST"]),
        "rank_stl":   _rank_of(stats["STL"], row["STL"]),
        "rank_blk":   _rank_of(stats["BLK"], row["BLK"]),
        "rank_fg":    _rank_of(qualified["FG_PCT"], row["FG_PCT"]),
        "rank_3fg":   _rank_of(qualified["FG3_PCT"], row["FG3_PCT"]),
        "rank_ft":    _rank_of(qualified["FT_PCT"], row["FT_PCT"]) if "FT_PCT" in qualified.columns else None,
        "rank_fta":   _rank_of(fta_series, fta_pg) if fta_series is not None and fta_pg else None,
        "rank_3fga":  _rank_of(fg3a_series, fg3a_pg) if fg3a_series is not None and fg3a_pg else None,
        "pts_rank":   _rank_of(stats["PTS"], row["PTS"]),
        "ortg":       ortg,
        "drtg":       drtg,
        "net_rtg":    net_rtg,
        "rank_ortg":  rank_ortg,
        "rank_drtg":  rank_drtg,
        "rank_net":   rank_net,
    }


# ── Team functions ────────────────────────────────────────────────────────────

# Static conference/division map — instant fallback if API call fails
_TEAM_CONF_DIV = {
    "Atlanta Hawks":          ("East", "Southeast"),
    "Boston Celtics":         ("East", "Atlantic"),
    "Brooklyn Nets":          ("East", "Atlantic"),
    "Charlotte Hornets":      ("East", "Southeast"),
    "Chicago Bulls":          ("East", "Central"),
    "Cleveland Cavaliers":    ("East", "Central"),
    "Dallas Mavericks":       ("West", "Southwest"),
    "Denver Nuggets":         ("West", "Northwest"),
    "Detroit Pistons":        ("East", "Central"),
    "Golden State Warriors":  ("West", "Pacific"),
    "Houston Rockets":        ("West", "Southwest"),
    "Indiana Pacers":         ("East", "Central"),
    "LA Clippers":            ("West", "Pacific"),
    "Los Angeles Lakers":     ("West", "Pacific"),
    "Memphis Grizzlies":      ("West", "Southwest"),
    "Miami Heat":             ("East", "Southeast"),
    "Milwaukee Bucks":        ("East", "Central"),
    "Minnesota Timberwolves": ("West", "Northwest"),
    "New Orleans Pelicans":   ("West", "Southwest"),
    "New York Knicks":        ("East", "Atlantic"),
    "Oklahoma City Thunder":  ("West", "Northwest"),
    "Orlando Magic":          ("East", "Southeast"),
    "Philadelphia 76ers":     ("East", "Atlantic"),
    "Phoenix Suns":           ("West", "Pacific"),
    "Portland Trail Blazers": ("West", "Northwest"),
    "Sacramento Kings":       ("West", "Pacific"),
    "San Antonio Spurs":      ("West", "Southwest"),
    "Toronto Raptors":        ("East", "Atlantic"),
    "Utah Jazz":              ("West", "Northwest"),
    "Washington Wizards":     ("East", "Southeast"),
}


def get_team_info(team_name):
    """Record, conference, division. Ranks computed from cached standings."""
    static_conf, static_div = _TEAM_CONF_DIV.get(team_name, ("", ""))

    # Build conf/div ranks from cached base stats — no extra API call needed
    base = _get_team_stats()
    conf_rank = div_rank = "—"
    w = l = "—"

    if not base.empty and "W" in base.columns:
        row = base[base["TEAM_NAME"] == team_name]
        if not row.empty:
            w = int(row.iloc[0]["W"])
            l = int(row.iloc[0]["L"])

        # Tag every team with its conf/div from static map
        base = base.copy()
        base["_conf"] = base["TEAM_NAME"].map(lambda n: _TEAM_CONF_DIV.get(n, ("", ""))[0])
        base["_div"]  = base["TEAM_NAME"].map(lambda n: _TEAM_CONF_DIV.get(n, ("", ""))[1])

        # Rank by wins descending within conference
        conf_teams = base[base["_conf"] == static_conf].sort_values("W", ascending=False).reset_index(drop=True)
        conf_match = conf_teams[conf_teams["TEAM_NAME"] == team_name]
        if not conf_match.empty:
            conf_rank = int(conf_match.index[0]) + 1

        # Rank by wins descending within division
        div_teams = base[base["_div"] == static_div].sort_values("W", ascending=False).reset_index(drop=True)
        div_match = div_teams[div_teams["TEAM_NAME"] == team_name]
        if not div_match.empty:
            div_rank = int(div_match.index[0]) + 1

    return {
        "wins":      w,
        "losses":    l,
        "conf":      static_conf,
        "div":       static_div,
        "conf_rank": conf_rank,
        "div_rank":  div_rank,
    }


def get_team_full_stats(team_name):
    """Team stats with league ranks + best performers."""
    stats = _get_team_stats()

    team_row = stats[stats["TEAM_NAME"] == team_name]
    if team_row.empty:
        return {"error": "Team not found"}

    row      = team_row.iloc[0]
    team_abbr = row.get("TEAM_ABBREVIATION", "")

    # ── best performers ───────────────────────────────────────────────────────
    player_stats = get_league_player_stats()
    team_players = player_stats[player_stats["TEAM_ABBREVIATION"] == team_abbr]
    # Fallback: match by team name if abbreviation yields nothing
    if team_players.empty and "TEAM_NAME" in player_stats.columns:
        team_players = player_stats[player_stats["TEAM_NAME"] == team_name]

    def best_player(col, label_suffix):
        if team_players.empty:
            return None
        p = team_players.loc[team_players[col].idxmax()]
        return {
            "name":     p["PLAYER_NAME"],
            "initials": "".join(w[0] for w in p["PLAYER_NAME"].split()[:2]),
            "stat_val": round(p[col], 1),
            "stat_lbl": label_suffix,
            "value":    f"{round(p[col], 1)} {label_suffix}",
        }

    info = get_team_info(team_name)

    # ── Advanced metrics ──────────────────────────────────────────────────────
    adv = _get_team_advanced_stats()
    ortg = drtg = net_rtg = None
    rank_ortg = rank_drtg = rank_net = None
    if adv is not None and not adv.empty:
        adv_row = adv[adv["TEAM_NAME"] == team_name]
        if not adv_row.empty:
            ar = adv_row.iloc[0]
            if "OFF_RATING" in adv.columns:
                ortg = round(ar["OFF_RATING"], 1)
                rank_ortg = _rank_of(adv["OFF_RATING"], ar["OFF_RATING"])
            if "DEF_RATING" in adv.columns:
                drtg = round(ar["DEF_RATING"], 1)
                rank_drtg = int((adv["DEF_RATING"] < ar["DEF_RATING"]).sum()) + 1
            if "NET_RATING" in adv.columns:
                net_rtg = round(ar["NET_RATING"], 1)
                rank_net = _rank_of(adv["NET_RATING"], ar["NET_RATING"])

    # ── Shooting ranks + FTA + 3FGA ──────────────────────────────────────────
    fta_pg  = round(row["FTA"] / row["GP"], 1) if "FTA"  in stats.columns else None
    fg3a_pg = round(row["FG3A"] / row["GP"], 1) if "FG3A" in stats.columns else None

    return {
        "team":       team_name,
        "abbr":       team_abbr,
        "gp":         int(row["GP"]),
        "ppg":        round(row["PTS"], 1),
        "reb":        round(row["REB"], 1),
        "ast":        round(row["AST"], 1),
        "stl":        round(row["STL"], 1),
        "blk":        round(row["BLK"], 1),
        "fg_pct":     round(row["FG_PCT"], 3),
        "three_pct":  round(row["FG3_PCT"], 3),
        "ft_pct":     round(row.get("FT_PCT", 0), 3),
        "fta_pg":     fta_pg,
        "fg3a_pg":    fg3a_pg,
        "rank_pts":   _rank_of(stats["PTS"],    row["PTS"]),
        "rank_reb":   _rank_of(stats["REB"],    row["REB"]),
        "rank_ast":   _rank_of(stats["AST"],    row["AST"]),
        "rank_stl":   _rank_of(stats["STL"],    row["STL"]),
        "rank_blk":   _rank_of(stats["BLK"],    row["BLK"]),
        "rank_fg":    _rank_of(stats["FG_PCT"],  row["FG_PCT"]),
        "rank_3fg":   _rank_of(stats["FG3_PCT"], row["FG3_PCT"]),
        "rank_ft":    _rank_of(stats["FT_PCT"],  row["FT_PCT"]) if "FT_PCT" in stats.columns else None,
        "rank_fta":   _rank_of(stats["FTA"] / stats["GP"], fta_pg) if "FTA" in stats.columns else None,
        "rank_3fga":  _rank_of(stats["FG3A"] / stats["GP"], fg3a_pg) if "FG3A" in stats.columns else None,
        "wins":       info.get("wins",      row.get("W", "—")),
        "losses":     info.get("losses",    row.get("L", "—")),
        "conf":       info.get("conf",      ""),
        "div":        info.get("div",       ""),
        "conf_rank":  info.get("conf_rank", "—"),
        "div_rank":   info.get("div_rank",  "—"),
        "ortg":       ortg,
        "drtg":       drtg,
        "net_rtg":    net_rtg,
        "rank_ortg":  rank_ortg,
        "rank_drtg":  rank_drtg,
        "rank_net":   rank_net,
        "best_scorer":    best_player("PTS", "PPG"),
        "best_rebounder": best_player("REB", "RPG"),
        "best_blocker":   best_player("BLK", "BPG"),
        # keep old keys for backward compat
        "best_offensive":  best_player("PTS", "PPG"),
        "best_defensive":  best_player("BLK", "BPG"),
    }


# ── Backward-compatible wrappers ──────────────────────────────────────────────

def get_team_season_stats(team_name):
    stats = _get_team_stats()
    team_row = stats[stats["TEAM_NAME"] == team_name]
    if team_row.empty:
        return {"error": "Team not found"}
    row = team_row.iloc[0]
    return {
        "team":      team_name,
        "ppg":       round(row["PTS"], 1),
        "fg_pct":    row["FG_PCT"],
        "three_pct": row["FG3_PCT"],
        "rebounds":  round(row["REB"], 1),
        "assists":   round(row["AST"], 1),
        "steals":    round(row["STL"], 1),
        "blocks":    round(row["BLK"], 1),
        "turnovers": round(row["TOV"], 1),
        "wins":      row["W"],
        "losses":    row["L"],
    }


def get_last_n_games(team_name, n=5):
    gamefinder = leaguegamefinder.LeagueGameFinder()
    games      = gamefinder.get_data_frames()[0]
    team_games = games[games["TEAM_NAME"] == team_name].head(n)
    if team_games.empty:
        return {"error": "No games found"}
    return [
        {"points": g["PTS"], "fg_pct": g["FG_PCT"],
         "three_pct": g["FG3_PCT"], "result": g["WL"]}
        for _, g in team_games.iterrows()
    ]


def get_team_game_log(team_name, n=5):
    """
    Return last N games for a team with full box score for each game.
    """
    gamefinder = leaguegamefinder.LeagueGameFinder()
    games      = gamefinder.get_data_frames()[0]
    team_games = games[games["TEAM_NAME"] == team_name].head(n)

    if team_games.empty:
        return {"error": "No games found"}

    log = []
    for _, game in team_games.iterrows():
        game_id = game["GAME_ID"]

        # Try to get box score
        players = []
        try:
            boxscore     = _nba_call(lambda gid=game_id: boxscoretraditionalv2.BoxScoreTraditionalV2(
                game_id=gid
            ).get_data_frames()[0])

            team_players = boxscore[boxscore["TEAM_ID"] == game["TEAM_ID"]]
            team_players = team_players.sort_values("PTS", ascending=False)

            for _, p in team_players.iterrows():
                if p["MIN"] and str(p["MIN"]) not in ("None", "nan", ""):
                    players.append({
                        "name":    p["PLAYER_NAME"],
                        "min":     str(p["MIN"])[:5],
                        "pts":     int(p["PTS"])   if p["PTS"]   == p["PTS"] else 0,
                        "reb":     int(p["REB"])   if p["REB"]   == p["REB"] else 0,
                        "ast":     int(p["AST"])   if p["AST"]   == p["AST"] else 0,
                        "stl":     int(p["STL"])   if p["STL"]   == p["STL"] else 0,
                        "blk":     int(p["BLK"])   if p["BLK"]   == p["BLK"] else 0,
                        "fg":      f"{int(p['FGM']) if p['FGM']==p['FGM'] else 0}-{int(p['FGA']) if p['FGA']==p['FGA'] else 0}",
                        "fg3":     f"{int(p['FG3M']) if p['FG3M']==p['FG3M'] else 0}-{int(p['FG3A']) if p['FG3A']==p['FG3A'] else 0}",
                        "ft":      f"{int(p['FTM']) if p['FTM']==p['FTM'] else 0}-{int(p['FTA']) if p['FTA']==p['FTA'] else 0}",
                        "plus_minus": int(p["PLUS_MINUS"]) if p["PLUS_MINUS"] == p["PLUS_MINUS"] else 0,
                    })
        except Exception:
            pass

        log.append({
            "date":       str(game.get("GAME_DATE", ""))[:10],
            "matchup":    game.get("MATCHUP", ""),
            "result":     "W" if game.get("WL") == "W" else "L",
            "pts":        int(game["PTS"]),
            "opp_pts":    None,   # not in gamefinder; shown in matchup string
            "fg_pct":     round(float(game["FG_PCT"]) * 100, 1),
            "three_pct":  round(float(game["FG3_PCT"]) * 100, 1),
            "reb":        int(game["REB"]),
            "ast":        int(game["AST"]),
            "tov":        int(game["TOV"]),
            "players":    players,
        })

    return log


def get_last_game_with_players(team_name):
    gamefinder = leaguegamefinder.LeagueGameFinder()
    games      = gamefinder.get_data_frames()[0]
    team_games = games[games["TEAM_NAME"] == team_name]
    if team_games.empty:
        return {"error": "Team not found"}

    last_game = team_games.iloc[0]
    boxscore  = boxscoretraditionalv2.BoxScoreTraditionalV2(
        game_id=last_game["GAME_ID"]
    )
    player_stats = boxscore.get_data_frames()[0]
    team_players = player_stats[
        player_stats["TEAM_ID"] == last_game["TEAM_ID"]
    ].sort_values(by="PTS", ascending=False).head(5)

    return {
        "team":      last_game["TEAM_NAME"],
        "matchup":   last_game["MATCHUP"],
        "points":    last_game["PTS"],
        "fg_pct":    last_game["FG_PCT"],
        "three_pct": last_game["FG3_PCT"],
        "turnovers": last_game["TOV"],
        "rebounds":  last_game["REB"],
        "result":    "win" if last_game["WL"] == "W" else "loss",
        "players": [
            {
                "name":      row["PLAYER_NAME"],
                "points":    row["PTS"],
                "assists":   row["AST"],
                "rebounds":  row["REB"],
                "steals":    row["STL"],
                "blocks":    row["BLK"],
                "minutes":   row["MIN"],
                "fg_pct":    row["FG_PCT"],
                "three_pct": row["FG3_PCT"],
            }
            for _, row in team_players.iterrows()
        ],
    }


def compare_teams(team1, team2):
    stats  = _get_team_stats()
    t1_row = stats[stats["TEAM_NAME"] == team1]
    t2_row = stats[stats["TEAM_NAME"] == team2]
    if t1_row.empty or t2_row.empty:
        return {"error": "One or both teams not found"}

    def build(r):
        return {
            "name": r["TEAM_NAME"], "ppg": round(r["PTS"], 1),
            "fg_pct": r["FG_PCT"], "three_pct": r["FG3_PCT"],
            "assists": round(r["AST"], 1), "steals": round(r["STL"], 1),
            "blocks": round(r["BLK"], 1), "rebounds": round(r["REB"], 1),
        }
    return {"team1": build(t1_row.iloc[0]), "team2": build(t2_row.iloc[0])}


def compare_players(player1, player2):
    stats   = get_league_player_stats()
    n1, n2  = _normalize(player1), _normalize(player2)
    p1_rows = stats[stats["PLAYER_NAME"].apply(lambda n: n1 in _normalize(n))]
    p2_rows = stats[stats["PLAYER_NAME"].apply(lambda n: n2 in _normalize(n))]
    if p1_rows.empty:
        return {"error": f"Player not found: {player1}"}
    if p2_rows.empty:
        return {"error": f"Player not found: {player2}"}

    def build(r):
        return {
            "name": r["PLAYER_NAME"], "team": r["TEAM_ABBREVIATION"],
            "ppg": round(r["PTS"], 1), "fg_pct": r["FG_PCT"],
            "three_pct": r["FG3_PCT"], "ast": round(r["AST"], 1),
            "reb": round(r["REB"], 1), "stl": round(r["STL"], 1),
            "blk": round(r["BLK"], 1), "tov": round(r["TOV"], 1),
        }
    return {"player1": build(p1_rows.iloc[0]), "player2": build(p2_rows.iloc[0])}


def get_top_league_leaders(stat="PTS", n=10):
    stats = get_league_player_stats()
    if stat not in stats.columns:
        return {"error": f"Unknown stat: {stat}"}
    return stats.nlargest(n, stat)[
        ["PLAYER_NAME", "TEAM_ABBREVIATION",
         "PTS", "AST", "REB", "STL", "BLK", "FG_PCT", "FG3_PCT"]
    ].to_dict(orient="records")


# ── Comparison helpers ────────────────────────────────────────────────────────

# ── Legend / retired players supplement ──────────────────────────────────────
# These players are in nba_api's ALL-player list (get_players()) but not active.
LEGENDS = [
    "Michael Jordan", "Kobe Bryant", "Shaquille O'Neal", "LeBron James",
    "Kareem Abdul-Jabbar", "Tim Duncan", "Magic Johnson", "Larry Bird",
    "Wilt Chamberlain", "Bill Russell", "Oscar Robertson", "Jerry West",
    "Charles Barkley", "Karl Malone", "John Stockton", "Hakeem Olajuwon",
    "Patrick Ewing", "David Robinson", "Isiah Thomas", "Clyde Drexler",
    "Scottie Pippen", "Dennis Rodman", "Kevin Garnett", "Allen Iverson",
    "Dirk Nowitzki", "Steve Nash", "Ray Allen", "Paul Pierce",
    "Tracy McGrady", "Vince Carter", "Dwyane Wade", "Chris Bosh",
    "Dwight Howard", "Pau Gasol", "Tony Parker", "Manu Ginobili",
    "Reggie Miller", "Gary Payton", "Alonzo Mourning", "Patrick Ewing",
    "Dominique Wilkins", "James Worthy", "Bob Cousy", "Willis Reed",
]


def _get_player_id_all(player_name):
    """Look up player ID including retired players. Uses progressive matching."""
    from nba_api.stats.static import players as nba_players
    norm = _normalize(player_name)

    all_players = nba_players.get_players()

    # 1. Exact normalized match
    for p in all_players:
        if _normalize(p["full_name"]) == norm:
            return p["id"]

    # 2. Partial normalized match (name contains search or vice versa)
    for p in all_players:
        pn = _normalize(p["full_name"])
        if norm in pn or pn in norm:
            return p["id"]

    # 3. Last name only match (e.g. "Abdul-Jabbar" → "Kareem Abdul-Jabbar")
    norm_parts = norm.split()
    if len(norm_parts) >= 2:
        last = norm_parts[-1]
        first = norm_parts[0]
        for p in all_players:
            pn = _normalize(p["full_name"])
            pn_parts = pn.split()
            if len(pn_parts) >= 2 and pn_parts[0] == first and pn_parts[-1] == last:
                return p["id"]

    # 4. All words in search appear somewhere in the player name
    for p in all_players:
        pn = _normalize(p["full_name"])
        if all(part in pn for part in norm_parts if len(part) > 2):
            return p["id"]

    return None


def get_player_career_stats(player_name):
    """
    Fetch career averages + top 5 seasons with per-season award flags + teams list.
    Works for active and retired players.
    """
    player_id = _get_player_id_all(player_name)
    if not player_id:
        return {"error": f"Player not found: {player_name}"}

    try:
        frames = _nba_call(lambda: playercareerstats.PlayerCareerStats(
            player_id=player_id,
            per_mode36="PerGame",
            timeout=NBA_TIMEOUT
        ).get_data_frames())

        career_df = frames[1] if len(frames) > 1 else frames[0]
        season_df = frames[0]

        if career_df.empty:
            return {"error": "No career data found"}

        row = career_df.iloc[0]

        def safe(col):
            try:
                return round(float(row[col]), 1) if col in row.index else None
            except Exception:
                return None

        # True Shooting %
        pts = safe("PTS") or 0
        fga = safe("FGA") or 0
        fta = safe("FTA") or 0
        ts  = round(pts / (2 * (fga + 0.44 * fta)) * 100, 1) if (fga + fta) > 0 else None

        # All teams played for (deduplicated, in order)
        teams = []
        if not season_df.empty and "TEAM_ABBREVIATION" in season_df.columns:
            seen = set()
            for t in season_df["TEAM_ABBREVIATION"].tolist():
                if t and t not in seen and t != "TOT":
                    seen.add(t)
                    teams.append(t)

        # Per-season award flags from playerawards
        # season_awards: {"2008-09": {"all_star": True, "all_nba": True, "ring": True}}
        season_awards = {}
        try:
            awards_df = _nba_call(lambda: playerawards.PlayerAwards(
                player_id=player_id, timeout=NBA_TIMEOUT
            ).get_data_frames()[0])
            if awards_df is not None and not awards_df.empty:
                awards_df["DESC_U"] = awards_df["DESCRIPTION"].str.strip().str.upper()
                season_col = "SEASON" if "SEASON" in awards_df.columns else None
                if season_col:
                    for _, aw in awards_df.iterrows():
                        s   = str(aw[season_col])
                        d   = aw["DESC_U"]
                        if s not in season_awards:
                            season_awards[s] = {"all_star": False, "all_nba": False,
                                                "ring": False, "finals_mvp": False,
                                                "mvp": False, "dpoy": False}
                        sa = season_awards[s]
                        if "ALL-STAR" in d and "SKILLS" not in d and "DUNK" not in d:
                            sa["all_star"] = True
                        if "ALL-NBA" in d or "ALL-ABA" in d:
                            sa["all_nba"] = True
                        if "CHAMPION" in d:
                            sa["ring"] = True
                        if d == "NBA FINALS MOST VALUABLE PLAYER":
                            sa["finals_mvp"] = True
                        if d == "NBA MOST VALUABLE PLAYER":
                            sa["mvp"] = True
                        if "DEFENSIVE PLAYER" in d and "YEAR" in d:
                            sa["dpoy"] = True
        except Exception:
            pass

        # Top 5 seasons by PPG
        top_seasons = []
        if not season_df.empty and "PTS" in season_df.columns:
            top5 = season_df.nlargest(5, "PTS")
            for _, sr in top5.iterrows():
                season_id = str(sr.get("SEASON_ID", ""))
                # Convert "22008" style to "2008-09" for award lookup
                award_key = season_id[1:] if len(season_id) == 5 else season_id
                flags = season_awards.get(award_key, {})

                def s_safe(col):
                    try: return round(float(sr[col]), 1) if col in sr.index else None
                    except: return None

                s_pts = s_safe("PTS")
                s_fga = s_safe("FGA") or 0
                s_fta = s_safe("FTA") or 0
                s_ts  = round(s_pts / (2 * (s_fga + 0.44 * s_fta)) * 100, 1) \
                        if (s_pts and (s_fga + s_fta) > 0) else None

                top_seasons.append({
                    "season":     season_id[1:] if len(season_id) == 5 else season_id,
                    "team":       sr.get("TEAM_ABBREVIATION", ""),
                    "gp":         int(sr["GP"]) if "GP" in sr.index else None,
                    "ppg":        s_safe("PTS"),
                    "reb":        s_safe("REB"),
                    "ast":        s_safe("AST"),
                    "fg_pct":     round(float(sr["FG_PCT"]), 3) if "FG_PCT" in sr.index else None,
                    "three_pct":  round(float(sr["FG3_PCT"]), 3) if "FG3_PCT" in sr.index else None,
                    "ft_pct":     round(float(sr["FT_PCT"]), 3) if "FT_PCT" in sr.index else None,
                    "ts_pct":     s_ts,
                    "all_star":   flags.get("all_star", False),
                    "all_nba":    flags.get("all_nba", False),
                    "ring":       flags.get("ring", False),
                    "finals_mvp": flags.get("finals_mvp", False),
                    "mvp":        flags.get("mvp", False),
                    "dpoy":       flags.get("dpoy", False),
                })

        return {
            "name":          player_name,
            "career_games":  int(row.get("GP", 0)) if "GP" in row.index else 0,
            "career_ppg":    safe("PTS"),
            "career_reb":    safe("REB"),
            "career_ast":    safe("AST"),
            "career_stl":    safe("STL"),
            "career_blk":    safe("BLK"),
            "career_fg_pct": round(float(row["FG_PCT"]), 3) if "FG_PCT" in row.index else None,
            "career_3_pct":  round(float(row["FG3_PCT"]), 3) if "FG3_PCT" in row.index else None,
            "career_ft_pct": round(float(row["FT_PCT"]), 3) if "FT_PCT" in row.index else None,
            "career_ts_pct": ts,
            "seasons":       len(season_df) if not season_df.empty else 0,
            "teams":         teams,
            "top_seasons":   top_seasons,
            # Keep old key for backward compat
            "best_season":   top_seasons[0] if top_seasons else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_all_player_names_with_legends():
    """Return sorted list of active players + legends for dropdowns."""
    from nba_api.stats.static import players as nba_players
    active = [p["full_name"] for p in nba_players.get_active_players()]
    # Add legends not already in active
    active_norm = {_normalize(n) for n in active}
    extras = [n for n in LEGENDS if _normalize(n) not in active_norm]
    return sorted(set(active + extras))


# ── 2025-26 Rookie supplement ─────────────────────────────────────────────────
ROOKIES_2025_26 = [
    ("Cooper Flagg",              "DAL"),
    ("Dylan Harper",              "SAS"),
    ("Ace Bailey",                "UTA"),
    ("VJ Edgecombe",              "PHI"),
    ("Tre Johnson",               "WAS"),
    ("Kon Knueppel",              "BKN"),
    ("Nolan Traore",              "NOP"),
    ("Kasparas Jakucionis",       "CHI"),
    ("Egor Demin",                "UTA"),
    ("Collin Murray-Boyles",      "MIA"),
    ("Jase Richardson",           "DET"),
    ("Asa Newell",                "POR"),
    ("Will Riley",                "IND"),
    ("Rasheer Fleming",           "MEM"),
    ("Liam McNeeley",             "DEN"),
    ("Walter Clayton Jr",         "MIL"),
    ("Khaman Maluach",            "LAC"),
    ("Labaron Philon",            "HOU"),
    ("Derik Queen",               "ORL"),
    ("Tyler Betsey",              "SAC"),
    ("Pacome Dadiet",             "NYK"),
    ("RJ Luis Jr",                "PHX"),
    ("Yves Missi",                "GSW"),
    ("Boogie Fland",              "MIN"),
    ("Sion James",                "CLE"),
    ("Johni Broome",              "ATL"),
    ("Adou Thiero",               "OKC"),
    ("Nique Clifford",            "BOS"),
    ("Tahaad Pettiford",          "SAS"),
    ("Isaiah Collier",            "MEM"),
]


def _rookie_in_static(name):
    """Check if a rookie is already in the nba_api static player list."""
    norm = _normalize(name)
    for p in nba_static_players.get_active_players():
        if _normalize(p["full_name"]) == norm:
            return True
    return False


def get_all_active_player_names():
    """
    Return sorted list of all active player full names for dropdowns.
    Merges nba_api static data with 2025-26 rookie supplement.
    """
    static_names = [p["full_name"] for p in nba_static_players.get_active_players()]

    # Add rookies not yet in static data
    extra = [name for name, _ in ROOKIES_2025_26 if not _rookie_in_static(name)]
    return sorted(set(static_names + extra))


def get_player_accolades(player_name):
    """
    Fetch career accolades. Deduplicates by (description, season) to prevent
    double-counting, and uses tight logical filters per award type.
    """
    player_id = _get_player_id_all(player_name)
    if not player_id:
        return {}

    try:
        awards_df = _nba_call(lambda: playerawards.PlayerAwards(
            player_id=player_id,
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0])

        if awards_df is None or awards_df.empty:
            return {}

        # Normalize description
        awards_df = awards_df.copy()
        awards_df["DESC_UPPER"] = awards_df["DESCRIPTION"].str.strip().str.upper()

        # Deduplicate: same award in the same season = 1 entry
        season_col = "SEASON" if "SEASON" in awards_df.columns else None
        if season_col:
            awards_df = awards_df.drop_duplicates(subset=["DESC_UPPER", season_col])

        desc = awards_df["DESC_UPPER"]

        # Championships
        rings = int(desc.str.contains("CHAMPION", na=False).sum())

        # Regular season MVP — exact string only
        # Raw API values: "NBA Most Valuable Player"
        mvps = int(
            (desc == "NBA MOST VALUABLE PLAYER").sum()
        )

        # Finals MVP — exact string
        # Raw API value: "NBA Finals Most Valuable Player"
        finals_mvp = int(
            (desc == "NBA FINALS MOST VALUABLE PLAYER").sum()
        )

        # All-NBA selections
        all_nba = int(desc.str.contains("ALL-NBA", na=False).sum())

        # All-Defensive
        all_defense = int(
            (desc.str.contains("ALL-DEFENSIVE", na=False) |
             desc.str.contains("DEFENSIVE TEAM", na=False)).sum()
        )

        # All-Star — exclude skills/celebrity/dunk/three/game events
        AS_EXCLUDE = ["SKILLS", "CELEBRITY", "DUNK", "THREE", "GAME MVP",
                      "RISING STARS", "PRACTICE"]
        as_mask = desc.str.contains("ALL-STAR", na=False)
        for word in AS_EXCLUDE:
            as_mask = as_mask & ~desc.str.contains(word, na=False)
        all_star = int(as_mask.sum())

        # Scoring title
        scoring = int(
            (desc.str.contains("SCORING", na=False) &
             (desc.str.contains("CHAMPION", na=False) |
              desc.str.contains("TITLE", na=False) |
              desc.str.contains("LEADER", na=False))).sum()
        )

        # DPOY — must contain "DEFENSIVE PLAYER" and "YEAR"
        dpoy = int(
            (desc.str.contains("DEFENSIVE PLAYER", na=False) &
             desc.str.contains("YEAR", na=False)).sum()
        )

        # ROY — must contain "ROOKIE" and "YEAR", cap at 1 (can only win once)
        roty = min(1, int(
            (desc.str.contains("ROOKIE", na=False) &
             desc.str.contains("YEAR", na=False)).sum()
        ))

        # Olympic medals
        olympic = int(
            (desc.str.contains("OLYMPIC", na=False) |
             desc.str.contains("USA BASKETBALL", na=False)).sum()
        )

        return {
            "rings":       rings,
            "finals_mvp":  finals_mvp,
            "mvps":        mvps,
            "all_nba":     all_nba,
            "all_defense": all_defense,
            "all_star":    all_star,
            "scoring":     scoring,
            "dpoy":        dpoy,
            "roty":        roty,
            "olympic":     olympic,
        }
    except Exception:
        return {}


def get_player_comparison_data(player1_name, player2_name):
    """Full data bundle for the comparison tab — stats, bio, accolades, zones, career."""
    def build(name):
        stats    = get_player_season_stats(name)
        bio      = get_player_bio(name)
        accolades= get_player_accolades(name)
        career   = get_player_career_stats(name)
        photo    = get_player_photo_url(name)
        zones    = get_player_shot_zones(name)
        team     = stats.get("team", "") if "error" not in stats else ""
        colors   = get_team_colors(team) if team else get_team_colors("Los Angeles Lakers")
        return {
            "name":      name,
            "stats":     stats,
            "bio":       bio,
            "accolades": accolades,
            "career":    career,
            "photo":     photo,
            "zones":     zones,
            "colors":    colors,
        }

    return build(player1_name), build(player2_name)


def get_all_active_player_names():
    """Return sorted list of all active players + legends for dropdowns."""
    return get_all_player_names_with_legends()


def get_team_accolades(team_name):
    """Championships and playoff appearances from teamyearbyyearstats."""
    team_id = _get_team_id(team_name)
    if not team_id:
        return {"championships": 0, "playoff_appearances": 0}

    try:
        df = _nba_call(lambda: teamyearbyyearstats.TeamYearByYearStats(
            team_id=team_id,
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0])

        if df is None or df.empty:
            return {"championships": 0, "playoff_appearances": 0}

        championships     = int(df["NBA_FINALS_APPEARANCE"].str.upper().str.contains("C").sum()) \
                            if "NBA_FINALS_APPEARANCE" in df.columns else 0
        playoff_appearances = int((df["PLAYOFF_WINS"] > 0).sum()) \
                            if "PLAYOFF_WINS" in df.columns else 0

        return {
            "championships":      championships,
            "playoff_appearances": playoff_appearances,
        }
    except Exception:
        return {"championships": 0, "playoff_appearances": 0}


def get_team_comparison_data(team1_name, team2_name):
    """Full data bundle for team comparison tab."""
    def build(name):
        stats    = get_team_full_stats(name)
        accolades= get_team_accolades(name)
        logo     = get_team_logo_url(name)
        colors   = get_team_colors(name)
        return {
            "name":      name,
            "stats":     stats,
            "accolades": accolades,
            "logo":      logo,
            "colors":    colors,
        }

    return build(team1_name), build(team2_name)


# ── Standings ─────────────────────────────────────────────────────────────────

_STANDINGS_CACHE = None

def get_league_standings():
    """
    Fetch full league standings including home/road records, conference rank,
    and playoff status indicators.
    Returns list of team dicts sorted by overall win%.
    """
    global _STANDINGS_CACHE
    if _STANDINGS_CACHE is not None:
        return _STANDINGS_CACHE

    def _fetch():
        return leaguestandingsv3.LeagueStandingsV3(
            season=CURRENT_SEASON,
            season_type="Regular Season",
            timeout=NBA_TIMEOUT
        ).get_data_frames()[0]

    try:
        df = _nba_call(_fetch)
    except Exception:
        # Fallback to base stats if endpoint unavailable
        base = _get_team_stats()
        result = []
        for _, row in base.iterrows():
            conf, div = _TEAM_CONF_DIV.get(row["TEAM_NAME"], ("", ""))
            result.append({
                "team":        row["TEAM_NAME"],
                "abbr":        row.get("TEAM_ABBREVIATION", ""),
                "conf":        conf,
                "div":         div,
                "wins":        int(row.get("W", 0)),
                "losses":      int(row.get("L", 0)),
                "win_pct":     round(row.get("W", 0) / max(row.get("GP", 1), 1), 3),
                "home_w":      None, "home_l": None,
                "road_w":      None, "road_l": None,
                "conf_rank":   None,
                "playoff_flag":"",
            })
        result.sort(key=lambda x: x["win_pct"], reverse=True)
        for i, t in enumerate(result):
            t["overall_rank"] = i + 1
        _STANDINGS_CACHE = result
        return result

    # Map available columns safely
    def safe(row, col, default=None):
        return row[col] if col in df.columns and not (row[col] != row[col]) else default

    # Determine playoff/play-in/eliminated flag per conference rank
    def playoff_flag(conf_rank, clinch_str, elim_str):
        """
        Returns: 'x' playoff, 'pi' play-in (7-10), '-' eliminated, '' in contention
        Some versions of the API have ClinchIndicator or ClinchedPlayoffBirth cols.
        """
        if clinch_str and str(clinch_str).strip().lower() not in ("none", "nan", ""):
            ci = str(clinch_str).strip().upper()
            if "E" in ci:
                return "-"   # eliminated
            return "x"      # clinched
        if elim_str and str(elim_str).strip() not in ("0", "", "nan", "None"):
            return "-"
        try:
            rank = int(conf_rank)
            if rank <= 6:
                return "x"
            elif rank <= 10:
                return "pi"
            else:
                return ""
        except Exception:
            return ""

    result = []
    for _, row in df.iterrows():
        # Column names vary by API version — try multiple options
        team  = safe(row, "TeamName") or safe(row, "TEAM_NAME", "")
        abbr  = safe(row, "TeamSlug") or safe(row, "TEAM_ABBREVIATION", "")
        conf  = safe(row, "Conference") or safe(row, "TEAM_CONFERENCE", "")
        div   = safe(row, "Division") or safe(row, "TEAM_DIVISION", "")
        wins  = int(safe(row, "WINS") or safe(row, "W") or 0)
        losses= int(safe(row, "LOSSES") or safe(row, "L") or 0)
        pct   = float(safe(row, "WinPCT") or safe(row, "WIN_PCT") or 0)
        c_rank= safe(row, "ConferenceRecord") or safe(row, "PlayoffRank") or safe(row, "ConferenceRank")
        clinch= safe(row, "ClinchIndicator") or safe(row, "ClinchedPlayoffBirth")
        elim  = safe(row, "EliminationNumber")

        # Home / Road record
        home_rec = str(safe(row, "HOME") or "")
        road_rec = str(safe(row, "ROAD") or "")
        hw = hl = rw = rl = None
        if "-" in home_rec:
            parts = home_rec.split("-")
            hw, hl = int(parts[0]), int(parts[1])
        if "-" in road_rec:
            parts = road_rec.split("-")
            rw, rl = int(parts[0]), int(parts[1])

        # Conference rank (integer)
        try:
            conf_rank_int = int(safe(row, "PlayoffRank") or safe(row, "ConferenceRank") or 0)
        except Exception:
            conf_rank_int = 0

        if not team:
            continue

        result.append({
            "team":         team,
            "abbr":         abbr,
            "conf":         conf,
            "div":          div,
            "wins":         wins,
            "losses":       losses,
            "win_pct":      pct,
            "home_w":       hw,
            "home_l":       hl,
            "road_w":       rw,
            "road_l":       rl,
            "conf_rank":    conf_rank_int,
            "playoff_flag": playoff_flag(conf_rank_int, clinch, elim),
        })

    result.sort(key=lambda x: x["win_pct"], reverse=True)
    for i, t in enumerate(result):
        t["overall_rank"] = i + 1

    _STANDINGS_CACHE = result
    return result


# ── Team schedule ─────────────────────────────────────────────────────────────

def _parse_nba_date(raw):
    """Convert NBA API date formats to YYYY-MM-DD string."""
    raw = str(raw).strip()
    if not raw:
        return ""
    # ISO format already: "2025-10-22"
    if len(raw) >= 10 and raw[4] == "-":
        return raw[:10]
    # NBA API format: "OCT 22, 2025"
    from datetime import datetime
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Fallback — return as-is
    return raw


def get_team_schedule(team_name, season=None):
    """
    Return full season schedule for a team (regular season + playoffs).
    Each game includes cumulative W-L record after that game.
    """
    season = season or CURRENT_SEASON
    team_id = _get_team_id(team_name)
    if not team_id:
        return {"error": f"Team not found: {team_name}"}

    try:
        df = _nba_call(lambda: teamgamelog.TeamGameLog(
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season",
            timeout=NBA_TIMEOUT,
        ).get_data_frames()[0])

        games = []
        if df is not None and not df.empty:
            # API returns most-recent first — reverse to chronological
            for _, row in df.iloc[::-1].iterrows():
                matchup = row.get("MATCHUP", "")
                is_home = "vs." in matchup
                opp     = matchup.split("vs.")[-1].strip() if is_home \
                          else matchup.split("@")[-1].strip()
                games.append({
                    "date":     _parse_nba_date(row.get("GAME_DATE", "")),
                    "home":     is_home,
                    "opponent": opp,
                    "result":   row.get("WL", ""),
                    "pts":      int(row["PTS"]) if "PTS" in row.index else None,
                    "matchup":  matchup,
                    "game_id":  str(row.get("Game_ID", "")),
                    "w":        int(row.get("W", 0)) if "W" in row.index else None,
                    "l":        int(row.get("L", 0)) if "L" in row.index else None,
                })

        # Try playoffs
        try:
            po_df = _nba_call(lambda: teamgamelog.TeamGameLog(
                team_id=team_id,
                season=season,
                season_type_all_star="Playoffs",
                timeout=NBA_TIMEOUT,
            ).get_data_frames()[0])
            if po_df is not None and not po_df.empty:
                for _, row in po_df.iloc[::-1].iterrows():
                    matchup = row.get("MATCHUP", "")
                    is_home = "vs." in matchup
                    opp     = matchup.split("vs.")[-1].strip() if is_home \
                              else matchup.split("@")[-1].strip()
                    games.append({
                        "date":     _parse_nba_date(row.get("GAME_DATE", "")),
                        "home":     is_home,
                        "opponent": opp,
                        "result":   row.get("WL", ""),
                        "pts":      int(row["PTS"]) if "PTS" in row.index else None,
                        "matchup":  matchup,
                        "game_id":  str(row.get("Game_ID", "")),
                        "playoffs": True,
                        "w":        int(row.get("W", 0)) if "W" in row.index else None,
                        "l":        int(row.get("L", 0)) if "L" in row.index else None,
                    })
        except Exception:
            pass

        games.sort(key=lambda g: g["date"])

        # Build cumulative record if W/L columns not in API response
        # (some API versions omit them in game log)
        cw = cl = 0
        for g in games:
            if g.get("w") is not None and not g.get("playoffs"):
                cw = g["w"]
                cl = g["l"]
            elif g.get("result") and not g.get("playoffs"):
                if g["result"] == "W":
                    cw += 1
                elif g["result"] == "L":
                    cl += 1
            g["cum_w"] = cw
            g["cum_l"] = cl

        return games
    except Exception as e:
        return {"error": str(e)}


# ── Box score game search ─────────────────────────────────────────────────────

def detect_season_type(date=None):
    """
    Determine NBA season type for a given date based on 2025-26 schedule:
    - Regular Season: Oct 21 2025 – Apr 12 2026
    - Play In:        Apr 14–17 2026
    - Playoffs:       Apr 18 2026 – Jun 19 2026
    Returns "Regular Season", "PlayIn", or "Playoffs"
    """
    from datetime import date as _date
    if date is None:
        date = _date.today()
    if isinstance(date, str):
        from datetime import datetime
        date = datetime.strptime(date, "%Y-%m-%d").date()

    if date >= _date(2026, 4, 18):
        return "Playoffs"
    if date >= _date(2026, 4, 14):
        return "PlayIn"
    if date >= _date(2025, 10, 21):
        return "Regular Season"
    return "Regular Season"


def get_todays_games(date_str=None):
    """
    Fetch today's games using NBA Live API (nba_api.live).
    This only returns real confirmed games — no ghost/placeholder series games.
    Falls back to scoreboardv2 and then leaguegamefinder.
    """
    from datetime import date as _date, datetime
    if date_str is None:
        date_str = _date.today().strftime("%Y-%m-%d")

    # ── Try NBA Live Scoreboard (most accurate, real-time) ────────────────
    try:
        from nba_api.live.nba.endpoints import scoreboard as live_sb
        board     = live_sb.ScoreBoard()
        data      = board.get_dict()
        games_raw = data.get("scoreboard", {}).get("games", [])
        results = []
        for g in games_raw:
            gid        = str(g.get("gameId", ""))
            status_val = int(g.get("gameStatus", 1))   # 1=pre 2=live 3=final
            status_txt = g.get("gameStatusText", "").strip()
            home       = g.get("homeTeam", {})
            away       = g.get("awayTeam", {})

            home_pts = home.get("score")
            away_pts = away.get("score")
            if home_pts is not None:
                try: home_pts = int(home_pts)
                except: home_pts = None
            if away_pts is not None:
                try: away_pts = int(away_pts)
                except: away_pts = None

            home_city  = home.get("teamCity", "")
            home_name  = home.get("teamName", "")
            away_city  = away.get("teamCity", "")
            away_name  = away.get("teamName", "")

            # Live period/clock info
            period = g.get("period", 0)
            clock  = g.get("gameClock", "")
            if status_val == 2 and period:
                # Format: "PT05M30.00S" → "Q3 5:30"
                try:
                    mins = int(float(clock.replace("PT","").replace("M",":").split(":")[0])) if clock else 0
                    secs = int(float(clock.split("M")[-1].replace("S",""))) if "M" in clock else 0
                    live_txt = f"Q{period} {mins}:{secs:02d}"
                except Exception:
                    live_txt = f"Q{period}"
            else:
                live_txt = status_txt

            # Series info from live API
            home_sw = int(home.get("wins", 0) or 0)
            away_sw = int(away.get("wins", 0) or 0)
            series_text = g.get("seriesText", "")

            results.append({
                "game_id":         gid,
                "date":            date_str,
                "status_id":       status_val,
                "status_txt":      live_txt,
                "is_live":         status_val == 2,
                "is_final":        status_val == 3,
                "home_abbr":       home.get("teamTricode", ""),
                "home_name":       f"{home_city} {home_name}".strip(),
                "home_pts":        home_pts,
                "away_abbr":       away.get("teamTricode", ""),
                "away_name":       f"{away_city} {away_name}".strip(),
                "away_pts":        away_pts,
                "finished":        status_val == 3,
                "home_series_wins":home_sw,
                "away_series_wins":away_sw,
                "series_text":     series_text,
            })
        if results:
            return results
    except Exception:
        pass

    # ── Fallback: scoreboardv2 ─────────────────────────────────────────────
    try:
        dt      = datetime.strptime(date_str, "%Y-%m-%d")
        sb_date = dt.strftime("%m/%d/%Y")
        sb = _nba_call(lambda: scoreboardv2.ScoreboardV2(
            game_date=sb_date, league_id="00", day_offset=0, timeout=NBA_TIMEOUT,
        ).get_data_frames())

        if sb is not None and len(sb) >= 2:
            game_header = sb[0]
            line_score  = sb[1]
            results = []
            for _, gh in game_header.iterrows():
                gid        = str(gh.get("GAME_ID", ""))
                status_val = int(gh.get("GAME_STATUS_ID", 1))
                status_txt = str(gh.get("GAME_STATUS_TEXT", "")).strip()
                home_tid   = gh.get("HOME_TEAM_ID")
                away_tid   = gh.get("VISITOR_TEAM_ID")

                home_row = line_score[line_score["TEAM_ID"] == home_tid]
                away_row = line_score[line_score["TEAM_ID"] == away_tid]

                def safe_name(row):
                    if row.empty: return ""
                    city = str(row["TEAM_CITY_NAME"].iloc[0]) if "TEAM_CITY_NAME" in row.columns else ""
                    name = str(row["TEAM_NAME"].iloc[0])      if "TEAM_NAME"      in row.columns else ""
                    return f"{city} {name}".strip()

                def safe_pts(row):
                    if row.empty or "PTS" not in row.columns: return None
                    v = row["PTS"].iloc[0]
                    return int(v) if v == v else None

                # Only include games that are live, final, or have confirmed time
                txt_up = status_txt.upper()
                if status_val in (2, 3) or any(x in txt_up for x in ["PM", "AM", "ET", ":"]):
                    results.append({
                        "game_id":    gid,
                        "date":       date_str,
                        "status_id":  status_val,
                        "status_txt": status_txt,
                        "is_live":    status_val == 2,
                        "is_final":   status_val == 3,
                        "home_abbr":  home_row["TEAM_ABBREVIATION"].iloc[0] if not home_row.empty else "",
                        "home_name":  safe_name(home_row),
                        "home_pts":   safe_pts(home_row),
                        "away_abbr":  away_row["TEAM_ABBREVIATION"].iloc[0] if not away_row.empty else "",
                        "away_name":  safe_name(away_row),
                        "away_pts":   safe_pts(away_row),
                        "finished":   status_val == 3,
                    })
            if results:
                return results
    except Exception:
        pass

    # ── Final fallback: leaguegamefinder (completed games only) ───────────
    stype = detect_season_type(date_str)
    return get_games_on_date(date_str, CURRENT_SEASON, stype)


def get_games_on_date(date_str, season=None, season_type="Regular Season"):
    """
    Return all games on a specific date — past, present, or future.
    Includes series wins for playoff games.
    """
    season   = season or CURRENT_SEASON
    from datetime import date as _date, datetime as _datetime
    try:
        req_date = _datetime.strptime(date_str, "%Y-%m-%d").date()
        is_future = req_date > _date.today()
    except Exception:
        is_future = False

    # ── For future or today: try scoreboardv2 first ───────────────────────
    if is_future or req_date == _date.today():
        try:
            dt      = _datetime.strptime(date_str, "%Y-%m-%d")
            sb_date = dt.strftime("%m/%d/%Y")
            sb = _nba_call(lambda: scoreboardv2.ScoreboardV2(
                game_date=sb_date, league_id="00", day_offset=0, timeout=NBA_TIMEOUT,
            ).get_data_frames())

            if sb is not None and len(sb) >= 2:
                game_header = sb[0]
                line_score  = sb[1]
                results = []
                for _, gh in game_header.iterrows():
                    gid        = str(gh.get("GAME_ID", ""))
                    status_val = int(gh.get("GAME_STATUS_ID", 1))
                    status_txt = str(gh.get("GAME_STATUS_TEXT", "")).strip()
                    home_tid   = gh.get("HOME_TEAM_ID")
                    away_tid   = gh.get("VISITOR_TEAM_ID")

                    home_row = line_score[line_score["TEAM_ID"] == home_tid]
                    away_row = line_score[line_score["TEAM_ID"] == away_tid]

                    def sn(row):
                        if row.empty: return ""
                        city = str(row["TEAM_CITY_NAME"].iloc[0]) if "TEAM_CITY_NAME" in row.columns else ""
                        name = str(row["TEAM_NAME"].iloc[0])      if "TEAM_NAME"      in row.columns else ""
                        return f"{city} {name}".strip()

                    def sp(row):
                        if row.empty or "PTS" not in row.columns: return None
                        v = row["PTS"].iloc[0]
                        return int(v) if v == v else None

                    txt_up = status_txt.upper()
                    # Skip TBD placeholders for ended series
                    if status_val not in (2, 3) and not any(x in txt_up for x in ["PM", "AM", "ET", ":"]):
                        continue

                    results.append({
                        "game_id":         gid,
                        "date":            date_str,
                        "status_id":       status_val,
                        "status_txt":      status_txt,
                        "is_live":         status_val == 2,
                        "is_final":        status_val == 3,
                        "home_abbr":       home_row["TEAM_ABBREVIATION"].iloc[0] if not home_row.empty else "",
                        "home_name":       sn(home_row),
                        "home_pts":        sp(home_row),
                        "away_abbr":       away_row["TEAM_ABBREVIATION"].iloc[0] if not away_row.empty else "",
                        "away_name":       sn(away_row),
                        "away_pts":        sp(away_row),
                        "finished":        status_val == 3,
                        "home_series_wins":0,
                        "away_series_wins":0,
                        "series_text":     "",
                    })
                if results:
                    return results
        except Exception:
            pass

    # ── For past games: leaguegamefinder ─────────────────────────────────
    try:
        df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
            date_from_nullable=date_str,
            date_to_nullable=date_str,
            season_nullable=season,
            season_type_nullable=season_type,
            league_id_nullable="00",
            timeout=NBA_TIMEOUT,
        ).get_data_frames()[0])

        if df is None or df.empty:
            return []

        # Build series win counts from the full season playoff log
        series_wins = {}  # game_id -> {home_abbr: wins, away_abbr: wins}
        if season_type == "Playoffs":
            try:
                # Get all playoff games this season to compute series records
                po_df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
                    season_nullable=season,
                    season_type_nullable="Playoffs",
                    league_id_nullable="00",
                    timeout=NBA_TIMEOUT,
                ).get_data_frames()[0])

                if po_df is not None and not po_df.empty:
                    # Group by matchup pairs and compute running series wins
                    po_df = po_df.sort_values("GAME_DATE")
                    # Build dict: (team_a, team_b) -> {wins_a, wins_b}
                    pair_wins = {}
                    for _, row in po_df.iterrows():
                        matchup = str(row.get("MATCHUP", ""))
                        t_abbr  = row.get("TEAM_ABBREVIATION", "")
                        gid     = str(row.get("GAME_ID", ""))
                        wl      = row.get("WL", "")
                        is_home = "vs." in matchup
                        opp_abbr = matchup.split("vs.")[-1].strip() if is_home else matchup.split("@")[-1].strip()

                        key = tuple(sorted([t_abbr, opp_abbr]))
                        if key not in pair_wins:
                            pair_wins[key] = {key[0]: 0, key[1]: 0}
                        if wl == "W":
                            pair_wins[key][t_abbr] = pair_wins[key].get(t_abbr, 0) + 1

                        series_wins[gid] = dict(pair_wins[key])
            except Exception:
                pass

        # Build game list
        games = {}
        for _, row in df.iterrows():
            gid     = str(row.get("GAME_ID", ""))
            matchup = row.get("MATCHUP", "")
            t_abbr  = row.get("TEAM_ABBREVIATION", "")
            is_home = "vs." in matchup
            opp_abbr = matchup.split("vs.")[-1].strip() if is_home \
                       else matchup.split("@")[-1].strip()

            if gid not in games:
                games[gid] = {
                    "game_id":   gid,
                    "date":      date_str,
                    "home_abbr": "", "home_name": "", "home_pts": None,
                    "away_abbr": "", "away_name": "", "away_pts": None,
                    "status_id": 3, "status_txt": "Final",
                    "is_live": False, "is_final": True, "finished": True,
                    "home_series_wins": 0, "away_series_wins": 0,
                    "series_text": "",
                }

            pts = int(row["PTS"]) if "PTS" in row.index and row["PTS"] == row["PTS"] else None
            team_name = row.get("TEAM_NAME", t_abbr)

            if is_home:
                games[gid]["home_abbr"] = t_abbr
                games[gid]["home_name"] = team_name
                games[gid]["home_pts"]  = pts
            else:
                games[gid]["away_abbr"] = t_abbr
                games[gid]["away_name"] = team_name
                games[gid]["away_pts"]  = pts

            # Attach series wins
            if gid in series_wins:
                sw = series_wins[gid]
                home_a = games[gid]["home_abbr"]
                away_a = games[gid]["away_abbr"]
                games[gid]["home_series_wins"] = sw.get(home_a, 0)
                games[gid]["away_series_wins"] = sw.get(away_a, 0)

        result = [g for g in games.values() if g["home_abbr"] and g["away_abbr"]]
        return sorted(result, key=lambda g: g.get("away_name", ""))
    except Exception:
        return []


def _get_series_info(home_abbr, away_abbr, game_date, season=None, season_type="Playoffs"):
    """Compute series wins and seedings for a playoff game."""
    season = season or CURRENT_SEASON
    info = {"home_wins": 0, "away_wins": 0, "game_number": 0,
            "home_seed": None, "away_seed": None}

    if season_type != "Playoffs":
        return info

    # Quick seeding lookup from static standings cache
    try:
        rows = get_full_standings()
        for r in rows:
            if r["abbr"].upper() == home_abbr.upper().strip():
                info["home_seed"] = r.get("conf_rank")
            if r["abbr"].upper() == away_abbr.upper().strip():
                info["away_seed"] = r.get("conf_rank")
    except Exception:
        pass

    # Series game log — only if we have a valid date
    if not game_date:
        return info

    try:
        home_full = next((t["full_name"] for t in nba_static_teams.get_teams()
                         if t["abbreviation"].upper() == home_abbr.upper().strip()), None)
        if not home_full:
            return info
        home_id = _get_team_id(home_full)
        if not home_id:
            return info

        df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
            team_id_nullable=home_id,
            season_nullable=season,
            season_type_nullable="Playoffs",
            timeout=15,   # short timeout so it doesn't stall UI
        ).get_data_frames()[0])

        if df is None or df.empty:
            return info

        # Filter to games vs the away team by abbreviation in matchup
        series_df = df[df["MATCHUP"].str.contains(away_abbr.strip(), case=False, na=False)]
        if series_df.empty:
            return info

        series_df = series_df.sort_values("GAME_DATE", ascending=True)
        games_up_to = series_df[series_df["GAME_DATE"] <= game_date]
        info["game_number"] = len(games_up_to)
        info["home_wins"]   = int((games_up_to["WL"] == "W").sum())
        info["away_wins"]   = int((games_up_to["WL"] == "L").sum())
    except Exception:
        pass

    return info


def get_boxscore_by_game_id(game_id, season_type="Regular Season", season=None):
    """Fetch full box score directly from a game_id, with series info and seedings."""
    season = season or CURRENT_SEASON
    try:
        bs = _nba_call(lambda: boxscoretraditionalv2.BoxScoreTraditionalV2(
            game_id=game_id, timeout=NBA_TIMEOUT
        ).get_data_frames())

        if bs is None:
            return {"error": "Box score unavailable"}

        players_df = bs[0]
        summary_df = bs[5] if len(bs) > 5 else None

        arena = attendance = date_str = ""
        if summary_df is not None and not summary_df.empty:
            s = summary_df.iloc[0]
            arena      = str(s.get("ARENA_NAME", ""))
            attendance = str(s.get("ATTENDANCE", ""))
            date_str   = _parse_nba_date(str(s.get("GAME_DATE_EST", "")))

        teams_out = {}
        abbr_list = []
        for team_abbr, grp in players_df.groupby("TEAM_ABBREVIATION"):
            abbr_list.append(team_abbr)
            grp = grp.sort_values("PTS", ascending=False)
            player_rows = []
            for _, p in grp.iterrows():
                if p.get("MIN") and str(p["MIN"]) not in ("None", "nan", ""):
                    player_rows.append({
                        "name":       p["PLAYER_NAME"],
                        "min":        str(p["MIN"])[:5],
                        "pts":        int(p["PTS"])       if p["PTS"]   == p["PTS"] else 0,
                        "reb":        int(p["REB"])       if p["REB"]   == p["REB"] else 0,
                        "ast":        int(p["AST"])       if p["AST"]   == p["AST"] else 0,
                        "stl":        int(p["STL"])       if p["STL"]   == p["STL"] else 0,
                        "blk":        int(p["BLK"])       if p["BLK"]   == p["BLK"] else 0,
                        "tov":        int(p["TO"])        if "TO" in p.index and p["TO"] == p["TO"] else 0,
                        "fg":         f"{int(p['FGM']) if p['FGM']==p['FGM'] else 0}-{int(p['FGA']) if p['FGA']==p['FGA'] else 0}",
                        "fg3":        f"{int(p['FG3M']) if p['FG3M']==p['FG3M'] else 0}-{int(p['FG3A']) if p['FG3A']==p['FG3A'] else 0}",
                        "ft":         f"{int(p['FTM']) if p['FTM']==p['FTM'] else 0}-{int(p['FTA']) if p['FTA']==p['FTA'] else 0}",
                        "plus_minus": int(p["PLUS_MINUS"]) if "PLUS_MINUS" in p.index and p["PLUS_MINUS"] == p["PLUS_MINUS"] else 0,
                    })
            teams_out[team_abbr] = {
                "players":   player_rows,
                "total_pts": sum(r["pts"] for r in player_rows),
            }

        away_abbr = abbr_list[0] if abbr_list else ""
        home_abbr = abbr_list[1] if len(abbr_list) > 1 else ""

        # Series info + seedings (for playoff games)
        series = _get_series_info(home_abbr, away_abbr, date_str, season, season_type)

        return {
            "game_id":          game_id,
            "date":             date_str,
            "matchup":          f"{away_abbr} @ {home_abbr}",
            "season":           season,
            "season_type":      season_type,
            "arena":            arena,
            "attendance":       attendance,
            "home_abbr":        home_abbr,
            "away_abbr":        away_abbr,
            "series_home_wins": series["home_wins"],
            "series_away_wins": series["away_wins"],
            "game_number":      series["game_number"],
            "home_seed":        series["home_seed"],
            "away_seed":        series["away_seed"],
            "teams":            teams_out,
        }
    except Exception as e:
        return {"error": str(e)}


def search_game_boxscore(team1_name, team2_name=None, date=None, season=None,
                         game_number=None, season_type="Regular Season"):
    """
    Find a specific game and return full box score for both teams.
    Searches by team + optional date or game number in a series.
    """
    season = season or CURRENT_SEASON
    team_id = _get_team_id(team1_name) if team1_name else None

    try:
        params = dict(
            season_nullable=season,
            league_id_nullable="00",
            season_type_nullable=season_type,
            timeout=NBA_TIMEOUT,
        )
        if team_id:
            params["team_id_nullable"] = team_id

        df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(**params)
                       .get_data_frames()[0])

        if df is None or df.empty:
            return {"error": "No games found"}

        # Filter by second team if provided
        if team2_name:
            t2_norm = _normalize(team2_name)
            df = df[df["MATCHUP"].apply(
                lambda m: t2_norm in _normalize(str(m))
            )]

        # Filter by date
        if date:
            df = df[df["GAME_DATE"].str.contains(date, na=False)]

        if df.empty:
            return {"error": "No matching game found"}

        # Sort by date desc, take first match (or nth for game_number)
        df = df.sort_values("GAME_DATE", ascending=False)
        if game_number and game_number > 1:
            # For playoff series — game N means the Nth game between these teams
            df = df.head(game_number)
            row = df.iloc[-1]
        else:
            row = df.iloc[0]

        game_id = str(row.get("GAME_ID", ""))
        if not game_id:
            return {"error": "Game ID not found"}

        # Fetch full box score
        bs = _nba_call(lambda: boxscoretraditionalv2.BoxScoreTraditionalV2(
            game_id=game_id, timeout=NBA_TIMEOUT
        ).get_data_frames())

        if bs is None:
            return {"error": "Box score unavailable"}

        players_df = bs[0]
        summary_df = bs[5] if len(bs) > 5 else None

        # Determine home/away from matchup string
        matchup_str = str(row.get("MATCHUP", ""))
        if " vs. " in matchup_str:
            home_abbr = row.get("TEAM_ABBREVIATION", "")
            away_abbr = matchup_str.split("vs.")[-1].strip()
        else:
            away_abbr = row.get("TEAM_ABBREVIATION", "")
            home_abbr = matchup_str.split("@")[-1].strip()

        # Series info for playoffs: count wins each team has in the series
        series_home_wins = series_away_wins = 0
        game_number_in_series = 1
        if season_type == "Playoffs":
            try:
                # Get all games between these two teams this season
                series_df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
                    team_id_nullable=_get_team_id(team1_name),
                    season_nullable=season,
                    season_type_nullable="Playoffs",
                    timeout=NBA_TIMEOUT,
                ).get_data_frames()[0])
                if series_df is not None and not series_df.empty and team2_name:
                    t2_norm = _normalize(team2_name)
                    series_df = series_df[series_df["MATCHUP"].apply(
                        lambda m: t2_norm in _normalize(str(m))
                    )]
                    # Sort chronologically
                    series_df = series_df.sort_values("GAME_DATE", ascending=True)
                    # Find where this game falls
                    game_date_str = str(row.get("GAME_DATE", ""))
                    games_up_to = series_df[series_df["GAME_DATE"] <= game_date_str]
                    game_number_in_series = len(games_up_to)
                    # Wins before this game
                    for _, sg in games_up_to.iterrows():
                        wl      = sg.get("WL", "")
                        t_abbr  = sg.get("TEAM_ABBREVIATION", "")
                        matchup = sg.get("MATCHUP", "")
                        is_home = "vs." in matchup
                        if wl == "W":
                            if is_home:
                                series_home_wins += 1
                            else:
                                series_away_wins += 1
                        elif wl == "L":
                            if is_home:
                                series_away_wins += 1
                            else:
                                series_home_wins += 1
                        break  # Only need per-game from team1's perspective, deduplicate
                    # Simpler: just count W/L from team1's side
                    series_home_wins = 0
                    series_away_wins = 0
                    for _, sg in games_up_to.iterrows():
                        wl     = sg.get("WL", "")
                        is_home_row = "vs." in sg.get("MATCHUP", "")
                        # team1 is away here since we searched with team1
                        if wl == "W":
                            series_away_wins += 1
                        else:
                            series_home_wins += 1
            except Exception:
                pass

        # Build team box scores
        teams_out = {}
        for team_abbr, grp in players_df.groupby("TEAM_ABBREVIATION"):
            grp = grp.sort_values("PTS", ascending=False)
            player_rows = []
            for _, p in grp.iterrows():
                if p.get("MIN") and str(p["MIN"]) not in ("None", "nan", ""):
                    player_rows.append({
                        "name":        p["PLAYER_NAME"],
                        "min":         str(p["MIN"])[:5],
                        "pts":         int(p["PTS"])   if p["PTS"]   == p["PTS"] else 0,
                        "reb":         int(p["REB"])   if p["REB"]   == p["REB"] else 0,
                        "ast":         int(p["AST"])   if p["AST"]   == p["AST"] else 0,
                        "stl":         int(p["STL"])   if p["STL"]   == p["STL"] else 0,
                        "blk":         int(p["BLK"])   if p["BLK"]   == p["BLK"] else 0,
                        "tov":         int(p["TO"])    if "TO" in p.index and p["TO"] == p["TO"] else 0,
                        "fg":          f"{int(p['FGM']) if p['FGM']==p['FGM'] else 0}-{int(p['FGA']) if p['FGA']==p['FGA'] else 0}",
                        "fg3":         f"{int(p['FG3M']) if p['FG3M']==p['FG3M'] else 0}-{int(p['FG3A']) if p['FG3A']==p['FG3A'] else 0}",
                        "ft":          f"{int(p['FTM']) if p['FTM']==p['FTM'] else 0}-{int(p['FTA']) if p['FTA']==p['FTA'] else 0}",
                        "plus_minus":  int(p["PLUS_MINUS"]) if "PLUS_MINUS" in p.index and p["PLUS_MINUS"] == p["PLUS_MINUS"] else 0,
                    })
            teams_out[team_abbr] = {
                "players": player_rows,
                "total_pts": sum(r["pts"] for r in player_rows),
            }

        # Summary info
        arena = ""
        attendance = ""
        if summary_df is not None and not summary_df.empty:
            s = summary_df.iloc[0]
            arena      = str(s.get("ARENA_NAME", ""))
            attendance = str(s.get("ATTENDANCE", ""))

        # Series record if playoffs
        series_record = ""
        if season_type == "Playoffs" and team2_name:
            try:
                t1_abbr = row.get("TEAM_ABBREVIATION","")
                wl      = row.get("WL", "")
                # Count wins in this series from leaguegamefinder results
                series_df = df.copy()
                t1_wins = int((series_df["WL"] == "W").sum())
                t1_loss = int((series_df["WL"] == "L").sum())
                series_record = f"{t1_wins}-{t1_loss}"
            except Exception:
                pass

        return {
            "game_id":             game_id,
            "date":                _parse_nba_date(row.get("GAME_DATE", "")),
            "matchup":             matchup_str,
            "season":              season,
            "season_type":         season_type,
            "arena":               arena,
            "attendance":          attendance,
            "home_abbr":           home_abbr,
            "away_abbr":           away_abbr,
            "series_record":       f"{series_away_wins}-{series_home_wins}",
            "game_number":         game_number_in_series,
            "series_away_wins":    series_away_wins,
            "series_home_wins":    series_home_wins,
            "teams":               teams_out,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Playoff career stats ──────────────────────────────────────────────────────

def get_player_playoff_stats(player_name):
    """
    Career + current season playoff averages from actual game-by-game log.
    Uses leaguegamefinder which is reliable regardless of frame index issues.
    """
    player_id = _get_player_id_all(player_name)
    if not player_id:
        return {"error": f"Player not found: {player_name}"}

    try:
        df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
            player_id_nullable=player_id,
            season_type_nullable="Playoffs",
            timeout=NBA_TIMEOUT,
        ).get_data_frames()[0])

        if df is None or df.empty:
            return {"error": "No playoff data found"}

        def _avgs(games):
            gp = len(games)
            if gp == 0:
                return None
            def avg(col):
                try: return round(float(games[col].mean()), 1) if col in games.columns else None
                except: return None
            def wpct(made, att):
                try:
                    m = float(games[made].sum())
                    a = float(games[att].sum())
                    return round(m/a, 3) if a > 0 else None
                except: return None
            pts = avg("PTS") or 0
            fga = float(games["FGA"].mean()) if "FGA" in games.columns else 0
            fta = float(games["FTA"].mean()) if "FTA" in games.columns else 0
            ts  = round(pts/(2*(fga+0.44*fta))*100, 1) if (fga+fta) > 0 else None
            return {
                "gp": gp, "ppg": avg("PTS"), "reb": avg("REB"),
                "ast": avg("AST"), "stl": avg("STL"), "blk": avg("BLK"),
                "fg_pct": wpct("FGM","FGA"), "three_pct": wpct("FG3M","FG3A"),
                "ft_pct": wpct("FTM","FTA"), "ts_pct": ts,
            }

        # Current season = most recent SEASON_ID
        curr_info = None
        if "SEASON_ID" in df.columns:
            curr_sid  = df["SEASON_ID"].iloc[0]
            curr_df   = df[df["SEASON_ID"] == curr_sid]
            curr      = _avgs(curr_df)
            if curr:
                sid_label = str(curr_sid)[1:] if len(str(curr_sid)) == 5 else str(curr_sid)
                team = curr_df["TEAM_ABBREVIATION"].iloc[0] if "TEAM_ABBREVIATION" in curr_df.columns else ""
                curr_info = {**curr, "season": sid_label, "team": team}

        career = _avgs(df)

        # Best playoff season by PPG
        best_po = None
        if "SEASON_ID" in df.columns:
            best_ppg, best_sid, best_team, best_gp = 0, None, "", 0
            for sid, grp in df.groupby("SEASON_ID"):
                ppg = float(grp["PTS"].mean()) if "PTS" in grp.columns else 0
                if ppg > best_ppg:
                    best_ppg = ppg
                    best_sid = sid
                    best_team = grp["TEAM_ABBREVIATION"].iloc[0] if "TEAM_ABBREVIATION" in grp.columns else ""
                    best_gp   = len(grp)
            if best_sid:
                sid_label = str(best_sid)[1:] if len(str(best_sid)) == 5 else str(best_sid)
                best_po = {"season": sid_label, "team": best_team,
                           "ppg": round(best_ppg, 1), "gp": best_gp}

        if career is None:
            return {"error": "No playoff data found"}

        return {
            "name":           player_name,
            "career_games":   career["gp"],
            "career_ppg":     career["ppg"],
            "career_reb":     career["reb"],
            "career_ast":     career["ast"],
            "career_stl":     career["stl"],
            "career_blk":     career["blk"],
            "career_fg_pct":  career["fg_pct"],
            "career_3_pct":   career["three_pct"],
            "career_ft_pct":  career["ft_pct"],
            "career_ts_pct":  career["ts_pct"],
            "seasons":        df["SEASON_ID"].nunique() if "SEASON_ID" in df.columns else 1,
            "best_season":    best_po,
            "current_season": curr_info,
        }
    except Exception as e:
        return {"error": str(e)}


def get_player_stats_vs_team(player_name, opponent_team):
    """
    Career averages for a player against a specific opponent,
    computed from box score game logs.
    """
    player_id = _get_player_id_all(player_name)
    opp_abbr  = None
    for t in nba_static_teams.get_teams():
        if _normalize(t["full_name"]) == _normalize(opponent_team) or \
           t["abbreviation"].upper() == opponent_team.upper():
            opp_abbr = t["abbreviation"]
            break

    if not player_id:
        return {"error": f"Player not found: {player_name}"}
    if not opp_abbr:
        return {"error": f"Team not found: {opponent_team}"}

    try:
        df = _nba_call(lambda: leaguegamefinder.LeagueGameFinder(
            player_id_nullable=player_id,
            timeout=NBA_TIMEOUT,
        ).get_data_frames()[0])

        if df is None or df.empty:
            return {"error": "No game data found"}

        # Filter to games against the opponent
        opp_df = df[df["MATCHUP"].str.contains(opp_abbr, na=False)]
        if opp_df.empty:
            return {"error": f"No games found vs {opponent_team}"}

        gp  = len(opp_df)
        avg = lambda col: round(float(opp_df[col].mean()), 1) if col in opp_df.columns else None
        pct = lambda col: round(float(opp_df[col].mean()), 3) if col in opp_df.columns else None

        return {
            "player":    player_name,
            "opponent":  opponent_team,
            "gp":        gp,
            "ppg":       avg("PTS"),
            "reb":       avg("REB"),
            "ast":       avg("AST"),
            "stl":       avg("STL"),
            "blk":       avg("BLK"),
            "fg_pct":    pct("FG_PCT"),
            "three_pct": pct("FG3_PCT"),
            "ft_pct":    pct("FT_PCT"),
        }
    except Exception as e:
        return {"error": str(e)}