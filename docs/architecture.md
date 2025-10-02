# YouTube 데이터 분석 프로토타입 설계

본 문서는 Python 기반으로 YouTube Data API, AWS S3, AWS DynamoDB를 연동해 채널 데이터를 수집하고 요약 보고서를 제공하는 프로토타입의 현재 구조를 정리합니다. 향후 OpenAI 분석 및 웹 대시보드 확장을 위한 여지도 함께 기술합니다.

## 1. 목표 및 현황
- **완료**
  - CLI/웹에서 호출 가능한 동기식 `fetch` 파이프라인.
  - S3에 원본 JSON 저장, DynamoDB에 메타데이터 인덱스 기록.
  - `report` 명령과 `/api/report`로 최근 영상 목록 조회.
  - 환경 변수 검증 및 단위 테스트(YouTube API 래퍼, S3/DynamoDB 헬퍼, 오케스트레이션) 구축.
- **진행 예정**
  - OpenAI 기반 `process` 파이프라인과 결과 저장.
  - Cognito 인증을 갖춘 React 대시보드, 세부 API(`/api/videos/{id}` 등) 확장.
  - Step Functions/SQS 등 비동기 오케스트레이션.

## 2. 모듈 구성
| 모듈 | 역할 | 구현 상태 |
| --- | --- | --- |
| `app.config` | 환경 변수 로딩, 필수 값 검증 | ✅ |
| `app.youtube` | 업로드 플레이리스트→영상 상세→댓글 조회, 재시도 헬퍼 | ✅ |
| `app.storage.s3` | JSON 업로드/다운로드, 오류 처리 | ✅ |
| `app.storage.dynamodb` | 메타데이터 인덱스 upsert 및 최근 영상 조회 | ✅ |
| `app.orchestration.jobs` | `fetch`/`report` 파이프라인, 실행 ID 생성 | ✅ |
| `app.cli` | Typer CLI(`fetch`, `process`, `report`) | ✅ (`process`는 스텁) |
| `app.web.api` | FastAPI 라우터(`/api/health`, `/api/fetch`, `/api/process`, `/api/report`) | ✅ (`process`는 스텁) |
| `app.ai` | OpenAI 분석기 | 스텁 |

## 3. 데이터 흐름
1. **수집(Fetch)**
   - 입력: `channel_id`.
   - 동작: 업로드 플레이리스트 페이지네이션 → 영상 상세 정보 `videos.list` → 댓글 `commentThreads.list`.
   - 저장: 실행 ID(`YYYYMMDDTHHMMSSZ`)를 기준으로 S3에 원본 JSON, DynamoDB에 메타데이터 upsert.
2. **보고(Report)**
   - 입력: `limit`, `channel_id`(선택).
   - 동작: DynamoDB `query` 또는 `scan` 결과를 최신순 정렬.
   - 출력: 영상 ID, 제목, 설명, 발행 시각, 통계 등.
3. **분석(Process, 예정)**
   - 원본/댓글을 OpenAI로 전달하여 요약·키워드·감성 분석 수행.
   - 결과를 `processed/` S3 프리픽스와 DynamoDB 추가 필드에 저장.

### S3 객체 구조
```
raw/channels/{channel_id}/{run_id}/playlist/page_{N}.json
raw/channels/{channel_id}/{run_id}/videos/{video_id}.json
raw/channels/{channel_id}/{run_id}/comments/{video_id}_page_{M}.json
raw/channels/{channel_id}/{run_id}/videos_index.json
```

### DynamoDB 테이블 구조
- **파티션 키**: `PK = CHANNEL#{channel_id}`
- **정렬 키**: `SK = PUBLISHED#{published_at}#VIDEO#{video_id}`
- **속성**: `videoId`, `channelId`, `title`, `description`, `publishedAt`, `runId`, `storedAt`, `statistics`(선택)

## 4. AWS 연동
- **S3**: 수집한 모든 JSON을 저장. `put_json`은 `application/json` Content-Type과 UTF-8 직렬화를 사용.
- **DynamoDB**: 빠른 목록 조회를 위한 1차 인덱스. 채널 필터가 없으면 `scan` 후 최신순 정렬.
- **IAM 고려사항**: 수집 역할에 S3 `PutObject/GetObject`, DynamoDB `PutItem/Query/Scan` 권한만 부여. API 키는 Secrets Manager 사용 권장.

## 5. FastAPI + CLI 통합
- CLI와 FastAPI 모두 `app.orchestration.jobs`를 호출해 동일한 파이프라인을 재사용합니다.
- FastAPI 응답은 JSON 형태로 감싸서 프런트엔드에서 바로 활용할 수 있도록 구성했습니다.
- 향후 Cognito 인증을 추가할 때는 FastAPI 라우터에 JWT 검증 디펜던시만 추가하면 됩니다.

## 6. 테스트 전략 및 현황
- `tests/test_config.py`: 환경 변수 누락·공백 처리.
- `tests/test_youtube_client.py`: 업로드 플레이리스트 조회, 재시도, 오류 처리.
- `tests/test_storage_s3.py`: 업로드/다운로드 성공 및 예외 시나리오.
- `tests/test_storage_dynamodb.py`: upsert, 채널별 조회, 전체 스캔.
- `tests/test_jobs_fetch.py`: YouTube/S3/DynamoDB 스텁을 조합한 수집 파이프라인 검증.
- 모든 테스트는 외부 네트워크 없이 실행되며 `pytest` 한 번으로 15개 케이스를 통과합니다.

## 7. 향후 확장 계획
1. **OpenAI 처리 파이프라인**: `app.ai.processor` 구현, S3 `processed/` 프리픽스 및 DynamoDB 확장.
2. **웹 API 확장**: `/api/videos`, `/api/videos/{id}`, `/api/comments` 추가. React 대시보드와 연동.
3. **인증**: AWS Cognito(User Pool) + API Gateway Authorizer + FastAPI JWT 검증.
4. **비동기화**: SQS/Step Functions 도입, 장기 실행 작업 분리, 실행 상태 추적 테이블 추가.
5. **모니터링**: CloudWatch Metrics/Logs, 비용 대시보드(QuickSight) 및 경보 설정.

