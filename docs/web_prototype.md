# 웹 프로토타입 실행 가이드

본 문서는 기존 CLI 스텁을 바탕으로 FastAPI와 간단한 정적 프런트엔드를 결합해 "브라우저에서 동작하는" 최소 기능 프로토타입을 구성하는 방법을 정리합니다. 아직 실제 구현 코드는 포함하지 않고 설계/로드맵 단계에 초점을 둡니다.

## 1. 목표
- 별도의 복잡한 배포 파이프라인 없이도 로컬에서 FastAPI + Vite(React) 조합으로 실행.
- 핵심 플로우(데이터 수집, 처리, 요약 보고)를 HTTP 엔드포인트와 간단한 UI 버튼/폼으로 노출.
- 이후 AWS Cognito, API Gateway, CloudFront 등과 연동하기 위한 발판 마련.

## 2. 로컬 개발 흐름
1. **FastAPI 엔드포인트 추가**
   - `app.web.api` 모듈(신규)에서 `fetch`, `process`, `report`를 각각 POST/GET 엔드포인트로 노출.
   - CLI에서 사용하던 서비스 레이어(`youtube.client`, `ai.processor`, `storage.s3`)를 주입해 동일한 비즈니스 로직을 재사용.
   - Pydantic 모델을 활용해 요청/응답 스키마 정의, Swagger UI 자동 제공.

2. **프런트엔드 최소 구성**
   - `frontend/` 디렉터리에 Vite + React + TypeScript 템플릿 생성.
   - 페이지 구성
     - `/`: 채널 ID 입력 후 `fetch` 호출, 진행 상황 출력.
     - `/videos`: 수집된 목록 표시, 개별 영상 선택 시 `process` 실행.
     - `/reports`: `report` 결과를 표/카드 형태로 시각화.
   - `fetch`/`process` 호출 시 로딩 상태와 결과를 Toast/Modal로 표시.

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

## 3. AWS 간단 배포 시나리오
1. **백엔드**
   - FastAPI 앱을 AWS Lambda + API Gateway HTTP API로 배포(SAM 또는 AWS CDK 사용).
   - Cognito 미도입 시에는 API 키 기반 단순 보호, 이후 OIDC Authorizer로 교체.

2. **프런트엔드**
   - `npm run build` 산출물을 S3 정적 호스팅 버킷에 업로드.
   - CloudFront 배포를 붙여 HTTPS/캐싱 제공.
   - 환경 변수는 CloudFront Behavior마다 Lambda@Edge 또는 S3 객체 내 `config.json`으로 주입.

3. **CI/CD**
   - GitHub Actions 워크플로우에서 백엔드(Lambda)와 프런트엔드(S3)에 각각 배포 단계 추가.
   - 배포 후 Smoke Test(헬스체크, 기본 API 호출) 수행.

## 4. 보안 및 확장 고려
- **인증**: 초기 프로토타입에서는 로컬/내부 사용자 가정 → 이후 Cognito Hosted UI 또는 OAuth2 PKCE 흐름 도입.
- **비용 절감**: API 호출, OpenAI 사용량을 프런트엔드에서 보여주고 한 번에 실행 가능한 요청 수 제한.
- **실시간 피드백**: Step Functions/SQS 도입 전까지는 폴링 기반, 이후 WebSocket/API Gateway + DynamoDB Streams로 확장.

## 5. 향후 작업 목록
- [ ] `app/web/api.py` 모듈 스켈레톤 작성 (FastAPI 인스턴스, 라우터, 의존성 주입).
- [ ] `frontend/` 템플릿 생성 및 API 클라이언트 유틸 구현.
- [ ] 로컬 개발용 docker-compose(선택) 작성: FastAPI, LocalStack, DynamoDB Local 등.
- [ ] QA 체크리스트 작성: API 응답 타임아웃, 오류 핸들링, 토큰 만료 처리.
- [ ] 문서화: 사용자 가이드, 설치 스크립트, 스크린샷.

위 로드맵을 통해 기존 CLI 중심 구조를 손대지 않으면서도, 브라우저에서 접근 가능한 간단한 웹 서비스 형태로 확장할 수 있습니다.
