# YouTube 데이터 분석 프로토타입 설계

본 문서는 Python 기반으로 YouTube Data API, OpenAI API, AWS를 연동하는 프로토타입의 아키텍처 개요를 기술한다.

## 목표
- 최소 기능: 채널 단위 데이터 수집, 원본 저장, OpenAI 분석, 결과 리포팅
- 확장 용이성: 서버리스 및 마이크로서비스로 확장할 수 있는 모듈 구조
- 운영 편의: CLI 중심의 단순 제어, 향후 웹/확장 프로그램으로 확장 가능
- **브라우저 기반 접근성**: FastAPI + OAuth2(OIDC) + AWS Cognito를 통해 인증된 사용자만 웹 대시보드에 접근
- **데이터 거버넌스**: 수집된 영상/게시물/댓글 데이터를 AWS 내 안전한 저장소에 보관하고, 프라이버시 제약을 준수

## 모듈 구성
- `app.cli`: 단순한 명령줄 인터페이스
- `app.youtube`: YouTube Data API 래퍼 및 모델 정의
- `app.ai`: OpenAI 연동 및 분석 로직
- `app.storage`: S3 등 저장소 추상화
- `app.orchestration`: 작업 큐 및 파이프라인 스텁
- `app.web`: FastAPI 엔드포인트, OAuth2 인증 미들웨어, 응답 스키마 정의(추가 예정)
- `app.utils`: 로깅, 재시도 등 공통 유틸리티

## 데이터 흐름
1. `fetch` 명령 → YouTube API 호출 → S3에 원본 저장
2. `process` 명령 → OpenAI로 분석 → 처리 결과 저장
3. `report` 명령 → 저장된 결과를 요약 출력
4. (웹) FastAPI → Cognito JWT 검증 → DynamoDB/S3에서 메타데이터/댓글 조회 → React/Vite 대시보드로 전달

## AWS 연동 계획
- **S3**: 원본/결과 저장 (버저닝, KMS 암호화)
- **DynamoDB**: 영상/게시물/댓글 메타데이터 색인, 조회 API의 기본 데이터 소스
- **RDS/Aurora (선택)**: 복잡한 조인/리포팅을 위한 관계형 저장소
- **SQS/Step Functions**: 비동기 작업 큐, 상태 추적
- **Lambda/Fargate**: API 호출 래퍼 및 배치 작업 실행
- **Secrets Manager**: API 키 및 민감 정보 관리
- **Cognito User Pool & Identity Pool**: OAuth2(OIDC) 기반 사용자 인증 및 역할 부여
- **API Gateway**: Cognito JWT 검증 후 FastAPI로 라우팅 (HTTP API 혹은 REST API)

## 향후 확장 포인트
- FastAPI 기반 REST API 및 React 대시보드 추가 (간단한 실행 시나리오는 `docs/web_prototype.md` 참고)
- Chrome 확장프로그램과의 연동 (Cognito 세션 공유 또는 독립 토큰 흐름)
- 비용 모니터링 및 경보 설정 (CloudWatch + QuickSight)
- 브라우저 기반 통합 테스트(Playwright) 도입으로 OAuth2 로그인 및 데이터 조회 플로우 자동 검증

## 인증 및 보안 개요
- **OAuth2 + OIDC**: Cognito Hosted UI와 PKCE 플로우 사용, FastAPI에서 `Authorization: Bearer <JWT>` 헤더 검증.
- **역할 기반 접근 제어(RBAC)**: Cognito 그룹 → FastAPI `Depends` 미들웨어로 권한 확인 (예: `viewer`, `operator`, `admin`).
- **비밀 관리**: OpenAI/YouTube API 키는 Secrets Manager에 저장, Lambda/FastAPI 컨테이너는 부팅 시 세션 캐시 후 사용.
- **로깅**: CloudWatch Logs에 구조화된 JSON 로그, 추적 ID(`X-Request-ID`)를 프런트엔드와 공유.
- **데이터 보존 정책**: S3 Lifecycle로 장기 보관 시 Glacier로 이전, 개인정보가 포함될 수 있는 댓글은 PII 마스킹 후 저장.

## 웹 접근 시나리오
1. 사용자가 Chrome 등 브라우저에서 React 대시보드 접속 → Cognito Hosted UI로 리디렉트.
2. 로그인 성공 후 Access Token/ID Token을 포함한 리디렉션 → 프런트엔드가 토큰을 메모리/세션에 저장.
3. 프런트엔드가 FastAPI `/api/videos`, `/api/posts`, `/api/comments` 엔드포인트 호출 → API Gateway가 Cognito 토큰을 검증 후 전달.
4. FastAPI는 DynamoDB/S3에서 데이터 조합 → 정제된 메타데이터 및 댓글 데이터를 JSON으로 응답.
5. 사용자는 UI에서 원하는 영상 선택 → 상세 정보, 요약, 댓글 리스트, 추가 분석 버튼 표시.

## 테스트 전략(개요)
- **단위 테스트**: YouTube/OpenAI 클라이언트 래퍼, Cognito JWT 검증 유틸, 데이터 매퍼에 대한 Mock 기반 테스트.
- **통합 테스트**: LocalStack + Cognito 모킹 도구를 사용해 인증 흐름을 검증하고, FastAPI TestClient로 API 경로 검증.
- **E2E 테스트**: Playwright(웹)로 Cognito Hosted UI 로그인 → 대시보드 접근 → 영상 목록 조회 → 세부 정보 열람까지 자동화.
- **성능 테스트**: Locust/k6로 `/api/videos` 및 `/api/videos/{id}` 병렬 호출 시 지연 시간을 측정, SQS/Step Functions 부하 대비.

