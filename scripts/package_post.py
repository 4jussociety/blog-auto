"""
리무브 체형교정 - 블로그 포스트 단일 통합 패키징 도구
기능:
1. 마크다운 포스트 파일에서 사용된 이미지들을 검색하여 output/<포스트명>/images/ 폴더로 번호순 복사
2. 본문복사용/스타일가이드 2종 분리를 없애고 단일 통합 원고(<포스트명>.md) 하나로 통일하여 보관
"""

import os
import re
import shutil
import sys
from pathlib import Path

# 윈도우 콘솔 UTF-8 인코딩 설정
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = BASE_DIR / "images"
ASSESTS_DIR = BASE_DIR / "assests"


def find_image_file(rel_path_str: str) -> Path | None:
    """assets, images, assests 폴더 등에서 파일 이름으로 이미지를 검색합니다."""
    clean_name = Path(rel_path_str).name
    # 1. 직접 상대경로 확인
    direct = BASE_DIR / rel_path_str
    if direct.exists() and direct.is_file():
        return direct

    # 2. 주요 에셋 폴더 검색
    candidates = [
        ASSETS_DIR / clean_name,
        ASSETS_DIR / "리뷰" / clean_name,
        IMAGES_DIR / clean_name,
        ASSESTS_DIR / clean_name,
        ASSESTS_DIR / "리뷰" / clean_name,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c

    # 3. 전체 assets 내 검색
    for p in ASSETS_DIR.rglob(clean_name):
        if p.is_file():
            return p

    return None


def package_single_post(md_file_path: Path):
    """마크다운 포스트 1개를 패키징하여 output/<stem>/ 폴더에 단일 원고와 이미지로 정돈"""
    stem = md_file_path.stem
    if stem.endswith("_본문복사용") or stem.endswith("_스타일가이드") or stem == "README":
        return

    print(f"\n📦 패키징 시작: {md_file_path.name}")
    content = md_file_path.read_text(encoding="utf-8")

    post_output_dir = OUTPUT_DIR / stem
    images_output_dir = post_output_dir / "images"
    post_output_dir.mkdir(parents=True, exist_ok=True)
    images_output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 이미지 마커 분석 및 복사
    image_markers = list(re.finditer(r"\[IMAGE:\s*([^\]]+)\]", content))
    print(f"   총 {len(image_markers)}개의 이미지를 발견했습니다.")

    image_mapping = {}  # 원본 경로 -> 새 상대 경로
    for idx, match in enumerate(image_markers, 1):
        orig_path = match.group(1).strip()
        found = find_image_file(orig_path)
        if found:
            ext = found.suffix
            orig_stem = found.stem
            new_filename = f"{idx:02d}_{orig_stem}{ext}"
            dest_file = images_output_dir / new_filename
            shutil.copy2(found, dest_file)
            image_mapping[orig_path] = f"images/{new_filename}"
            print(f"   ✅ [사진 {idx}] 복사 완료: {found.name} -> images/{new_filename}")
        else:
            print(f"   ⚠️ 이미지를 찾을 수 없음: {orig_path}")
            image_mapping[orig_path] = orig_path

    # 2. 이미지 경로가 로컬 images/ 로 보정된 단일 통합 원고 생성
    def replace_img_path(m):
        orig_p = m.group(1).strip()
        new_rel = image_mapping.get(orig_p, orig_p)
        return f"[IMAGE: {new_rel}]"

    unified_content = re.sub(r"\[IMAGE:\s*([^\]]+)\]", replace_img_path, content)

    # 단일 통합 원고 저장
    unified_file_path = post_output_dir / f"{stem}.md"
    unified_file_path.write_text(unified_content, encoding="utf-8")
    print(f"   📄 단일 통합 원고 생성: {unified_file_path.name}")

    # 3. 브라우저에서 바로 훑어볼 수 있는 프리뷰 HTML 자동 생성
    try:
        from generate_preview import generate_preview_html
    except ImportError:
        from scripts.generate_preview import generate_preview_html
    preview_html_path = post_output_dir / f"{stem}_미리보기.html"
    generate_preview_html(unified_file_path, preview_html_path)
    print(f"   👁️ 프리뷰 HTML 생성: {preview_html_path.name}")
    print(f"   ✨ 패키징 완료! 폴더 위치: output/{stem}/")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target_files = []

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.exists() and p.is_file() and p.suffix == ".md":
                target_files.append(p)
            elif (BASE_DIR / arg).exists():
                target_files.append(BASE_DIR / arg)
    else:
        for f in BASE_DIR.glob("*.md"):
            name = f.name
            if name.endswith("_본문복사용.md") or name.endswith("_스타일가이드.md") or name == "README.md":
                continue
            target_files.append(f)

    if not target_files:
        print("대상 마크다운 포스트 파일을 찾을 수 없습니다.")
        return

    print(f"🚀 총 {len(target_files)}개 포스트의 패키징을 시작합니다...")
    for f in target_files:
        package_single_post(f)

    print("\n🎉 모든 포스트 패키징이 단일 통합 규격으로 깔끔하게 완료되었습니다!")


if __name__ == "__main__":
    main()
