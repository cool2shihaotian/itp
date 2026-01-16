"""工具函数"""
import os
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 项目根目录
BASE_DIR = Path(__file__).parent.parent


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认为 config.yaml

    Returns:
        配置字典
    """
    if config_path is None:
        config_path = BASE_DIR / "config.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    设置日志

    Args:
        config: 配置字典

    Returns:
        logger 对象
    """
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('log_file', 'logs/itp_bot.log')
    save_to_file = log_config.get('save_to_file', True)

    # 创建 logger
    logger = logging.getLogger('ITPBot')
    logger.setLevel(log_level)

    # 清除已有的 handlers
    logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # 文件输出
    if save_to_file:
        log_path = BASE_DIR / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def ensure_dir(path: str) -> None:
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)
