"""로깅 설정 헬퍼."""

from __future__ import annotations

import logging


def setup_logging(level: int = logging.INFO) -> None:
    """기본 로깅 설정을 초기화한다."""

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    # TODO: 구조화 로깅(JSON) 또는 CloudWatch 핸들러 연동을 추가할 수 있다.
