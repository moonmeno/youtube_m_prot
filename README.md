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

현재 모든 명령은 스텁 상태이며, AWS Step Functions/SQS, OpenAI API 호출 로직 등을 추가로 구현해야 합니다.

## 간단한 웹 실행 구상
- FastAPI 기반의 얇은 웹 API/정적 파일 서버로 확장해 브라우저에서 접근 가능한 최소 UI를 제공할 수 있습니다.
- `docs/web_prototype.md` 문서에서 Cognito 없이 로컬 개발용으로 실행하는 방법과, AWS에 배포해 간단한 대시보드를 띄우는 로드맵을 정리했습니다.
- CLI 스텁을 직접 호출하던 흐름을 HTTP 엔드포인트(`/api/fetch`, `/api/process`, `/api/report`)와 React/Vite로 구성한 프런트엔드에서 호출하도록 전환하는 시나리오를 설명합니다.
