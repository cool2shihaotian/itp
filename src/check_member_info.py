"""检查 member_info 中的真实手机号"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager


def main():
    config = load_config()
    logger = setup_logging(config)

    client = ITPClient(config, logger)

    # 登录
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')

    # 桥接
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

    # 获取会员信息
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    print("\n" + "=" * 70)
    print("会员信息详情:")
    print("=" * 70)
    print(f"Name: {member_info.get('name')}")
    print(f"Email: {member_info.get('email')}")
    print(f"Phone: {member_info.get('phone')}")
    print(f"BirthDate: {member_info.get('birthDate')}")
    print(f"\n完整 member_info:")
    import json
    print(json.dumps(member_info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
