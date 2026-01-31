#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
《仙途问道》- AI驱动的交互式修仙游戏
主程序入口

使用方法:
    python main.py              # 正常运行（需要OpenAI API）
    python main.py --mock       # 使用模拟AI运行（测试用）
    python main.py --help       # 显示帮助信息
"""

import sys
import os
import argparse

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_engine import GameEngine
from config import OPENAI_API_KEY, GAME_TITLE, GAME_VERSION


def check_api_key() -> bool:
    """检查API密钥是否配置"""
    if OPENAI_API_KEY == "your-api-key-here" or not OPENAI_API_KEY:
        return False
    return True


def print_welcome():
    """打印欢迎信息"""
    print()
    print("=" * 60)
    print(f"  《{GAME_TITLE}》 v{GAME_VERSION}")
    print("  一款由AI驱动的交互式修仙文字游戏")
    print("=" * 60)
    print()


def print_api_help():
    """打印API配置帮助"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                      API 配置说明                              ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  本游戏需要 OpenAI API 来生成故事内容。                        ║
║                                                                ║
║  配置方法（任选其一）：                                        ║
║                                                                ║
║  方法1: 设置环境变量                                           ║
║    Windows:                                                    ║
║      set OPENAI_API_KEY=your-api-key                          ║
║    Linux/Mac:                                                  ║
║      export OPENAI_API_KEY=your-api-key                       ║
║                                                                ║
║  方法2: 修改 config.py 文件                                    ║
║    找到 OPENAI_API_KEY 变量，填入你的API密钥                   ║
║                                                                ║
║  可选配置：                                                    ║
║    OPENAI_BASE_URL - API基础地址（用于兼容其他API服务）        ║
║    OPENAI_MODEL - 使用的模型名称                               ║
║                                                                ║
║  测试模式：                                                    ║
║    python main.py --mock                                       ║
║    使用模拟AI运行，不需要API密钥（用于测试游戏功能）           ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
""")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description=f'《{GAME_TITLE}》- AI驱动的交互式修仙游戏'
    )
    parser.add_argument(
        '--mock', 
        action='store_true',
        help='使用模拟AI运行（测试用，不需要API密钥）'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='开启调试模式'
    )
    
    args = parser.parse_args()
    
    # 打印欢迎信息
    print_welcome()
    
    # 检查是否使用模拟模式
    use_mock = args.mock
    
    if not use_mock:
        # 检查API密钥
        if not check_api_key():
            print("  ⚠ 未检测到有效的 OpenAI API 密钥！")
            print()
            print_api_help()
            print()
            response = input("  是否使用模拟模式运行？(y/n): ").strip().lower()
            if response == 'y':
                use_mock = True
            else:
                print("\n  请配置API密钥后再运行游戏。")
                sys.exit(1)
    
    if use_mock:
        print("  ℹ 正在使用模拟AI模式运行...")
        print("  （故事内容为预设模板，非AI生成）")
        print()
    
    try:
        # 创建并运行游戏引擎
        engine = GameEngine(use_mock=use_mock)
        engine.run()
    except KeyboardInterrupt:
        print("\n\n  游戏被中断，感谢游玩！")
        sys.exit(0)
    except Exception as e:
        if args.debug:
            raise
        print(f"\n  发生错误: {e}")
        print("  请检查配置或使用 --debug 参数查看详细信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()
