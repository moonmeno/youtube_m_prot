# YouTube 데이터 분석 프로토타입 설계

본 문서는 Python 기반으로 YouTube Data API, OpenAI API, AWS를 연동하는 프로토타입의 아키텍처 개요를 기술한다.

## 목표
- 최소 기능: 채널 단위 데이터 수집, 원본 저장, OpenAI 분석, 결과 리포팅
- 확장 용이성: 서버리스 및 마이크로서비스로 확장할 수 있는 모듈 구조
- 운영 편의: CLI 중심의 단순 제어, 향후 웹/확장 프로그램으로 확장 가능

## 모듈 구성
- `app.cli`: 단순한 명령줄 인터페이스
- `app.youtube`: YouTube Data API 래퍼 및 모델 정의
- `app.ai`: OpenAI 연동 및 분석 로직
- `app.storage`: S3 등 저장소 추상화
- `app.orchestration`: 작업 큐 및 파이프라인 스텁
- `app.utils`: 로깅, 재시도 등 공통 유틸리티

## 데이터 흐름
1. `fetch` 명령 → YouTube API 호출 → S3에 원본 저장
2. `process` 명령 → OpenAI로 분석 → 처리 결과 저장
3. `report` 명령 → 저장된 결과를 요약 출력

## AWS 연동 계획
- **S3**: 원본/결과 저장
- **SQS/Step Functions**: 비동기 작업 큐, 상태 추적
- **Lambda**: API 호출 래퍼 및 배치 작업 실행
- **Secrets Manager**: API 키 및 민감 정보 관리

## 향후 확장 포인트
- FastAPI 기반 REST API 및 React 대시보드 추가 (간단한 실행 시나리오는 `docs/web_prototype.md` 참고)
- 크롬 확장프로그램과의 연동
- 비용 모니터링 및 경보 설정

