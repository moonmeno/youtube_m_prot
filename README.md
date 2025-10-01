# YouTube 데이터 분석 프로토타입

Python 기반으로 YouTube Data API, OpenAI API, AWS를 연동하는 실험용 프로젝트입니다. 현재는 구조 설계와 최소한의 코드 스텁만 포함되어 있으며, 향후 FastAPI 백엔드와 React 대시보드를 추가할 수 있도록 여지를 남겨두었습니다.

## 주요 구성 요소
- `app/cli.py`: 단순한 CLI 인터페이스 (fetch/process/report)
- `app/youtube/`: YouTube API 호출 래퍼
- `app/ai/`: OpenAI 분석 프로세서 스텁
- `app/storage/`: S3 저장소 헬퍼 스텁
- `app/orchestration/`: 작업 큐/파이프라인 스텁
- `docs/architecture.md`: 전체 아키텍처 설계 문서

## 준비 사항
1. Python 3.11 이상
2. `pyproject.toml` 기반 의존성 설치
   ```bash
   pip install -e .
   ```
3. 환경 변수 설정
   ```bash
   export YOUTUBE_API_KEY=your_key
   export OPENAI_API_KEY=your_key
   export DATA_BUCKET=your_bucket
   export AWS_REGION=ap-northeast-2
   ```

## 사용 예시
```bash
python -m app.cli fetch --channel-id UCxxxxxxxx
python -m app.cli process --video-id dQw4w9WgXcQ
python -m app.cli report --limit 5
```

현재 모든 명령은 스텁 상태이며, AWS Step Functions/SQS, OpenAI API 호출 로직 등을 추가로 구현해야 합니다. FastAPI + React 기반 웹 확장과 Cognito 인증, DynamoDB/S3 데이터 뷰 설계는 `docs/web_prototype.md`와 `docs/architecture.md`에 정리되어 있습니다.

## 간단한 웹 실행 구상
- FastAPI 기반의 얇은 웹 API/정적 파일 서버로 확장해 브라우저에서 접근 가능한 최소 UI를 제공할 수 있습니다.
- `docs/web_prototype.md`에서 OAuth2(OIDC) + AWS Cognito를 사용한 인증 흐름, 영상/게시물/댓글 메타데이터를 DynamoDB/S3에 보존하는 데이터 경로, Playwright 기반 E2E 테스트 전략을 포함한 최신 로드맵을 정리했습니다.
- CLI 스텁을 직접 호출하던 흐름을 HTTP 엔드포인트(`/api/fetch`, `/api/process`, `/api/report`, `/api/videos`, `/api/videos/{id}`, `/api/comments`)와 React/Vite로 구성한 프런트엔드에서 호출하도록 전환하는 시나리오를 설명합니다.
- 웹 대시보드에서 인증된 사용자가 YouTube 데이터 수집을 트리거하고 결과를 확인할 수 있도록 Cognito Hosted UI, API Gateway Authorizer, FastAPI JWT 미들웨어 구성을 명시했습니다.
