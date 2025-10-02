# 웹 프로토타입 실행 가이드

FastAPI 백엔드와 React 기반 프런트엔드를 조합해 브라우저에서 실행 가능한 최소 기능 웹 대시보드를 구성하기 위한 로드맵입니다. 현재 저장소에는 FastAPI `/api/health`, `/api/fetch`, `/api/process`, `/api/report`가 구현되어 있으며, `fetch`는 실제로 S3/DynamoDB에 데이터를 적재하고 `report`는 DynamoDB에 저장된 영상을 반환합니다. 본 문서는 해당 기능을 기반으로 OAuth2(OIDC) + AWS Cognito 통합, 프런트엔드 UI, 테스트 전략을 정리합니다.

## 1. 목표
- 로컬 환경에서 FastAPI(백엔드)와 Vite + React(프런트엔드)를 동시에 구동하여 브라우저로 확인.
- Cognito Hosted UI를 이용한 OAuth2 로그인 후 `/api/*` 호출.
- 수집한 영상/댓글 데이터의 요약 리스트를 화면에 표시하고, 추가 상세 뷰를 확장할 수 있는 구조 확보.
- 향후 OpenAI 분석 결과를 표시할 수 있도록 API/스토리지 스키마를 미리 설계.

## 2. 현재 백엔드 엔드포인트
| 메서드 | 경로 | 설명 | 구현 상태 |
| --- | --- | --- | --- |
| `GET` | `/api/health` | 헬스 체크 | ✅ |
| `POST` | `/api/fetch` | 채널 수집 파이프라인 실행 | ✅ (S3/DynamoDB 적재) |
| `POST` | `/api/process` | OpenAI 분석 파이프라인 실행 | 스텁 (로그만 출력) |
| `GET` | `/api/report` | DynamoDB 기반 영상 리스트 반환 | ✅ |

> `/api/report` 응답은 `{ "items": [...], "limit": 10, "channelId": null }` 형태입니다. 프런트엔드는 `items` 배열을 표/카드로 렌더링하면 됩니다.

향후 `/api/videos`, `/api/videos/{video_id}`, `/api/comments`와 같은 세부 엔드포인트를 추가해 프런트엔드에서 선택한 영상의 메타데이터와 댓글을 조회하도록 확장할 예정입니다.

## 3. 로컬 개발 절차
1. **FastAPI 실행**
   ```bash
   uvicorn app.web.api:app --reload --port 8000
   ```
2. **프런트엔드 템플릿 생성**
   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install
   ```
3. **API 연동**
   - `.env.development`에 `VITE_API_BASE=http://localhost:8000/api` 설정.
   - React Query를 사용해 `/report` 데이터를 불러오고, `fetch` 버튼에서 `/fetch` POST 요청을 전송.
   - 인증이 붙기 전까지는 CORS 허용(`http://localhost:5173`)을 FastAPI에 적용합니다.
4. **동시 실행**
   ```bash
   npm run dev -- --port 5173
   ```
   브라우저에서 `http://localhost:5173` 접속 → 영상 리스트 렌더링 확인.

## 4. Cognito 기반 인증 흐름
1. **User Pool 구성**
   - 이메일 기반 회원 가입, Password 정책, MFA(선택).
   - App Client에서 Authorization Code + PKCE 활성화, Callback URL은 `https://<프런트엔드 도메인>/auth/callback`.
2. **API Gateway Authorizer**
   - Cognito User Pool을 검증자로 지정하고 FastAPI 앞단에 배치.
   - 개발 단계에서는 FastAPI에 직접 JWKS 검증 로직(`Depends(get_current_user)`)을 추가하고, 운영 단계에서는 API Gateway가 1차 검증 수행.
3. **프런트엔드 통합**
   - `amazon-cognito-identity-js` 또는 AWS Amplify Auth를 사용해 Hosted UI 리다이렉션 및 토큰 저장.
   - 액세스 토큰 만료 시 자동 갱신 또는 재로그인.
4. **FastAPI 미들웨어**
   - `/api` 라우터에 JWT 검증 디펜던시를 추가해 인증된 요청만 수락.
   - Cognito 그룹과 역할(`viewer`, `operator`, `admin`)을 FastAPI 권한 체크와 매핑.

## 5. 데이터 표시 아이디어
- **대시보드 홈**: `/api/report` 결과를 표로 출력, 각 행에 “상세 보기” 버튼.
- **상세 패널**: 영상 ID를 전달하여 `/api/videos/{video_id}`(향후 구현) 호출 → 메타데이터, 댓글 요약 표시.
- **액션 버튼**: “데이터 새로고침” 클릭 시 `/api/fetch` 호출. 요청 진행 상태는 Toast/Progress로 표현.
- **분석 탭(예정)**: OpenAI 분석 결과를 DynamoDB에 저장한 뒤 `/api/report` 응답에 포함하여 카드 형태로 시각화.

## 6. 테스트 전략
| 범위 | 목적 | 도구 |
| --- | --- | --- |
| 단위 | React 훅/컴포넌트 렌더링, API 클라이언트 | React Testing Library, MSW |
| 통합 | FastAPI + Cognito 모킹 + DynamoDB(LocalStack) | pytest, localstack, httpx |
| E2E | Cognito Hosted UI 로그인 후 대시보드 흐름 | Playwright |

- 백엔드: 이미 구현된 `pytest` 스위트를 CI에 포함하고, `/api` 엔드포인트를 FastAPI `TestClient`로 추가 검증.
- 프런트엔드: Mock Service Worker(MSW)로 `/api` 응답을 가짜로 만들고 UI 동작을 검증.
- 인증: `cognito-local` 또는 Amplify Mock을 이용해 로컬에서 OIDC 플로우를 재현.

## 7. 배포 로드맵
1. **백엔드**: AWS Lambda + API Gateway HTTP API. 배포 시 `DATA_BUCKET`, `VIDEO_INDEX_TABLE` 등 환경 변수를 Lambda에 주입.
2. **프런트엔드**: `npm run build` 산출물을 S3 정적 호스팅 + CloudFront 배포. Cognito Hosted UI 도메인과 동일한 루트 도메인 하위 경로를 사용.
3. **CI/CD**: GitHub Actions에서 `pytest` → 프런트엔드 `npm test` → 배포. 배포 이후 Smoke Test로 `/api/health` 확인 및 `/api/report` 호출.

## 8. 향후 할 일 체크리스트
- [ ] `/api/videos`, `/api/videos/{id}`, `/api/comments` 구현 및 문서화.
- [ ] OpenAI 분석 결과 저장 스키마 설계(`processed/` 프리픽스, DynamoDB 필드 확장).
- [ ] React 대시보드 기본 화면(로그인, 리스트, 상세 패널) 구현.
- [ ] Cognito + API Gateway + FastAPI JWT 검증 연동 테스트.
- [ ] Playwright 기반 E2E 시나리오(로그인 → 수집 요청 → 보고서 확인) 작성.

