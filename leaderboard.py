"""
排行榜系统 - 记录游戏数据和贡献排行
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class LeaderboardType(Enum):
    """排行榜类型"""
    CONTRIBUTION = "contribution"  # 贡献榜（礼物）
    VOTE_PARTICIPATION = "vote"    # 投票参与榜
    LUCKY = "lucky"                # 幸运榜（选择正确）
    GAME_PROGRESS = "progress"     # 游戏进度榜


@dataclass
class LeaderboardEntry:
    """排行榜条目"""
    user_id: str
    username: str
    platform: str
    score: float
    extra_data: Dict = field(default_factory=dict)
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        platform_icons = {
            "bilibili": "📺",
            "douyin": "🎵",
            "mock": "🎮",
        }
        icon = platform_icons.get(self.platform, "👤")
        return f"{icon}{self.username}"


@dataclass 
class GameStats:
    """游戏统计数据"""
    # 角色数据
    character_name: str = ""
    character_realm: str = "凡人"
    character_cultivation: int = 0
    
    # 游戏进度
    total_choices: int = 0
    total_stories: int = 0
    breakthroughs: int = 0
    deaths: int = 0
    
    # 投票统计
    total_votes: int = 0
    winning_votes: int = 0  # 选中了获胜选项的次数
    
    # 直播统计
    total_viewers: int = 0
    peak_viewers: int = 0
    total_gifts_value: float = 0.0
    total_gifts_count: int = 0
    
    # 时间统计
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    play_time_seconds: int = 0


class Leaderboard:
    """排行榜管理器"""
    
    def __init__(self, save_file: str = "leaderboard.json"):
        self.save_file = save_file
        
        # 各类排行榜数据
        self.boards: Dict[str, Dict[str, LeaderboardEntry]] = {
            LeaderboardType.CONTRIBUTION.value: {},
            LeaderboardType.VOTE_PARTICIPATION.value: {},
            LeaderboardType.LUCKY.value: {},
        }
        
        # 游戏统计
        self.game_stats = GameStats()
        
        # 历史记录
        self.history: List[Dict] = []  # 重要事件历史
        
        # 加载数据
        self._load()
    
    def update_contribution(self, user_id: str, username: str, platform: str, 
                           value: float, gift_name: str = ""):
        """更新贡献榜"""
        board = self.boards[LeaderboardType.CONTRIBUTION.value]
        key = f"{platform}_{user_id}"
        
        if key not in board:
            board[key] = LeaderboardEntry(
                user_id=user_id,
                username=username,
                platform=platform,
                score=0,
                extra_data={"gifts": []},
            )
        
        entry = board[key]
        entry.score += value
        entry.username = username
        entry.last_update = datetime.now().isoformat()
        
        # 记录礼物
        if len(entry.extra_data.get("gifts", [])) < 100:
            entry.extra_data.setdefault("gifts", []).append({
                "name": gift_name,
                "value": value,
                "time": datetime.now().isoformat(),
            })
        
        # 更新游戏统计
        self.game_stats.total_gifts_value += value
        self.game_stats.total_gifts_count += 1
        
        self._save()
    
    def update_vote_participation(self, user_id: str, username: str, 
                                   platform: str, voted_option: str,
                                   winning_option: str):
        """更新投票参与榜"""
        board = self.boards[LeaderboardType.VOTE_PARTICIPATION.value]
        key = f"{platform}_{user_id}"
        
        if key not in board:
            board[key] = LeaderboardEntry(
                user_id=user_id,
                username=username,
                platform=platform,
                score=0,
                extra_data={"total_votes": 0, "correct_votes": 0},
            )
        
        entry = board[key]
        entry.extra_data["total_votes"] = entry.extra_data.get("total_votes", 0) + 1
        entry.username = username
        entry.last_update = datetime.now().isoformat()
        
        # 参与积分
        entry.score += 1
        
        # 如果选中了获胜选项，额外加分
        if voted_option == winning_option:
            entry.score += 2
            entry.extra_data["correct_votes"] = entry.extra_data.get("correct_votes", 0) + 1
            
            # 更新幸运榜
            self._update_lucky_board(user_id, username, platform)
        
        self._save()
    
    def _update_lucky_board(self, user_id: str, username: str, platform: str):
        """更新幸运榜"""
        board = self.boards[LeaderboardType.LUCKY.value]
        key = f"{platform}_{user_id}"
        
        if key not in board:
            board[key] = LeaderboardEntry(
                user_id=user_id,
                username=username,
                platform=platform,
                score=0,
            )
        
        entry = board[key]
        entry.score += 1
        entry.username = username
        entry.last_update = datetime.now().isoformat()
    
    def get_leaderboard(self, board_type: LeaderboardType, limit: int = 10) -> List[LeaderboardEntry]:
        """获取排行榜"""
        board = self.boards.get(board_type.value, {})
        
        sorted_entries = sorted(
            board.values(),
            key=lambda e: e.score,
            reverse=True
        )
        
        return sorted_entries[:limit]
    
    def get_user_rank(self, board_type: LeaderboardType, user_id: str, platform: str) -> Optional[int]:
        """获取用户排名"""
        board = self.boards.get(board_type.value, {})
        key = f"{platform}_{user_id}"
        
        if key not in board:
            return None
        
        sorted_entries = sorted(
            board.values(),
            key=lambda e: e.score,
            reverse=True
        )
        
        for i, entry in enumerate(sorted_entries):
            if f"{entry.platform}_{entry.user_id}" == key:
                return i + 1
        
        return None
    
    def add_history_event(self, event_type: str, description: str, data: Dict = None):
        """添加历史事件"""
        event = {
            "type": event_type,
            "description": description,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }
        
        self.history.append(event)
        
        # 只保留最近500条
        if len(self.history) > 500:
            self.history = self.history[-500:]
        
        self._save()
    
    def update_game_stats(self, **kwargs):
        """更新游戏统计"""
        for key, value in kwargs.items():
            if hasattr(self.game_stats, key):
                if isinstance(value, int) and key.startswith("total_"):
                    # 累加
                    current = getattr(self.game_stats, key)
                    setattr(self.game_stats, key, current + value)
                else:
                    setattr(self.game_stats, key, value)
        
        self.game_stats.last_update = datetime.now().isoformat()
        self._save()
    
    def get_formatted_leaderboard(self, board_type: LeaderboardType, limit: int = 10) -> str:
        """获取格式化的排行榜文本"""
        entries = self.get_leaderboard(board_type, limit)
        
        if not entries:
            return "暂无数据"
        
        titles = {
            LeaderboardType.CONTRIBUTION: "🏆 贡献榜",
            LeaderboardType.VOTE_PARTICIPATION: "🗳️ 参与榜",
            LeaderboardType.LUCKY: "🍀 幸运榜",
        }
        
        lines = [titles.get(board_type, "排行榜"), "━" * 25]
        
        rank_icons = ["🥇", "🥈", "🥉"]
        
        for i, entry in enumerate(entries):
            rank = rank_icons[i] if i < 3 else f"{i+1}."
            
            if board_type == LeaderboardType.CONTRIBUTION:
                score_text = f"¥{entry.score:.1f}"
            elif board_type == LeaderboardType.VOTE_PARTICIPATION:
                correct = entry.extra_data.get("correct_votes", 0)
                total = entry.extra_data.get("total_votes", 0)
                score_text = f"{entry.score}分 ({correct}/{total})"
            else:
                score_text = f"{int(entry.score)}次"
            
            lines.append(f"{rank} {entry.display_name}: {score_text}")
        
        return "\n".join(lines)
    
    def get_stats_summary(self) -> str:
        """获取统计摘要"""
        stats = self.game_stats
        
        lines = [
            "📊 直播统计",
            "━" * 25,
            f"角色: {stats.character_name or '未创建'}",
            f"境界: {stats.character_realm}",
            f"修为: {stats.character_cultivation}%",
            "",
            f"📖 故事数: {stats.total_stories}",
            f"🎯 选择数: {stats.total_choices}",
            f"⬆️ 突破数: {stats.breakthroughs}",
            "",
            f"🗳️ 总投票: {stats.total_votes}",
            f"🎁 礼物数: {stats.total_gifts_count}",
            f"💰 礼物价值: ¥{stats.total_gifts_value:.1f}",
        ]
        
        return "\n".join(lines)
    
    def _save(self):
        """保存数据"""
        data = {
            "boards": {
                k: {kk: asdict(vv) for kk, vv in v.items()}
                for k, v in self.boards.items()
            },
            "game_stats": asdict(self.game_stats),
            "history": self.history[-100:],  # 只保存最近100条历史
        }
        
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load(self):
        """加载数据"""
        if not os.path.exists(self.save_file):
            return
        
        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载排行榜
            for board_type, entries in data.get("boards", {}).items():
                if board_type in self.boards:
                    self.boards[board_type] = {
                        k: LeaderboardEntry(**v) for k, v in entries.items()
                    }
            
            # 加载统计
            if "game_stats" in data:
                self.game_stats = GameStats(**data["game_stats"])
            
            # 加载历史
            self.history = data.get("history", [])
            
        except Exception as e:
            print(f"加载排行榜数据失败: {e}")
    
    def reset(self):
        """重置所有数据"""
        self.boards = {
            LeaderboardType.CONTRIBUTION.value: {},
            LeaderboardType.VOTE_PARTICIPATION.value: {},
            LeaderboardType.LUCKY.value: {},
        }
        self.game_stats = GameStats()
        self.history = []
        self._save()
