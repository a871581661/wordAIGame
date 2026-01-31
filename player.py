"""
玩家角色类
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional
from config import CULTIVATION_REALMS, BASE_ATTRIBUTES, SPIRITUAL_ROOTS, SAVE_DIRECTORY


class Player:
    """修仙游戏玩家角色类"""
    
    def __init__(self, name: str, gender: str, spiritual_root: Dict = None):
        self.name = name
        self.gender = gender
        self.spiritual_root = spiritual_root or random.choice(SPIRITUAL_ROOTS)
        
        # 境界相关
        self.realm_index = 0  # 当前境界索引
        self.cultivation_progress = 0  # 当前境界修为进度 (0-100)
        
        # 基础属性
        self.attributes = BASE_ATTRIBUTES.copy()
        # 应用灵根加成
        for attr, bonus in self.spiritual_root.get("bonus", {}).items():
            self.attributes[attr] = self.attributes.get(attr, 10) + bonus
        
        # 战斗属性
        self.max_hp = self._calculate_max_hp()
        self.hp = self.max_hp
        self.max_mp = self._calculate_max_mp()
        self.mp = self.max_mp
        
        # 背包和装备
        self.inventory: List[Dict] = []
        self.equipment: Dict[str, Optional[Dict]] = {
            "武器": None,
            "护甲": None,
            "饰品": None,
            "法宝": None,
        }
        
        # 功法和技能
        self.skills: List[Dict] = []
        self.techniques: List[Dict] = []  # 修炼的功法
        
        # 故事相关
        self.story_history: List[str] = []  # 故事历史记录
        self.current_location = "青云山"  # 当前位置
        self.relationships: Dict[str, int] = {}  # 与NPC的关系度
        
        # 游戏统计
        self.created_at = datetime.now().isoformat()
        self.play_time = 0  # 游戏时间（秒）
        self.choices_made = 0  # 做出的选择数量
        
    def _calculate_max_hp(self) -> int:
        """计算最大生命值"""
        base_hp = 100
        realm_bonus = self.realm_index * 50
        attribute_bonus = self.attributes.get("体魄", 10) * 5
        return base_hp + realm_bonus + attribute_bonus
    
    def _calculate_max_mp(self) -> int:
        """计算最大灵力值"""
        base_mp = 50
        realm_bonus = self.realm_index * 30
        attribute_bonus = self.attributes.get("神识", 10) * 3
        return base_mp + realm_bonus + attribute_bonus
    
    @property
    def realm(self) -> Dict:
        """获取当前境界信息"""
        return CULTIVATION_REALMS[self.realm_index]
    
    @property
    def realm_name(self) -> str:
        """获取当前境界名称"""
        return self.realm["name"]
    
    def add_cultivation(self, amount: int) -> Dict:
        """增加修为
        
        Returns:
            Dict: 包含是否突破等信息
        """
        result = {
            "cultivation_gained": amount,
            "breakthrough": False,
            "new_realm": None,
        }
        
        self.cultivation_progress += amount
        
        # 检查是否可以突破
        while self.cultivation_progress >= 100 and self.realm_index < len(CULTIVATION_REALMS) - 1:
            self.cultivation_progress -= 100
            self.realm_index += 1
            result["breakthrough"] = True
            result["new_realm"] = self.realm_name
            
            # 突破后更新属性
            self.max_hp = self._calculate_max_hp()
            self.hp = self.max_hp  # 突破后满血
            self.max_mp = self._calculate_max_mp()
            self.mp = self.max_mp  # 突破后满蓝
        
        # 确保进度不超过100
        if self.realm_index >= len(CULTIVATION_REALMS) - 1:
            self.cultivation_progress = min(self.cultivation_progress, 100)
            
        return result
    
    def lose_cultivation(self, amount: int) -> None:
        """失去修为"""
        self.cultivation_progress = max(0, self.cultivation_progress - amount)
    
    def take_damage(self, damage: int) -> bool:
        """受到伤害
        
        Returns:
            bool: 是否死亡
        """
        self.hp = max(0, self.hp - damage)
        return self.hp <= 0
    
    def heal(self, amount: int) -> int:
        """治疗
        
        Returns:
            int: 实际恢复的生命值
        """
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp
    
    def use_mp(self, amount: int) -> bool:
        """消耗灵力
        
        Returns:
            bool: 是否有足够灵力
        """
        if self.mp >= amount:
            self.mp -= amount
            return True
        return False
    
    def restore_mp(self, amount: int) -> int:
        """恢复灵力
        
        Returns:
            int: 实际恢复的灵力值
        """
        old_mp = self.mp
        self.mp = min(self.max_mp, self.mp + amount)
        return self.mp - old_mp
    
    def add_item(self, item: Dict) -> None:
        """添加物品到背包"""
        self.inventory.append(item)
    
    def remove_item(self, item_name: str) -> bool:
        """从背包移除物品
        
        Returns:
            bool: 是否成功移除
        """
        for i, item in enumerate(self.inventory):
            if item.get("name") == item_name:
                self.inventory.pop(i)
                return True
        return False
    
    def add_story(self, story: str) -> None:
        """添加故事到历史记录"""
        self.story_history.append(story)
        # 只保留最近的20条故事
        if len(self.story_history) > 20:
            self.story_history = self.story_history[-20:]
    
    def get_recent_story(self, count: int = 3) -> str:
        """获取最近的故事内容"""
        recent = self.story_history[-count:] if self.story_history else []
        return "\n\n".join(recent)
    
    def get_status_display(self) -> str:
        """获取状态显示字符串"""
        hp_bar = self._create_bar(self.hp, self.max_hp, "♥", 20)
        mp_bar = self._create_bar(self.mp, self.max_mp, "✦", 20)
        cultivation_bar = self._create_bar(self.cultivation_progress, 100, "◆", 20)
        
        status = f"""
╔══════════════════════════════════════════════════════════════╗
║  【{self.name}】 {self.gender} · {self.spiritual_root['name']}
║  境界：{self.realm_name} ({self.realm['description']})
╠══════════════════════════════════════════════════════════════╣
║  生命：{hp_bar} {self.hp}/{self.max_hp}
║  灵力：{mp_bar} {self.mp}/{self.max_mp}
║  修为：{cultivation_bar} {self.cultivation_progress}%
╠══════════════════════════════════════════════════════════════╣
║  体魄: {self.attributes['体魄']:>3}  │  神识: {self.attributes['神识']:>3}  │  悟性: {self.attributes['悟性']:>3}
║  机缘: {self.attributes['机缘']:>3}  │  心境: {self.attributes['心境']:>3}  │  位置: {self.current_location}
╚══════════════════════════════════════════════════════════════╝"""
        return status
    
    def _create_bar(self, current: int, maximum: int, char: str, length: int) -> str:
        """创建进度条"""
        filled = int((current / maximum) * length) if maximum > 0 else 0
        empty = length - filled
        return f"[{char * filled}{'·' * empty}]"
    
    def to_dict(self) -> Dict:
        """将玩家数据转换为字典"""
        return {
            "name": self.name,
            "gender": self.gender,
            "spiritual_root": self.spiritual_root,
            "realm_index": self.realm_index,
            "cultivation_progress": self.cultivation_progress,
            "attributes": self.attributes,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "inventory": self.inventory,
            "equipment": self.equipment,
            "skills": self.skills,
            "techniques": self.techniques,
            "story_history": self.story_history,
            "current_location": self.current_location,
            "relationships": self.relationships,
            "created_at": self.created_at,
            "play_time": self.play_time,
            "choices_made": self.choices_made,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Player":
        """从字典创建玩家对象"""
        player = cls(
            name=data["name"],
            gender=data["gender"],
            spiritual_root=data["spiritual_root"],
        )
        player.realm_index = data["realm_index"]
        player.cultivation_progress = data["cultivation_progress"]
        player.attributes = data["attributes"]
        player.hp = data["hp"]
        player.max_hp = data["max_hp"]
        player.mp = data["mp"]
        player.max_mp = data["max_mp"]
        player.inventory = data["inventory"]
        player.equipment = data["equipment"]
        player.skills = data["skills"]
        player.techniques = data["techniques"]
        player.story_history = data["story_history"]
        player.current_location = data["current_location"]
        player.relationships = data["relationships"]
        player.created_at = data["created_at"]
        player.play_time = data["play_time"]
        player.choices_made = data["choices_made"]
        return player
    
    def save(self, filename: str = None) -> str:
        """保存玩家数据到文件
        
        Returns:
            str: 保存的文件路径
        """
        if not os.path.exists(SAVE_DIRECTORY):
            os.makedirs(SAVE_DIRECTORY)
        
        if filename is None:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(SAVE_DIRECTORY, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        return filepath
    
    @classmethod
    def load(cls, filepath: str) -> "Player":
        """从文件加载玩家数据"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @staticmethod
    def list_saves() -> List[str]:
        """列出所有存档文件"""
        if not os.path.exists(SAVE_DIRECTORY):
            return []
        
        saves = []
        for filename in os.listdir(SAVE_DIRECTORY):
            if filename.endswith('.json'):
                saves.append(os.path.join(SAVE_DIRECTORY, filename))
        return sorted(saves, reverse=True)  # 按时间倒序
