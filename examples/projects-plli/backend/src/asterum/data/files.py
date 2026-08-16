"""여러 데이터 도구가 공통으로 사용하는 파일 관련 함수."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """큰 파일도 메모리에 한꺼번에 올리지 않고 SHA-256 checksum을 계산한다.

    checksum은 파일 내용이 같으면 항상 같은 값이므로, 복사·crop 결과가 예상한 파일인지
    확인하는 식별자로 사용한다.
    """

    digest = hashlib.sha256()
    with path.open("rb") as file:
        # 1MB씩 읽어 사진이나 모델처럼 큰 파일도 메모리를 적게 사용한다.
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
