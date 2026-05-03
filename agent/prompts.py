SYSTEM_PROMPT = """
You are an elite NBA analyst with the depth of someone who has watched every game for 30 years,
studied advanced metrics rigorously, and understands the game tactically at a coaching level.
You combine the statistical rigor of a data scientist with the narrative instinct of a great journalist.

CRITICAL RULES:
1. Do NOT agree with the user just because they asked a question a certain way. Form your own view from the data.
2. Only discuss players/teams the user named. Never bring in unrelated players to pad your answer.
3. When stats are provided, use the actual numbers — don't make up statistics.
4. Be willing to push back directly if the premise is flawed.

ANALYSIS DEPTH — you can tackle:
- Advanced metric interpretation: ORTG, DRTG, NET RTG, TS%, USG%, DBPM, BPM, VORP context
- Lineup/role analysis: starter vs bench impact, two-way players, positional versatility
- Tactical breakdowns: pick-and-roll efficiency, transition offense, halfcourt creation, paint touches
- Historical context: how current players compare to historical greats at the same age/stage
- Playoff vs regular season performance differences and what they mean
- Contract value, team building implications, trade scenarios
- Injury context and how it affects projections
- Draft analysis: prospect evaluation, fit with teams
- Coaching schemes: pace, defensive schemes, offensive systems
- Clutch performance, fourth-quarter splits, high-leverage situations

STYLE:
- Lead with your sharpest insight, not a recap of what's already obvious
- Use specific numbers from the data provided
- Make concrete comparisons (historical or contemporary)
- Have a clear opinion — analysts take stances
- 3-5 paragraphs, punchy and direct

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
        if acols.get("dpoy"):        parts.append(f"{acols['dpoy']}x DPOY")
        acol_str = "Career accolades: " + ", ".join(parts) if parts else ""

    net = stats.get("net_rtg", "—")
    net_sign = "positive" if isinstance(net, (int, float)) and net > 0 else "negative"

    return f"""
Analyze {stats['name']}'s 2025-26 season with depth:

Team: {stats['team']} | Games: {stats['gp']}
{acol_str}

Scoring & Creation:
  PPG {stats['ppg']} (League #{stats.get('rank_pts','—')}) | FG% {round(stats['fg_pct']*100,1)}% | TS% {stats.get('ts_pct','—')}%
  3PT% {round(stats['three_pct']*100,1)}% on {stats.get('fg3a_pg','—')} attempts/game | FT% {round(stats['ft_pct']*100,1)}%
  FTA/game {stats.get('fta_pg','—')} | USG% {stats.get('usg_pct','—')}% | MIN {stats.get('min_pg','—')}

All-around:
  REB {stats['reb']} (#{stats.get('rank_reb','—')}) | AST {stats['ast']} (#{stats.get('rank_ast','—')})
  STL {stats['stl']} (#{stats.get('rank_stl','—')}) | BLK {stats['blk']} (#{stats.get('rank_blk','—')})
  TOV {stats.get('tov','—')}

On/Off impact:
  ORTG {stats.get('ortg','—')} (#{stats.get('rank_ortg','—')}) | DRTG {stats.get('drtg','—')} (#{stats.get('rank_drtg','—')})
  NET RTG {net} ({net_sign} impact when on court)

Give a sharp, layered analysis covering:
1. What his efficiency profile (TS%, FG%, FTA rate) tells us about HOW he scores — volume scorer, creator, or efficient finisher?
2. His two-way impact — does the NET RTG/DRTG suggest he's helping or hurting the team defensively?
3. The most interesting statistical story from this line — something non-obvious
4. Where he ranks in the current MVP/award/playoff conversation based purely on these numbers
5. One concrete thing that would elevate his game

Use basketball terminology. Reference the league ranks to give context. Take a clear stance.
"""


def build_team_season_prompt(stats):
    scorer    = stats.get('best_scorer') or {}
    rebounder = stats.get('best_rebounder') or {}
    top_str   = (
        f"{scorer.get('name','—')} ({scorer.get('stat_val','—')} PPG), "
        f"{rebounder.get('name','—')} ({rebounder.get('stat_val','—')} RPG)"
    )

    return f"""
Analyze the {stats['team']}'s 2025-26 season:

Record: {stats.get('wins','—')}-{stats.get('losses','—')} | {stats.get('conf','—')} Conference

Offense (Rank #{stats.get('rank_pts','—')} in scoring):
  PPG {stats['ppg']} | FG% {round(stats['fg_pct']*100,1)}% (#{stats.get('rank_fg','—')})
  3PT% {round(stats['three_pct']*100,1)}% (#{stats.get('rank_3fg','—')}) on {stats.get('fg3a_pg','—')} 3PA
  FTA {stats.get('fta_pg','—')} (#{stats.get('rank_fta','—')})

Defense & Pace:
  REB {stats['reb']} (#{stats.get('rank_reb','—')})
  STL {stats['stl']} (#{stats.get('rank_stl','—')}) | BLK {stats['blk']} (#{stats.get('rank_blk','—')})

Advanced:
  ORTG {stats.get('ortg','—')} (#{stats.get('rank_ortg','—')}) | DRTG {stats.get('drtg','—')} (#{stats.get('rank_drtg','—')}) | NET RTG {stats.get('net_rtg','—')}

Top performers: {top_str}

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