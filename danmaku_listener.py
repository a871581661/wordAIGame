"""
弹幕监听模块 - 支持B站和抖音直播弹幕
"""

import asyncio
import threading
import time
import json
import re
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from queue import Queue

# 尝试导入B站弹幕库
try:
    import blivedm
    import blivedm.models.web as web_models
    BILIBILI_AVAILABLE = True
except ImportError:
    BILIBILI_AVAILABLE = False
    print("提示: 安装 blivedm 以支持B站弹幕: pip install blivedm")

# 抖音弹幕需要使用 websocket
try:
    import websockets
    DOUYIN_AVAILABLE = True
except ImportError:
    DOUYIN_AVAILABLE = False
    print("提示: 安装 websockets 以支持抖音弹幕: pip install websockets")


@dataclass
class DanmakuMessage:
    """弹幕消息"""
    platform: str  # "bilibili" 或 "douyin"
    user_id: str
    username: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"[{self.platform}] {self.username}: {self.content}"


@dataclass
class GiftMessage:
    """礼物消息"""
    platform: str
    user_id: str
    username: str
    gift_name: str
    gift_count: int
    gift_value: float  # 礼物价值（元）
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"[{self.platform}] {self.username} 赠送 {self.gift_name} x{self.gift_count}"


class BaseDanmakuListener(ABC):
    """弹幕监听器基类"""
    
    def __init__(self):
        self.running = False
        self.danmaku_callbacks: List[Callable[[DanmakuMessage], None]] = []
        self.gift_callbacks: List[Callable[[GiftMessage], None]] = []
    
    def on_danmaku(self, callback: Callable[[DanmakuMessage], None]):
        """注册弹幕回调"""
        self.danmaku_callbacks.append(callback)
    
    def on_gift(self, callback: Callable[[GiftMessage], None]):
        """注册礼物回调"""
        self.gift_callbacks.append(callback)
    
    def _emit_danmaku(self, msg: DanmakuMessage):
        """触发弹幕回调"""
        for callback in self.danmaku_callbacks:
            try:
                callback(msg)
            except Exception as e:
                print(f"弹幕回调错误: {e}")
    
    def _emit_gift(self, msg: GiftMessage):
        """触发礼物回调"""
        for callback in self.gift_callbacks:
            try:
                callback(msg)
            except Exception as e:
                print(f"礼物回调错误: {e}")
    
    @abstractmethod
    def start(self):
        """开始监听"""
        pass
    
    @abstractmethod
    def stop(self):
        """停止监听"""
        pass


class BilibiliDanmakuListener(BaseDanmakuListener):
    """B站弹幕监听器"""
    
    def __init__(self, room_id: int):
        super().__init__()
        self.room_id = room_id
        self.client = None
        self._thread = None
        self._loop = None
    
    def start(self):
        """开始监听B站弹幕"""
        if not BILIBILI_AVAILABLE:
            print("错误: blivedm 未安装，无法监听B站弹幕")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_async, daemon=True)
        self._thread.start()
        print(f"B站弹幕监听已启动，房间号: {self.room_id}")
    
    def _run_async(self):
        """在新线程中运行异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._listen())
    
    async def _listen(self):
        """异步监听"""
        self.client = blivedm.BLiveClient(self.room_id)
        handler = BilibiliHandler(self)
        self.client.add_handler(handler)
        
        self.client.start()
        try:
            while self.running:
                await asyncio.sleep(1)
        finally:
            await self.client.stop_and_close()
    
    def stop(self):
        """停止监听"""
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        print("B站弹幕监听已停止")


if BILIBILI_AVAILABLE:
    class BilibiliHandler(blivedm.BaseHandler):
        """B站弹幕处理器"""
        
        def __init__(self, listener: BilibiliDanmakuListener):
            self.listener = listener
        
        def _on_danmaku(self, client, message: web_models.DanmakuMessage):
            """处理弹幕"""
            msg = DanmakuMessage(
                platform="bilibili",
                user_id=str(message.uid),
                username=message.uname,
                content=message.msg,
            )
            self.listener._emit_danmaku(msg)
        
        def _on_gift(self, client, message: web_models.GiftMessage):
            """处理礼物"""
            # B站礼物价值计算（金瓜子 / 1000 = 元）
            gift_value = message.total_coin / 1000 if message.coin_type == "gold" else 0
            
            msg = GiftMessage(
                platform="bilibili",
                user_id=str(message.uid),
                username=message.uname,
                gift_name=message.gift_name,
                gift_count=message.num,
                gift_value=gift_value,
            )
            self.listener._emit_gift(msg)


class DouyinDanmakuListener(BaseDanmakuListener):
    """抖音弹幕监听器
    
    注意：抖音直播弹幕获取较为复杂，这里提供一个基础框架。
    实际使用可能需要：
    1. 使用第三方抖音弹幕获取工具
    2. 或者通过 OBS 等工具转发弹幕
    """
    
    def __init__(self, room_id: str, ws_url: str = None):
        super().__init__()
        self.room_id = room_id
        # 抖音弹幕通常需要通过第三方工具获取，这里提供 WebSocket 接口
        self.ws_url = ws_url or f"ws://localhost:8888/douyin/{room_id}"
        self._thread = None
        self._loop = None
    
    def start(self):
        """开始监听抖音弹幕"""
        if not DOUYIN_AVAILABLE:
            print("错误: websockets 未安装")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_async, daemon=True)
        self._thread.start()
        print(f"抖音弹幕监听已启动，房间号: {self.room_id}")
        print(f"WebSocket地址: {self.ws_url}")
    
    def _run_async(self):
        """在新线程中运行异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._listen())
    
    async def _listen(self):
        """异步监听 WebSocket"""
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    print("已连接到抖音弹幕服务")
                    while self.running:
                        try:
                            data = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            self._handle_message(json.loads(data))
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            print(f"接收消息错误: {e}")
                            break
            except Exception as e:
                print(f"WebSocket连接错误: {e}")
                if self.running:
                    await asyncio.sleep(5)  # 重连等待
    
    def _handle_message(self, data: dict):
        """处理消息"""
        msg_type = data.get("type", "")
        
        if msg_type == "danmaku":
            msg = DanmakuMessage(
                platform="douyin",
                user_id=data.get("user_id", ""),
                username=data.get("username", ""),
                content=data.get("content", ""),
            )
            self._emit_danmaku(msg)
        
        elif msg_type == "gift":
            msg = GiftMessage(
                platform="douyin",
                user_id=data.get("user_id", ""),
                username=data.get("username", ""),
                gift_name=data.get("gift_name", ""),
                gift_count=data.get("gift_count", 1),
                gift_value=data.get("gift_value", 0),
            )
            self._emit_gift(msg)
    
    def stop(self):
        """停止监听"""
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        print("抖音弹幕监听已停止")


class MockDanmakuListener(BaseDanmakuListener):
    """模拟弹幕监听器（用于测试）"""
    
    def __init__(self):
        super().__init__()
        self._thread = None
    
    def start(self):
        """开始模拟"""
        self.running = True
        self._thread = threading.Thread(target=self._simulate, daemon=True)
        self._thread.start()
        print("模拟弹幕监听已启动")
    
    def _simulate(self):
        """模拟弹幕和礼物"""
        import random
        
        test_users = ["仙道求索", "剑心通明", "云游四海", "逍遥子", "青云弟子"]
        test_danmakus = ["1", "2", "3", "4", "选1", "选2", "选3", "666", "加油"]
        test_gifts = ["小心心", "棒棒糖", "仙女棒", "告白气球", "嘉年华"]
        
        while self.running:
            time.sleep(random.uniform(2, 5))
            
            if not self.running:
                break
            
            # 随机发送弹幕或礼物
            if random.random() < 0.8:  # 80%弹幕
                msg = DanmakuMessage(
                    platform="mock",
                    user_id=str(random.randint(10000, 99999)),
                    username=random.choice(test_users),
                    content=random.choice(test_danmakus),
                )
                self._emit_danmaku(msg)
            else:  # 20%礼物
                msg = GiftMessage(
                    platform="mock",
                    user_id=str(random.randint(10000, 99999)),
                    username=random.choice(test_users),
                    gift_name=random.choice(test_gifts),
                    gift_count=random.randint(1, 10),
                    gift_value=random.uniform(0.1, 100),
                )
                self._emit_gift(msg)
    
    def stop(self):
        """停止模拟"""
        self.running = False
        print("模拟弹幕监听已停止")


class VoteManager:
    """投票管理器 - 统计弹幕选项"""
    
    def __init__(self, vote_duration: int = 15):
        self.vote_duration = vote_duration  # 投票时长（秒）
        self.votes: Dict[str, Dict[str, str]] = {}  # {option: {user_id: username}}
        self.option_patterns: Dict[str, List[str]] = {}  # {option_key: [patterns]}
        self.voting_active = False
        self.vote_start_time = None
        self.vote_callback: Optional[Callable[[str, Dict], None]] = None
    
    def start_vote(self, options: List[str], callback: Callable[[str, Dict], None] = None):
        """开始新的投票
        
        Args:
            options: 选项列表
            callback: 投票结束回调，参数为 (获胜选项, 投票统计)
        """
        self.votes = {str(i+1): {} for i in range(len(options))}
        self.option_patterns = {}
        
        # 为每个选项创建匹配模式
        for i, opt in enumerate(options):
            key = str(i + 1)
            patterns = [
                key,  # 数字
                f"选{key}",  # 选1
                f"选择{key}",  # 选择1
                f"{key}号",  # 1号
            ]
            self.option_patterns[key] = patterns
        
        self.voting_active = True
        self.vote_start_time = time.time()
        self.vote_callback = callback
        
        # 启动投票计时器
        threading.Thread(target=self._vote_timer, daemon=True).start()
        
        return self.vote_duration
    
    def _vote_timer(self):
        """投票计时器"""
        time.sleep(self.vote_duration)
        if self.voting_active:
            self.end_vote()
    
    def process_danmaku(self, msg: DanmakuMessage) -> Optional[str]:
        """处理弹幕，检查是否是投票
        
        Returns:
            如果是有效投票，返回选项key；否则返回None
        """
        if not self.voting_active:
            return None
        
        content = msg.content.strip()
        
        # 检查是否匹配任何选项
        for key, patterns in self.option_patterns.items():
            for pattern in patterns:
                if content == pattern or content.startswith(pattern):
                    # 每个用户只能投一票
                    if msg.user_id not in self.votes[key]:
                        # 移除该用户之前的投票
                        for k in self.votes:
                            if msg.user_id in self.votes[k]:
                                del self.votes[k][msg.user_id]
                        
                        self.votes[key][msg.user_id] = msg.username
                        return key
        
        return None
    
    def get_vote_counts(self) -> Dict[str, int]:
        """获取当前投票统计"""
        return {k: len(v) for k, v in self.votes.items()}
    
    def get_remaining_time(self) -> int:
        """获取剩余投票时间"""
        if not self.voting_active or not self.vote_start_time:
            return 0
        elapsed = time.time() - self.vote_start_time
        remaining = max(0, self.vote_duration - int(elapsed))
        return remaining
    
    def end_vote(self) -> tuple:
        """结束投票
        
        Returns:
            (获胜选项key, 投票统计)
        """
        self.voting_active = False
        
        counts = self.get_vote_counts()
        
        # 找出得票最多的选项
        if counts:
            winner = max(counts.keys(), key=lambda k: counts[k])
        else:
            winner = "1"  # 默认选第一个
        
        # 触发回调
        if self.vote_callback:
            self.vote_callback(winner, counts)
        
        return winner, counts
    
    def is_voting(self) -> bool:
        """是否正在投票"""
        return self.voting_active
