import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Web search ────────────────────────────────────────────────────────────────
_tavily_client = None

def _get_tavily():
    global _tavily_client
    if _tavily_client is None:
        try:
            from tavily import TavilyClient
            key = os.getenv("TAVILY_API_KEY", "")
            if key:
                _tavily_client = TavilyClient(api_key=key)
        except ImportError:
            pass
    return _tavily_client


def _web_search(query, max_results=4):
    """
    Search the web. Returns (context_str, sources_list).
    sources_list = [{"title": ..., "url": ..., "domain": ...}, ...]
    """
    tavily = _get_tavily()
    if not tavily:
        return "", []
    try:
        results = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
        )
        parts   = []
        sources = []

        if results.get("answer"):
            parts.append(f"Summary: {results['answer']}")

        for i, r in enumerate(results.get("results", []), 1):
            title   = r.get("title", "")
            content = r.get("content", "")[:400]
            url     = r.get("url", "")
            domain  = url.split("/")[2].replace("www.", "") if url else ""
            if content:
                parts.append(f"[{i}] {title}: {content}")
                sources.append({"title": title, "url": url, "domain": domain})

        return "\n\n".join(parts), sources
    except Exception:
        return "", []

from agent.tools import (
    get_last_game_with_players,
    get_team_season_stats,
    get_last_n_games,
    compare_teams,
    compare_players,
    get_top_league_leaders,
    get_player_season_stats,
    get_team_full_stats,
    get_team_game_log,
    get_full_standings,
)

from agent.prompts import (
    SYSTEM_PROMPT,
    build_game_prompt,
    build_season_prompt,
    build_trend_prompt,
    build_comparison_prompt,
    build_series_prompt,
    build_player_comparison_prompt,
    build_league_leaders_prompt,
    build_player_stats_prompt,
    build_team_season_prompt,
    build_team_comparison_prompt,
    build_opinion_prompt,
)

from utils.parser import (
    extract_team,
    extract_teams,
    extract_players,
    extract_stat_category,
    is_league_wide_query,
    extract_single_player,
    NICKNAMES,
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


OPINION_KEYWORDS = [
    "who do you think", "who wins", "predict", "prediction", "your opinion",
    "who will win", "mvp race", "finals prediction", "playoff prediction",
    "best player", "goat", "greatest", "who is better", "who would win",
    "draft lottery", "who should", "do you think", "what do you think",
    "your take", "your pick", "make a case", "argue", "convince me",
    "realistically", "honestly", "favorite to", "odds", "chances",
    "going to win", "dark horse", "sleeper", "overrated", "underrated",
]

TREND_KEYWORDS = [
    "last", "recent", "lately", "form", "streak", "hot", "cold",
    "trending", "games", "game log", "past few",
]

SERIES_KEYWORDS = [
    "series", "playoffs", "matchup", "first round", "second round",
    "finals", "championship", "would win", "head to head", "7 games",
]

# Queries where web search adds most value
NEWS_KEYWORDS = [
    "news", "trade", "injured", "injury", "out", "return", "latest",
    "update", "report", "rumor", "rumour", "sign", "signed", "contract",
    "waived", "suspend", "suspended", "fired", "hired", "draft pick",
    "transaction", "wire", "buyout", "extension", "max contract",
    "starting", "lineup", "rotation", "minutes", "coaching",
    "what happened", "did", "when did", "how did", "why did",
]


def _call_llm(prompt, temperature=0.7, max_tokens=1024):
    """Call the Groq LLM with the given prompt."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Analysis unavailable: {e}"


def _get_standings_context():
    """Build a brief standings summary for opinion prompts."""
    try:
        rows = get_full_standings()
        east = sorted([r for r in rows if r["conf"] == "East"],
                      key=lambda r: r.get("conf_rank", 99))[:5]
        west = sorted([r for r in rows if r["conf"] == "West"],
                      key=lambda r: r.get("conf_rank", 99))[:5]

        east_str = " | ".join(f"{r['name']} ({r['w']}-{r['l']})" for r in east)
        west_str = " | ".join(f"{r['name']} ({r['w']}-{r['l']})" for r in west)
        return f"East top 5: {east_str}\nWest top 5: {west_str}"
    except Exception:
        return ""


def _get_scoring_leaders_context():
    """Top 5 scorers for opinion context."""
    try:
        leaders = get_top_league_leaders(stat="PTS", n=5)
        return "Scoring leaders: " + " | ".join(
            f"{p['PLAYER_NAME']} {p['PTS']} PPG" for p in leaders
        )
    except Exception:
        return ""


def run_agent(user_input):
    """
    Returns (analysis_text, sources_list).
    sources_list = [{"title": ..., "url": ..., "domain": ...}, ...]
    """
    lower = user_input.lower()
    all_sources = []

    # ── 0. News / injury / transaction queries → web first ────────────────────
    if any(kw in lower for kw in NEWS_KEYWORDS):
        query = f"NBA 2025-26 {user_input}"
        web, sources = _web_search(query, max_results=5)
        all_sources.extend(sources)

        stat_context = ""
        player = extract_single_player(user_input)
        if player:
            try:
                ps = get_player_season_stats(player)
                if "error" not in ps:
                    stat_context = (
                        f"\n{ps['name']} current stats: {ps['ppg']} PPG | "
                        f"{ps['reb']} REB | {ps['ast']} AST | "
                        f"TS% {ps.get('ts_pct','—')}%"
                    )
            except Exception:
                pass

        prompt = f"""
The user asked: "{user_input}"

Latest web results (2025-26 NBA season):
{web if web else "No web results available."}
{stat_context}

Answer the question using the web results above as your primary source.
Be specific, cite what you found, and add brief analytical context where relevant.
If the web results don't directly answer the question, say so and use your knowledge.
Keep it concise and factual — 2-4 paragraphs max.
"""
        return _call_llm(prompt, temperature=0.5, max_tokens=900), all_sources

    # ── 1. Opinion / prediction queries ───────────────────────────────────────
    if any(kw in lower for kw in OPINION_KEYWORDS):
        context_parts = []
        context_parts.append(_get_standings_context())

        all_mentioned_players = []
        for word in lower.split():
            if word in NICKNAMES:
                resolved = NICKNAMES[word]
                if resolved not in all_mentioned_players:
                    all_mentioned_players.append(resolved)
        for alias, full in NICKNAMES.items():
            if " " in alias and alias in lower and full not in all_mentioned_players:
                all_mentioned_players.append(full)
        standard = extract_single_player(user_input)
        if standard and standard not in all_mentioned_players:
            all_mentioned_players.append(standard)
        try:
            multi = extract_players(user_input)
            for p in multi:
                if p not in all_mentioned_players:
                    all_mentioned_players.append(p)
        except Exception:
            pass

        if not all_mentioned_players:
            context_parts.append(_get_scoring_leaders_context())

        player_stat_lines = []
        for player in all_mentioned_players[:5]:
            try:
                pstats = get_player_season_stats(player)
                if "error" not in pstats:
                    player_stat_lines.append(
                        f"{pstats['name']} ({pstats['team']}): "
                        f"{pstats['ppg']} PPG (#{pstats.get('rank_pts','—')}) | "
                        f"{pstats['reb']} REB | {pstats['ast']} AST | "
                        f"{pstats['stl']} STL | {pstats['blk']} BLK | "
                        f"FG% {round(pstats['fg_pct']*100,1)}% | "
                        f"3PT% {round(pstats['three_pct']*100,1)}% | "
                        f"TS% {pstats.get('ts_pct','—')}% | "
                        f"USG% {pstats.get('usg_pct','—')}% | "
                        f"ORTG {pstats.get('ortg','—')} | DRTG {pstats.get('drtg','—')} | "
                        f"NET RTG {pstats.get('net_rtg','—')}"
                    )
            except Exception:
                pass

        if player_stat_lines:
            context_parts.append(
                "ACTUAL 2025-26 STATS — analyze ONLY these players, do not introduce others:\n"
                + "\n".join(player_stat_lines)
            )

        teams = extract_teams(user_input)
        for team_name in teams[:2]:
            try:
                tstats = get_team_full_stats(team_name)
                if "error" not in tstats:
                    context_parts.append(
                        f"{team_name}: {tstats.get('wins','—')}-{tstats.get('losses','—')} | "
                        f"PPG {tstats.get('ppg','—')} | NET RTG {tstats.get('net_rtg','—')} | "
                        f"ORTG {tstats.get('ortg','—')} | DRTG {tstats.get('drtg','—')}"
                    )
            except Exception:
                pass

        context = "\n".join(p for p in context_parts if p)

        web_results, sources = _web_search(f"NBA 2025-26 {user_input}", max_results=3)
        all_sources.extend(sources)
        if web_results:
            context += f"\n\nCurrent web context:\n{web_results}"

        prompt = build_opinion_prompt(user_input, context)
        return _call_llm(prompt, temperature=0.72, max_tokens=1200), all_sources

    # ── 2. League-wide leaders ────────────────────────────────────────────────
    if is_league_wide_query(user_input):
        stat = extract_stat_category(user_input)
        leaders = get_top_league_leaders(stat=stat, n=10)
        if isinstance(leaders, dict) and "error" in leaders:
            return f"Could not fetch league leaders: {leaders['error']}", []
        stat_labels = {
            "PTS": "Points Per Game", "AST": "Assists Per Game",
            "REB": "Rebounds Per Game", "STL": "Steals Per Game",
            "BLK": "Blocks Per Game",  "FG_PCT": "Field Goal %",
            "FG3_PCT": "3-Point %",
        }
        prompt = build_league_leaders_prompt(leaders, stat_labels.get(stat, stat))
        return _call_llm(prompt, temperature=0.7, max_tokens=900), []

    # ── 3. Player comparison ──────────────────────────────────────────────────
    if ("vs" in lower or "compare" in lower) and not extract_teams(user_input):
        players = extract_players(user_input)
        if len(players) >= 2:
            stats = compare_players(players[0], players[1])
            if "error" not in stats:
                prompt = build_player_comparison_prompt(stats)
                return _call_llm(prompt, temperature=0.75, max_tokens=1000), []

    # ── 4. Team vs team (series / matchup) ───────────────────────────────────
    teams = extract_teams(user_input)
    if len(teams) >= 2:
        if any(kw in lower for kw in SERIES_KEYWORDS):
            stats = compare_teams(teams[0], teams[1])
            if "error" not in stats:
                prompt = build_series_prompt(stats)
                return _call_llm(prompt, temperature=0.75, max_tokens=1000), []
        else:
            stats = compare_teams(teams[0], teams[1])
            if "error" not in stats:
                prompt = build_team_comparison_prompt(stats)
                return _call_llm(prompt, temperature=0.7, max_tokens=1000), []

    # ── 5. Single player stats ────────────────────────────────────────────────
    player = extract_single_player(user_input)
    if player:
        stats = get_player_season_stats(player)
        if "error" not in stats:
            prompt = build_player_stats_prompt(stats)
            return _call_llm(prompt, temperature=0.7, max_tokens=900), []

    # ── 6. Team game log / trend ──────────────────────────────────────────────
    if teams and any(kw in lower for kw in TREND_KEYWORDS):
        team = teams[0]
        n = 5
        for word in lower.split():
            if word.isdigit():
                n = min(int(word), 10)
                break
        log = get_team_game_log(team, n)
        if isinstance(log, list) and log:
            prompt = build_trend_prompt(team, log)
            return _call_llm(prompt, temperature=0.7, max_tokens=900), []

    # ── 7. Single team season stats ───────────────────────────────────────────
    if teams:
        team = teams[0]
        stats = get_team_full_stats(team)
        if "error" not in stats:
            prompt = build_team_season_prompt(stats)
            return _call_llm(prompt, temperature=0.7, max_tokens=900), []

    # ── 8. Generic fallback ───────────────────────────────────────────────────
    web_ctx, sources = _web_search(f"NBA 2025 {user_input}", max_results=3)
    all_sources.extend(sources)
    context = _get_standings_context() + "\n" + _get_scoring_leaders_context()
    if web_ctx:
        context += f"\n\nWeb search results:\n{web_ctx}"
    prompt = build_opinion_prompt(user_input, context)
    return _call_llm(prompt, temperature=0.8, max_tokens=1000), all_sources