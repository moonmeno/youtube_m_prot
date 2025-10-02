"""테스트 공통 설정."""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가하여 `app` 패키지를 import할 수 있도록 한다.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
