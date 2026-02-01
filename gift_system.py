"""
礼物系统 - 处理直播礼物，提供属性加成和特殊效果
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import defaultdict

from danmaku_listener import GiftMessage


@dataclass
class GiftEffect:
    """礼物效果定义"""
    name: str
    min_value: float  # 最低触发价值（元）
    effects: Dict[str, any] = field(default_factory=dict)
    description: str = ""


# 礼物效果配置
GIFT_EFFECTS = {
    # 小额礼物 - 修为加成
    "cultivation_small": GiftEffect(
        name="灵气注入",
        min_value=0.1,
        effects={"cultivation": 5},
        description="获得5点修为"
    ),
    "cultivation_medium": GiftEffect(
        name="灵石馈赠",
        min_value=1.0,
        effects={"cultivation": 20},
        description="获得20点修为"
    ),
    "cultivation_large": GiftEffect(
        name="仙晶灌顶",
        min_value=10.0,
        effects={"cultivation": 100},
        description="获得100点修为"
    ),
    
    # 中额礼物 - 属性加成
    "hp_boost": GiftEffect(
        name="生命祝福",
        min_value=5.0,
        effects={"max_hp": 50, "hp": 50},
        description="最大生命值+50，恢复50生命"
    ),
    "mp_boost": GiftEffect(
        name="灵力灌注",
        min_value=5.0,
        effects={"max_mp": 30, "mp": 30},
        description="最大灵力+30，恢复30灵力"
    ),
    "attribute_boost": GiftEffect(
        name="天赋觉醒",
        min_value=20.0,
        effects={"random_attribute": 2},
        description="随机属性+2"
    ),
    
    # 高额礼物 - 特殊效果
    "rename": GiftEffect(
        name="赐名权",
        min_value=50.0,
        effects={"can_rename": True},
        description="可以为主角改名"
    ),
    "breakthrough_chance": GiftEffect(
        name="天道眷顾",
        min_value=100.0,
        effects={"breakthrough_boost": 30},
        description="突破成功率+30%"
    ),
    "resurrection": GiftEffect(
        name="复活秘法",
        min_value=200.0,
        effects={"resurrection": True},
        description="死亡时可复活一次"
    ),
}


@dataclass
class GiftRecord:
    """礼物记录"""
    user_id: str
    username: str
    platform: str
    gift_name: str
    gift_count: int
    gift_value: float
    effect_applied: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DonorStats:
    """打赏者统计"""
    user_id: str
    username: str
    platform: str
    total_value: float = 0.0
    total_gifts: int = 0
    last_gift_time: str = ""
    contribution_rank: int = 0


class GiftProcessor:
    """礼物处理器"""
    
    def __init__(self, save_file: str = "gift_records.json"):
        self.save_file = save_file
        self.records: List[GiftRecord] = []
        self.donor_stats: Dict[str, DonorStats] = {}  # user_id -> stats
        self.pending_effects: List[Dict] = []  # 待处理的效果
        self.pending_rename: Optional[Dict] = None  # 待处理的改名
        self.effect_callbacks: List[Callable] = []
        
        # 加载历史记录
        self._load_records()
    
    def register_effect_callback(self, callback: Callable):
        """注册效果应用回调"""
        self.effect_callbacks.append(callback)
    
    def process_gift(self, gift: GiftMessage) -> Optional[GiftEffect]:
        """处理礼物，返回触发的效果"""
        total_value = gift.gift_value * gift.gift_count
        
        # 更新打赏者统计
        self._update_donor_stats(gift, total_value)
        
        # 确定触发的效果
        effect = self._determine_effect(total_value)
        
        if effect:
            # 记录礼物
            record = GiftRecord(
                user_id=gift.user_id,
                username=gift.username,
                platform=gift.platform,
                gift_name=gift.gift_name,
                gift_count=gift.gift_count,
                gift_value=total_value,
                effect_applied=effect.name,
            )
            self.records.append(record)
            
            # 添加到待处理效果
            self.pending_effects.append({
                "effect": effect,
                "donor": gift.username,
                "value": total_value,
            })
            
            # 特殊处理：改名权
            if effect.effects.get("can_rename"):
                self.pending_rename = {
                    "donor": gift.username,
                    "user_id": gift.user_id,
                }
            
            # 保存记录
            self._save_records()
            
            # 触发回调
            for callback in self.effect_callbacks:
                try:
                    callback(effect, gift)
                except Exception as e:
                    print(f"效果回调错误: {e}")
        
        return effect
    
    def _determine_effect(self, value: float) -> Optional[GiftEffect]:
        """根据礼物价值确定效果"""
        # 按价值从高到低排序
        sorted_effects = sorted(
            GIFT_EFFECTS.values(),
            key=lambda e: e.min_value,
            reverse=True
        )
        
        for effect in sorted_effects:
            if value >= effect.min_value:
                return effect
        
        return None
    
    def _update_donor_stats(self, gift: GiftMessage, value: float):
        """更新打赏者统计"""
        key = f"{gift.platform}_{gift.user_id}"
        
        if key not in self.donor_stats:
            self.donor_stats[key] = DonorStats(
                user_id=gift.user_id,
                username=gift.username,
                platform=gift.platform,
            )
        
        stats = self.donor_stats[key]
        stats.total_value += value
        stats.total_gifts += gift.gift_count
        stats.last_gift_time = datetime.now().isoformat()
        stats.username = gift.username  # 更新用户名（可能会变）
        
        # 更新排名
        self._update_rankings()
    
    def _update_rankings(self):
        """更新排名"""
        sorted_donors = sorted(
            self.donor_stats.values(),
            key=lambda d: d.total_value,
            reverse=True
        )
        
        for i, donor in enumerate(sorted_donors):
            donor.contribution_rank = i + 1
    
    def get_pending_effects(self) -> List[Dict]:
        """获取并清空待处理效果"""
        effects = self.pending_effects.copy()
        self.pending_effects = []
        return effects
    
    def has_pending_rename(self) -> bool:
        """是否有待处理的改名"""
        return self.pending_rename is not None
    
    def get_pending_rename(self) -> Optional[Dict]:
        """获取并清空待处理的改名"""
        rename = self.pending_rename
        self.pending_rename = None
        return rename
    
    def apply_effects_to_player(self, player, effects: List[Dict]) -> List[str]:
        """将效果应用到玩家
        
        Args:
            player: Player对象
            effects: 效果列表
            
        Returns:
            应用的效果描述列表
        """
        import random
        
        messages = []
        
        for effect_data in effects:
            effect = effect_data["effect"]
            donor = effect_data["donor"]
            
            for key, value in effect.effects.items():
                if key == "cultivation":
                    result = player.add_cultivation(value)
                    msg = f"【{donor}】的{effect.name}：修为+{value}"
                    if result.get("breakthrough"):
                        msg += f"，突破至【{result['new_realm']}】！"
                    messages.append(msg)
                
                elif key == "max_hp":
                    player.max_hp += value
                    messages.append(f"【{donor}】的{effect.name}：最大生命+{value}")
                
                elif key == "hp":
                    healed = player.heal(value)
                    if healed > 0:
                        messages.append(f"恢复生命值 {healed}")
                
                elif key == "max_mp":
                    player.max_mp += value
                    messages.append(f"【{donor}】的{effect.name}：最大灵力+{value}")
                
                elif key == "mp":
                    restored = player.restore_mp(value)
                    if restored > 0:
                        messages.append(f"恢复灵力 {restored}")
                
                elif key == "random_attribute":
                    attrs = list(player.attributes.keys())
                    attr = random.choice(attrs)
                    player.attributes[attr] += value
                    messages.append(f"【{donor}】的{effect.name}：{attr}+{value}")
        
        return messages
    
    def get_top_donors(self, limit: int = 10) -> List[DonorStats]:
        """获取贡献排行榜"""
        sorted_donors = sorted(
            self.donor_stats.values(),
            key=lambda d: d.total_value,
            reverse=True
        )
        return sorted_donors[:limit]
    
    def get_recent_gifts(self, limit: int = 20) -> List[GiftRecord]:
        """获取最近礼物记录"""
        return self.records[-limit:][::-1]  # 最新的在前
    
    def _save_records(self):
        """保存记录到文件"""
        data = {
            "records": [asdict(r) for r in self.records[-1000:]],  # 只保留最近1000条
            "donor_stats": {k: asdict(v) for k, v in self.donor_stats.items()},
        }
        
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_records(self):
        """从文件加载记录"""
        if not os.path.exists(self.save_file):
            return
        
        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.records = [
                GiftRecord(**r) for r in data.get("records", [])
            ]
            
            self.donor_stats = {
                k: DonorStats(**v) for k, v in data.get("donor_stats", {}).items()
            }
        except Exception as e:
            print(f"加载礼物记录失败: {e}")
