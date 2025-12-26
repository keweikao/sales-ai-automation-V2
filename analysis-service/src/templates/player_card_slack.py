"""
Player Card Slack Templates - Slack Block Kit 訊息模板

用於生成球員卡的 Slack 訊息格式。
"""

from typing import Dict, List, Any


def build_personal_player_card_blocks(card: Dict[str, Any], rank: int = 0, total_reps: int = 0) -> List[Dict]:
    """
    建立個人球員卡 Slack Blocks
    
    Args:
        card: Player card data
        rank: 團隊排名 (0 表示不顯示)
        total_reps: 團隊總人數
        
    Returns:
        List of Slack blocks
    """
    indices = card.get("indices", {})
    trends = card.get("trends", {})
    stats = card.get("stats", {})
    highlights = card.get("highlights", {})
    
    # Rank 顯示
    rank_text = ""
    if rank > 0:
        rank_emoji = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
        rank_text = f" ({rank_emoji} 團隊第{rank})"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"👤 {card.get('repName', 'Unknown')} 的本週球員卡",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🏆 *綜合戰鬥力 (SHI): {indices.get('overall', 0)} / 100*{rank_text}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"🔺 *產出:* {indices.get('activity', 0)} {_trend_arrow(trends.get('activity', 0))}"},
                {"type": "mrkdwn", "text": f"🔹 *品質:* {indices.get('quality', 0)} {_trend_arrow(trends.get('quality', 0))}"},
                {"type": "mrkdwn", "text": f"🔸 *潛力:* {indices.get('opportunity', 0)} {_trend_arrow(trends.get('opportunity', 0))}"},
                {"type": "mrkdwn", "text": f"🟢 *執行:* {indices.get('execution', 0)} {_trend_arrow(trends.get('execution', 0))}"},
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"📁 *本週統計*\n"
                    f"• 上傳: {stats.get('uploadCount', 0)} 件 | 成功分析: {stats.get('demoCount', 0)} 件\n"
                    f"• 立即成交機會: {stats.get('closeNowCount', 0)} 件 🔥\n"
                    f"• 風險案件: {stats.get('riskCount', 0)} 件 ⚠️"
                )
            }
        },
    ]
    
    # 明星案件
    top_wins = highlights.get("topWins", [])
    if top_wins:
        wins_text = "🏆 *明星案件*\n"
        for win in top_wins[:3]:
            strategy_emoji = "🔥" if "CloseNow" in win.get("strategy", "") or "立即成交" in win.get("strategy", "") else "📈"
            wins_text += f"• {win.get('storeName', 'Unknown')} ({win.get('score', 0)}分) {strategy_emoji}\n"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": wins_text.strip()}
        })
    
    # 風險案件
    risk_cases = highlights.get("riskCases", [])
    if risk_cases:
        risk_text = "⚠️ *風險案件*\n"
        for risk in risk_cases[:3]:
            risk_text += f"• {risk.get('storeName', 'Unknown')}: {risk.get('reason', '需關注')}\n"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": risk_text.strip()}
        })
    
    # 教練評語
    coach_note = card.get("coachNote", "")
    if coach_note:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *教練評語*\n_{coach_note}_"
            }
        })
    
    # 週次資訊
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"📅 {card.get('weekOf', '')} | 由 AI 銷售教練自動生成"}
        ]
    })
    
    return blocks


def build_team_dashboard_blocks(
    cards: List[Dict[str, Any]],
    week_of: str,
    team_stats: Dict[str, Any],
) -> List[Dict]:
    """
    建立團隊儀表板 Slack Blocks
    
    Args:
        cards: List of player cards
        week_of: ISO week format
        team_stats: Aggregated team statistics
        
    Returns:
        List of Slack blocks
    """
    # 按 SHI 排序
    sorted_cards = sorted(
        cards,
        key=lambda c: c.get("indices", {}).get("overall", 0),
        reverse=True
    )
    
    # 團隊統計
    total_demos = sum(c.get("stats", {}).get("demoCount", 0) for c in cards)
    total_close_now = sum(c.get("stats", {}).get("closeNowCount", 0) for c in cards)
    total_risk = sum(c.get("stats", {}).get("riskCount", 0) for c in cards)
    
    avg_shi = int(sum(c.get("indices", {}).get("overall", 0) for c in cards) / len(cards)) if cards else 0
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 {week_of} 團隊球員卡",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*📈 團隊總 Demo:*\n{total_demos} 件"},
                {"type": "mrkdwn", "text": f"*⭐ 平均戰鬥力:*\n{avg_shi}"},
                {"type": "mrkdwn", "text": f"*🔥 立即成交:*\n{total_close_now} 件"},
                {"type": "mrkdwn", "text": f"*⚠️ 風險案件:*\n{total_risk} 件"},
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🏆 績效排行*"}
        },
    ]
    
    # 績效排行表
    rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, card in enumerate(sorted_cards[:10]):
        rank = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}."
        name = card.get("repName", "Unknown")
        shi = card.get("indices", {}).get("overall", 0)
        demos = card.get("stats", {}).get("demoCount", 0)
        
        # 狀態標示
        status = ""
        if shi >= 80:
            status = "⭐ Star"
        elif shi >= 60:
            status = "💪 Solid"
        elif shi < 50:
            status = "📚 Coaching"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{rank} *{name}* | SHI: {shi} | Demo: {demos} {status}"
            }
        })
    
    # 需關注的業務
    low_performers = [c for c in sorted_cards if c.get("indices", {}).get("overall", 0) < 50]
    if low_performers:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📚 需要 Coaching*"}
        })
        
        for card in low_performers[:3]:
            name = card.get("repName", "Unknown")
            indices = card.get("indices", {})
            
            # 找出最弱項
            weakest = min(
                ["activity", "quality", "opportunity", "execution"],
                key=lambda k: indices.get(k, 100)
            )
            weakest_labels = {
                "activity": "產出",
                "quality": "品質",
                "opportunity": "潛力",
                "execution": "執行",
            }
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• *{name}*: {weakest_labels[weakest]}({indices.get(weakest, 0)}) 需加強"
                }
            })
    
    # 週次資訊
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"📅 {week_of} | 由 AI 銷售教練自動生成"}
        ]
    })
    
    return blocks


def _trend_arrow(change: int) -> str:
    """生成趨勢箭頭"""
    if change > 10:
        return f"↑{change}%"
    elif change > 0:
        return f"↗{change}%"
    elif change < -10:
        return f"↓{abs(change)}%"
    elif change < 0:
        return f"↘{abs(change)}%"
    else:
        return "→"
