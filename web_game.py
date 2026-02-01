#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web版游戏界面 - 使用 Gradio 创建 Web 界面
避免 tkinter 在虚拟环境中的问题
"""

import os
import sys
import io
import base64
from typing import Optional, List, Tuple

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import gradio as gr
except ImportError:
    print("请先安装 gradio: pip install gradio")
    sys.exit(1)

from PIL import Image
from config import (
    GAME_TITLE, GAME_VERSION, SPIRITUAL_ROOTS,
    SD_WIDTH, SD_HEIGHT, IMAGE_SAVE_DIRECTORY,
)
from player import Player
from ai_storyteller import AIStoryteller, MockStoryteller
from image_generator import ImageGenerator, MockImageGenerator, create_prompt_from_story


class WebGame:
    """Web版游戏"""
    
    def __init__(self, use_mock_ai: bool = False, use_mock_sd: bool = False):
        self.use_mock_ai = use_mock_ai
        self.use_mock_sd = use_mock_sd
        
        self.storyteller = MockStoryteller() if use_mock_ai else AIStoryteller()
        self.image_generator = MockImageGenerator() if use_mock_sd else ImageGenerator()
        
        self.player: Optional[Player] = None
        self.current_story = ""
        self.current_options: List[str] = []
        self.current_image: Optional[Image.Image] = None
        self.image_count = 0
        self.game_state = "menu"  # menu, playing
    
    def create_character(self, name: str, gender: str, spiritual_root_idx: int) -> Tuple[str, str, Image.Image, str, str, str, str]:
        """创建角色"""
        if not name.strip():
            return ("请输入道号！", "", self._create_placeholder_image(), 
                    "", "", "", "")
        
        spiritual_root = SPIRITUAL_ROOTS[spiritual_root_idx]
        gender_text = "他" if gender == "男" else "她"
        
        self.player = Player(
            name=name.strip(),
            gender=gender_text,
            spiritual_root=spiritual_root
        )
        self.storyteller.reset_conversation()
        self.game_state = "playing"
        
        # 生成背景故事
        player_info = self._get_player_info()
        story, options = self.storyteller.generate_background_story(player_info)
        
        # 获取角色信息用于图片生成
        char_info = {
            "gender": self.player.gender,
            "spiritual_root": self.player.spiritual_root,
            "realm": self.player.realm_name,
        }
        
        # 生成图片（包含主角）
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
        
        return (
            story,
            self._get_status_text(),
            image,
            options[0] if len(options) > 0 else "",
            options[1] if len(options) > 1 else "",
            options[2] if len(options) > 2 else "",
            options[3] if len(options) > 3 else "",
        )
    
    def make_choice(self, choice_idx: int) -> Tuple[str, str, Image.Image, str, str, str, str]:
        """做出选择"""
        if not self.player or choice_idx < 0 or choice_idx >= len(self.current_options):
            return (self.current_story, self._get_status_text(), 
                    self.current_image or self._create_placeholder_image(),
                    "", "", "", "")
        
        player_choice = self.current_options[choice_idx]
        self.player.choices_made += 1
        
        # 生成续写故事
        player_info = self._get_player_info()
        story, options, effects = self.storyteller.continue_story(
            player_info,
            player_choice,
            self.player.get_recent_story(3)
        )
        
        # 应用效果
        self._apply_effects(effects)
        
        # 获取角色信息用于图片生成
        char_info = {
            "gender": self.player.gender,
            "spiritual_root": self.player.spiritual_root,
            "realm": self.player.realm_name,
        }
        
        # 生成图片（包含主角）
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
        
        return (
            story,
            self._get_status_text(),
            image,
            options[0] if len(options) > 0 else "",
            options[1] if len(options) > 1 else "",
            options[2] if len(options) > 2 else "",
            options[3] if len(options) > 3 else "",
        )
    
    def save_game(self) -> str:
        """保存游戏"""
        if not self.player:
            return "没有可保存的游戏！"
        try:
            filepath = self.player.save()
            return f"游戏已保存到：{filepath}"
        except Exception as e:
            return f"保存失败：{e}"
    
    def load_game(self, save_file: str) -> Tuple[str, str, Image.Image, str, str, str, str]:
        """加载游戏"""
        if not save_file:
            return ("请选择存档文件！", "", self._create_placeholder_image(),
                    "", "", "", "")
        
        try:
            self.player = Player.load(save_file)
            self.game_state = "playing"
            
            story = self.player.get_recent_story(1)
            self.current_story = story
            self.current_options = ["继续探索", "原地修炼", "查看周围环境"]
            
            return (
                story,
                self._get_status_text(),
                self._create_placeholder_image(),
                self.current_options[0],
                self.current_options[1],
                self.current_options[2],
                "",
            )
        except Exception as e:
            return (f"加载失败：{e}", "", self._create_placeholder_image(),
                    "", "", "", "")
    
    def get_saves(self) -> List[str]:
        """获取存档列表"""
        return Player.list_saves()
    
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
        
        hp_bar = self._create_bar(self.player.hp, self.player.max_hp, 20)
        mp_bar = self._create_bar(self.player.mp, self.player.max_mp, 20)
        cult_bar = self._create_bar(self.player.cultivation_progress, 100, 20)
        
        return f"""【{self.player.name}】{self.player.spiritual_root['name']} · {self.player.realm_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
生命 {hp_bar} {self.player.hp}/{self.player.max_hp}
灵力 {mp_bar} {self.player.mp}/{self.player.max_mp}
修为 {cult_bar} {self.player.cultivation_progress}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def _create_bar(self, current: int, maximum: int, length: int) -> str:
        """创建进度条"""
        filled = int((current / maximum) * length) if maximum > 0 else 0
        empty = length - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    def _apply_effects(self, effects: dict):
        """应用效果"""
        if not self.player or not effects:
            return
        
        if effects.get("cultivation_change", 0) != 0:
            change = effects["cultivation_change"]
            if change > 0:
                self.player.add_cultivation(change)
            else:
                self.player.lose_cultivation(abs(change))
        
        if effects.get("hp_change", 0) != 0:
            change = effects["hp_change"]
            if change > 0:
                self.player.heal(change)
            else:
                self.player.take_damage(abs(change))
        
        if effects.get("mp_change", 0) != 0:
            change = effects["mp_change"]
            if change > 0:
                self.player.restore_mp(change)
            else:
                self.player.use_mp(abs(change))
        
        for item_name in effects.get("items", []):
            self.player.add_item({"name": item_name, "type": "misc"})
    
    def _create_placeholder_image(self) -> Image.Image:
        """创建占位图"""
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
        """保存图片"""
        if image is None:
            return
        
        if not os.path.exists(IMAGE_SAVE_DIRECTORY):
            os.makedirs(IMAGE_SAVE_DIRECTORY)
        
        self.image_count += 1
        save_path = os.path.join(IMAGE_SAVE_DIRECTORY, f"scene_{self.image_count:04d}.png")
        image.save(save_path)


def create_interface(game: WebGame):
    """创建 Gradio 界面"""
    
    # 灵根选项
    spiritual_root_choices = [
        f"{r['name']} ({', '.join([f'{k}+{v}' for k, v in r['bonus'].items()])})"
        for r in SPIRITUAL_ROOTS
    ]
    
    with gr.Blocks(
        title=f"{GAME_TITLE}",
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="blue",
        ),
        css="""
        .story-text { font-size: 16px; line-height: 1.8; }
        .status-text { font-family: monospace; font-size: 14px; }
        .option-btn { margin: 5px 0; }
        """
    ) as interface:
        
        gr.Markdown(f"# 🌟 《{GAME_TITLE}》")
        gr.Markdown("*一款AI驱动的交互式修仙游戏*")
        
        with gr.Tabs() as tabs:
            # 创建角色标签页
            with gr.TabItem("📝 创建角色", id=0):
                with gr.Row():
                    with gr.Column(scale=1):
                        name_input = gr.Textbox(
                            label="道号",
                            placeholder="请输入你的道号...",
                            value="云逸"
                        )
                        gender_input = gr.Radio(
                            choices=["男", "女"],
                            label="性别",
                            value="男"
                        )
                        spiritual_root_input = gr.Dropdown(
                            choices=spiritual_root_choices,
                            label="灵根",
                            value=spiritual_root_choices[0],
                            type="index"
                        )
                        create_btn = gr.Button("🎮 开始修仙", variant="primary")
            
            # 读取存档标签页
            with gr.TabItem("💾 读取存档", id=1):
                save_dropdown = gr.Dropdown(
                    choices=game.get_saves(),
                    label="选择存档",
                    interactive=True
                )
                refresh_btn = gr.Button("🔄 刷新列表")
                load_btn = gr.Button("📂 加载存档", variant="primary")
            
            # 游戏界面标签页
            with gr.TabItem("🎮 游戏", id=2):
                with gr.Row():
                    # 左侧：图片
                    with gr.Column(scale=1):
                        scene_image = gr.Image(
                            label="场景",
                            type="pil",
                            height=400,
                        )
                    
                    # 右侧：状态
                    with gr.Column(scale=1):
                        status_text = gr.Textbox(
                            label="角色状态",
                            lines=8,
                            interactive=False,
                            elem_classes=["status-text"]
                        )
                
                # 故事文本
                story_text = gr.Textbox(
                    label="故事",
                    lines=10,
                    interactive=False,
                    elem_classes=["story-text"]
                )
                
                # 选项按钮
                gr.Markdown("### 📜 做出你的选择")
                with gr.Row():
                    option1_btn = gr.Button("", visible=False, elem_classes=["option-btn"])
                    option2_btn = gr.Button("", visible=False, elem_classes=["option-btn"])
                with gr.Row():
                    option3_btn = gr.Button("", visible=False, elem_classes=["option-btn"])
                    option4_btn = gr.Button("", visible=False, elem_classes=["option-btn"])
                
                # 保存按钮
                with gr.Row():
                    save_btn = gr.Button("💾 保存游戏")
                    save_status = gr.Textbox(label="", interactive=False, scale=3)
        
        # 用于存储选项文本
        option1_text = gr.State("")
        option2_text = gr.State("")
        option3_text = gr.State("")
        option4_text = gr.State("")
        
        def update_options(opt1, opt2, opt3, opt4):
            """更新选项按钮"""
            return (
                gr.update(value=f"1. {opt1}" if opt1 else "", visible=bool(opt1)),
                gr.update(value=f"2. {opt2}" if opt2 else "", visible=bool(opt2)),
                gr.update(value=f"3. {opt3}" if opt3 else "", visible=bool(opt3)),
                gr.update(value=f"4. {opt4}" if opt4 else "", visible=bool(opt4)),
                opt1, opt2, opt3, opt4
            )
        
        def on_create(name, gender, root_idx):
            result = game.create_character(name, gender, root_idx)
            story, status, image, opt1, opt2, opt3, opt4 = result
            btn_updates = update_options(opt1, opt2, opt3, opt4)
            return [story, status, image] + list(btn_updates) + [gr.update(selected=2)]
        
        def on_choice(choice_idx):
            def handler():
                result = game.make_choice(choice_idx)
                story, status, image, opt1, opt2, opt3, opt4 = result
                btn_updates = update_options(opt1, opt2, opt3, opt4)
                return [story, status, image] + list(btn_updates)
            return handler
        
        def on_load(save_file):
            result = game.load_game(save_file)
            story, status, image, opt1, opt2, opt3, opt4 = result
            btn_updates = update_options(opt1, opt2, opt3, opt4)
            return [story, status, image] + list(btn_updates) + [gr.update(selected=2)]
        
        def on_save():
            return game.save_game()
        
        def on_refresh():
            return gr.update(choices=game.get_saves())
        
        # 绑定事件
        outputs = [
            story_text, status_text, scene_image,
            option1_btn, option2_btn, option3_btn, option4_btn,
            option1_text, option2_text, option3_text, option4_text
        ]
        
        create_btn.click(
            on_create,
            inputs=[name_input, gender_input, spiritual_root_input],
            outputs=outputs + [tabs]
        )
        
        load_btn.click(
            on_load,
            inputs=[save_dropdown],
            outputs=outputs + [tabs]
        )
        
        option1_btn.click(on_choice(0), outputs=outputs)
        option2_btn.click(on_choice(1), outputs=outputs)
        option3_btn.click(on_choice(2), outputs=outputs)
        option4_btn.click(on_choice(3), outputs=outputs)
        
        save_btn.click(on_save, outputs=[save_status])
        refresh_btn.click(on_refresh, outputs=[save_dropdown])
    
    return interface


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description=f"《{GAME_TITLE}》Web版")
    parser.add_argument("--mock-ai", action="store_true", help="使用模拟AI")
    parser.add_argument("--mock-sd", action="store_true", help="使用模拟图片生成")
    parser.add_argument("--port", type=int, default=7861, help="端口号")
    parser.add_argument("--name", type=str, default='0.0.0.0', help="server_name")
    parser.add_argument("--share", action="store_true", help="创建公开链接")
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"《{GAME_TITLE}》Web版")
    print("=" * 50)
    
    # 检查 SD 连接
    use_mock_sd = args.mock_sd
    if not use_mock_sd:
        print("正在检查 Stable Diffusion 连接...")
        test_gen = ImageGenerator()
        if not test_gen.check_connection():
            print("  警告：无法连接到 SD，将使用模拟图片")
            use_mock_sd = True
        else:
            print("  SD 连接成功！")
    
    # 创建游戏实例
    game = WebGame(use_mock_ai=args.mock_ai, use_mock_sd=use_mock_sd)
    
    # 创建并启动界面
    interface = create_interface(game)
    
    print(f"\n启动 Web 服务器，端口: {args.port}")
    print(f"请在浏览器中打开: http://localhost:{args.port}")
    
    interface.launch(
        server_name = args.name,
        server_port=args.port,
        share=args.share,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()
