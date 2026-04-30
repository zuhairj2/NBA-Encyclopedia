import re
import unicodedata
from typing import Optional, List

# ---------------------------------------------------------------------------
# Team extraction
# ---------------------------------------------------------------------------

TEAM_MAP = {
    "lakers":        "Los Angeles Lakers",
    "warriors":      "Golden State Warriors",
    "celtics":       "Boston Celtics",
    "bucks":         "Milwaukee Bucks",
    "nets":          "Brooklyn Nets",
    "suns":          "Phoenix Suns",
    "heat":          "Miami Heat",
    "knicks":        "New York Knicks",
    "clippers":      "LA Clippers",
    "mavericks":     "Dallas Mavericks",
    "mavs":          "Dallas Mavericks",
    "bulls":         "Chicago Bulls",
    "raptors":       "Toronto Raptors",
    "76ers":         "Philadelphia 76ers",
    "sixers":        "Philadelphia 76ers",
    "jazz":          "Utah Jazz",
    "nuggets":       "Denver Nuggets",
    "grizzlies":     "Memphis Grizzlies",
    "pelicans":      "New Orleans Pelicans",
    "hawks":         "Atlanta Hawks",
    "pacers":        "Indiana Pacers",
    "magic":         "Orlando Magic",
    "wizards":       "Washington Wizards",
    "hornets":       "Charlotte Hornets",
    "timberwolves":  "Minnesota Timberwolves",
    "wolves":        "Minnesota Timberwolves",
    "pistons":       "Detroit Pistons",
    "blazers":       "Portland Trail Blazers",
    "trail blazers": "Portland Trail Blazers",
    "kings":         "Sacramento Kings",
    "thunder":       "Oklahoma City Thunder",
    "spurs":         "San Antonio Spurs",
    "cavaliers":     "Cleveland Cavaliers",
    "cavs":          "Cleveland Cavaliers",
    "rockets":       "Houston Rockets",
}


def extract_teams(user_input):
    user_input_lower = user_input.lower()
    found = []
    for key, value in TEAM_MAP.items():
        # Use word boundaries to prevent "nets" matching inside "hornets" etc.
        if re.search(r'\b' + re.escape(key) + r'\b', user_input_lower) and value not in found:
            found.append(value)
    return found


def extract_team(user_input):
    teams = extract_teams(user_input)
    return teams[0] if teams else "Los Angeles Lakers"


# ---------------------------------------------------------------------------
# Player extraction
# ---------------------------------------------------------------------------

# Lookup dicts populated lazily from nba_api static data (no network call)
_PLAYER_LOWER: dict = {}  # normalized full name -> canonical
_PLAYER_LAST:  dict = {}  # normalized last name -> canonical

# Nickname -> canonical full name (as the NBA API stores it)
NICKNAMES = {
    # Guards
    "ant":           "Anthony Edwards",
    "ant man":       "Anthony Edwards",
    "ant-man":       "Anthony Edwards",
    "edwards":       "Anthony Edwards",
    "steph":         "Stephen Curry",
    "chef curry":    "Stephen Curry",
    "curry":         "Stephen Curry",
    "splash brother":"Stephen Curry",
    "spida":         "Donovan Mitchell",
    "mitchell":      "Donovan Mitchell",
    "donovan":       "Donovan Mitchell",
    "bron":          "LeBron James",
    "lebron":        "LeBron James",
    "king james":    "LeBron James",
    "kyrie":         "Kyrie Irving",
    "uncle drew":    "Kyrie Irving",
    "dame":          "Damian Lillard",
    "dame time":     "Damian Lillard",
    "cp3":           "Chris Paul",
    "the point god": "Chris Paul",
    "harden":        "James Harden",
    "the beard":     "James Harden",
    "russ":          "Russell Westbrook",
    "trae":          "Trae Young",
    "ice trae":      "Trae Young",
    "ja":            "Ja Morant",
    "sga":           "Shai Gilgeous-Alexander",
    "shai":          "Shai Gilgeous-Alexander",
    "fox":           "De'Aaron Fox",
    "hali":          "Tyrese Haliburton",
    "tyrese":        "Tyrese Haliburton",
    "maxey":         "Tyrese Maxey",
    "brunson":       "Jalen Brunson",
    "jalen":         "Jalen Brunson",
    "klay":          "Klay Thompson",
    "dlo":           "D'Angelo Russell",
    # Forwards / Bigs
    "giannis":       "Giannis Antetokounmpo",
    "greek freak":   "Giannis Antetokounmpo",
    "the greek freak":"Giannis Antetokounmpo",
    "luka":          "Luka Doncic",
    "luka magic":    "Luka Doncic",
    "joker":         "Nikola Jokic",
    "the joker":     "Nikola Jokic",
    "jokic":         "Nikola Jokic",
    "embiid":        "Joel Embiid",
    "jojo":          "Joel Embiid",
    "the process":   "Joel Embiid",
    "tatum":         "Jayson Tatum",
    "jt":            "Jayson Tatum",
    "jayson":        "Jayson Tatum",
    "jaylen":        "Jaylen Brown",
    "jb":            "Jaylen Brown",
    "kawhi":         "Kawhi Leonard",
    "the klaw":      "Kawhi Leonard",
    "klaw":          "Kawhi Leonard",
    "kd":            "Kevin Durant",
    "durant":        "Kevin Durant",
    "slim reaper":   "Kevin Durant",
    "ad":            "Anthony Davis",
    "the brow":      "Anthony Davis",
    "zion":          "Zion Williamson",
    "bam":           "Bam Adebayo",
    "kat":           "Karl-Anthony Towns",
    "towns":         "Karl-Anthony Towns",
    "pg":            "Paul George",
    "pg13":          "Paul George",
    "book":          "Devin Booker",
    "booker":        "Devin Booker",
    "devin":         "Devin Booker",
    "wemby":         "Victor Wembanyama",
    "chet":          "Chet Holmgren",
    "paolo":         "Paolo Banchero",
    "franz":         "Franz Wagner",
    "jjj":           "Jaren Jackson Jr",
    "jaren":         "Jaren Jackson Jr",
    "draymond":      "Draymond Green",
    "jimmy":         "Jimmy Butler",
    "jimmy buckets": "Jimmy Butler",
    "herro":         "Tyler Herro",
    "gobert":        "Rudy Gobert",
    "stifle tower":  "Rudy Gobert",
    "mobley":        "Evan Mobley",
    "scottie":       "Scottie Barnes",
    "mikal":         "Mikal Bridges",
    "bridges":       "Mikal Bridges",
    "jamal":         "Jamal Murray",
    "murray":        "Jamal Murray",
    "garland":       "Darius Garland",
    "darius":        "Darius Garland",
    "randle":        "Julius Randle",
    "wembanyama":    "Victor Wembanyama",

    # ── Legends / Retired ──────────────────────────────────────────────────
    # Michael Jordan
    "mj":               "Michael Jordan",
    "air jordan":       "Michael Jordan",
    "jordan":           "Michael Jordan",
    "michael":          "Michael Jordan",

    # Kobe Bryant
    "kobe":             "Kobe Bryant",
    "black mamba":      "Kobe Bryant",
    "mamba":            "Kobe Bryant",
    "kb24":             "Kobe Bryant",
    "kb8":              "Kobe Bryant",

    # Shaquille O'Neal
    "shaq":             "Shaquille O'Neal",
    "shaquille":        "Shaquille O'Neal",
    "diesel":           "Shaquille O'Neal",
    "big diesel":       "Shaquille O'Neal",
    "the big aristotle":"Shaquille O'Neal",

    # Kareem Abdul-Jabbar
    "kareem":           "Kareem Abdul-Jabbar",
    "kaj":              "Kareem Abdul-Jabbar",
    "cap":              "Kareem Abdul-Jabbar",
    "the cap":          "Kareem Abdul-Jabbar",
    "lew alcindor":     "Kareem Abdul-Jabbar",

    # Magic Johnson
    "magic":            "Magic Johnson",
    "magic johnson":    "Magic Johnson",
    "earvin":           "Magic Johnson",

    # Larry Bird
    "bird":             "Larry Bird",
    "larry bird":       "Larry Bird",
    "larry legend":     "Larry Bird",

    # LeBron James (also in active but add aliases)
    "king":             "LeBron James",
    "chosen one":       "LeBron James",
    "LBJ":               "LeBron James",

    # Tim Duncan
    "timmy":            "Tim Duncan",
    "td":               "Tim Duncan",
    "duncan":           "Tim Duncan",
    "the big fundamental": "Tim Duncan",
    "tim":              "Tim Duncan",

    # Dirk Nowitzki
    "dirk":             "Dirk Nowitzki",
    "nowitzki":         "Dirk Nowitzki",
    "the german wunderkind": "Dirk Nowitzki",

    # Hakeem Olajuwon
    "hakeem":           "Hakeem Olajuwon",
    "olajuwon":         "Hakeem Olajuwon",
    "the dream":        "Hakeem Olajuwon",
    "akeem":            "Hakeem Olajuwon",

    # Charles Barkley
    "barkley":          "Charles Barkley",
    "chuck":            "Charles Barkley",
    "sir charles":      "Charles Barkley",
    "round mound of rebound": "Charles Barkley",

    # Allen Iverson
    "ai":               "Allen Iverson",
    "iverson":          "Allen Iverson",
    "the answer":       "Allen Iverson",
    "a.i.":             "Allen Iverson",
    "AI":               "Allen Iverson",

    # Kevin Garnett
    "kg":               "Kevin Garnett",
    "garnett":          "Kevin Garnett",
    "the big ticket":   "Kevin Garnett",

    # Dwyane Wade
    "wade":             "Dwyane Wade",
    "flash":            "Dwyane Wade",
    "d-wade":           "Dwyane Wade",
    "dwade":            "Dwyane Wade",

    # Steve Nash
    "nash":             "Steve Nash",

    # Ray Allen
    "ray allen":        "Ray Allen",
    "jesus shuttlesworth": "Ray Allen",

    # Scottie Pippen
    "pippen":           "Scottie Pippen",
    "pip":              "Scottie Pippen",

    # Wilt Chamberlain
    "wilt":             "Wilt Chamberlain",
    "chamberlain":      "Wilt Chamberlain",
    "wilt the stilt":   "Wilt Chamberlain",
    "the big dipper":   "Wilt Chamberlain",

    # Bill Russell
    "russell":          "Bill Russell",
    "bill russell":     "Bill Russell",

    # Oscar Robertson
    "oscar":            "Oscar Robertson",
    "the big o":        "Oscar Robertson",

    # Jerry West
    "jerry west":       "Jerry West",
    "the logo":         "Jerry West",
    "zeke from cabin creek": "Jerry West",

    # Patrick Ewing
    "ewing":            "Patrick Ewing",

    # Karl Malone
    "malone":           "Karl Malone",
    "the mailman":      "Karl Malone",

    # John Stockton
    "stockton":         "John Stockton",

    # Dominique Wilkins
    "dominique":        "Dominique Wilkins",
    "nique":            "Dominique Wilkins",
    "the human highlight film": "Dominique Wilkins",

    # David Robinson
    "the admiral":      "David Robinson",
    "robinson":         "David Robinson",

    # Isiah Thomas
    "isiah":            "Isiah Thomas",
    "zeke":             "Isiah Thomas",

    # Tracy McGrady
    "tmac":             "Tracy McGrady",
    "t-mac":            "Tracy McGrady",

    # Vince Carter
    "vince":            "Vince Carter",
    "half man half amazing": "Vince Carter",
    "vc":               "Vince Carter",
    "vinsanity":        "Vince Carter",

    # Reggie Miller
    "reggie":           "Reggie Miller",
    "miller":           "Reggie Miller",

    # Gary Payton
    "gary payton":      "Gary Payton",
    "the glove":        "Gary Payton",
    "gp":               "Gary Payton",

    # Pau Gasol
    "pau":              "Pau Gasol",

    # Tony Parker
    "tp":               "Tony Parker",
    "tony":             "Tony Parker",

    # Manu Ginobili
    "manu":             "Manu Ginobili",
    "ginobili":         "Manu Ginobili",

    # Paul Pierce
    "the truth":        "Paul Pierce",
    "pierce":           "Paul Pierce",

    # Clyde Drexler
    "clyde":            "Clyde Drexler",
    "clyde the glide":  "Clyde Drexler",
    "drexler":          "Clyde Drexler",

    # Dennis Rodman
    "rodman":           "Dennis Rodman",
    "the worm":         "Dennis Rodman",

    # James Worthy
    "worthy":           "James Worthy",
    "big game james":   "James Worthy",
}


def _normalize(text: str) -> str:
    """Strip accents: 'Doncic' matches 'Dončić', 'Jokic' matches 'Jokić'."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()


def _resolve_nickname(text: str) -> Optional[str]:
    """Return canonical name if text is a known nickname, else None."""
    return NICKNAMES.get(_normalize(text).strip())


def _load_player_index():
    """Build lookup dicts from nba_api static JSON + 2025-26 rookie supplement."""
    if _PLAYER_LOWER:
        return
    from nba_api.stats.static import players as nba_players
    from agent.tools import ROOKIES_2025_26

    all_players = [p["full_name"] for p in nba_players.get_active_players()]

    # Merge rookies not already present
    existing_norm = {_normalize(n) for n in all_players}
    for name, _ in ROOKIES_2025_26:
        if _normalize(name) not in existing_norm:
            all_players.append(name)

    for full in all_players:
        lower     = _normalize(full)
        _PLAYER_LOWER[lower] = full
        last_norm = _normalize(full.split()[-1])
        if last_norm not in _PLAYER_LAST:
            _PLAYER_LAST[last_norm] = full


def _match_player(token: str) -> Optional[str]:
    """Resolve a token to a canonical player name."""
    _load_player_index()

    # 1. Nickname dict first
    nick = _resolve_nickname(token)
    if nick:
        return nick

    t = _normalize(token.strip())

    # 2. Exact full-name match
    if t in _PLAYER_LOWER:
        return _PLAYER_LOWER[t]

    # 3. Last-name match
    if t in _PLAYER_LAST:
        return _PLAYER_LAST[t]

    # 4. Substring match with word boundaries
    for lower_name, canonical in _PLAYER_LOWER.items():
        if re.search(r'\b' + re.escape(t) + r'\b', lower_name):
            return canonical

    return None


def extract_players(user_input: str) -> List[str]:
    """Extract up to 2 player names from a query."""
    # Check nicknames for multi-word phrases before splitting
    norm_input = _normalize(user_input)
    for nick, canonical in NICKNAMES.items():
        if len(nick.split()) > 1 and nick in norm_input:
            norm_input = norm_input.replace(nick, "")

    segments = re.split(r'\bvs\.?\b|\bversus\b|\band\b|,|&', user_input, flags=re.IGNORECASE)

    matched = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        result = _match_player(seg)
        if result and result not in matched:
            matched.append(result)
            continue

        words = seg.split()
        found_in_seg = False

        for i in range(len(words) - 1):
            phrase = words[i] + " " + words[i + 1]
            result = _match_player(phrase)
            if result and result not in matched:
                matched.append(result)
                found_in_seg = True
                break

        if not found_in_seg:
            for word in words:
                result = _match_player(word)
                if result and result not in matched:
                    matched.append(result)
                    break

    # Fallback: consecutive capitalized words
    if len(matched) < 2:
        words = user_input.split()
        for i in range(len(words) - 1):
            if words[i][0].isupper() and words[i + 1][0].isupper():
                candidate = words[i] + " " + words[i + 1]
                if candidate not in matched:
                    matched.append(candidate)
            if len(matched) >= 2:
                break

    return matched[:2]


# ---------------------------------------------------------------------------
# Query intent helpers
# ---------------------------------------------------------------------------

STAT_KEYWORDS = {
    "PTS":    ["points", "scoring", "ppg", "scorer"],
    "AST":    ["assists", "playmaking", "apg", "passer"],
    "REB":    ["rebounds", "rebounding", "rpg", "boards"],
    "STL":    ["steals", "steal", "spg"],
    "BLK":    ["blocks", "block", "bpg", "shot blocker"],
    "FG_PCT": ["field goal", "fg%", "shooting percentage"],
    "FG3_PCT":["three point", "3pt", "3-point", "threes", "3pt%"],
}


def extract_stat_category(user_input: str) -> str:
    lower = user_input.lower()
    for stat, keywords in STAT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return stat
    return "PTS"


def is_league_wide_query(user_input: str) -> bool:
    triggers = ["league", "best in the", "top players", "leaders",
                "who leads", "who is the best"]
    lower = user_input.lower()
    return any(t in lower for t in triggers)


_PLAYER_QUERY_TRIGGERS = [
    "how many", "how much", "average", "averages", "averaging",
    "rank", "ranked", "stats", "statistics", "ppg", "apg", "rpg",
    "points per game", "season", "this year", "where does", "how is",
    "what did", "how did", "what are", "tell me about",
]


def extract_single_player(user_input: str) -> Optional[str]:
    """
    Return a canonical player name if the query is about one specific player.
    Checks nicknames first, then the full player index.
    """
    _load_player_index()
    lower     = _normalize(user_input)
    raw_lower = user_input.lower()

    # Skip comparisons
    if "vs" in raw_lower or ("compare" in raw_lower and "and" in raw_lower):
        return None

    # Must look like a player stat question
    if not any(t in lower for t in _PLAYER_QUERY_TRIGGERS):
        return None

    # 1. Check multi-word nicknames first (e.g. "greek freak", "ant man")
    for nick in sorted(NICKNAMES, key=len, reverse=True):
        if len(nick.split()) > 1 and _normalize(nick) in lower:
            return NICKNAMES[nick]

    # 2. Check single-word nicknames with word boundaries
    for nick, canonical in NICKNAMES.items():
        if len(nick.split()) == 1:
            if re.search(r'\b' + re.escape(_normalize(nick)) + r'\b', lower):
                return canonical

    # 3. Full player name match
    for full, canonical in _PLAYER_LOWER.items():
        if re.search(r'\b' + re.escape(full) + r'\b', lower):
            return canonical

    # 4. Last name match (word boundary, min 4 chars to avoid false matches)
    for last, canonical in _PLAYER_LAST.items():
        if len(last) >= 4 and re.search(r'\b' + re.escape(last) + r'\b', lower):
            return canonical

    return None