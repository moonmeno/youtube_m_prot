# YouTube 데이터 분석 프로토타입

YouTube Data API로 채널 데이터를 수집하고, AWS S3/DynamoDB에 저장한 뒤 보고서를 노출하는 Python 기반 프로토타입입니다. 현재 버전은
다음과 같은 특징을 갖습니다.

- `fetch` 명령 또는 FastAPI `/api/fetch` 호출 시 채널 업로드 플레이리스트를 순회하면서 영상 상세 정보와 댓글을 수집합니다.
- 수집한 JSON은 S3 버킷에 저장하고, DynamoDB 테이블에 메타데이터 인덱스를 갱신하여 빠른 조회를 지원합니다.
- `report` 명령과 `/api/report` 엔드포인트는 DynamoDB에 저장된 최신 영상을 조회해 간단한 리스트 형태로 제공합니다.
- `process` 경로는 향후 OpenAI 분석을 위한 자리이며 아직 스텁 상태입니다.

자세한 아키텍처와 확장 계획은 `docs/architecture.md`, 웹 대시보드 로드맵은 `docs/web_prototype.md`에서 확인할 수 있습니다.

## 주요 디렉터리
- `app/cli.py`: `fetch`, `process`, `report` 명령을 제공하는 Typer 기반 CLI.
- `app/web/api.py`: FastAPI 라우터. `/api/health`, `/api/fetch`, `/api/process`, `/api/report`를 노출합니다.
- `app/youtube/`: YouTube Data API 호출 래퍼와 재시도 헬퍼.
- `app/storage/`: S3 업로드/다운로드, DynamoDB 메타데이터 인덱스 모듈.
- `app/orchestration/`: 수집 파이프라인 구현 및 보고서 로직.
- `docs/`: 아키텍처·웹 프로토타입 문서.
- `tests/`: pytest 기반 단위 테스트 모음.

## 준비 사항
1. Python 3.11 이상.
2. 개발/테스트 의존성 설치.
   ```bash
   pip install -e .[dev]
   ```
3. AWS 리소스 준비.
   - **S3 버킷**: 수집된 JSON을 저장할 버킷. 버킷 이름을 `DATA_BUCKET` 환경 변수로 지정합니다.
   - **DynamoDB 테이블**: 파티션 키 `PK`, 정렬 키 `SK`를 갖는 테이블. 예시 스키마는 아래 참고.
4. 필수 환경 변수 설정.
   ```bash
   export YOUTUBE_API_KEY=발급받은_API_키
   export OPENAI_API_KEY=임시값(분석 단계 미구현이지만 스키마상 필요)
   export DATA_BUCKET=your_bucket
   export AWS_REGION=ap-northeast-2
   export VIDEO_INDEX_TABLE=your_video_metadata_table
   ```
   - 로컬 개발에서는 `.env` 파일이나 VS Code `launch.json`에도 동일한 키를 설정할 수 있습니다.
   - 운영 환경에서는 AWS Secrets Manager/Parameter Store 사용을 권장합니다.

### DynamoDB 테이블 예시
```text
PK (HASH)    : 문자열, 예) CHANNEL#UC_xxxxx
SK (RANGE)   : 문자열, 예) PUBLISHED#2024-01-01T00:00:00Z#VIDEO#dQw4w9WgXcQ
videoId      : 문자열
channelId    : 문자열
title        : 문자열
description  : 문자열
publishedAt  : ISO8601 문자열
runId        : 수집 실행 ID
storedAt     : ISO8601 문자열
statistics   : (선택) YouTube statistics 객체
```

## 실행 방법
1. 환경 변수를 설정한 뒤 `pytest`로 기본 동작을 검증합니다.
   ```bash
   pytest
   ```
2. 채널 전체 수집.
   ```bash
   python -m app.cli fetch --channel-id UC_xxxxxxxxx
   ```
   - 업로드 플레이리스트 → 영상 상세 → 댓글을 순회하며 S3에 JSON 파일을 저장합니다.
   - 각 영상 메타데이터는 DynamoDB 인덱스에 upsert 됩니다.
3. 보고서 확인.
   ```bash
   python -m app.cli report --limit 5
   ```
   - DynamoDB에서 최신 영상 정보를 읽어와 콘솔에 요약 로그를 출력하고, JSON 리스트를 반환합니다.
4. FastAPI 서버 실행(선택).
   ```bash
   uvicorn app.web.api:app --reload --port 8000
   curl 'http://localhost:8000/api/report?limit=5'
   ```
   - `/api/fetch` POST 요청으로 CLI와 동일한 수집 파이프라인을 트리거할 수 있습니다.

> 현재 `process` 명령과 `/api/process`는 OpenAI 연동 전까지 로그만 출력합니다. 분석 파이프라인은 향후 릴리스에서 확장될 예정입니다.

## S3 저장 구조
- `raw/channels/{channel_id}/{run_id}/playlist/page_00000.json`
- `raw/channels/{channel_id}/{run_id}/videos/{video_id}.json`
- `raw/channels/{channel_id}/{run_id}/comments/{video_id}_page_00000.json`
- `raw/channels/{channel_id}/{run_id}/videos_index.json`

각 실행(run)은 타임스탬프 기반 ID로 분리되어 동일 채널을 여러 번 수집해도 히스토리를 남길 수 있습니다.

## 테스트 및 검증
- `pytest`: 설정 로더, YouTube 클라이언트 재시도, S3 입출력, DynamoDB 메타데이터 인덱스, 수집 파이프라인을 대상으로 15개의 단위 테스트를 제공합니다.
- 테스트는 httpx `MockTransport`, boto3 `Stubber`, 로컬 인메모리 인덱스를 사용해 외부 호출 없이 실행됩니다.
- GitHub Actions나 로컬 CI에서 `pytest` 명령만으로 회귀 검증을 수행할 수 있습니다.

## 다음 단계
- OpenAI 기반 영상/댓글 분석 로직 구현 (`process` 명령 고도화).
- DynamoDB 항목에 분석 결과 필드 추가 및 `/api/report` 확장.
- Cognito 인증을 갖춘 React 대시보드 구현(자세한 내용은 `docs/web_prototype.md`).
