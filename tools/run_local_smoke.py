import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from main import run_skill


def main() -> None:
    payload = {
        "platform": "taobao",
        "keyword": "蓝牙耳机",
        "constraints": {},
        "action": "search_only",
        "notify_channel": "feishu",
        "max_candidates": 3,
        "need_login": True,
    }

    result = run_skill(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()