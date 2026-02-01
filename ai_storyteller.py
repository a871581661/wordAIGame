"""
AI故事生成器 - 使用OpenAI API生成修仙故事
"""

import re
from typing import Dict, List, Tuple, Optional
from openai import OpenAI
from config import (
    OPENAI_API_KEY, 
    OPENAI_BASE_URL, 
    OPENAI_MODEL,
    SYSTEM_PROMPT,
    STORY_GENERATION_PROMPT,
    STORY_CONTINUE_PROMPT,
    IMAGE_PROMPT_TEMPLATE,
)


class AIStoryteller:
    """AI故事生成器类"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or OPENAI_MODEL
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # 对话历史（用于保持上下文）
        self.conversation_history: List[Dict] = []
        self.max_history = 10  # 保留最近的对话轮数
        
    def _call_api(self, messages: List[Dict], temperature: float = 0.8) -> str:
        """调用OpenAI API
        
        Args:
            messages: 消息列表
            temperature: 温度参数，控制创造性
            
        Returns:
            str: AI生成的回复
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[API调用错误] {str(e)}\n\n请检查您的API配置是否正确。"
    
    def generate_background_story(self, player_info: Dict) -> Tuple[str, List[str]]:
        """生成背景故事
        
        Args:
            player_info: 玩家信息字典
            
        Returns:
            Tuple[str, List[str]]: (故事内容, 选项列表)
        """
        prompt = STORY_GENERATION_PROMPT.format(
            name=player_info["name"],
            gender=player_info["gender"],
            spiritual_root=player_info["spiritual_root"],
            realm=player_info["realm"],
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = self._call_api(messages)
        
        # 解析故事和选项
        story, options = self._parse_story_response(response)
        
        # 保存到对话历史
        self.conversation_history = [
            {"role": "assistant", "content": response}
        ]
        
        return story, options
    
    def continue_story(self, player_info: Dict, player_choice: str, previous_story: str) -> Tuple[str, List[str], Dict]:
        """续写故事
        
        Args:
            player_info: 玩家信息字典
            player_choice: 玩家的选择
            previous_story: 之前的故事内容
            
        Returns:
            Tuple[str, List[str], Dict]: (故事内容, 选项列表, 效果字典)
        """
        prompt = STORY_CONTINUE_PROMPT.format(
            name=player_info["name"],
            gender=player_info["gender"],
            spiritual_root=player_info["spiritual_root"],
            realm=player_info["realm"],
            cultivation_progress=player_info["cultivation_progress"],
            hp=player_info["hp"],
            max_hp=player_info["max_hp"],
            mp=player_info["mp"],
            max_mp=player_info["max_mp"],
            previous_story=previous_story,
            player_choice=player_choice,
        )
        
        # 构建消息，包含历史上下文
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        
        # 添加历史对话（最近几轮）
        for msg in self.conversation_history[-self.max_history:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": prompt})
        
        response = self._call_api(messages)
        
        # 解析故事、选项和效果
        story, options = self._parse_story_response(response)
        effects = self._parse_effects(response)
        
        # 更新对话历史
        self.conversation_history.append({"role": "user", "content": f"玩家选择：{player_choice}"})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # 保持历史长度
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
        
        return story, options, effects
    
    def _parse_story_response(self, response: str) -> Tuple[str, List[str]]:
        """解析AI回复，提取故事和选项
        
        Args:
            response: AI的回复内容
            
        Returns:
            Tuple[str, List[str]]: (故事内容, 选项列表)
        """
        # 查找选项模式 [选项X] 内容
        option_pattern = r'\[选项\d+\]\s*(.+?)(?=\[选项\d+\]|\[修为|$|\[生命|\[灵力|\[物品|\[突破)'
        options = re.findall(option_pattern, response, re.DOTALL)
        options = [opt.strip() for opt in options if opt.strip()]
        
        # 如果没有找到选项，尝试其他模式
        if not options:
            # 尝试匹配数字编号的选项
            option_pattern2 = r'^\d+[.、]\s*(.+?)$'
            lines = response.split('\n')
            for line in lines:
                match = re.match(option_pattern2, line.strip())
                if match:
                    options.append(match.group(1).strip())
        
        # 提取故事内容（移除选项部分）
        story = response
        # 移除选项部分
        story = re.sub(r'\[选项\d+\].+', '', story, flags=re.DOTALL)
        # 移除效果标记
        story = re.sub(r'\[修为[+-]\d+\]', '', story)
        story = re.sub(r'\[生命[+-]\d+\]', '', story)
        story = re.sub(r'\[灵力[+-]\d+\]', '', story)
        story = re.sub(r'\[物品:.+?\]', '', story)
        story = re.sub(r'\[突破\]', '', story)
        story = story.strip()
        
        # 如果没有解析到选项，提供默认选项
        if not options:
            options = [
                "继续探索",
                "原地修炼",
                "寻找机缘",
            ]
        
        return story, options
    
    def _parse_effects(self, response: str) -> Dict:
        """解析故事中的效果标记
        
        Args:
            response: AI的回复内容
            
        Returns:
            Dict: 效果字典
        """
        effects = {
            "cultivation_change": 0,
            "hp_change": 0,
            "mp_change": 0,
            "items": [],
            "breakthrough": False,
        }
        
        # 解析修为变化
        cultivation_matches = re.findall(r'\[修为([+-])(\d+)\]', response)
        for sign, value in cultivation_matches:
            change = int(value) if sign == '+' else -int(value)
            effects["cultivation_change"] += change
        
        # 解析生命变化
        hp_matches = re.findall(r'\[生命([+-])(\d+)\]', response)
        for sign, value in hp_matches:
            change = int(value) if sign == '+' else -int(value)
            effects["hp_change"] += change
        
        # 解析灵力变化
        mp_matches = re.findall(r'\[灵力([+-])(\d+)\]', response)
        for sign, value in mp_matches:
            change = int(value) if sign == '+' else -int(value)
            effects["mp_change"] += change
        
        # 解析获得物品
        item_matches = re.findall(r'\[物品:(.+?)\]', response)
        effects["items"] = item_matches
        
        # 解析突破
        if '[突破]' in response:
            effects["breakthrough"] = True
        
        return effects
    
    def generate_death_story(self, player_info: Dict, cause: str) -> str:
        """生成死亡故事
        
        Args:
            player_info: 玩家信息
            cause: 死亡原因
            
        Returns:
            str: 死亡故事
        """
        prompt = f"""玩家角色已经陨落，请生成一段简短的结局描写：

玩家信息：
- 姓名：{player_info["name"]}
- 境界：{player_info["realm"]}
- 死亡原因：{cause}

要求：
1. 简短但有诗意的描写
2. 约100-150字
3. 体现修仙世界的残酷与无常"""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        return self._call_api(messages, temperature=0.7)
    
    def generate_breakthrough_story(self, player_info: Dict, new_realm: str) -> str:
        """生成突破故事
        
        Args:
            player_info: 玩家信息
            new_realm: 新境界名称
            
        Returns:
            str: 突破故事
        """
        prompt = f"""玩家角色成功突破到新境界，请生成一段突破描写：

玩家信息：
- 姓名：{player_info["name"]}
- 灵根：{player_info["spiritual_root"]}
- 新境界：{new_realm}

要求：
1. 描写突破过程中的异象
2. 体现境界提升的感觉
3. 约100-200字
4. 可以适当加入天地异象的描写"""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        return self._call_api(messages, temperature=0.8)
    
    def reset_conversation(self) -> None:
        """重置对话历史"""
        self.conversation_history = []
    
    def generate_image_prompt(self, story: str) -> str:
        """根据故事生成图片提示词
        
        Args:
            story: 故事内容
            
        Returns:
            str: 英文图片提示词
        """
        prompt = IMAGE_PROMPT_TEMPLATE.format(scene=story[:500])  # 限制长度
        
        messages = [
            {"role": "system", "content": "你是一个专业的AI绘画提示词生成器，擅长将中文场景描述转换为高质量的英文提示词。"},
            {"role": "user", "content": prompt},
        ]
        
        response = self._call_api(messages, temperature=0.7)
        
        # 清理响应，只保留提示词部分
        # 移除可能的解释文本
        response = response.strip()
        
        # 如果响应太长或包含中文，使用备用方法
        if len(response) > 300 or any('\u4e00' <= char <= '\u9fff' for char in response):
            return self._fallback_image_prompt(story)
        
        return response
    
    def _fallback_image_prompt(self, story: str) -> str:
        """备用图片提示词生成方法（基于关键词）"""
        # 场景关键词映射
        scene_keywords = {
            "山": "mountain, peaks, cliff",
            "洞": "cave, cavern, underground",
            "森林": "forest, ancient trees",
            "林": "woods, forest path",
            "河": "river, flowing water",
            "湖": "lake, still water",
            "海": "ocean, waves",
            "天": "sky, clouds, heavens",
            "宫殿": "palace, grand architecture",
            "殿": "temple, sacred hall",
            "塔": "tower, pagoda",
            "城": "city, fortress walls",
            "村": "village, rural settlement",
            "夜": "night scene, moonlight",
            "战": "battle scene, combat",
            "修炼": "meditation, energy cultivation",
            "突破": "energy breakthrough, power surge",
        }
        
        found_keywords = []
        for cn_word, en_word in scene_keywords.items():
            if cn_word in story:
                found_keywords.append(en_word)
        
        base = "masterpiece, best quality, chinese xianxia fantasy, cultivation world, mystical atmosphere"
        
        if found_keywords:
            scene = ", ".join(found_keywords[:4])
            return f"{base}, {scene}, cinematic lighting, highly detailed"
        
        return f"{base}, ancient chinese landscape, ethereal lighting, highly detailed"


class MockStoryteller:
    """模拟故事生成器（用于测试，不需要API）"""
    
    def __init__(self):
        self.story_count = 0
    
    def generate_background_story(self, player_info: Dict) -> Tuple[str, List[str]]:
        """生成模拟背景故事"""
        story = f"""
在这片修仙大陆上，青云山脉绵延万里，灵气充沛。

{player_info["name"]}出生于山脚下的一个小村庄，自幼便与常人不同。{player_info["gender"]}体内蕴含着罕见的{player_info["spiritual_root"]}，这让{player_info["gender"]}能够感知到常人无法感知的天地灵气。

十六岁那年，一位云游的老道士路过村庄，一眼便看出{player_info["name"]}的不凡资质。老道士留下一本《太虚心法》和一句话："三年后，青云山顶见。"

如今三年已过，{player_info["name"]}已初步感悟了心法奥义，踏上了前往青云山的道路。

刚走出村口不远，便遇到了一个分岔路口。左边是一条幽暗的山间小道，据说是通往青云山的捷径，但常有妖兽出没；右边是一条宽阔的官道，虽然绕远，但相对安全。

正在犹豫之际，林中突然传来一阵打斗声...
"""
        options = [
            "循着打斗声查看情况",
            "走左边的山间小道",
            "走右边安全的官道",
            "原地静观其变",
        ]
        return story.strip(), options
    
    def continue_story(self, player_info: Dict, player_choice: str, previous_story: str) -> Tuple[str, List[str], Dict]:
        """生成模拟续写故事"""
        self.story_count += 1
        
        story = f"""
{player_info["name"]}决定{player_choice}。

这个选择似乎引发了一连串的事件。在前行的道路上，{player_info["gender"]}遇到了一位受伤的年轻修士，对方自称是青云门的外门弟子，在执行任务时遭遇了妖兽袭击。

"多谢道友相救，"年轻修士抱拳道，"在下林风，青云门外门弟子。敢问道友尊姓大名？"

{player_info["name"]}扶起林风，将随身携带的伤药递了过去。林风感激之余，告诉{player_info["name"]}一个消息：青云山深处最近出现了一处上古遗迹，各大势力都派人前去探查。

"道友若有兴趣，可以与我同行。"林风说道。

[修为+5]
"""
        options = [
            "与林风结伴同行",
            "婉拒林风，独自前往",
            "询问更多关于遗迹的信息",
            "先护送林风回青云门",
        ]
        effects = {
            "cultivation_change": 5,
            "hp_change": 0,
            "mp_change": 0,
            "items": [],
            "breakthrough": False,
        }
        return story.strip(), options, effects
    
    def generate_death_story(self, player_info: Dict, cause: str) -> str:
        return f"""
天道无常，仙路艰难。

{player_info["name"]}的修仙之路在此戛然而止，{cause}。

或许在另一个轮回，{player_info["gender"]}能够重新踏上这条问道之路...

【游戏结束】
"""
    
    def generate_breakthrough_story(self, player_info: Dict, new_realm: str) -> str:
        return f"""
天地变色，风云际会！

{player_info["name"]}周身灵气涌动，体内真元如潮水般翻涌。{player_info["spiritual_root"]}散发出耀眼的光芒，与天地灵气产生共鸣。

轰隆！

一道惊雷划过天际，{player_info["name"]}成功突破，踏入【{new_realm}】！

一股前所未有的力量涌遍全身，{player_info["gender"]}感到自己与天地的联系更加紧密了。

【恭喜突破至{new_realm}！】
"""
    
    def reset_conversation(self) -> None:
        self.story_count = 0
