#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直播版游戏界面 - 支持弹幕投票和礼物互动
使用 Gradio 创建 Web 界面
"""

import os
import sys
import time
import threading
from typing import Optional, List, Dict, Tuple
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import gradio as gr
except ImportError:
    print("请先安装 gradio: pip install gradio")
    sys.exit(1)

from PIL import Image
from config import (
    GAME_TITLE, GAME_VERSION, SPIRITUAL_ROOTS,
    IMAGE_SAVE_DIRECTORY, LIVE_VOTE_DURATION,
    BILIBILI_ROOM_ID, DOUYIN_ROOM_ID,
)
from player import Player
from ai_storyteller import AIStoryteller, MockStoryteller
from image_generator import ImageGenerator, MockImageGenerator, create_prompt_from_story
from danmaku_listener import (
    BilibiliDanmakuListener, DouyinDanmakuListener, MockDanmakuListener,
    VoteManager, DanmakuMessage, GiftMessage, BILIBILI_AVAILABLE
)
from gift_system import GiftProcessor, GiftEffect
from leaderboard import Leaderboard, LeaderboardType


class LiveGame:
    """直播版游戏"""
    
    def __init__(self, 
                 use_mock_ai: bool = False, 
                 use_mock_sd: bool = False,
                 use_mock_danmaku: bool = False,
                 bilibili_room: int = None,
                 douyin_room: str = None):
        
        self.use_mock_ai = use_mock_ai
        self.use_mock_sd = use_mock_sd
        
        # 初始化组件
        self.storyteller = MockStoryteller() if use_mock_ai else AIStoryteller()
        self.image_generator = MockImageGenerator() if use_mock_sd else ImageGenerator()
        self.vote_manager = VoteManager(vote_duration=LIVE_VOTE_DURATION)
        self.gift_processor = GiftProcessor()
        self.leaderboard = Leaderboard()
        
        # 弹幕监听器
        self.danmaku_listeners = []
        self._setup_danmaku_listeners(use_mock_danmaku, bilibili_room, douyin_room)
        
        # 游戏状态
        self.player: Optional[Player] = None
        self.current_story = ""
        self.current_options: List[str] = []
        self.current_image: Optional[Image.Image] = None
        self.image_count = 0
        self.game_state = "menu"  # menu, character_creation, playing, voting
        
        # 投票状态
        self.vote_counts: Dict[str, int] = {}
        self.vote_result: Optional[str] = None
        
        # 弹幕/礼物消息队列（用于显示）
        self.recent_danmakus: List[str] = []
        self.recent_gifts: List[str] = []
        self.effect_messages: List[str] = []
        
        # 自动游戏模式
        self.auto_mode = True
        
        # 注册回调
        self.gift_processor.register_effect_callback(self._on_gift_effect)
    
    def _setup_danmaku_listeners(self, use_mock: bool, bilibili_room: int, douyin_room: str):
        """设置弹幕监听器"""
        if use_mock:
            listener = MockDanmakuListener()
            listener.on_danmaku(self._on_danmaku)
            listener.on_gift(self._on_gift)
            self.danmaku_listeners.append(listener)
        else:
            # B站
            if bilibili_room and BILIBILI_AVAILABLE:
                listener = BilibiliDanmakuListener(bilibili_room)
                listener.on_danmaku(self._on_danmaku)
                listener.on_gift(self._on_gift)
                self.danmaku_listeners.append(listener)
            
            # 抖音（需要额外配置）
            if douyin_room:
                listener = DouyinDanmakuListener(douyin_room)
                listener.on_danmaku(self._on_danmaku)
                listener.on_gift(self._on_gift)
                self.danmaku_listeners.append(listener)
    
    def start_listeners(self):
        """启动所有弹幕监听器"""
        for listener in self.danmaku_listeners:
            listener.start()
    
    def stop_listeners(self):
        """停止所有弹幕监听器"""
        for listener in self.danmaku_listeners:
            listener.stop()
    
    def _on_danmaku(self, msg: DanmakuMessage):
        """处理弹幕"""
        # 添加到最近弹幕
        display = f"[{msg.username}] {msg.content}"
        self.recent_danmakus.append(display)
        if len(self.recent_danmakus) > 50:
            self.recent_danmakus = self.recent_danmakus[-50:]
        
        # 检查是否是投票
        if self.vote_manager.is_voting():
            result = self.vote_manager.process_danmaku(msg)
            if result:
                self.vote_counts = self.vote_manager.get_vote_counts()
        
        # 检查是否是改名弹幕
        if self.gift_processor.has_pending_rename():
            rename_info = self.gift_processor.pending_rename
            if msg.user_id == rename_info["user_id"]:
                # 检查是否是改名指令
                if msg.content.startswith("改名") or msg.content.startswith("赐名"):
                    new_name = msg.content.replace("改名", "").replace("赐名", "").strip()
                    if new_name and self.player:
                        old_name = self.player.name
                        self.player.name = new_name
                        self.effect_messages.append(f"🎭 {rename_info['donor']} 将主角改名为【{new_name}】")
                        self.leaderboard.add_history_event(
                            "rename",
                            f"{rename_info['donor']} 将主角从 {old_name} 改名为 {new_name}",
                            {"old_name": old_name, "new_name": new_name}
                        )
                        self.gift_processor.pending_rename = None
    
    def _on_gift(self, msg: GiftMessage):
        """处理礼物"""
        # 添加到最近礼物
        display = f"🎁 {msg.username} 赠送 {msg.gift_name}x{msg.gift_count}"
        self.recent_gifts.append(display)
        if len(self.recent_gifts) > 30:
            self.recent_gifts = self.recent_gifts[-30:]
        
        # 处理礼物效果
        effect = self.gift_processor.process_gift(msg)
        
        # 更新排行榜
        self.leaderboard.update_contribution(
            msg.user_id, msg.username, msg.platform,
            msg.gift_value * msg.gift_count, msg.gift_name
        )
    
    def _on_gift_effect(self, effect: GiftEffect, gift: GiftMessage):
        """礼物效果回调"""
        self.effect_messages.append(f"✨ {gift.username}: {effect.description}")
        
        # 记录历史
        self.leaderboard.add_history_event(
            "gift_effect",
            f"{gift.username} 触发 {effect.name}",
            {"effect": effect.name, "gift": gift.gift_name}
        )
    
    def create_character(self, name: str, gender: str, spiritual_root_idx: int) -> Dict:
        """创建角色"""
        if not name.strip():
            return {"error": "请输入道号！"}
        
        spiritual_root = SPIRITUAL_ROOTS[spiritual_root_idx]
        gender_text = "他" if gender == "男" else "她"
        
        self.player = Player(
            name=name.strip(),
            gender=gender_text,
            spiritual_root=spiritual_root
        )
        self.storyteller.reset_conversation()
        self.game_state = "playing"
        
        # 更新排行榜
        self.leaderboard.update_game_stats(
            character_name=name.strip(),
            character_realm=self.player.realm_name,
        )
        
        # 生成背景故事
        return self._generate_story(is_new=True)
    
    def _generate_story(self, is_new: bool = False, choice_idx: int = None) -> Dict:
        """生成故事"""
        player_info = self._get_player_info()
        char_info = {
            "gender": self.player.gender,
            "spiritual_root": self.player.spiritual_root,
            "realm": self.player.realm_name,
        }
        
        if is_new:
            story, options = self.storyteller.generate_background_story(player_info)
            self.leaderboard.update_game_stats(total_stories=1)
        else:
            if choice_idx is not None and choice_idx < len(self.current_options):
                player_choice = self.current_options[choice_idx]
            else:
                player_choice = self.current_options[0] if self.current_options else "继续"
            
            story, options, effects = self.storyteller.continue_story(
                player_info,
                player_choice,
                self.player.get_recent_story(3)
            )
            
            # 应用效果
            self._apply_effects(effects)
            self.leaderboard.update_game_stats(total_stories=1, total_choices=1)
        
        # 应用待处理的礼物效果
        pending_effects = self.gift_processor.get_pending_effects()
        if pending_effects and self.player:
            messages = self.gift_processor.apply_effects_to_player(self.player, pending_effects)
            self.effect_messages.extend(messages)
        
        # 生成图片
        image_prompt = create_prompt_from_story(story, char_info)
        image = self.image_generator.generate_image(image_prompt)
        if image is None:
            image = self._create_placeholder_image()
        
        self.current_story = story
        self.current_options = options
        self.current_image = image
        self.player.add_story(story)
        
        # 保存图片
        self._save_image(image)
        
        # 更新排行榜统计
        self.leaderboard.update_game_stats(
            character_realm=self.player.realm_name,
            character_cultivation=self.player.cultivation_progress,
        )
        
        return {
            "story": story,
            "options": options,
            "image": image,
            "status": self._get_status_text(),
        }
    
    def start_vote(self) -> int:
        """开始投票"""
        if not self.current_options:
            return 0
        
        self.game_state = "voting"
        self.vote_counts = {}
        
        duration = self.vote_manager.start_vote(
            self.current_options,
            callback=self._on_vote_end
        )
        
        return duration
    
    def _on_vote_end(self, winner: str, counts: Dict):
        """投票结束回调"""
        self.vote_result = winner
        self.vote_counts = counts
        self.game_state = "playing"
        
        # 更新参与者排行榜
        for option_key, voters in self.vote_manager.votes.items():
            for user_id, username in voters.items():
                # 简单处理platform（实际应从投票记录中获取）
                self.leaderboard.update_vote_participation(
                    user_id, username, "unknown", option_key, winner
                )
        
        # 更新统计
        total_votes = sum(counts.values())
        self.leaderboard.update_game_stats(total_votes=total_votes)
        
        # 记录历史
        self.leaderboard.add_history_event(
            "vote_end",
            f"投票结束，选项{winner}获胜 ({counts})",
            {"winner": winner, "counts": counts}
        )
    
    def get_vote_status(self) -> Dict:
        """获取投票状态"""
        return {
            "is_voting": self.vote_manager.is_voting(),
            "remaining_time": self.vote_manager.get_remaining_time(),
            "counts": self.vote_manager.get_vote_counts(),
            "options": self.current_options,
        }
    
    def process_vote_result(self) -> Dict:
        """处理投票结果，生成新故事"""
        if self.vote_result:
            choice_idx = int(self.vote_result) - 1
            self.vote_result = None
            return self._generate_story(choice_idx=choice_idx)
        return {}
    
    def _apply_effects(self, effects: dict):
        """应用故事效果"""
        if not self.player or not effects:
            return
        
        if effects.get("cultivation_change", 0) != 0:
            change = effects["cultivation_change"]
            if change > 0:
                result = self.player.add_cultivation(change)
                if result.get("breakthrough"):
                    self.effect_messages.append(f"⬆️ 突破至【{result['new_realm']}】！")
                    self.leaderboard.update_game_stats(breakthroughs=1)
            else:
                self.player.lose_cultivation(abs(change))
        
        if effects.get("hp_change", 0) != 0:
            change = effects["hp_change"]
            if change > 0:
                self.player.heal(change)
            else:
                is_dead = self.player.take_damage(abs(change))
                if is_dead:
                    self.effect_messages.append("💀 角色陨落...")
                    self.leaderboard.update_game_stats(deaths=1)
        
        if effects.get("mp_change", 0) != 0:
            change = effects["mp_change"]
            if change > 0:
                self.player.restore_mp(change)
            else:
                self.player.use_mp(abs(change))
        
        for item_name in effects.get("items", []):
            self.player.add_item({"name": item_name, "type": "misc"})
            self.effect_messages.append(f"📦 获得物品: {item_name}")
    
    def _get_player_info(self) -> dict:
        """获取玩家信息"""
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
    
    def _get_status_text(self) -> str:
        """获取状态文本"""
        if not self.player:
            return ""
        
        hp_bar = self._create_bar(self.player.hp, self.player.max_hp, 15)
        mp_bar = self._create_bar(self.player.mp, self.player.max_mp, 15)
        cult_bar = self._create_bar(self.player.cultivation_progress, 100, 15)
        
        return f"""【{self.player.name}】{self.player.spiritual_root['name']}
境界: {self.player.realm_name}
━━━━━━━━━━━━━━━━━━━━
生命 {hp_bar} {self.player.hp}/{self.player.max_hp}
灵力 {mp_bar} {self.player.mp}/{self.player.max_mp}
修为 {cult_bar} {self.player.cultivation_progress}%"""
    
    def _create_bar(self, current: int, maximum: int, length: int) -> str:
        filled = int((current / maximum) * length) if maximum > 0 else 0
        return f"[{'█' * filled}{'░' * (length - filled)}]"
    
    def _create_placeholder_image(self) -> Image.Image:
        width, height = 576, 400
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        for y in range(height):
            for x in range(width):
                r = int(26 + (y / height) * 30)
                g = int(26 + (y / height) * 20)
                b = int(46 + (y / height) * 50)
                pixels[x, y] = (r, g, b)
        return image
    
    def _save_image(self, image: Image.Image):
        if image is None:
            return
        if not os.path.exists(IMAGE_SAVE_DIRECTORY):
            os.makedirs(IMAGE_SAVE_DIRECTORY)
        self.image_count += 1
        save_path = os.path.join(IMAGE_SAVE_DIRECTORY, f"live_{self.image_count:04d}.png")
        image.save(save_path)
    
    def get_danmaku_display(self) -> str:
        """获取弹幕显示文本"""
        return "\n".join(self.recent_danmakus[-15:]) if self.recent_danmakus else "等待弹幕..."
    
    def get_gift_display(self) -> str:
        """获取礼物显示文本"""
        return "\n".join(self.recent_gifts[-10:]) if self.recent_gifts else "等待礼物..."
    
    def get_effect_display(self) -> str:
        """获取效果显示文本"""
        messages = self.effect_messages[-10:]
        self.effect_messages = self.effect_messages[-10:]  # 保留最近10条
        return "\n".join(messages) if messages else ""
    
    def get_contribution_board(self) -> str:
        """获取贡献榜"""
        return self.leaderboard.get_formatted_leaderboard(LeaderboardType.CONTRIBUTION, 10)
    
    def get_participation_board(self) -> str:
        """获取参与榜"""
        return self.leaderboard.get_formatted_leaderboard(LeaderboardType.VOTE_PARTICIPATION, 10)
    
    def get_stats_summary(self) -> str:
        """获取统计摘要"""
        return self.leaderboard.get_stats_summary()


def create_live_interface(game: LiveGame):
    """创建直播版 Gradio 界面"""
    
    spiritual_root_choices = [
        f"{r['name']} ({', '.join([f'{k}+{v}' for k, v in r['bonus'].items()])})"
        for r in SPIRITUAL_ROOTS
    ]
    
    with gr.Blocks(
        title=f"{GAME_TITLE} - 直播版",
        theme=gr.themes.Soft(primary_hue="purple", secondary_hue="blue"),
        css="""
        .story-text { font-size: 16px; line-height: 1.8; }
        .status-text { font-family: monospace; font-size: 12px; }
        .danmaku-box { font-size: 12px; height: 200px; overflow-y: auto; }
        .vote-btn { font-size: 18px; padding: 15px; }
        """
    ) as interface:
        
        gr.Markdown(f"# 🎮 《{GAME_TITLE}》直播互动版")
        gr.Markdown("*弹幕投票 | 礼物加成 | 实时互动*")
        
        with gr.Row():
            # 左侧：游戏主界面
            with gr.Column(scale=2):
                with gr.Tabs() as tabs:
                    # 创建角色
                    with gr.TabItem("📝 创建角色", id=0):
                        name_input = gr.Textbox(label="道号", value="云逸")
                        gender_input = gr.Radio(["男", "女"], label="性别", value="男")
                        root_input = gr.Dropdown(
                            spiritual_root_choices, label="灵根",
                            value=spiritual_root_choices[0], type="index"
                        )
                        create_btn = gr.Button("🎮 开始直播游戏", variant="primary")
                    
                    # 游戏界面
                    with gr.TabItem("🎮 游戏", id=1):
                        scene_image = gr.Image(label="场景", type="pil", height=350)
                        status_text = gr.Textbox(
                            label="角色状态", lines=6, interactive=False,
                            elem_classes=["status-text"]
                        )
                        story_text = gr.Textbox(
                            label="故事", lines=8, interactive=False,
                            elem_classes=["story-text"]
                        )
                        
                        # 投票区域
                        gr.Markdown("### 🗳️ 弹幕投票")
                        with gr.Row():
                            vote_info = gr.Textbox(
                                label="投票状态", interactive=False, scale=2
                            )
                            start_vote_btn = gr.Button("开始投票", variant="primary")
                        
                        with gr.Row():
                            opt1_btn = gr.Button("1.", visible=False, elem_classes=["vote-btn"])
                            opt2_btn = gr.Button("2.", visible=False, elem_classes=["vote-btn"])
                        with gr.Row():
                            opt3_btn = gr.Button("3.", visible=False, elem_classes=["vote-btn"])
                            opt4_btn = gr.Button("4.", visible=False, elem_classes=["vote-btn"])
                        
                        effect_text = gr.Textbox(label="✨ 效果提示", lines=3, interactive=False)
            
            # 右侧：互动面板
            with gr.Column(scale=1):
                gr.Markdown("### 💬 弹幕")
                danmaku_text = gr.Textbox(
                    label="", lines=10, interactive=False,
                    elem_classes=["danmaku-box"]
                )
                
                gr.Markdown("### 🎁 礼物")
                gift_text = gr.Textbox(
                    label="", lines=5, interactive=False
                )
                
                gr.Markdown("### 🏆 排行榜")
                with gr.Tabs():
                    with gr.TabItem("贡献榜"):
                        contribution_text = gr.Textbox(
                            label="", lines=12, interactive=False,
                            elem_classes=["status-text"]
                        )
                    with gr.TabItem("参与榜"):
                        participation_text = gr.Textbox(
                            label="", lines=12, interactive=False,
                            elem_classes=["status-text"]
                        )
                    with gr.TabItem("统计"):
                        stats_text = gr.Textbox(
                            label="", lines=12, interactive=False,
                            elem_classes=["status-text"]
                        )
        
        # 状态存储
        options_state = gr.State([])
        
        def on_create(name, gender, root_idx):
            result = game.create_character(name, gender, root_idx)
            if "error" in result:
                return [result["error"], "", None, "", gr.update()] + [gr.update()] * 4 + [[]]
            
            opts = result["options"]
            btn_updates = [
                gr.update(value=f"1. {opts[0]}" if len(opts) > 0 else "", visible=len(opts) > 0),
                gr.update(value=f"2. {opts[1]}" if len(opts) > 1 else "", visible=len(opts) > 1),
                gr.update(value=f"3. {opts[2]}" if len(opts) > 2 else "", visible=len(opts) > 2),
                gr.update(value=f"4. {opts[3]}" if len(opts) > 3 else "", visible=len(opts) > 3),
            ]
            
            return [
                result["story"],
                result["status"],
                result["image"],
                "等待开始投票...",
                gr.update(selected=1),
            ] + btn_updates + [opts]
        
        def on_start_vote():
            duration = game.start_vote()
            return f"投票进行中... 剩余 {duration} 秒\n发送弹幕 1/2/3/4 投票"
        
        def update_vote_display():
            """更新投票显示"""
            status = game.get_vote_status()
            if status["is_voting"]:
                counts = status["counts"]
                opts = status["options"]
                lines = [f"⏱️ 剩余 {status['remaining_time']} 秒"]
                for i, opt in enumerate(opts):
                    key = str(i + 1)
                    count = counts.get(key, 0)
                    lines.append(f"  {key}. {opt}: {count} 票")
                return "\n".join(lines)
            elif game.vote_result:
                # 投票结束，处理结果
                result = game.process_vote_result()
                if result:
                    return f"投票结束！选项 {game.vote_counts} 获胜"
            return "等待开始投票..."
        
        def refresh_ui():
            """刷新UI"""
            vote_status = update_vote_display()
            
            # 如果有新故事
            story = game.current_story
            status = game._get_status_text()
            image = game.current_image
            opts = game.current_options
            
            btn_updates = [
                gr.update(value=f"1. {opts[0]}" if len(opts) > 0 else "", visible=len(opts) > 0),
                gr.update(value=f"2. {opts[1]}" if len(opts) > 1 else "", visible=len(opts) > 1),
                gr.update(value=f"3. {opts[2]}" if len(opts) > 2 else "", visible=len(opts) > 2),
                gr.update(value=f"4. {opts[3]}" if len(opts) > 3 else "", visible=len(opts) > 3),
            ]
            
            return [
                story,
                status,
                image,
                vote_status,
                game.get_effect_display(),
                game.get_danmaku_display(),
                game.get_gift_display(),
                game.get_contribution_board(),
                game.get_participation_board(),
                game.get_stats_summary(),
            ] + btn_updates + [opts]
        
        # 绑定事件
        create_btn.click(
            on_create,
            inputs=[name_input, gender_input, root_input],
            outputs=[
                story_text, status_text, scene_image, vote_info, tabs,
                opt1_btn, opt2_btn, opt3_btn, opt4_btn, options_state
            ]
        )
        
        start_vote_btn.click(on_start_vote, outputs=[vote_info])
        
        # 定时刷新
        refresh_outputs = [
            story_text, status_text, scene_image, vote_info, effect_text,
            danmaku_text, gift_text, contribution_text, participation_text, stats_text,
            opt1_btn, opt2_btn, opt3_btn, opt4_btn, options_state
        ]
        
        # 使用定时器刷新
        interface.load(refresh_ui, outputs=refresh_outputs, every=2)
    
    return interface


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description=f"《{GAME_TITLE}》直播版")
    parser.add_argument("--mock-ai", action="store_true", help="使用模拟AI")
    parser.add_argument("--mock-sd", action="store_true", help="使用模拟图片")
    parser.add_argument("--mock-danmaku", action="store_true", help="使用模拟弹幕")
    parser.add_argument("--bilibili", type=int, help="B站房间号")
    parser.add_argument("--douyin", type=str, help="抖音房间号")
    parser.add_argument("--port", type=int, default=7862, help="端口号")
    parser.add_argument("--share", action="store_true", help="创建公开链接")
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"《{GAME_TITLE}》直播互动版")
    print("=" * 50)
    
    # 检查SD连接
    use_mock_sd = args.mock_sd
    if not use_mock_sd:
        from image_generator import ImageGenerator
        test_gen = ImageGenerator()
        if not test_gen.check_connection():
            print("警告：无法连接到 SD，将使用模拟图片")
            use_mock_sd = True
    
    # 获取房间号
    bilibili_room = args.bilibili or BILIBILI_ROOM_ID
    douyin_room = args.douyin or DOUYIN_ROOM_ID
    
    # 创建游戏
    game = LiveGame(
        use_mock_ai=args.mock_ai,
        use_mock_sd=use_mock_sd,
        use_mock_danmaku=args.mock_danmaku,
        bilibili_room=bilibili_room,
        douyin_room=douyin_room,
    )
    
    # 启动弹幕监听
    game.start_listeners()
    
    print(f"\n启动 Web 服务器，端口: {args.port}")
    print(f"请在浏览器中打开: http://localhost:{args.port}")
    
    if bilibili_room:
        print(f"B站房间号: {bilibili_room}")
    if douyin_room:
        print(f"抖音房间号: {douyin_room}")
    
    # 创建界面
    interface = create_live_interface(game)
    
    try:
        interface.launch(
            server_port=args.port,
            share=args.share,
            inbrowser=True,
        )
    finally:
        game.stop_listeners()


if __name__ == "__main__":
    main()
