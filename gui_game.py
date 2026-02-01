"""
GUI游戏界面 - 使用 tkinter 创建手机风格的游戏界面
上方显示图片，下方显示文字和选项
"""

import os
import sys

# 修复虚拟环境中的 Tcl/Tk 路径问题
def fix_tcl_tk_path():
    """修复 Tcl/Tk 库路径问题（尤其是在虚拟环境中）"""
    # 尝试查找 Python 安装目录中的 tcl/tk
    python_path = sys.base_prefix  # 获取 Python 的基础安装路径（非虚拟环境）
    
    # 常见的 tcl/tk 路径
    possible_tcl_paths = [
        os.path.join(python_path, 'tcl', 'tcl8.6'),
        os.path.join(python_path, 'lib', 'tcl8.6'),
        os.path.join(python_path, 'Library', 'lib', 'tcl8.6'),  # Windows conda
        'C:/Users/lcx/AppData/Local/Programs/Python/Python313/tcl/tcl8.6',
    ]
    
    possible_tk_paths = [
        os.path.join(python_path, 'tcl', 'tk8.6'),
        os.path.join(python_path, 'lib', 'tk8.6'),
        os.path.join(python_path, 'Library', 'lib', 'tk8.6'),  # Windows conda
        'C:/Users/lcx/AppData/Local/Programs/Python/Python313/tcl/tk8.6',
    ]
    
    # 查找存在的 tcl 路径
    for tcl_path in possible_tcl_paths:
        if os.path.exists(tcl_path):
            os.environ['TCL_LIBRARY'] = tcl_path
            break
    
    # 查找存在的 tk 路径
    for tk_path in possible_tk_paths:
        if os.path.exists(tk_path):
            os.environ['TK_LIBRARY'] = tk_path
            break

# 在导入 tkinter 之前修复路径
fix_tcl_tk_path()

import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
from typing import Optional, List, Callable
import queue
import time

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GAME_TITLE, GAME_VERSION, SPIRITUAL_ROOTS,
    GUI_WINDOW_WIDTH, GUI_WINDOW_HEIGHT, GUI_IMAGE_HEIGHT,
    GUI_FONT_FAMILY, GUI_FONT_SIZE,
    SD_WIDTH, SD_HEIGHT, IMAGE_SAVE_DIRECTORY,
)
from player import Player
from ai_storyteller import AIStoryteller, MockStoryteller
from image_generator import ImageGenerator, MockImageGenerator, create_prompt_from_story


class GameGUI:
    """游戏图形界面"""
    
    def __init__(self, use_mock_ai: bool = False, use_mock_sd: bool = False):
        self.use_mock_ai = use_mock_ai
        self.use_mock_sd = use_mock_sd
        
        # 初始化组件
        self.player: Optional[Player] = None
        self.storyteller = MockStoryteller() if use_mock_ai else AIStoryteller()
        self.image_generator = MockImageGenerator() if use_mock_sd else ImageGenerator()
        
        # 当前状态
        self.current_story = ""
        self.current_options: List[str] = []
        self.current_image: Optional[ImageTk.PhotoImage] = None
        self.image_count = 0
        
        # 线程相关
        self.task_queue = queue.Queue()
        self.is_generating = False
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(f"{GAME_TITLE} v{GAME_VERSION}")
        self.root.geometry(f"{GUI_WINDOW_WIDTH}x{GUI_WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        
        # 设置样式
        self._setup_styles()
        
        # 创建界面
        self._create_widgets()
        
        # 显示主菜单
        self._show_main_menu()
        
        # 启动任务处理
        self._process_tasks()
    
    def _setup_styles(self):
        """设置界面样式"""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 配色方案 - 仙侠风格
        self.colors = {
            "bg_dark": "#1a1a2e",
            "bg_medium": "#16213e",
            "bg_light": "#0f3460",
            "accent": "#e94560",
            "text": "#eaeaea",
            "text_dim": "#a0a0a0",
            "gold": "#ffd700",
            "hp": "#e74c3c",
            "mp": "#3498db",
            "cultivation": "#9b59b6",
        }
        
        # 按钮样式
        self.style.configure(
            "Game.TButton",
            background=self.colors["bg_light"],
            foreground=self.colors["text"],
            padding=(10, 8),
            font=(GUI_FONT_FAMILY, GUI_FONT_SIZE),
        )
        self.style.map(
            "Game.TButton",
            background=[("active", self.colors["accent"])],
        )
        
        # 选项按钮样式
        self.style.configure(
            "Option.TButton",
            background=self.colors["bg_medium"],
            foreground=self.colors["text"],
            padding=(8, 6),
            font=(GUI_FONT_FAMILY, GUI_FONT_SIZE - 1),
        )
        self.style.map(
            "Option.TButton",
            background=[("active", self.colors["bg_light"])],
        )
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        self.main_frame = tk.Frame(self.root, bg=self.colors["bg_dark"])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图片显示区域
        self.image_frame = tk.Frame(
            self.main_frame,
            bg=self.colors["bg_dark"],
            height=GUI_IMAGE_HEIGHT
        )
        self.image_frame.pack(fill=tk.X, padx=5, pady=5)
        self.image_frame.pack_propagate(False)
        
        self.image_label = tk.Label(
            self.image_frame,
            bg=self.colors["bg_medium"],
            text="画面加载中...",
            fg=self.colors["text_dim"],
            font=(GUI_FONT_FAMILY, 12)
        )
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏区域
        self.status_frame = tk.Frame(self.main_frame, bg=self.colors["bg_dark"])
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 玩家信息标签
        self.player_info_label = tk.Label(
            self.status_frame,
            text="",
            bg=self.colors["bg_dark"],
            fg=self.colors["gold"],
            font=(GUI_FONT_FAMILY, 10, "bold"),
            anchor="w"
        )
        self.player_info_label.pack(fill=tk.X)
        
        # 属性条
        self.bars_frame = tk.Frame(self.status_frame, bg=self.colors["bg_dark"])
        self.bars_frame.pack(fill=tk.X, pady=2)
        
        # HP条
        self.hp_frame = tk.Frame(self.bars_frame, bg=self.colors["bg_dark"])
        self.hp_frame.pack(fill=tk.X)
        self.hp_label = tk.Label(
            self.hp_frame, text="生命", bg=self.colors["bg_dark"],
            fg=self.colors["hp"], font=(GUI_FONT_FAMILY, 9), width=4
        )
        self.hp_label.pack(side=tk.LEFT)
        self.hp_bar = ttk.Progressbar(self.hp_frame, length=200, mode="determinate")
        self.hp_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.hp_text = tk.Label(
            self.hp_frame, text="100/100", bg=self.colors["bg_dark"],
            fg=self.colors["text_dim"], font=(GUI_FONT_FAMILY, 8), width=10
        )
        self.hp_text.pack(side=tk.LEFT)
        
        # MP条
        self.mp_frame = tk.Frame(self.bars_frame, bg=self.colors["bg_dark"])
        self.mp_frame.pack(fill=tk.X)
        self.mp_label = tk.Label(
            self.mp_frame, text="灵力", bg=self.colors["bg_dark"],
            fg=self.colors["mp"], font=(GUI_FONT_FAMILY, 9), width=4
        )
        self.mp_label.pack(side=tk.LEFT)
        self.mp_bar = ttk.Progressbar(self.mp_frame, length=200, mode="determinate")
        self.mp_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.mp_text = tk.Label(
            self.mp_frame, text="50/50", bg=self.colors["bg_dark"],
            fg=self.colors["text_dim"], font=(GUI_FONT_FAMILY, 8), width=10
        )
        self.mp_text.pack(side=tk.LEFT)
        
        # 修为条
        self.cult_frame = tk.Frame(self.bars_frame, bg=self.colors["bg_dark"])
        self.cult_frame.pack(fill=tk.X)
        self.cult_label = tk.Label(
            self.cult_frame, text="修为", bg=self.colors["bg_dark"],
            fg=self.colors["cultivation"], font=(GUI_FONT_FAMILY, 9), width=4
        )
        self.cult_label.pack(side=tk.LEFT)
        self.cult_bar = ttk.Progressbar(self.cult_frame, length=200, mode="determinate")
        self.cult_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.cult_text = tk.Label(
            self.cult_frame, text="0%", bg=self.colors["bg_dark"],
            fg=self.colors["text_dim"], font=(GUI_FONT_FAMILY, 8), width=10
        )
        self.cult_text.pack(side=tk.LEFT)
        
        # 故事文本区域
        self.story_frame = tk.Frame(self.main_frame, bg=self.colors["bg_dark"])
        self.story_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.story_text = scrolledtext.ScrolledText(
            self.story_frame,
            bg=self.colors["bg_medium"],
            fg=self.colors["text"],
            font=(GUI_FONT_FAMILY, GUI_FONT_SIZE),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.story_text.pack(fill=tk.BOTH, expand=True)
        
        # 选项按钮区域
        self.options_frame = tk.Frame(self.main_frame, bg=self.colors["bg_dark"])
        self.options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.option_buttons: List[ttk.Button] = []
        
        # 底部控制区域
        self.control_frame = tk.Frame(self.main_frame, bg=self.colors["bg_dark"])
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.save_btn = ttk.Button(
            self.control_frame, text="保存", style="Game.TButton",
            command=self._save_game
        )
        self.save_btn.pack(side=tk.LEFT, padx=2)
        
        self.menu_btn = ttk.Button(
            self.control_frame, text="菜单", style="Game.TButton",
            command=self._show_main_menu
        )
        self.menu_btn.pack(side=tk.RIGHT, padx=2)
        
        # 加载指示器
        self.loading_label = tk.Label(
            self.control_frame,
            text="",
            bg=self.colors["bg_dark"],
            fg=self.colors["accent"],
            font=(GUI_FONT_FAMILY, 9)
        )
        self.loading_label.pack(side=tk.LEFT, padx=10)
    
    def _show_main_menu(self):
        """显示主菜单"""
        # 隐藏游戏界面
        self.status_frame.pack_forget()
        self.bars_frame.pack_forget()
        
        # 清空选项
        self._clear_options()
        
        # 显示菜单图片/标题
        self._set_story_text(f"""
══════════════════════════════════

         《 {GAME_TITLE} 》
         
      一款AI驱动的修仙文字游戏
      
           版本 {GAME_VERSION}

══════════════════════════════════

    仙路漫漫，道阻且长
    且看你如何在这修仙世界中
    披荆斩棘，问鼎大道

══════════════════════════════════
        """)
        
        # 显示菜单选项
        self._show_options([
            "开始新的修仙之旅",
            "继续修仙 (读取存档)",
            "退出游戏"
        ], self._handle_menu_choice)
        
        # 显示默认图片
        self._show_placeholder_image()
    
    def _handle_menu_choice(self, choice_idx: int):
        """处理菜单选择"""
        if choice_idx == 0:  # 新游戏
            self._show_character_creation()
        elif choice_idx == 1:  # 读档
            self._show_load_game()
        elif choice_idx == 2:  # 退出
            self.root.quit()
    
    def _show_character_creation(self):
        """显示角色创建界面"""
        # 创建角色创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("角色创建")
        dialog.geometry("350x400")
        dialog.configure(bg=self.colors["bg_dark"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry(f"+{self.root.winfo_x() + 25}+{self.root.winfo_y() + 200}")
        
        # 标题
        tk.Label(
            dialog, text="创建你的角色", bg=self.colors["bg_dark"],
            fg=self.colors["gold"], font=(GUI_FONT_FAMILY, 14, "bold")
        ).pack(pady=10)
        
        # 姓名输入
        name_frame = tk.Frame(dialog, bg=self.colors["bg_dark"])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(
            name_frame, text="道号:", bg=self.colors["bg_dark"],
            fg=self.colors["text"], font=(GUI_FONT_FAMILY, 11)
        ).pack(side=tk.LEFT)
        name_entry = tk.Entry(
            name_frame, bg=self.colors["bg_medium"],
            fg=self.colors["text"], font=(GUI_FONT_FAMILY, 11),
            insertbackground=self.colors["text"]
        )
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        name_entry.insert(0, "云逸")
        
        # 性别选择
        gender_frame = tk.Frame(dialog, bg=self.colors["bg_dark"])
        gender_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(
            gender_frame, text="性别:", bg=self.colors["bg_dark"],
            fg=self.colors["text"], font=(GUI_FONT_FAMILY, 11)
        ).pack(side=tk.LEFT)
        gender_var = tk.StringVar(value="他")
        tk.Radiobutton(
            gender_frame, text="男", variable=gender_var, value="他",
            bg=self.colors["bg_dark"], fg=self.colors["text"],
            selectcolor=self.colors["bg_medium"], font=(GUI_FONT_FAMILY, 10)
        ).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(
            gender_frame, text="女", variable=gender_var, value="她",
            bg=self.colors["bg_dark"], fg=self.colors["text"],
            selectcolor=self.colors["bg_medium"], font=(GUI_FONT_FAMILY, 10)
        ).pack(side=tk.LEFT, padx=10)
        
        # 灵根选择
        root_frame = tk.Frame(dialog, bg=self.colors["bg_dark"])
        root_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(
            root_frame, text="灵根:", bg=self.colors["bg_dark"],
            fg=self.colors["text"], font=(GUI_FONT_FAMILY, 11)
        ).pack(anchor=tk.W)
        
        root_var = tk.StringVar()
        root_listbox = tk.Listbox(
            root_frame, bg=self.colors["bg_medium"],
            fg=self.colors["text"], font=(GUI_FONT_FAMILY, 10),
            height=6, selectmode=tk.SINGLE
        )
        root_listbox.pack(fill=tk.X, pady=5)
        
        for root in SPIRITUAL_ROOTS:
            bonus_str = ", ".join([f"{k}+{v}" for k, v in root["bonus"].items()])
            root_listbox.insert(tk.END, f"{root['name']} ({bonus_str})")
        root_listbox.selection_set(0)
        
        def create_character():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入道号！")
                return
            
            gender = gender_var.get()
            root_idx = root_listbox.curselection()
            root_idx = root_idx[0] if root_idx else 0
            spiritual_root = SPIRITUAL_ROOTS[root_idx]
            
            # 创建玩家
            self.player = Player(name=name, gender=gender, spiritual_root=spiritual_root)
            self.storyteller.reset_conversation()
            
            dialog.destroy()
            
            # 开始游戏
            self._start_game()
        
        # 创建按钮
        ttk.Button(
            dialog, text="开始修仙", style="Game.TButton",
            command=create_character
        ).pack(pady=20)
    
    def _show_load_game(self):
        """显示读档界面"""
        saves = Player.list_saves()
        
        if not saves:
            messagebox.showinfo("提示", "没有找到任何存档！")
            return
        
        # 创建读档对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("读取存档")
        dialog.geometry("350x300")
        dialog.configure(bg=self.colors["bg_dark"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.geometry(f"+{self.root.winfo_x() + 25}+{self.root.winfo_y() + 250}")
        
        tk.Label(
            dialog, text="选择存档", bg=self.colors["bg_dark"],
            fg=self.colors["gold"], font=(GUI_FONT_FAMILY, 14, "bold")
        ).pack(pady=10)
        
        save_listbox = tk.Listbox(
            dialog, bg=self.colors["bg_medium"],
            fg=self.colors["text"], font=(GUI_FONT_FAMILY, 10),
            height=8, selectmode=tk.SINGLE
        )
        save_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        for save_path in saves:
            filename = os.path.basename(save_path)
            save_listbox.insert(tk.END, filename)
        save_listbox.selection_set(0)
        
        def load_selected():
            selection = save_listbox.curselection()
            if not selection:
                return
            
            save_path = saves[selection[0]]
            try:
                self.player = Player.load(save_path)
                dialog.destroy()
                self._start_game()
            except Exception as e:
                messagebox.showerror("错误", f"加载存档失败：{e}")
        
        ttk.Button(
            dialog, text="加载", style="Game.TButton",
            command=load_selected
        ).pack(pady=10)
    
    def _start_game(self):
        """开始游戏"""
        # 显示状态栏
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 更新玩家状态显示
        self._update_player_status()
        
        # 如果是新游戏，生成背景故事
        if not self.player.story_history:
            self._set_story_text("正在生成你的修仙故事...\n\n请稍候，仙途即将开启...")
            self._clear_options()
            self._set_loading(True, "AI正在创作故事...")
            
            # 在后台线程生成故事
            def generate():
                try:
                    player_info = self._get_player_info()
                    # 获取完整的角色信息用于图片生成
                    char_info = {
                        "gender": self.player.gender,
                        "spiritual_root": self.player.spiritual_root,
                        "realm": self.player.realm_name,
                    }
                    story, options = self.storyteller.generate_background_story(player_info)
                    
                    # 生成图片（包含主角）
                    image_prompt = create_prompt_from_story(story, char_info)
                    image = self.image_generator.generate_image(image_prompt)
                    
                    # 更新UI（通过队列）
                    self.task_queue.put(("story", story, options, image))
                except Exception as e:
                    self.task_queue.put(("error", str(e)))
            
            threading.Thread(target=generate, daemon=True).start()
        else:
            # 继续游戏
            self.current_story = self.player.get_recent_story(1)
            self._set_story_text(self.current_story)
            self._show_options(
                ["继续探索", "原地修炼", "查看周围环境"],
                self._handle_story_choice
            )
            self._show_placeholder_image()
    
    def _handle_story_choice(self, choice_idx: int):
        """处理故事选择"""
        if choice_idx < 0 or choice_idx >= len(self.current_options):
            return
        
        player_choice = self.current_options[choice_idx]
        self.player.choices_made += 1
        
        # 显示加载状态
        self._set_story_text(f"你选择了：{player_choice}\n\n命运的齿轮开始转动...")
        self._clear_options()
        self._set_loading(True, "AI正在续写故事...")
        
        # 在后台线程生成故事
        def generate():
            try:
                player_info = self._get_player_info()
                # 获取完整的角色信息用于图片生成
                char_info = {
                    "gender": self.player.gender,
                    "spiritual_root": self.player.spiritual_root,
                    "realm": self.player.realm_name,
                }
                story, options, effects = self.storyteller.continue_story(
                    player_info,
                    player_choice,
                    self.player.get_recent_story(3)
                )
                
                # 生成图片（包含主角）
                image_prompt = create_prompt_from_story(story, char_info)
                image = self.image_generator.generate_image(image_prompt)
                
                # 更新UI
                self.task_queue.put(("continue", story, options, effects, image))
            except Exception as e:
                self.task_queue.put(("error", str(e)))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def _process_tasks(self):
        """处理后台任务队列"""
        try:
            while True:
                task = self.task_queue.get_nowait()
                
                if task[0] == "story":
                    _, story, options, image = task
                    self.current_story = story
                    self.current_options = options
                    self.player.add_story(story)
                    
                    self._set_story_text(story)
                    self._show_options(options, self._handle_story_choice)
                    self._set_loading(False)
                    
                    if image:
                        self._display_image(image)
                    
                elif task[0] == "continue":
                    _, story, options, effects, image = task
                    self.current_story = story
                    self.current_options = options
                    self.player.add_story(story)
                    
                    # 应用效果
                    self._apply_effects(effects)
                    
                    self._set_story_text(story)
                    self._show_options(options, self._handle_story_choice)
                    self._update_player_status()
                    self._set_loading(False)
                    
                    if image:
                        self._display_image(image)
                    
                elif task[0] == "error":
                    _, error_msg = task
                    self._set_loading(False)
                    messagebox.showerror("错误", f"发生错误：{error_msg}")
                    self._show_options(self.current_options or ["返回菜单"], self._handle_story_choice)
                
        except queue.Empty:
            pass
        
        # 继续轮询
        self.root.after(100, self._process_tasks)
    
    def _apply_effects(self, effects: dict):
        """应用故事效果"""
        if not self.player or not effects:
            return
        
        # 修为变化
        if effects.get("cultivation_change", 0) != 0:
            change = effects["cultivation_change"]
            if change > 0:
                result = self.player.add_cultivation(change)
                if result["breakthrough"]:
                    messagebox.showinfo(
                        "突破",
                        f"恭喜！你已突破至【{result['new_realm']}】！"
                    )
            else:
                self.player.lose_cultivation(abs(change))
        
        # 生命变化
        if effects.get("hp_change", 0) != 0:
            change = effects["hp_change"]
            if change > 0:
                self.player.heal(change)
            else:
                is_dead = self.player.take_damage(abs(change))
                if is_dead:
                    messagebox.showinfo("陨落", "你的修仙之路在此终结...")
                    self._show_main_menu()
                    return
        
        # 灵力变化
        if effects.get("mp_change", 0) != 0:
            change = effects["mp_change"]
            if change > 0:
                self.player.restore_mp(change)
            else:
                self.player.use_mp(abs(change))
        
        # 物品
        for item_name in effects.get("items", []):
            self.player.add_item({"name": item_name, "type": "misc"})
    
    def _set_story_text(self, text: str):
        """设置故事文本"""
        self.story_text.config(state=tk.NORMAL)
        self.story_text.delete(1.0, tk.END)
        self.story_text.insert(tk.END, text)
        self.story_text.config(state=tk.DISABLED)
        self.story_text.see(tk.END)
    
    def _show_options(self, options: List[str], callback: Callable):
        """显示选项按钮"""
        self._clear_options()
        self.current_options = options
        
        for i, option in enumerate(options):
            btn = ttk.Button(
                self.options_frame,
                text=f"{i+1}. {option}",
                style="Option.TButton",
                command=lambda idx=i: callback(idx)
            )
            btn.pack(fill=tk.X, pady=2)
            self.option_buttons.append(btn)
    
    def _clear_options(self):
        """清除选项按钮"""
        for btn in self.option_buttons:
            btn.destroy()
        self.option_buttons = []
    
    def _update_player_status(self):
        """更新玩家状态显示"""
        if not self.player:
            return
        
        # 玩家信息
        info_text = f"【{self.player.name}】{self.player.spiritual_root['name']} · {self.player.realm_name}"
        self.player_info_label.config(text=info_text)
        
        # HP条
        hp_percent = (self.player.hp / self.player.max_hp) * 100
        self.hp_bar["value"] = hp_percent
        self.hp_text.config(text=f"{self.player.hp}/{self.player.max_hp}")
        
        # MP条
        mp_percent = (self.player.mp / self.player.max_mp) * 100
        self.mp_bar["value"] = mp_percent
        self.mp_text.config(text=f"{self.player.mp}/{self.player.max_mp}")
        
        # 修为条
        self.cult_bar["value"] = self.player.cultivation_progress
        self.cult_text.config(text=f"{self.player.cultivation_progress}%")
    
    def _display_image(self, image: Image.Image):
        """显示图片"""
        if image is None:
            return
        
        # 计算适合的显示尺寸
        display_width = GUI_WINDOW_WIDTH - 10
        display_height = GUI_IMAGE_HEIGHT - 10
        
        # 保持宽高比缩放
        img_width, img_height = image.size
        ratio = min(display_width / img_width, display_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        # 缩放图片
        image_resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为 PhotoImage
        self.current_image = ImageTk.PhotoImage(image_resized)
        
        # 更新标签
        self.image_label.config(image=self.current_image, text="")
        
        # 保存图片
        self.image_count += 1
        save_path = os.path.join(IMAGE_SAVE_DIRECTORY, f"scene_{self.image_count:04d}.png")
        if not os.path.exists(IMAGE_SAVE_DIRECTORY):
            os.makedirs(IMAGE_SAVE_DIRECTORY)
        image.save(save_path)
    
    def _show_placeholder_image(self):
        """显示占位图片"""
        # 创建渐变占位图
        width = GUI_WINDOW_WIDTH - 10
        height = GUI_IMAGE_HEIGHT - 10
        
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        
        for y in range(height):
            for x in range(width):
                r = int(26 + (y / height) * 30)
                g = int(26 + (y / height) * 20)
                b = int(46 + (y / height) * 50)
                pixels[x, y] = (r, g, b)
        
        self.current_image = ImageTk.PhotoImage(image)
        self.image_label.config(image=self.current_image, text="")
    
    def _set_loading(self, loading: bool, message: str = ""):
        """设置加载状态"""
        self.is_generating = loading
        if loading:
            self.loading_label.config(text=f"⟳ {message}")
            for btn in self.option_buttons:
                btn.config(state=tk.DISABLED)
        else:
            self.loading_label.config(text="")
            for btn in self.option_buttons:
                btn.config(state=tk.NORMAL)
    
    def _save_game(self):
        """保存游戏"""
        if not self.player:
            messagebox.showinfo("提示", "没有可保存的游戏！")
            return
        
        try:
            filepath = self.player.save()
            messagebox.showinfo("保存成功", f"游戏已保存到：\n{filepath}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存失败：{e}")
    
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
    
    def run(self):
        """运行游戏"""
        self.root.mainloop()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description=f"《{GAME_TITLE}》GUI版")
    parser.add_argument("--mock-ai", action="store_true", help="使用模拟AI（测试用）")
    parser.add_argument("--mock-sd", action="store_true", help="使用模拟图片生成（测试用）")
    args = parser.parse_args()
    
    # 检查SD连接
    use_mock_sd = args.mock_sd
    if not use_mock_sd:
        print("正在检查 Stable Diffusion 连接...")
        test_gen = ImageGenerator()
        if not test_gen.check_connection():
            print("警告：无法连接到 Stable Diffusion WebUI，将使用模拟图片生成")
            use_mock_sd = True
        else:
            print("Stable Diffusion 连接成功！")
    
    # 创建并运行游戏
    game = GameGUI(use_mock_ai=args.mock_ai, use_mock_sd=use_mock_sd)
    game.run()


if __name__ == "__main__":
    main()
