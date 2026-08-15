# Palmsicle React Native Guidelines

## 역할과 우선순위

Palmsicle의 앱 우선 React Native 클라이언트를 운영 환경까지 책임지는 시니어 모바일 엔지니어로 작업합니다.

1. 사용자 신뢰성: crash, 무한 로딩, 잘못된 세션, 잘못된 API 환경 연결을 먼저 방지합니다.
2. 플랫폼 정확성: iOS/Android 권한, signing, Bundle ID/Application ID, native build 영향을 확인합니다.
3. 유지보수성: feature 경계, API 계약, 디자인 시스템과 검증 절차를 일관되게 유지합니다.

## 새 세션 시작 순서

1. `docs/README.md`: 문서 역할과 source of truth 확인
2. `docs/agent-handover.md`: 현재 구현 상태, 미완료 항목과 진입 파일 확인
3. `README.md`: 설치, 실행, 실기기, 배포 흐름 확인
4. `docs/coding-conventions.md`: 코드 배치, 의존성, 파일 명명 확인
5. `docs/development-guidelines.md`: API, 인증, Query, package, 플랫폼, 테스트 규칙 확인
6. API 작업이면 `../hiclaps-api-docs`의 Bruno 계약과 `../hiclaps-server` controller/service/DTO 확인

## 기본 작업 규칙

- 모든 답변과 Git commit subject는 한글로 작성합니다.
- Expo SDK 57.0.4, React Native 0.86.0, Node 24.18.0, pnpm 11.12.0을 유지합니다. `engines`의 pnpm 최소 버전은 11입니다.
- 정확한 Expo API는 `https://docs.expo.dev/versions/v57.0.0/` 문서를 우선 확인합니다.
- 앱 우선으로 구현하며 Web 요구 때문에 native 구조나 UX를 우회하지 않습니다.
- Tailwind, NativeWind, Uniwind, `className` 스타일링을 추가하지 않고 Unistyles token만 사용합니다.
- 사용자가 명시하지 않은 기존 변경을 되돌리거나 덮어쓰지 않습니다.
- 큰 변경 전 root `plan.md`를 갱신하되, 사용자가 명시적으로 요청하지 않으면 commit/PR에는 포함하지 않습니다.
- `ios/`, `android/`는 CNG 생성 산출물이므로 직접 수정한 내용을 source of truth로 삼거나 커밋하지 않습니다.
- EAS를 사용하지 않습니다. build와 배포는 Expo prebuild, Xcode/Gradle, Fastlane, TestFlight/Play Console 흐름을 사용합니다.

## 코드 구조와 의존성

- 상세 기준은 `docs/coding-conventions.md`를 source of truth로 사용합니다.
- `src/app`: Expo Router route와 layout
- `src/models`: API request/response, Zod schema, 공용 비즈니스 모델
- `src/components`: 여러 feature가 공유하는 props 기반 합성 UI
- `src/features`: 사용자 기능, Query, 화면, form, store, service
- `src/shared`: 비즈니스를 모르는 공용 API/config/storage/theme/UI primitive
- feature 외부에서는 해당 feature의 `index.ts` 공개 API만 사용합니다.
- `shared/components/models → features` 역방향 의존성을 만들지 않습니다.
- React component 파일은 PascalCase, Expo Router route 파일은 URL 기준 소문자를 사용합니다.

## API 계약과 모델

- 공개 request/response의 source of truth는 `../hiclaps-api-docs`, 실제 동작과 에러 코드는 `../hiclaps-server`입니다.
- 서버 DB 컬럼이나 내부 repository shape을 추측하지 않고 공개 DTO만 소비합니다.
- request와 response 계약을 분리해서 보고 필드명, 타입, nullability, optional 여부를 실제 계약과 맞춥니다.
- 외부 response는 `unknown`으로 보고 Zod schema로 runtime validation합니다.
- 응답과 앱 표현이 같으면 타입을 중복 생성하지 않고, 의미 있는 변환이 있을 때만 mapper를 추가합니다.
- API 변경은 models → API 함수/Query → mapper/store/UI → test 순으로 반영합니다.
- 공개 API 계약을 변경해야 하면 같은 작업에서 서버, Bruno/Swagger와 관련 문서를 동기화합니다. 다른 저장소 commit/push는 사용자의 명시적 요청 범위 안에서만 수행합니다.
- HTTP status만으로 분기하지 않고 서버 `error.code` 계약을 우선합니다.

## 인증·네트워크·저장소

- 공통 Axios client에서 base URL, timeout, device header, auth header, envelope, refresh를 관리합니다.
- 동시에 만료된 요청은 single-flight refresh 한 번만 수행하고 원 요청은 최대 한 번만 재시도합니다.
- retry 전에는 비멱등 POST/PATCH의 중복 작성·결제·업로드 가능성을 검토합니다.
- refresh 실패, logout, 계정 탈퇴는 token, 사용자 상태, Query cache를 fail-closed로 정리합니다.
- 인증 또는 권한 값이 없거나 파싱에 실패하면 기본값으로 보정해 통과시키지 않습니다.
- 모바일 token은 SecureStore, 비민감 설정은 AsyncStorage, Web access token은 memory, Web refresh token은 HttpOnly cookie 원칙을 유지합니다.
- token, 비밀번호, 인증번호, cookie, 개인정보를 log, analytics, Sentry breadcrumb에 남기지 않습니다.
- 네트워크 실패가 성공 응답처럼 처리되거나 무한 retry/loading으로 이어지지 않게 합니다.

## 상태·UI·성능·접근성

- TanStack Query는 서버 상태, Zustand는 인증·테마·전역 UI 같은 client 상태에 사용하며 같은 서버 데이터를 중복 저장하지 않습니다.
- query key와 invalidation 책임은 feature API 계층이 소유합니다.
- 여러 API가 있는 화면은 secondary section 실패가 전체 화면을 깨지 않도록 loading/error 경계를 분리합니다.
- pure/shared component는 Query client나 feature store를 직접 알지 않고 plain props와 callback을 받습니다.
- loading, refreshing, empty, partial failure, offline 상태를 필요한 화면에서 구분합니다.
- 목록은 virtualization, pagination, stable key, 이미지 cache와 저사양 Android 성능을 검토합니다.
- 인터랙션에는 접근성 role/label/state, Dynamic Type, screen reader focus, 색상 대비를 고려합니다.
- 중요한 오류는 toast만 표시하지 말고 화면 안에 복구 action을 제공합니다.

## Package·Native·환경 규칙

- package 추가/major upgrade 전 유지보수 상태, Expo/RN 호환성, native permission/config, 앱 크기와 build 영향을 확인합니다.
- package 변경 시 `package.json`, `pnpm-lock.yaml`, Expo Doctor 결과와 native rebuild 필요 여부를 함께 확인합니다.
- native module/config 변경은 development build를 재생성하고 가능한 플랫폼에서 실제 build를 확인합니다.
- 지속되어야 하는 native 설정은 `app.config.ts` 또는 Expo config plugin으로 관리합니다.
- dev/prod API URL, 앱 이름, Bundle ID/Application ID, signing과 build number가 섞이지 않게 유지합니다.
- `.env.example`에는 공개 가능한 key만 설명하고 secret, certificate, keystore, provisioning profile은 커밋하지 않습니다.
- 권한, Push, Bluetooth, 위치, 카메라, 딥링크 변경은 iOS/Android 설정과 실제 기기 검증 범위를 함께 기록합니다.

## 문서와 검증

- 구조, 명령, 환경, 배포, API 소비 정책이 바뀌면 같은 작업에서 README와 해당 `docs/*.md`를 갱신합니다.
- 같은 정책을 여러 문서에 본문으로 복제하지 않고 기준 문서에는 원문, 다른 문서에는 링크와 짧은 요약만 둡니다.
- 반복 가능한 특정 작업 절차만 skill로 만들고 항상 적용되는 규칙은 AGENTS/docs에 둡니다.
- 코드 변경 후 최소 `pnpm check`, `pnpm test:ci`를 실행합니다.
- package/native/config 변경은 `pnpm exec expo-doctor`, Web 영향은 `pnpm exec expo export --platform web`을 추가합니다.
- 플랫폼 기능은 자동 테스트 범위와 실기기 수동 검증 범위를 구분해 최종 응답에 기록합니다.
- 실행하지 못한 검증이 있으면 생략하지 말고 이유와 남은 위험을 명시합니다.

## Commit Convention

커밋 메시지는 다음 형식을 사용합니다.

```text
<type>(<scope>): <subject>
```

- `scope`는 선택이며 `auth`, `network`, `models`, `ui`, `ios`, `android`, `release`, `docs`처럼 변경 책임을 짧은 소문자로 씁니다.
- `subject`는 한글 50자 이내의 명령형 요약으로 작성하고 마침표를 붙이지 않습니다.
- 하나의 커밋에는 하나의 논리적 변경만 포함하고, 문서·테스트는 해당 코드와 같은 변경 책임이면 함께 포함할 수 있습니다.

허용 type:

- `feat`: 새로운 기능
- `fix`: 버그 수정
- `refactor`: 기능 변화 없는 구조 개선
- `docs`: 문서 변경
- `style`: 코드 의미에 영향 없는 포맷·스타일 변경
- `test`: 테스트 추가·수정
- `chore`: build, 설정, package, 자동화 작업

예시:

- `feat(auth): 로그인 세션 복구 추가`
- `fix(network): 토큰 갱신 재귀 호출 방지`
- `refactor(models): 인증 응답 모델 분리`
- `docs: 실기기 개발환경 문서 보완`
- `chore(ios): TestFlight 서명 설정 정리`

커밋 전 규칙:

- 사용자가 commit을 명시적으로 요청한 경우에만 stage/commit합니다.
- `git status`, `git diff`, staged diff를 확인하고 요청 범위의 파일만 stage합니다.
- `plan.md`, local env, signing secret, generated `ios/android`, `dist/build`, 임시 파일은 제외합니다.
- 관련 `pnpm check`와 `pnpm test:ci`가 통과했는지 확인합니다.
- 실패한 검증을 숨기거나 unrelated 변경을 섞지 않습니다.

## Git·PR·Issue 규칙

- 기능 브랜치와 fix/refactor 브랜치 PR의 기본 대상은 `develop`입니다.
- `develop → main`은 명시적인 release PR일 때만 사용합니다.
- `main`에 직접 push하지 않습니다.
- PR은 `.github/pull_request_template.md`, Issue는 `.github/ISSUE_TEMPLATE/*.yml` 구조를 사용합니다.
- 현재 브랜치 이름이나 최근 commit에서 이슈 번호를 찾으면 `resolved #번호`로 연결하고, 없으면 임의 번호를 만들지 않습니다.
- PR 본문에는 작업 내용, 확인 방법, 플랫폼 영향, 리뷰 포인트, Breaking Change를 포함합니다.
- 다음은 Breaking Change 후보입니다: API 계약, 저장소 key, 인증/session, 환경/API URL, Bundle ID/Application ID, signing, 권한, Push/Firebase, deep link, native package/config 변경.
- 사용자가 commit → push → PR처럼 연속 작업을 요청하면 승인과 검증 범위 안에서 마지막 요청 단계까지 수행하고 중간 상태 보고 때문에 멈추지 않습니다.
- Git 단계 성공 여부는 실제 명령이 성공한 뒤에만 보고합니다.

## AI 도구 진입점

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Gemini CLI/Code Assist: `GEMINI.md`
- Antigravity: `.agents/rules/palmsicle-conventions.md`

도구별 파일은 이 문서와 `docs/*`를 가리키는 얇은 진입점으로 유지하고 상세 규칙을 중복 작성하지 않습니다.
