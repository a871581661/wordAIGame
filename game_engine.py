"""
游戏引擎 - 核心游戏逻辑
"""

import os
import sys
import time
import random
from typing import Dict, List, Optional, Tuple
from player import Player
from ai_storyteller import AIStoryteller, MockStoryteller
from config import SPIRITUAL_ROOTS, GAME_TITLE, GAME_VERSION, CULTIVATION_REALMS


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_slowly(text: str, delay: float = 0.02):
    """逐字打印文本（打字机效果）"""
    for char in text:
        print(char, end='', flush=True)
        if char in '。！？，、；：':
            time.sleep(delay * 3)
        else:
            time.sleep(delay)
    print()


def print_divider(char: str = "═", length: int = 60):
    """打印分隔线"""
    print(char * length)


def print_box(text: str, width: int = 60):
    """打印带边框的文本"""
    lines = text.split('\n')
    print("╔" + "═" * (width - 2) + "╗")
    for line in lines:
        # 处理中文字符宽度
        visible_len = sum(2 if ord(c) > 127 else 1 for c in line)
        padding = width - 2 - visible_len
        print(f"║{line}{' ' * max(0, padding)}║")
    print("╚" + "═" * (width - 2) + "╝")


class GameEngine:
    """游戏引擎类"""
    
    def __init__(self, use_mock: bool = False):
        """初始化游戏引擎
        
        Args:
            use_mock: 是否使用模拟AI（用于测试）
        """
        self.player: Optional[Player] = None
        self.storyteller = MockStoryteller() if use_mock else AIStoryteller()
        self.current_story: str = ""
        self.current_options: List[str] = []
        self.game_running: bool = False
        self.use_slow_print: bool = True  # 是否使用打字机效果
        
    def print_title(self):
        """打印游戏标题"""
        clear_screen()
        title_art = f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ██╗  ██╗██╗ █████╗ ███╗   ██╗████████╗██╗   ██╗           ║
    ║     ╚██╗██╔╝██║██╔══██╗████╗  ██║╚══██╔══╝██║   ██║           ║
    ║      ╚███╔╝ ██║███████║██╔██╗ ██║   ██║   ██║   ██║           ║
    ║      ██╔██╗ ██║██╔══██║██║╚██╗██║   ██║   ██║   ██║           ║
    ║     ██╔╝ ██╗██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝           ║
    ║     ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝            ║
    ║                                                               ║
    ║                      《 {GAME_TITLE} 》                          ║
    ║                                                               ║
    ║                   一款AI驱动的修仙文字游戏                    ║
    ║                        版本 {GAME_VERSION}                          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
        """
        print(title_art)
    
    def main_menu(self) -> str:
        """显示主菜单
        
        Returns:
            str: 用户选择
        """
        print("\n")
        print("    ┌─────────────────────────────────────┐")
        print("    │                                     │")
        print("    │       1. 开始新的修仙之旅           │")
        print("    │       2. 继续修仙                   │")
        print("    │       3. 游戏设置                   │")
        print("    │       4. 退出游戏                   │")
        print("    │                                     │")
        print("    └─────────────────────────────────────┘")
        print()
        
        while True:
            choice = input("    请选择 (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            print("    无效的选择，请重新输入。")
    
    def create_character(self) -> Player:
        """创建角色
        
        Returns:
            Player: 创建的玩家角色
        """
        clear_screen()
        print("\n")
        print_divider()
        print("                    【 角色创建 】")
        print_divider()
        print()
        
        # 输入姓名
        while True:
            name = input("  请输入你的道号: ").strip()
            if name:
                break
            print("  道号不能为空！")
        
        # 选择性别
        print("\n  请选择性别:")
        print("    1. 男")
        print("    2. 女")
        while True:
            gender_choice = input("  请选择 (1/2): ").strip()
            if gender_choice == '1':
                gender = "他"
                break
            elif gender_choice == '2':
                gender = "她"
                break
            print("  无效的选择！")
        
        # 选择灵根
        print("\n  请选择你的灵根:")
        print_divider("─", 50)
        for i, root in enumerate(SPIRITUAL_ROOTS, 1):
            bonus_str = ", ".join([f"{k}+{v}" for k, v in root["bonus"].items()])
            print(f"    {i}. {root['name']} ({root['element']}属性)")
            print(f"       加成: {bonus_str}")
        print_divider("─", 50)
        
        while True:
            root_choice = input(f"  请选择 (1-{len(SPIRITUAL_ROOTS)}): ").strip()
            if root_choice.isdigit():
                idx = int(root_choice) - 1
                if 0 <= idx < len(SPIRITUAL_ROOTS):
                    spiritual_root = SPIRITUAL_ROOTS[idx]
                    break
            print("  无效的选择！")
        
        # 创建玩家
        player = Player(name=name, gender=gender, spiritual_root=spiritual_root)
        
        print("\n")
        print_divider()
        print(f"  恭喜！道友【{name}】已踏入修仙之路！")
        print(f"  灵根: {spiritual_root['name']}")
        print(f"  当前境界: {player.realm_name}")
        print_divider()
        input("\n  按回车键继续...")
        
        return player
    
    def load_game(self) -> Optional[Player]:
        """加载游戏存档
        
        Returns:
            Optional[Player]: 加载的玩家对象，如果取消则返回None
        """
        clear_screen()
        print("\n")
        print_divider()
        print("                    【 读取存档 】")
        print_divider()
        
        saves = Player.list_saves()
        
        if not saves:
            print("\n  没有找到任何存档！")
            input("\n  按回车键返回...")
            return None
        
        print()
        for i, save_path in enumerate(saves, 1):
            filename = os.path.basename(save_path)
            print(f"    {i}. {filename}")
        print(f"    0. 返回主菜单")
        print()
        
        while True:
            choice = input(f"  请选择 (0-{len(saves)}): ").strip()
            if choice == '0':
                return None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(saves):
                    try:
                        player = Player.load(saves[idx])
                        print(f"\n  成功加载存档：{player.name}")
                        input("\n  按回车键继续...")
                        return player
                    except Exception as e:
                        print(f"\n  加载失败：{e}")
            print("  无效的选择！")
    
    def settings_menu(self):
        """设置菜单"""
        while True:
            clear_screen()
            print("\n")
            print_divider()
            print("                    【 游戏设置 】")
            print_divider()
            print()
            print(f"    1. 打字机效果: {'开启' if self.use_slow_print else '关闭'}")
            print("    0. 返回主菜单")
            print()
            
            choice = input("  请选择: ").strip()
            
            if choice == '1':
                self.use_slow_print = not self.use_slow_print
            elif choice == '0':
                break
    
    def display_story(self, story: str):
        """显示故事内容"""
        print()
        print_divider("─")
        if self.use_slow_print:
            print_slowly(story, delay=0.01)
        else:
            print(story)
        print_divider("─")
    
    def display_options(self, options: List[str]) -> int:
        """显示选项并获取玩家选择
        
        Returns:
            int: 选择的选项索引（从0开始）
        """
        print("\n  【 请做出你的选择 】\n")
        for i, option in enumerate(options, 1):
            print(f"    {i}. {option}")
        print()
        print("    S. 保存游戏")
        print("    Q. 退出到主菜单")
        print()
        
        while True:
            choice = input("  你的选择: ").strip().upper()
            
            if choice == 'S':
                self.save_game()
                continue
            elif choice == 'Q':
                return -1  # 退出信号
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return idx
            
            print("  无效的选择，请重新输入。")
    
    def save_game(self):
        """保存游戏"""
        if self.player:
            filepath = self.player.save()
            print(f"\n  游戏已保存到: {filepath}")
            input("  按回车键继续...")
    
    def apply_effects(self, effects: Dict):
        """应用故事效果到玩家"""
        if not self.player or not effects:
            return
        
        messages = []
        
        # 修为变化
        if effects.get("cultivation_change", 0) != 0:
            change = effects["cultivation_change"]
            if change > 0:
                result = self.player.add_cultivation(change)
                messages.append(f"  【修为 +{change}】")
                if result["breakthrough"]:
                    messages.append(f"  ★★★ 恭喜突破至【{result['new_realm']}】！★★★")
                    # 生成突破故事
                    breakthrough_story = self.storyteller.generate_breakthrough_story(
                        self._get_player_info(),
                        result['new_realm']
                    )
                    print("\n")
                    self.display_story(breakthrough_story)
            else:
                self.player.lose_cultivation(abs(change))
                messages.append(f"  【修为 {change}】")
        
        # 生命变化
        if effects.get("hp_change", 0) != 0:
            change = effects["hp_change"]
            if change > 0:
                actual = self.player.heal(change)
                messages.append(f"  【生命 +{actual}】")
            else:
                is_dead = self.player.take_damage(abs(change))
                messages.append(f"  【生命 {change}】")
                if is_dead:
                    self.handle_death("在历险中不幸陨落")
                    return
        
        # 灵力变化
        if effects.get("mp_change", 0) != 0:
            change = effects["mp_change"]
            if change > 0:
                actual = self.player.restore_mp(change)
                messages.append(f"  【灵力 +{actual}】")
            else:
                self.player.use_mp(abs(change))
                messages.append(f"  【灵力 {change}】")
        
        # 获得物品
        for item_name in effects.get("items", []):
            self.player.add_item({"name": item_name, "type": "misc"})
            messages.append(f"  【获得物品: {item_name}】")
        
        # 显示所有变化
        if messages:
            print()
            print_divider("·", 40)
            for msg in messages:
                print(msg)
            print_divider("·", 40)
    
    def handle_death(self, cause: str):
        """处理玩家死亡"""
        death_story = self.storyteller.generate_death_story(
            self._get_player_info(),
            cause
        )
        clear_screen()
        print("\n")
        print_divider("═")
        print("                    【 道陨身消 】")
        print_divider("═")
        print()
        if self.use_slow_print:
            print_slowly(death_story, delay=0.03)
        else:
            print(death_story)
        print()
        print_divider("═")
        input("\n  按回车键返回主菜单...")
        self.game_running = False
    
    def _get_player_info(self) -> Dict:
        """获取玩家信息字典"""
        if not self.player:
            return {}
        return {
            "name": self.player.name,
            "gender": self.player.gender,
            "spiritual_root": self.player.spiritual_root["name"],
            "realm": self.player.realm_name,
            "cultivation_progress": self.player.cultivation_progress,
            "hp": self.player.hp,
            "max_hp": self.player.max_hp,
            "mp": self.player.mp,
            "max_mp": self.player.max_mp,
        }
    
    def game_loop(self):
        """游戏主循环"""
        self.game_running = True
        
        # 如果是新游戏，生成背景故事
        if not self.player.story_history:
            clear_screen()
            print("\n  正在生成你的修仙故事...")
            print("  （首次生成可能需要一些时间，请稍候...）\n")
            
            story, options = self.storyteller.generate_background_story(
                self._get_player_info()
            )
            self.current_story = story
            self.current_options = options
            self.player.add_story(story)
        else:
            # 加载存档，使用最后的故事
            self.current_story = self.player.get_recent_story(1)
            self.current_options = ["继续探索", "原地修炼", "查看周围环境"]
        
        while self.game_running:
            clear_screen()
            
            # 显示玩家状态
            print(self.player.get_status_display())
            
            # 显示当前故事
            self.display_story(self.current_story)
            
            # 显示选项并获取选择
            choice_idx = self.display_options(self.current_options)
            
            if choice_idx == -1:  # 退出
                self.game_running = False
                break
            
            # 获取玩家选择
            player_choice = self.current_options[choice_idx]
            self.player.choices_made += 1
            
            # 生成续写故事
            clear_screen()
            print("\n  命运的齿轮开始转动...")
            print("  （正在生成故事...）\n")
            
            story, options, effects = self.storyteller.continue_story(
                self._get_player_info(),
                player_choice,
                self.player.get_recent_story(3)
            )
            
            # 应用效果
            self.apply_effects(effects)
            
            # 更新当前故事
            self.current_story = story
            self.current_options = options
            self.player.add_story(story)
    
    def run(self):
        """运行游戏"""
        while True:
            self.print_title()
            choice = self.main_menu()
            
            if choice == '1':  # 新游戏
                self.player = self.create_character()
                self.storyteller.reset_conversation()
                self.game_loop()
                
            elif choice == '2':  # 继续游戏
                player = self.load_game()
                if player:
                    self.player = player
                    self.game_loop()
                    
            elif choice == '3':  # 设置
                self.settings_menu()
                
            elif choice == '4':  # 退出
                clear_screen()
                print("\n")
                print_divider()
                print("          感谢游玩《仙途问道》，愿道友仙途顺遂！")
                print_divider()
                print()
                break
