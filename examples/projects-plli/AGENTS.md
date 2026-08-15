# Asterum Interpreter Guidelines

## 역할과 우선순위

아스테룸어 해석기 실습 프로젝트를 구현하는 풀스택·ML 엔지니어로 작업한다.

1. 정답 무결성: 승인된 28개 문자 매핑과 순서 있는 label만 정답으로 사용한다.
2. 결정적 해석: 인식된 자모는 명시된 한글 조합 규칙으로 변환하며 생성형 AI로 보정하지 않는다.
3. 사용자 자료 보호: 업로드 이미지와 결과 문자열을 저장하거나 로그에 남기지 않는다.
4. 재현 가능성: Python 3.14.7, uv lock, 고정 평가 세트와 자동 테스트를 유지한다.
5. 학습 가능성: 비개발자도 작은 단계와 검증 결과를 보고 다음 작업을 승인할 수 있게 한다.

## 새 작업 시작 순서

1. 이 파일에서 프로젝트 규칙을 확인한다.
2. `README.md`에서 현재 구현 범위와 실제 명령을 확인한다.
3. `docs/asterum-grammar.md`에서 문자 해석 규칙과 미확정 항목을 확인한다.
4. 저장소 root의 `plan.md`와 `git status --short --branch`를 확인한다.
5. 관련 코드와 테스트를 읽어 문서가 실제 구현과 일치하는지 확인한다.

이 디렉터리에서는 이 문서가 상위 저장소의 Palmsicle/React Native 규칙보다 우선한다. 상위 문서의 한국어 응답, 변경 보존, 큰 변경 전 `plan.md` 작성, 명시적 요청 없는 commit 금지 규칙은 유지한다.

## 작업 범위와 승인

- 사용자가 요청하지 않은 기존 변경을 되돌리거나 덮어쓰지 않는다.
- 큰 변경 전 저장소 root의 `plan.md`에 목표, 범위, 단계, 검증 방법을 기록한다.
- commit, push, PR, 배포는 사용자가 명시적으로 요청한 경우에만 수행한다.
- 단계별 작업 후 변경 파일, 검증 결과, 미해결 위험을 보고한다.
- 기술 스택이나 공개 계약을 바꿔야 하면 실패 재현과 대안을 제시하고 승인을 기다린다.
- 매핑, 폰트, 문장 이미지, label, 권리 정보를 실제 자료처럼 임의 생성하지 않는다.
- 아직 구현되지 않은 기능과 명령을 동작하는 것처럼 문서화하지 않는다.

## 확정 기술과 제외 기술

### Backend와 ML

- Python은 API, OCR, 학습 도구 모두 `3.14.7`로 고정한다.
- 의존성, 가상환경, 실행, lock은 uv만 사용한다.
- 표준 명령은 `uv add`, `uv remove`, `uv sync --frozen`, `uv run`, `uv lock --check`다.
- 패키지 메타데이터는 PEP 621, build backend는 `uv_build`, 잠금 파일은 `uv.lock`을 사용한다.
- API는 FastAPI와 Pydantic v2, 이미지 처리는 OpenCV, Pillow, pillow-heif를 사용한다.
- OCR 학습·추론은 Python 3.14.7에서 검증된 PyTorch를 사용한다.
- 테스트와 정적 검사는 pytest, Ruff, mypy를 사용한다.
- Python 3.14.7을 지원하지 않는 의존성 때문에 Python을 자동으로 낮추거나 제품을 무단 교체하지 않는다.

### Frontend와 운영

- frontend는 React, TypeScript, Vite, TanStack Query, React Hook Form, Zod, CSS Modules를 사용한다.
- UI 검증은 Vitest, Testing Library, Playwright를 사용한다.
- Traefik은 외부 routing과 TLS, Nginx는 React 정적 파일과 SPA fallback을 담당한다.
- 실습 버전의 FastAPI는 요청 안에서 OCR을 동기 실행하고 결과를 바로 반환한다.
- 계정, 영구 DB, Redis, Celery, RAG, Caddy, Streamlit은 현재 범위에 포함하지 않는다.
- 동시 사용자가 생기거나 처리시간이 실측 기준을 넘을 때만 작업 큐 도입을 별도 결정한다.

## 코드 경계

- `backend/src/asterum/api`: HTTP 입력 검증, 응답 schema, 오류 변환
- `backend/src/asterum/domain`: 외부 framework를 모르는 매핑·자모 조합 규칙
- `backend/src/asterum/data`: 자산 import, schema, checksum, dataset 검증
- `backend/src/asterum/ocr`: 전처리, 검출, 분류, confidence 계산
- `backend/tests`: domain, API, asset, OCR 계약 테스트
- `frontend`: React 웹 앱
- `assets/asterum`: 문자 SVG, 매핑, dataset manifest, 폰트, 권리 문서
- `infra`: Traefik, Nginx, Docker Compose
- `.agents/skills`: 이 프로젝트에서 반복 검증하는 에이전트 절차

API가 domain/data를 호출할 수 있지만 domain/data가 FastAPI를 import하지 않게 한다. OCR이 HTTP request나 React 표현을 알지 않게 한다.

## Coding convention

### Python

- public 함수와 method의 입력·출력 타입을 명시하고 mypy strict를 통과시킨다.
- Pydantic 공개 model은 `extra="forbid"`를 기본으로 사용한다.
- 파일과 함수는 `snake_case`, class는 `PascalCase`, 상수는 `UPPER_SNAKE_CASE`를 사용한다.
- 경로는 `pathlib.Path`, 문자열 정규화는 NFC, 자산 식별자는 ASCII `snake_case`를 사용한다.
- domain 오류는 위치와 안정적인 오류 코드를 포함한 구조화된 값으로 반환한다.
- broad `except Exception`으로 오류를 숨기거나 실패를 빈 성공값으로 바꾸지 않는다.
- 이미지, 인식 문자열, 개인정보, 로컬 절대 경로를 운영 log에 남기지 않는다.
- Ruff format을 적용하고 불필요한 `noqa`, `type: ignore`를 추가하지 않는다.

### React

- component 파일과 component는 `PascalCase`, hook은 `use*`, 일반 module은 `camelCase`를 사용한다.
- 서버 응답은 `unknown`으로 받아 Zod로 runtime 검증한다.
- TanStack Query는 서버 상태에만 사용하고 같은 결과를 별도 전역 store에 중복 저장하지 않는다.
- 화면은 loading, success, no-text, low-confidence, invalid-file, inference-error를 구분한다.
- API 호출과 화면 표현을 분리하고 여러 화면에서 쓰는 순수 UI만 공용 component로 추출한다.
- 키보드 탐색, focus, screen reader label/state, 색상 대비, 44px touch target을 검증한다.

### 테스트와 파일

- 새 domain 규칙에는 성공·경계·실패 테스트를 함께 작성한다.
- 테스트 이름은 관찰 가능한 동작을 설명한다.
- generated dataset, model weight, upload image, `.env`, secret을 commit하지 않는다.
- 합성 이미지는 train에만 사용하고 validation/test에는 넣지 않는다.
- 손글씨 split은 writer와 촬영 session을 묶은 `group_id` 단위로 나눈다.

## 자산, 매핑, label

- 단일 매핑 파일은 `assets/asterum/mapping/asterum.mapping.v1.json`이다.
- 28개 SVG는 `assets/asterum/characters/svg`에 저장한다.
- 매핑의 `glyph_id`, `source_svg`, `ko_jamo`는 중복될 수 없다.
- SVG 변경은 안전 구조, 개수, 예상 자모, 경로, SHA-256을 검증한다.
- 정답 파일명에는 한글, 정답 문자열, PUA, 실제 작성자 이름을 넣지 않는다.
- `labels.json`은 순서 있는 `glyph_id` token, split, group, checksum, license를 가진다.
- 파일명을 분석해 정답을 생성하지 않는다. 한글 결과는 매핑과 조합기로 계산한다.
- 자산 사용 범위는 `assets/asterum/licenses/README.md`를 따른다. 현재 28개 SVG는 합성 데이터와 OCR 모델 학습에 사용할 수 있지만 운영 서비스 배포와 외부 재사용은 별도 확인한다.
- 관련 작업에는 `$asterum-asset-audit` skill을 사용한다.

## API와 개인정보

- 공개 endpoint는 `/api/v1` 아래에 둔다.
- 예정된 사진 해석 endpoint는 `POST /api/v1/interpret`이며 multipart 이미지 한 장을 동기 처리한다.
- 지원 입력은 JPEG, PNG, WebP, HEIC/HEIF, 최대 10MB와 25MP다.
- 확장자가 아니라 실제 content와 decoder 결과로 형식을 확인한다.
- 임시 파일을 만들면 성공·실패·취소와 관계없이 응답 전에 삭제한다.
- 입력 이미지와 결과 문자열은 DB, cache, log, metric label에 저장하지 않는다.
- 오류 코드는 `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `IMAGE_TOO_LARGE`, `NO_TEXT_DETECTED`, `LOW_CONFIDENCE`, `UNSUPPORTED_CHARACTER`, `INFERENCE_FAILED`로 고정한다.
- 계약 변경 시 backend schema, frontend Zod schema, 테스트, README를 함께 갱신한다.

## 검증 기준

- 기본: `uv lock --check`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy backend`, `uv run pytest`
- 자산: `uv run asterum-asset-audit`
- 매핑: 문자 28개, 중복 없음, NFC, checksum, `ㄱ ㅑ ㅇ ㅗ ㅐ → 갸왜`
- OCR: 분리된 실제 test set에서 인쇄 문자 정확도 98% 이상
- 손글씨: writer/session 누수 없는 test set에서 90% 이상일 때만 beta 활성화
- 성능: 실습 기준 장비와 입력 조건을 기록한 뒤 p95 5초 이하
- 개인정보: 성공과 모든 실패 경로에서 임시 이미지가 남지 않는지 검증
- 실행하지 못한 검증은 이유와 남은 위험을 최종 보고에 포함한다.

## Skill 관리

- 항상 적용되는 원칙은 이 문서에 두고 반복 실행되는 안정된 절차만 skill로 만든다.
- 현재 skill은 SVG import와 매핑 검증을 담당하는 `$asterum-asset-audit` 하나다.
- dataset 생성, OCR 평가, 배포는 실제 script와 중단 조건이 확정된 뒤 각각 별도 skill로 만든다.
- skill은 프로젝트에 의존하므로 `.agents/skills` 아래에서 관리한다.

## Git commit convention

형식은 `<type>(<scope>): <subject>`다. `scope`는 선택이며 subject는 한글 50자 이내의 명령형 요약으로 쓰고 마침표를 붙이지 않는다.

- `feat`: 기능 추가
- `fix`: 버그 수정
- `refactor`: 기능 변화 없는 구조 개선
- `docs`: 문서 변경
- `style`: 코드 의미에 영향 없는 형식 변경
- `test`: 테스트 추가·수정
- `chore`: build, 의존성, 환경, 자동화

예시:

- `feat(mapping): 기본 문자 매핑 검증 추가`
- `test(domain): 한글 자모 조합 경계 검증`
- `docs: 바이브코딩 실행 절차 보완`
- `chore(python): uv 개발환경 구성`

commit 전 `git status`, 전체 diff, staged diff를 확인하고 요청 범위의 파일만 stage한다. `plan.md`, secret, 로컬 환경, 모델 weight, generated dataset, 사용자 비공개 원본은 제외한다.
