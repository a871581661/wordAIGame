"""
图片生成器 - 使用 Stable Diffusion WebUI API 生成图片
"""

import base64
import io
import os
import requests
import json
from typing import Optional, Tuple
from PIL import Image
from config import (
    SD_API_URL,
    SD_MODEL,
    SD_SAMPLER,
    SD_STEPS,
    SD_CFG_SCALE,
    SD_WIDTH,
    SD_HEIGHT,
    SD_NEGATIVE_PROMPT,
    IMAGE_SAVE_DIRECTORY,
)


class ImageGenerator:
    """Stable Diffusion 图片生成器"""
    
    def __init__(self, api_url: str = None):
        self.api_url = api_url or SD_API_URL
        self.txt2img_url = f"{self.api_url}/sdapi/v1/txt2img"
        self.models_url = f"{self.api_url}/sdapi/v1/sd-models"
        self.options_url = f"{self.api_url}/sdapi/v1/options"
        
        # 确保图片保存目录存在
        if not os.path.exists(IMAGE_SAVE_DIRECTORY):
            os.makedirs(IMAGE_SAVE_DIRECTORY)
    
    def check_connection(self) -> bool:
        """检查与 SD WebUI 的连接"""
        try:
            response = requests.get(self.models_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = None,
        width: int = None,
        height: int = None,
        steps: int = None,
        cfg_scale: float = None,
        sampler: str = None,
        seed: int = -1,
    ) -> Optional[Image.Image]:
        """生成图片
        
        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            width: 图片宽度
            height: 图片高度
            steps: 采样步数
            cfg_scale: CFG Scale
            sampler: 采样器
            seed: 随机种子 (-1 为随机)
            
        Returns:
            PIL.Image 对象，失败返回 None
        """
        # 使用默认值
        negative_prompt = negative_prompt or SD_NEGATIVE_PROMPT
        width = width or SD_WIDTH
        height = height or SD_HEIGHT
        steps = steps or SD_STEPS
        cfg_scale = cfg_scale or SD_CFG_SCALE
        sampler = sampler or SD_SAMPLER
        
        # 构建请求数据
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler,
            "seed": seed,
            "batch_size": 1,
            "n_iter": 1,
        }
        
        try:
            response = requests.post(
                self.txt2img_url,
                json=payload,
                timeout=120  # 图片生成可能需要较长时间
            )
            
            if response.status_code == 200:
                result = response.json()
                # 解码 base64 图片
                if "images" in result and len(result["images"]) > 0:
                    image_data = base64.b64decode(result["images"][0])
                    image = Image.open(io.BytesIO(image_data))
                    return image
            else:
                print(f"[SD API错误] 状态码: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print("[SD API错误] 请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print("[SD API错误] 无法连接到 Stable Diffusion WebUI")
            return None
        except Exception as e:
            print(f"[SD API错误] {str(e)}")
            return None
    
    def generate_and_save(
        self,
        prompt: str,
        filename: str,
        **kwargs
    ) -> Optional[str]:
        """生成图片并保存到文件
        
        Args:
            prompt: 提示词
            filename: 文件名（不含路径）
            **kwargs: 传递给 generate_image 的其他参数
            
        Returns:
            保存的文件路径，失败返回 None
        """
        image = self.generate_image(prompt, **kwargs)
        
        if image:
            filepath = os.path.join(IMAGE_SAVE_DIRECTORY, filename)
            image.save(filepath, "PNG")
            return filepath
        
        return None
    
    def generate_scene_image(
        self,
        scene_description: str,
        character_info: dict = None,
        style: str = "chinese fantasy"
    ) -> Optional[Image.Image]:
        """根据场景描述生成图片
        
        Args:
            scene_description: 场景描述（中文）
            character_info: 角色信息
            style: 风格
            
        Returns:
            PIL.Image 对象
        """
        # 构建提示词
        prompt = self._build_scene_prompt(scene_description, character_info, style)
        return self.generate_image(prompt)
    
    def _build_scene_prompt(
        self,
        scene_description: str,
        character_info: dict = None,
        style: str = "chinese fantasy"
    ) -> str:
        """构建场景提示词
        
        将中文场景描述转换为适合 SD 的英文提示词
        """
        # 基础风格提示词
        style_prompts = {
            "chinese fantasy": "chinese xianxia fantasy, ancient chinese cultivation world, mystical atmosphere, ethereal lighting, dramatic scenery",
            "dark": "dark fantasy, ominous atmosphere, dramatic shadows, mystical fog",
            "bright": "bright fantasy, golden light, celestial atmosphere, divine radiance",
            "battle": "epic battle scene, dynamic action, energy effects, intense atmosphere",
        }
        
        base_style = style_prompts.get(style, style_prompts["chinese fantasy"])
        
        # 质量提示词
        quality_prompt = "masterpiece, best quality, highly detailed, 8k, cinematic lighting, artstation"
        
        # 组合提示词
        full_prompt = f"{quality_prompt}, {base_style}, {scene_description}"
        
        # 如果有角色信息，添加角色相关提示词
        if character_info:
            gender = character_info.get("gender", "他")
            gender_prompt = "1boy, male cultivator" if gender == "他" else "1girl, female cultivator"
            
            # 灵根对应的元素效果
            element_effects = {
                "金": "golden energy, metallic aura",
                "木": "nature energy, green aura, plants",
                "水": "water energy, blue aura, flowing water",
                "火": "fire energy, red flames, burning aura",
                "土": "earth energy, brown aura, stone",
                "雷": "lightning energy, purple thunder, electric sparks",
                "冰": "ice energy, frost, snowflakes",
                "天": "celestial energy, rainbow light, divine glow",
                "混沌": "chaos energy, multicolor aura, cosmic power",
            }
            
            spiritual_root = character_info.get("spiritual_root", {})
            element = spiritual_root.get("element", "")
            element_prompt = element_effects.get(element, "mystical energy")
            
            full_prompt = f"{full_prompt}, {gender_prompt}, {element_prompt}"
        
        return full_prompt


class MockImageGenerator:
    """模拟图片生成器（用于测试，不需要 SD）"""
    
    def __init__(self):
        self.image_count = 0
        
        # 确保图片保存目录存在
        if not os.path.exists(IMAGE_SAVE_DIRECTORY):
            os.makedirs(IMAGE_SAVE_DIRECTORY)
    
    def check_connection(self) -> bool:
        return True
    
    def generate_image(self, prompt: str, **kwargs) -> Optional[Image.Image]:
        """生成一个占位图片"""
        self.image_count += 1
        
        # 创建一个渐变色的占位图
        width = kwargs.get("width", SD_WIDTH)
        height = kwargs.get("height", SD_HEIGHT)
        
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        
        # 创建渐变效果
        for y in range(height):
            for x in range(width):
                # 蓝紫渐变，模拟仙侠风格
                r = int(50 + (x / width) * 100)
                g = int(30 + (y / height) * 50)
                b = int(100 + ((x + y) / (width + height)) * 155)
                pixels[x, y] = (r, g, b)
        
        return image
    
    def generate_and_save(self, prompt: str, filename: str, **kwargs) -> Optional[str]:
        image = self.generate_image(prompt, **kwargs)
        if image:
            filepath = os.path.join(IMAGE_SAVE_DIRECTORY, filename)
            image.save(filepath, "PNG")
            return filepath
        return None
    
    def generate_scene_image(self, scene_description: str, character_info: dict = None, style: str = "chinese fantasy") -> Optional[Image.Image]:
        return self.generate_image(scene_description)


def create_prompt_from_story(story: str, character_info: dict = None, max_length: int = 350) -> str:
    """从故事文本中提取关键场景生成提示词（包含主角）
    
    Args:
        story: 故事文本
        character_info: 角色信息字典，包含 gender, spiritual_root 等
        max_length: 最大提示词长度
        
    Returns:
        英文提示词
    """
    # ========== 主角描述（必须包含）==========
    character_prompt = ""
    if character_info:
        gender = character_info.get("gender", "他")
        # 性别描述
        if gender == "他":
            character_prompt = "1boy, single male protagonist, young handsome man, chinese cultivator, long black hair, traditional hanfu robes"
        else:
            character_prompt = "1girl, single female protagonist, beautiful young woman, chinese cultivator, long black hair, elegant hanfu dress"
        
        # 灵根对应的视觉效果
        element_effects = {
            "金": "golden energy aura, metallic glow around body",
            "木": "green nature energy, leaves and vines surrounding",
            "水": "blue water energy, flowing water effects",
            "火": "red fire energy, flames surrounding body",
            "土": "brown earth energy, stone and dust effects",
            "雷": "purple lightning energy, electric sparks around",
            "冰": "ice blue aura, frost and snowflakes",
            "天": "rainbow celestial light, divine golden halo",
            "混沌": "multicolor chaos energy, cosmic aurora effects",
        }
        
        spiritual_root = character_info.get("spiritual_root", {})
        if isinstance(spiritual_root, dict):
            element = spiritual_root.get("element", "")
        else:
            # 如果是字符串，尝试提取元素
            element = ""
            for key in element_effects.keys():
                if key in str(spiritual_root):
                    element = key
                    break
        
        element_prompt = element_effects.get(element, "mystical energy aura")
        character_prompt = f"{character_prompt}, {element_prompt}"
        
        # 根据境界添加描述
        realm = character_info.get("realm", "")
        if "炼气" in realm:
            character_prompt += ", beginner cultivator, faint energy glow"
        elif "筑基" in realm:
            character_prompt += ", intermediate cultivator, visible energy aura"
        elif "金丹" in realm or "元婴" in realm:
            character_prompt += ", powerful cultivator, strong energy manifestation"
        elif "化神" in realm or "炼虚" in realm or "合体" in realm:
            character_prompt += ", supreme cultivator, overwhelming power aura"
        elif "大乘" in realm or "渡劫" in realm:
            character_prompt += ", immortal level cultivator, heavenly transcendent aura"
    else:
        # 默认主角描述
        character_prompt = "1boy, young chinese cultivator protagonist, long black hair, traditional hanfu, mystical energy aura"
    
    # ========== 场景关键词 ==========
    scene_keywords = {
        # 地点
        "山": "mountain peaks, cliff",
        "洞": "cave, cavern interior",
        "森林": "dense forest, ancient trees",
        "林": "bamboo forest, woods",
        "河": "river, flowing stream",
        "湖": "serene lake, reflection",
        "海": "vast ocean, waves",
        "天空": "sky, clouds",
        "宫殿": "grand palace, ornate architecture",
        "殿": "temple hall, sacred chamber",
        "塔": "tall pagoda, tower",
        "城": "ancient city, fortress walls",
        "村": "peaceful village",
        "门": "sect gate, grand entrance",
        "阵": "magic formation, glowing circles",
        "秘境": "secret realm, mystical dimension",
        "遗迹": "ancient ruins, mysterious relics",
        "悬崖": "cliff edge, precipice",
        "瀑布": "waterfall, cascading water",
        
        # 天气/时间
        "夜": "night scene, moonlit",
        "日": "daytime, sunlight",
        "月": "full moon, moonlight",
        "云": "clouds, misty",
        "雾": "thick fog, mysterious mist",
        "雨": "rain, stormy weather",
        "雪": "snow falling, winter scene",
        "雷电": "thunder and lightning",
        
        # 动作/状态
        "战斗": "battle scene, combat pose, action",
        "打斗": "fighting stance, dynamic action",
        "修炼": "meditation pose, sitting cross-legged, cultivating",
        "突破": "breakthrough moment, energy explosion",
        "飞行": "flying through sky, soaring",
        "行走": "walking on path, traveling",
        
        # 生物
        "妖兽": "mystical beast, monster",
        "龙": "chinese dragon",
        "凤凰": "phoenix bird",
        "虎": "white tiger",
        "灵兽": "spirit beast companion",
        
        # 物品/效果
        "剑": "holding sword, blade gleaming",
        "丹药": "glowing pill, elixir",
        "法宝": "magical artifact, glowing treasure",
        "符箓": "talisman paper, magical seals",
    }
    
    # 提取关键词
    found_keywords = []
    for cn_word, en_word in scene_keywords.items():
        if cn_word in story:
            found_keywords.append(en_word)
    
    # 构建场景提示词
    if found_keywords:
        scene_prompt = ", ".join(found_keywords[:4])  # 最多取4个关键词
    else:
        scene_prompt = "ancient chinese landscape, mystical scenery"
    
    # ========== 组合最终提示词 ==========
    # 质量提示词
    quality = "masterpiece, best quality, highly detailed, 8k uhd, cinematic lighting, artstation"
    
    # 风格提示词
    style = "chinese xianxia fantasy, cultivation world, ethereal atmosphere, dramatic composition"
    
    # 组合：质量 + 主角 + 风格 + 场景
    final_prompt = f"{quality}, {character_prompt}, {style}, {scene_prompt}"
    
    return final_prompt[:max_length]
