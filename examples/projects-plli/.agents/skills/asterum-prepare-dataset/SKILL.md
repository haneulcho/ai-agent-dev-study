---
name: asterum-prepare-dataset
description: Safely crop, split, resize, and preprocess Asterum OCR training images with the project CLI. Use when preparing local printed or handwriting images, reproducing page splits from crop recipes, generating grayscale/contrast/binary variants, or checking that generated image artifacts remain outside Git.
---

# Asterum Dataset Preparation

원본을 보존하면서 versioned crop recipe와 공용 전처리 CLI로 학습 이미지를 준비한다.

## Workflow

1. 프로젝트 root에서 `AGENTS.md`, `README.md`, `git status --short --branch`를 확인한다.
2. 입력 이미지의 학습 권리, 분류, 작성자·촬영 session 정보를 확인한다.
3. 페이지 분할이면 recipe를 먼저 검증한다.

   ```bash
   uv run asterum-prepare-images crop \
     --recipe assets/asterum/datasets/crop-recipes.v1.json \
     --dry-run
   ```

4. dry-run의 출력 크기와 대상 경로를 확인한 뒤 실제 crop을 실행한다. 기존 결과를 검토 없이 덮어쓰지 않는다.

   ```bash
   uv run asterum-prepare-images crop \
     --recipe assets/asterum/datasets/crop-recipes.v1.json
   ```

5. OCR 비교용 전처리는 `assets/asterum/datasets/work` 아래에 생성한다. 목적에 따라 `grayscale`, `contrast`, `binary` 중 하나를 선택한다.

   ```bash
   uv run asterum-prepare-images preprocess \
     --input assets/asterum/datasets/printed/raw/images/prt_src0002_img000002.jpeg \
     --output-dir assets/asterum/datasets/work/preprocessed \
     --variant contrast
   ```

6. 결과 이미지의 방향, 잘림, 글자 보존 여부를 시각적으로 확인한다.
7. `sample-inventory.csv`의 크기, SHA-256, 분류, group, annotation 상태를 실제 결과와 동기화한다.
8. raw, crop, 전처리 이미지는 Git에 넣지 않고 code, recipe, manifest, 문서만 stage한다.

## Rules

- crop 좌표는 `[x, y, width, height]` 형식의 0~1 정규화 값으로 기록한다.
- recipe의 입출력은 프로젝트 root 밖을 가리키지 않는다.
- 출력 파일이 이미 있으면 기본 동작을 중단한다. `--overwrite`는 기존 결과와 recipe를 대조한 뒤에만 사용한다.
- 손글씨 자료는 작성자와 촬영 session이 같은 이미지를 동일한 `source_group`으로 유지한다.
- 서로 다른 작성자나 session을 train·validation·test에 나눠 넣지 않는다.
- 정답을 추측하거나 파일명에 한글 정답·실제 작성자 이름을 넣지 않는다.

## Stop conditions

- 입력 이미지의 학습 권리가 확인되지 않은 경우
- dry-run 크기가 예상 페이지 경계와 다른 경우
- crop이 글자를 자르거나 두 작성자의 영역을 함께 포함하는 경우
- 기존 출력과 새 출력의 SHA-256이 달라졌는데 변경 이유를 설명할 수 없는 경우
- 출력이 Git stage 대상에 포함된 경우

중단 시 입력, recipe 항목, 예상·실제 크기와 안전한 다음 조치를 보고한다.
