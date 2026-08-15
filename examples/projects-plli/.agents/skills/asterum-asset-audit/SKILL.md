---
name: asterum-asset-audit
description: Audit and import the 28 Asterum SVG source glyphs and their versioned mapping. Use when adding, replacing, reviewing, or validating files under assets/asterum/characters or assets/asterum/mapping, before dataset generation or OCR work.
---

# Asterum Asset Audit

아스테룸 SVG와 매핑의 개수, 스키마, 경로, checksum, 안전성을 같은 명령으로 검증한다.

## Workflow

1. 프로젝트 root에서 `AGENTS.md`, `README.md`, `git status --short --branch`를 확인한다.
2. 기존 매핑과 SVG 변경을 먼저 읽는다. 사용자 변경을 덮어쓰지 않는다.
3. 검증만 필요하면 다음 명령을 실행한다.

   ```bash
   uv run asterum-asset-audit
   uv run pytest backend/tests/test_asset_audit.py
   ```

4. 사용자가 검토한 28개 SVG를 가져오라고 요청한 경우에만 다음 명령을 사용한다.

   ```bash
   uv run asterum-import-characters --source "/absolute/path/to/characters"
   ```

5. 대상 파일이 기존 파일과 다르면 import가 중단된다. diff와 출처를 확인하기 전에는 `--force`를 사용하지 않는다.
6. 결과에서 `ok`, 문자 수, 매핑 버전, issue code를 보고한다.

## Stop conditions

- SVG가 28개가 아니거나 예상 자모가 빠진 경우
- 외부 참조, `script`, `foreignObject` 등 안전하지 않은 SVG 구조가 있는 경우
- checksum, 중복, 매핑 경로 검증이 실패한 경우
- 출처 또는 사용 권리가 확인되지 않은 자산으로 공개 배포나 모델 학습을 요청한 경우

검증 실패를 임의로 수정하거나 운영 자료를 추측하지 않는다. 변경 파일, 실행 명령, 검증 결과, 남은 권리 문제를 함께 보고한다.
