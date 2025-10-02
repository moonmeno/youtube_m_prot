"""간단한 명령줄 인터페이스(CLI) 엔트리포인트."""

from __future__ import annotations

import argparse
from typing import Callable, Dict

from app.orchestration import jobs


# 각 서브커맨드에 연결할 실행 함수를 등록하는 레지스트리.
COMMAND_REGISTRY: Dict[str, Callable[[argparse.Namespace], None]] = {}


def command(name: str) -> Callable[[Callable[[argparse.Namespace], None]], Callable[[argparse.Namespace], None]]:
    """명령 함수를 레지스트리에 등록하는 데코레이터."""

    def decorator(func: Callable[[argparse.Namespace], None]) -> Callable[[argparse.Namespace], None]:
        COMMAND_REGISTRY[name] = func
        return func

    return decorator


@command("fetch")
def fetch_command(args: argparse.Namespace) -> None:
    """YouTube에서 데이터를 수집하는 작업을 큐에 넣는다."""

    jobs.enqueue_fetch_job(channel_id=args.channel_id, force=args.force)


@command("process")
def process_command(args: argparse.Namespace) -> None:
    """S3 등 저장소에 적재된 원본 데이터를 OpenAI로 처리한다."""

    jobs.enqueue_process_job(video_id=args.video_id, segment=args.segment)


@command("report")
def report_command(args: argparse.Namespace) -> None:
    """누적된 결과를 요약하여 출력한다."""

    results = jobs.render_report(limit=args.limit, channel_id=args.channel_id)
    for idx, video in enumerate(results, start=1):
        title = video.get("title") or "(제목 없음)"
        video_id = video.get("videoId")
        channel_id = video.get("channelId")
        published_at = video.get("publishedAt")
        print(f"[{idx}] {title} (videoId={video_id}, channelId={channel_id}, publishedAt={published_at})")


def build_parser() -> argparse.ArgumentParser:
    """최소 옵션만 포함한 아규먼트 파서를 구성한다."""

    parser = argparse.ArgumentParser(description="YouTube 데이터 파이프라인 프로토타입")

    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="YouTube 데이터 수집")
    fetch_parser.add_argument("--channel-id", required=True, help="수집 대상 채널 ID")
    fetch_parser.add_argument("--force", action="store_true", help="캐시 여부와 상관없이 강제 수집")

    process_parser = subparsers.add_parser("process", help="원본 데이터 분석")
    process_parser.add_argument("--video-id", required=True, help="분석 대상 비디오 ID")
    process_parser.add_argument("--segment", help="분석할 구간 정보(예: start-end)")

    report_parser = subparsers.add_parser("report", help="결과 요약 출력")
    report_parser.add_argument("--limit", type=int, default=10, help="표시할 결과 수 제한")
    report_parser.add_argument("--channel-id", help="특정 채널의 결과만 조회")

    return parser


def main() -> None:
    """CLI 진입점. 추후 Typer 등으로 교체하기 쉽게 구성한다."""

    parser = build_parser()
    args = parser.parse_args()

    handler = COMMAND_REGISTRY.get(args.command)
    if handler is None:
        parser.error("지원하지 않는 명령입니다.")

    handler(args)


if __name__ == "__main__":
    main()
