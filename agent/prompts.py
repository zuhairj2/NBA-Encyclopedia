SYSTEM_PROMPT = """
You are an elite NBA analyst — part data scientist, part former scout, part sharp sports journalist.
You've watched every game, studied every box score, and have strong, well-reasoned opinions backed by data.

CRITICAL: You form your own opinion from the data. You do NOT simply agree with the user's premise.
If someone asks "does X have a solid argument over Y?" — evaluate the actual numbers and give your
honest take, even if it means disagreeing with them. A good analyst pushes back when the data
doesn't support the framing. Do not be a yes-man.

Your analysis style:
- Lead with your own conclusion, not the user's framing
- Give concrete, specific takes — reference actual stats provided
- Use basketball terminology naturally (net rating, paint touches, transition defense, creation rate)
- Be willing to say "actually, the data doesn't support that"
- When asked for predictions or opinions, commit to a position and defend it with data
- Keep responses focused and punchy — 3-5 paragraphs max
- Never just validate whoever the user mentions first

Current season: 2025-26 NBA season.
"""


def build_player_stats_prompt(stats):
    acols  = stats.get("_accolades", {})
    acol_str = ""
    if acols:
        parts = []
        if acols.get("mvps"):        parts.append(f"{acols['mvps']}x MVP")
        if acols.get("rings"):       parts.append(f"{acols['rings']}x Champion")
        if acols.get("all_star"):    parts.append(f"{acols['all_star']}x All-Star")
        if acols.get("all_nba"):     parts.append(f"{acols['all_nba']}x All-NBA")
        if acols.get("scoring"):     parts.append(f"{acols['scoring']}x Scoring Title")
        acol_str = "Career accolades: " + ", ".join(parts) if parts else ""

    return f"""
Analyze {stats['name']}'s 2025-26 season:

Team: {stats['team']} | Games: {stats['gp']}
{acol_str}

Scoring & Creation:
  PPG {stats['ppg']} (League #{stats.get('rank_pts','—')}) | FG% {round(stats['fg_pct']*100,1)}% | TS% {stats.get('ts_pct','—')}%
  3PT% {round(stats['three_pct']*100,1)}% on {stats.get('fg3a_pg','—')} attempts | FT% {round(stats['ft_pct']*100,1)}% | USG% {stats.get('usg_pct','—')}%

All-around:
  REB {stats['reb']} (#{stats.get('rank_reb','—')}) | AST {stats['ast']} (#{stats.get('rank_ast','—')})
  STL {stats['stl']} (#{stats.get('rank_stl','—')}) | BLK {stats['blk']} (#{stats.get('rank_blk','—')})
  TOV {stats.get('tov','—')} | MIN {stats.get('min_pg','—')}

On/Off ratings:
  ORTG {stats.get('ortg','—')} (#{stats.get('rank_ortg','—')}) | DRTG {stats.get('drtg','—')} (#{stats.get('rank_drtg','—')}) | NET {stats.get('net_rtg','—')}

Write a sharp, opinionated breakdown of this player's season. Cover:
1. What these numbers say about his role and impact — is he living up to expectations?
2. The single most impressive AND most concerning stat line
3. How he fits into the MVP/award race or playoff picture based on these numbers
4. One specific thing he needs to improve to elevate his game

Be direct. Use basketball context. Take a position.
"""


def build_team_season_prompt(stats):
    return f"""
Analyze the {stats['team']}'s 2025-26 season:

Record: {stats.get('wins','—')}-{stats.get('losses','—')} | {stats.get('conf','—')} Conference

Offense (Rank #{stats.get('rank_pts','—')} in scoring):
  PPG {stats['ppg']} | FG% {round(stats['fg_pct']*100,1)}% (#{stats.get('rank_fg','—')})
  3PT% {round(stats['three_pct']*100,1)}% (#{stats.get('rank_3fg','—')}) on {stats.get('fg3a_pg','—')} 3PA
  FTA {stats.get('fta_pg','—')} (#{stats.get('rank_fta','—')})

Defense & Pace:
  Opp PPG allowed: context from DRTG | REB {stats['reb']} (#{stats.get('rank_reb','—')})
  STL {stats['stl']} (#{stats.get('rank_stl','—')}) | BLK {stats['blk']} (#{stats.get('rank_blk','—')})

Advanced:
  ORTG {stats.get('ortg','—')} (#{stats.get('rank_ortg','—')}) | DRTG {stats.get('drtg','—')} (#{stats.get('rank_drtg','—')}) | NET RTG {stats.get('net_rtg','—')}

Top performers: {stats.get('best_scorer',{}).get('name','—')} ({stats.get('best_scorer',{}).get('stat_val','—')} PPG), {stats.get('best_rebounder',{}).get('name','—')} ({stats.get('best_rebounder',{}).get('stat_val','—')} RPG)

Give a real analysis of this team — what's working, what's broken, and what their playoff ceiling looks like.
Cover: identity (what kind of team are they?), biggest strength, most glaring weakness, and a realistic playoff projection.
Be specific. Reference the advanced metrics. Take a stance on their ceiling.
"""


def build_trend_prompt(team, games):
    lines = []
    for g in games:
        lines.append(
            f"  {g['result']} | {g['date']} vs {g.get('matchup','?')} | "
            f"{g['pts']} pts | FG {g['fg_pct']}% | 3PT {g['three_pct']}% | "
            f"REB {g['reb']} | AST {g['ast']} | TOV {g['tov']}"
        )
    game_log = "\n".join(lines)

    wins  = sum(1 for g in games if g['result'] == 'W')
    losses= len(games) - wins

    return f"""
Analyze the {team}'s recent form ({wins}-{losses} in last {len(games)} games):

Game log (newest first):
{game_log}

Dig into what's really going on with this team right now:
1. Is their record indicative of how they're actually playing, or are results masking bigger issues?
2. Shooting efficiency trend — are they running hot/cold, or is this sustainable?
3. The one stat pattern that tells you the most about where this team is headed
4. Specific prediction: do they make a run or fall off from here?

Be an analyst, not a box score reader. Find the story in the data.
"""


def build_player_comparison_prompt(stats):
    p1, p2 = stats["player1"], stats["player2"]

    def pct(v):
        try: return f"{round(float(v)*100,1)}%"
        except: return str(v)

    return f"""
Compare {p1['name']} vs {p2['name']} this season:

                    {p1['name']:<22} {p2['name']}
PPG                 {str(p1['ppg']):<22} {p2['ppg']}
REB                 {str(p1['reb']):<22} {p2['reb']}
AST                 {str(p1['ast']):<22} {p2['ast']}
STL                 {str(p1['stl']):<22} {p2['stl']}
BLK                 {str(p1['blk']):<22} {p2['blk']}
FG%                 {pct(p1['fg_pct']):<22} {pct(p2['fg_pct'])}
3PT%                {pct(p1['three_pct']):<22} {pct(p2['three_pct'])}
TOV                 {str(p1['tov']):<22} {p2['tov']}

Give a real take on this matchup:
1. Who is the better player RIGHT NOW this season — and why?
2. Where does each guy have a clear edge?
3. Who has the higher ceiling for the rest of this season?
4. If these players met in the playoffs, who would you want on your team?

Commit to a winner. Use the data to back it up.
"""


def build_team_comparison_prompt(stats):
    t1, t2 = stats["team1"], stats["team2"]

    return f"""
Compare the {t1['name']} vs {t2['name']}:

                    {t1['name']:<28} {t2['name']}
Record              {str(t1.get('wins','—'))+'-'+str(t1.get('losses','—')):<28} {t2.get('wins','—')}-{t2.get('losses','—')}
PPG                 {str(t1['ppg']):<28} {t2['ppg']}
FG%                 {str(round(t1['fg_pct']*100,1))+'%':<28} {round(t2['fg_pct']*100,1)}%
3PT%                {str(round(t1['three_pct']*100,1))+'%':<28} {round(t2['three_pct']*100,1)}%
REB                 {str(t1['reb']):<28} {t2['reb']}
AST                 {str(t1['ast']):<28} {t2['ast']}
NET RTG             {str(t1.get('net_rtg','—')):<28} {t2.get('net_rtg','—')}
ORTG                {str(t1.get('ortg','—')):<28} {t2.get('ortg','—')}
DRTG                {str(t1.get('drtg','—')):<28} {t2.get('drtg','—')}

Analyze this matchup:
1. Which team is genuinely better and why — don't just go by record
2. The statistical category that would decide a playoff series between them
3. Each team's biggest vulnerability the other could exploit
4. Predict the outcome if these teams met in the playoffs — series length, key factor

Be opinionated. Analysts make calls.
"""


def build_league_leaders_prompt(leaders, stat_label):
    rows = "\n".join([
        f"  {i+1}. {p['PLAYER_NAME']} ({p['TEAM_ABBREVIATION']}): "
        f"{p['PTS']} PPG | {p['AST']} APG | {p['REB']} RPG | "
        f"{p['STL']} SPG | {p['BLK']} BPG"
        for i, p in enumerate(leaders)
    ])

    return f"""
2025-26 NBA leaders — {stat_label}:

{rows}

Give a rich breakdown of this leaderboard:
1. Who's the standout and what makes their numbers special in context?
2. Who's the most surprising name on this list — why are they here?
3. Who's underrated or flying under the radar?
4. Any MVP implications from this list?

Go beyond just restating numbers. Be an analyst.
"""


def build_opinion_prompt(user_question, context_data=None):
    context = f"\nCurrent verified stats and standings:\n{context_data}\n" if context_data else ""

    return f"""
The user asked: "{user_question}"
{context}
RULES you must follow:
1. Only discuss players/teams explicitly named by the user or listed in the stats above.
   Do NOT introduce any other player not mentioned. If the user asks about Wemby, Jokic, and SGA,
   your answer must be about those three only — not Luka, LeBron, or anyone else.
2. Form your own conclusion from the actual stats above. Do NOT simply agree with the user's premise.
   If the data contradicts their framing, say so directly.
3. Lead with your honest assessment based on numbers, not the user's framing.

Structure:
1. Your verdict based on the data (be direct — who/what wins and why)
2. The 2-3 strongest stats supporting your conclusion
3. Address the user's specific framing — do you agree or disagree?
4. One bold, specific prediction

Commit to a position. Restrict your analysis to the players/teams the user named.
"""


def build_game_prompt(stats):
    """Legacy single-game analysis prompt."""
    players = "\n".join([
        f"  {p['name']}: {p['points']} pts | {p['assists']} ast | {p['rebounds']} reb | "
        f"FG% {p['fg_pct']} | 3PT% {p['three_pct']}"
        for p in stats.get("players", [])
    ])

    return f"""
Game result — {stats['team']}:
  Result: {stats['result']} | Score: {stats['points']} pts
  FG% {stats['fg_pct']} | 3PT% {stats['three_pct']} | TOV {stats['turnovers']} | REB {stats['rebounds']}

Key players:
{players}

What was the decisive factor in this game? Who stood out, who let the team down,
and what does this result say about where this team is heading? Be specific and direct.
"""


def build_season_prompt(stats):
    """Legacy season prompt."""
    return build_team_season_prompt(stats)


def build_comparison_prompt(stats):
    """Legacy team comparison prompt."""
    return build_team_comparison_prompt(stats)


def build_series_prompt(stats):
    return build_team_comparison_prompt(stats)