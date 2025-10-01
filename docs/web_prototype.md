# 웹 프로토타입 실행 가이드

본 문서는 기존 CLI 스텁을 바탕으로 FastAPI와 간단한 정적 프런트엔드를 결합해 "브라우저에서 동작하는" 최소 기능 프로토타입을 구성하는 방법을 정리합니다. 아직 실제 구현 코드는 포함하지 않고 설계/로드맵 단계에 초점을 둡니다. 이번 개정에서는 **OAuth2 기반 개인 정보 보호 인증(AWS Cognito)**, **OpenAI·YouTube Data API 호출을 묶은 백엔드 흐름**, **웹 UI에서의 데이터 접근 및 테스트 전략**을 명시합니다.

## 1. 목표
- 별도의 복잡한 배포 파이프라인 없이도 로컬에서 FastAPI + Vite(React) 조합으로 실행.
- 핵심 플로우(데이터 수집, 처리, 요약 보고, 댓글 수집)를 HTTP 엔드포인트와 간단한 UI 버튼/폼으로 노출.
- 이후 AWS Cognito, API Gateway, CloudFront 등과 연동하기 위한 발판 마련.
- OAuth2/OIDC + Cognito Hosted UI를 통해 인증 후에만 웹 대시보드 접근 가능하도록 설계.
- 수집·처리된 영상/게시판 메타데이터를 DynamoDB/S3에 보존하고, FastAPI를 통해 선택적으로 필요한 리소스만 전송.

## 2. 로컬 개발 흐름
1. **FastAPI 엔드포인트 추가**
   - `app.web.api` 모듈(신규)에서 `fetch`, `process`, `report`, `videos.list`, `videos.retrieve`, `comments.list`를 POST/GET 엔드포인트로 노출.
   - CLI에서 사용하던 서비스 레이어(`youtube.client`, `ai.processor`, `storage.s3`)를 주입해 동일한 비즈니스 로직을 재사용.
   - Pydantic 모델을 활용해 요청/응답 스키마 정의, Swagger UI 자동 제공.
   - OAuth2 Password/Authorization Code Flow 대신 Cognito Hosted UI를 사용하므로 FastAPI에서는 JWT 검증 의존성(`Depends(get_current_user)`)을 제공.

2. **프런트엔드 최소 구성**
   - `frontend/` 디렉터리에 Vite + React + TypeScript 템플릿 생성.
   - 페이지 구성
     - `/login`: Cognito Hosted UI 리다이렉트 버튼, 테스트 모드에서는 mock 로그인 지원.
     - `/`: 채널 ID 입력 후 `fetch` 호출, 진행 상황 출력.
     - `/videos`: 수집된 목록 표시, 개별 영상 선택 시 `process` 실행 및 메타데이터/댓글 패널 표시.
     - `/reports`: `report` 결과를 표/카드 형태로 시각화.
   - `fetch`/`process` 호출 시 로딩 상태와 결과를 Toast/Modal로 표시.
   - React Query로 API 캐싱/리페치 제어, Recoil/Zustand로 인증 토큰 상태 공유.

3. **로컬 실행**
   ```bash
   # 터미널 1
   uvicorn app.web.api:app --reload --port 8000

   # 터미널 2
   cd frontend
   npm install
   npm run dev -- --port 5173
   ```
   - 개발 단계에서는 CORS 허용(`http://localhost:5173`).
   - 프런트엔드 `.env`에 API 베이스 URL(`VITE_API_BASE`)을 설정해 환경 전환 용이.
   - Cognito를 바로 붙이지 않는 경우에는 FastAPI에 테스트용 JWT 발급 엔드포인트(`/auth/mock-login`)를 추가하고, 실제 AWS 연결 시 해당 경로를 제거.

## 3. 인증 & 권한 부여 설계
1. **Cognito 구성**
   - User Pool: 이메일 기반 로그인, 비밀번호 정책, MFA 옵션 정의.
   - App Client: Authorization Code + PKCE 활성화, Refresh Token TTL(예: 30일) 설정, Callback URL은 `https://app.example.com/callback`.
   - Domain: Cognito Hosted UI 커스텀 도메인(e.g., `auth.example.com`).
   - 그룹: `viewer`, `operator`, `admin` 세 그룹을 생성하고 IAM 역할과 매핑.
2. **API Gateway Authorizer**
   - JWT Authorizer를 사용해 Cognito User Pool을 검증자로 지정.
   - 유효한 토큰만 FastAPI 백엔드로 포워딩하며, Stage 변수로 환경별(User Pool ID, Client ID) 설정을 분리.
3. **FastAPI 미들웨어**
   - `Depends` 기반 JWT 검증 및 역할 확인. `sub`(사용자 ID), `cognito:groups`를 읽어 권한 부여.
   - 사용자-채널 매핑을 DynamoDB/RDS에 저장하고 요청마다 접근 가능한 리소스인지 확인.
4. **프런트엔드 연동**
   - `amazon-cognito-identity-js` 또는 AWS Amplify Auth를 사용해 Hosted UI 로그인/토큰 갱신.
   - 토큰 만료 시 백엔드 401 응답을 감지해 Hosted UI로 자동 리디렉션.

## 4. AWS 간단 배포 시나리오
1. **백엔드**
   - FastAPI 앱을 AWS Lambda + API Gateway HTTP API로 배포(SAM 또는 AWS CDK 사용).
   - Cognito JWT를 API Gateway 레벨에서 검증하고, FastAPI는 역할 검증과 감사 로깅에 집중.

2. **프런트엔드**
   - `npm run build` 산출물을 S3 정적 호스팅 버킷에 업로드.
   - CloudFront 배포를 붙여 HTTPS/캐싱 제공.
   - 환경 변수는 CloudFront Behavior마다 Lambda@Edge 또는 S3 객체 내 `config.json`으로 주입.

3. **CI/CD**
   - GitHub Actions 워크플로우에서 백엔드(Lambda)와 프런트엔드(S3)에 각각 배포 단계 추가.
   - 배포 후 Smoke Test(헬스체크, 기본 API 호출) 수행.

## 5. 보안 및 확장 고려
- **인증**: 초기 프로토타입에서도 Cognito Hosted UI + PKCE를 기본으로 사용하고, 로컬에서는 cognito-local 또는 Amplify Mock을 활용.
- **프라이버시**: 댓글 등 PII 가능성이 있는 데이터는 수집 시 마스킹, 민감 텍스트는 Private S3 Prefix에 저장하고 접근 권한을 최소화.
- **비용 절감**: API 호출/토큰 사용량을 프런트엔드에서 실시간 표기, 요청당 호출 수 제한.
- **실시간 피드백**: Step Functions/SQS 도입 전까지는 폴링 기반, 이후 WebSocket/API Gateway + DynamoDB Streams로 확장.
- **최소 권한**: Lambda/Step Functions/S3/DynamoDB/Secrets Manager에 대해 세분화된 IAM 역할을 정의하고, CloudTrail로 감사.

## 6. 테스트 전략 (웹/인증 중심)
| 범위 | 목적 | 도구 | 세부 항목 |
| --- | --- | --- | --- |
| 단위 | JWT 검증, 요청/응답 스키마 | `pytest`, `fastapi.testclient` | 잘못된 토큰/권한 부족 시 403 반환, 필수 파라미터 누락 검증 |
| 통합 | Cognito + FastAPI + DynamoDB/LocalStack | `pytest`, `moto`, `localstack` | `/api/videos` 호출 시 인증 성공/실패 케이스, DynamoDB 조회 결과 검증 |
| E2E (웹) | 브라우저에서 로그인 → 영상 목록 조회 | Playwright | Cognito Hosted UI 로그인, 영상 목록 렌더링, 특정 영상 클릭 후 상세 패널 표시 |
| 성능 | `/api/videos`, `/api/videos/{id}` 부하 | k6/Locust | 95% 타일 지연 시간 < 500ms, 동시 50 세션 |
| 보안 | OAuth 구성 점검 | AWS Security Hub, IAM Access Analyzer | 최소 권한, 비공개 S3, HTTPS 강제 |

테스트 파이프라인 예시 (GitHub Actions):
1. `lint` → `ruff`/`mypy`.
2. `unit-tests` → FastAPI TestClient + pytest.
3. `integration-tests` → LocalStack + cognito-local 기반 인증 플로우.
4. `e2e-tests` → Playwright(헤드리스)로 스테이징 배포 대상 검증.

## 7. 향후 작업 목록
- [ ] `app/web/api.py` 모듈 스켈레톤 작성 (FastAPI 인스턴스, OAuth2 디펜던시, 라우터, 의존성 주입).
- [ ] `frontend/` 템플릿 생성 및 Cognito 인증 훅/컨텍스트 구현.
- [ ] 로컬 개발용 docker-compose(선택) 작성: FastAPI, LocalStack, DynamoDB Local, cognito-local.
- [ ] QA 체크리스트 작성: API 응답 타임아웃, 오류 핸들링, 토큰 만료 처리, PII 마스킹 검증.
- [ ] 문서화: 사용자 가이드, 설치 스크립트, OAuth2 시퀀스 다이어그램, 스크린샷.

위 로드맵을 통해 기존 CLI 중심 구조를 손대지 않으면서도, 브라우저에서 접근 가능한 간단한 웹 서비스 형태로 확장할 수 있습니다.
