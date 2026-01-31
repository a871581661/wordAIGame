"""
修仙游戏配置文件
"""

import os

# OpenAI API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")  # 可以修改为其他兼容的API地址
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-r1")  # 默认模型

# 游戏设置
GAME_TITLE = "仙途问道"
GAME_VERSION = "1.0.0"

# 修仙境界设定
CULTIVATION_REALMS = [
    {"name": "凡人", "level": 0, "description": "尚未踏入修仙之路"},
    {"name": "炼气期", "level": 1, "description": "感知天地灵气，初窥仙道"},
    {"name": "筑基期", "level": 2, "description": "筑就道基，正式踏入修仙之路"},
    {"name": "金丹期", "level": 3, "description": "凝聚金丹，寿元大增"},
    {"name": "元婴期", "level": 4, "description": "元婴出窍，神魂可离体"},
    {"name": "化神期", "level": 5, "description": "化神合道，领悟天道法则"},
    {"name": "炼虚期", "level": 6, "description": "炼虚合道，虚空挪移"},
    {"name": "合体期", "level": 7, "description": "天人合一，掌控天地之力"},
    {"name": "大乘期", "level": 8, "description": "大乘圆满，即将飞升"},
    {"name": "渡劫期", "level": 9, "description": "渡过天劫，飞升仙界"},
]

# 角色属性
BASE_ATTRIBUTES = {
    "体魄": 10,      # 影响生命值和物理防御
    "神识": 10,      # 影响法术攻击和感知能力
    "悟性": 10,      # 影响修炼速度和领悟功法
    "机缘": 10,      # 影响获得机缘和奇遇的概率
    "心境": 10,      # 影响突破瓶颈和抵抗心魔
}

# 角色根骨类型
SPIRITUAL_ROOTS = [
    {"name": "金灵根", "element": "金", "bonus": {"体魄": 3, "神识": 1}},
    {"name": "木灵根", "element": "木", "bonus": {"悟性": 2, "心境": 2}},
    {"name": "水灵根", "element": "水", "bonus": {"神识": 3, "心境": 1}},
    {"name": "火灵根", "element": "火", "bonus": {"神识": 2, "体魄": 2}},
    {"name": "土灵根", "element": "土", "bonus": {"体魄": 2, "心境": 2}},
    {"name": "雷灵根", "element": "雷", "bonus": {"神识": 4}},
    {"name": "冰灵根", "element": "冰", "bonus": {"神识": 2, "悟性": 2}},
    {"name": "天灵根", "element": "天", "bonus": {"悟性": 3, "机缘": 2}},
    {"name": "混沌灵根", "element": "混沌", "bonus": {"体魄": 2, "神识": 2, "悟性": 2, "机缘": 2, "心境": 2}},
]

# AI提示词模板
SYSTEM_PROMPT = """你是一位资深的修仙小说作者，擅长创作精彩的修仙故事。你需要为一个互动修仙游戏生成故事内容。

游戏世界观设定：
- 这是一个以修仙为主题的东方玄幻世界
- 世界中存在灵气，修士可以通过修炼吸收灵气提升境界
- 有各种宗门、世家、散修等修仙势力
- 存在各种灵兽、妖族、魔族等生物
- 有丹药、法宝、阵法、符箓等修仙元素

你的职责：
1. 根据玩家当前状态生成引人入胜的故事情节
2. 提供2-4个有意义的选择选项供玩家决策
3. 保持故事的连贯性和逻辑性
4. 适当增加惊喜和转折，但不要太过突兀
5. 根据玩家的选择合理推进故事发展

请用生动的文笔描写场景，适当加入对话和心理描写。"""

STORY_GENERATION_PROMPT = """请为以下玩家生成一段开篇背景故事：

玩家信息：
- 姓名：{name}
- 性别：{gender}
- 灵根：{spiritual_root}
- 当前境界：{realm}

要求：
1. 描写玩家的出身背景和踏入修仙之路的缘由
2. 故事长度约300-500字
3. 在故事结尾设置一个情境，引出玩家需要做出的第一个选择
4. 提供2-4个选择选项，格式如下：
[选项1] 选项内容
[选项2] 选项内容
...

请保持故事的沉浸感，让玩家感受到修仙世界的魅力。"""

STORY_CONTINUE_PROMPT = """请根据玩家的选择继续故事：

玩家信息：
- 姓名：{name}
- 性别：{gender}
- 灵根：{spiritual_root}
- 当前境界：{realm}
- 修为进度：{cultivation_progress}%
- 生命值：{hp}/{max_hp}
- 灵力：{mp}/{max_mp}

之前的故事：
{previous_story}

玩家选择了：{player_choice}

要求：
1. 根据玩家的选择自然地推进故事
2. 故事长度约200-400字
3. 可能发生的事件类型：战斗、获得机缘、遇到NPC、发现秘境、突破境界等
4. 在合适的时候给予玩家奖励或惩罚（修为提升、受伤、获得物品等）
5. 在故事结尾设置新的情境和选择
6. 提供2-4个选择选项，格式如下：
[选项1] 选项内容
[选项2] 选项内容
...

如果故事中发生了以下事件，请在故事末尾用特殊标记说明：
[修为+X] - 获得X点修为
[修为-X] - 失去X点修为  
[生命-X] - 失去X点生命
[生命+X] - 恢复X点生命
[灵力-X] - 消耗X点灵力
[灵力+X] - 恢复X点灵力
[物品:物品名称] - 获得物品
[突破] - 境界突破

请继续创作精彩的故事。"""

# 保存文件路径
SAVE_DIRECTORY = "saves"
IMAGE_SAVE_DIRECTORY = "images"

# ============== Stable Diffusion 配置 ==============
# SD WebUI API 地址 (AUTOMATIC1111 webui)
SD_API_URL = os.getenv("SD_API_URL", "http://127.0.0.1:7860")

# 模型设置
SD_MODEL = os.getenv("SD_MODEL", "")  # 留空使用当前加载的模型

# 采样器设置
SD_SAMPLER = "DPM++ 2M Karras"  # 推荐采样器
SD_STEPS = 20  # 采样步数
SD_CFG_SCALE = 7.0  # CFG Scale

# 图片尺寸 (适配手机屏幕比例 9:16)
SD_WIDTH = 576   # 宽度
SD_HEIGHT = 1024  # 高度

# 负面提示词
SD_NEGATIVE_PROMPT = """
(worst quality, low quality:1.4), (bad anatomy:1.3), (deformed, distorted:1.2),
blurry, pixelated, watermark, signature, text, logo,
(ugly:1.2), (duplicate:1.1), (morbid:1.1), (mutilated:1.1),
out of frame, extra fingers, mutated hands, poorly drawn hands,
poorly drawn face, mutation, deformed, bad proportions, extra limbs,
cloned face, disfigured, gross proportions, malformed limbs,
missing arms, missing legs, extra arms, extra legs, fused fingers,
too many fingers, long neck, username, artist name
"""

# 图片生成提示词模板
IMAGE_PROMPT_TEMPLATE = """请根据以下故事场景，生成一段简短的英文图片描述提示词（用于AI绘画）：

故事场景：
{scene}

要求：
1. 提取场景中的关键视觉元素
2. 使用英文描述
3. 长度控制在50-100个英文单词
4. 风格偏向中国仙侠/玄幻
5. 注重氛围和光影描写
6. 只输出提示词，不要其他内容

示例格式：
masterpiece, best quality, chinese xianxia fantasy, [场景描述], [人物描述], [氛围描述], cinematic lighting
"""

# GUI 窗口设置 (模拟手机屏幕)
GUI_WINDOW_WIDTH = 400  # 窗口宽度
GUI_WINDOW_HEIGHT = 800  # 窗口高度
GUI_IMAGE_HEIGHT = 350  # 图片显示区域高度
GUI_FONT_FAMILY = "Microsoft YaHei"  # 字体
GUI_FONT_SIZE = 11  # 字体大小

# ============== 直播互动配置 ==============
# B站直播房间号
BILIBILI_ROOM_ID = int(os.getenv("BILIBILI_ROOM_ID", "0"))  # 设置为你的B站房间号

# 抖音直播房间号
DOUYIN_ROOM_ID = os.getenv("DOUYIN_ROOM_ID", "")  # 设置为你的抖音房间号

# 投票设置
LIVE_VOTE_DURATION = 15  # 投票时长（秒）

# 弹幕投票关键词
VOTE_KEYWORDS = {
    "1": ["1", "选1", "选择1", "1号"],
    "2": ["2", "选2", "选择2", "2号"],
    "3": ["3", "选3", "选择3", "3号"],
    "4": ["4", "选4", "选择4", "4号"],
}

# 礼物效果阈值（元）
GIFT_THRESHOLDS = {
    "cultivation_small": 0.1,   # 小额修为加成
    "cultivation_medium": 1.0,  # 中额修为加成
    "cultivation_large": 10.0,  # 大额修为加成
    "attribute_boost": 20.0,    # 属性加成
    "rename": 50.0,             # 改名权
    "resurrection": 200.0,      # 复活权
}

# 礼物效果倍率
GIFT_CULTIVATION_MULTIPLIER = 10  # 每1元 = 10点修为
