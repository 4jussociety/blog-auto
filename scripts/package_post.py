# 기능: 블로그 원고와 사용된 이미지를 분석하여 output 폴더에 순서별 번호 사진과 2종 md 파일을 자동 패키징합니다.
# 목적: 네이버 스마트에디터 ONE에 복붙 및 사진 배치를 1분 만에 끝낼 수 있도록 원클릭 패키지를 생성합니다.

import os
import re
import shutil
import sys
from pathlib import Path

# 윈도우 콘솔 UTF-8 인코딩 설정
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
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
    
    # 2. assets 폴더 우선 검색
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
    print(f"\n📦 패키징 시작: {md_file_path.name}")
    content = md_file_path.read_text(encoding="utf-8")

    # 포스트 폴더 이름 생성 (날짜와 제목 기반)
    stem = md_file_path.stem
    # 접미사가 이미 붙은 파일은 제외 (예: _본문복사용, _스타일가이드)
    if stem.endswith("_본문복사용") or stem.endswith("_스타일가이드"):
        return

    post_output_dir = OUTPUT_DIR / stem
    images_output_dir = post_output_dir / "images"
    post_output_dir.mkdir(parents=True, exist_ok=True)
    images_output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 프론트매터 파싱 (제목, 카테고리, 태그)
    title = ""
    category = ""
    tags = []
    
    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    body_content = content
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        body_content = content[frontmatter_match.end():]
        for line in fm.splitlines():
            if line.startswith("title:"):
                title = line.split("title:", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("category:"):
                category = line.split("category:", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("tags:"):
                tags_str = line.split("tags:", 1)[1].strip()
                # 따옴표, 대괄호 완전 제거
                raw_tags = tags_str.split(",")
                tags = [re.sub(r'["\'\[\]\s]', '', t) for t in raw_tags]
                tags = [t for t in tags if t]

    if not title:
        title = stem
    else:
        title = title.strip('"\'')

    tags_line = ", ".join(tags)

    # 2. 이미지 마커 분석 및 번호 매기기
    # 패턴: [IMAGE: 경로]
    image_markers = list(re.finditer(r"\[IMAGE:\s*([^\]]+)\]", body_content))
    image_mapping = {} # 원본 경로 -> (새 파일명, 캡션/설명, 새 상대경로)

    print(f"   총 {len(image_markers)}개의 이미지를 발견했습니다.")

    for idx, match in enumerate(image_markers, 1):
        orig_path = match.group(1).strip()
        found = find_image_file(orig_path)
        if found:
            ext = found.suffix
            orig_stem = found.stem
            # 번호 접두사 부여: 01_원장_프로필.png
            new_filename = f"{idx:02d}_{orig_stem}{ext}"
            dest_file = images_output_dir / new_filename
            shutil.copy2(found, dest_file)
            image_mapping[orig_path] = (new_filename, f"images/{new_filename}")
            print(f"   ✅ [사진 {idx}] 복사 완료: {found.name} -> images/{new_filename}")
        else:
            print(f"   ⚠️ 이미지를 찾을 수 없음: {orig_path}")
            image_mapping[orig_path] = (f"{idx:02d}_누락된이미지.png", f"images/{idx:02d}_누락된이미지.png")

    # 3. 본문 복사용 파일 생성 (순수 텍스트)
    # [IMAGE], [STICKER], [DIVIDER], [QUOTE], [/QUOTE], **볼드**, # 헤딩 등 제거
    clean_body = body_content
    # 이미지 마커 제거
    clean_body = re.sub(r"\[IMAGE:[^\]]+\]", "", clean_body)
    # 스티커 제거
    clean_body = re.sub(r"\[STICKER:[^\]]+\]", "", clean_body)
    # 구분선 제거
    clean_body = re.sub(r"\[DIVIDER\]", "\n\n", clean_body)
    # 인용구 태그 제거
    clean_body = re.sub(r"\[QUOTE\]", "", clean_body)
    clean_body = re.sub(r"\[/QUOTE\]", "", clean_body)
    # 볼드 제거
    clean_body = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_body)
    # 헤딩 기호(#) 제거
    clean_body = re.sub(r"^#{1,6}\s*", "", clean_body, flags=re.MULTILINE)
    # 인용 블록 (>) 기호 제거
    clean_body = re.sub(r"^>\s*", "", clean_body, flags=re.MULTILINE)
    # 연속 빈 줄 정리 (최대 2줄)
    clean_body = re.sub(r"\n{3,}", "\n\n", clean_body).strip()

    copy_paste_text = f"""<!-- 기능: 네이버 블로그 스마트에디터 ONE 본문 입력창에 서식 오류 없이 바로 붙여넣기 위한 순수 텍스트 원고 -->
<!-- 목적: 마크다운 기호와 특수 태그를 모두 배제하여 복사-붙여넣기 편의성을 극대화합니다. -->

[글 제목]
{title}

[카테고리]
{category}

[발행 태그 (쉼표 포함 전체 복사 후 태그 입력창에 붙여넣고 엔터)]
{tags_line}

---
(여기서부터 본문 끝까지 드래그하여 복사 후 에디터 본문에 붙여넣으세요)

{clean_body}
"""
    copy_paste_path = post_output_dir / f"{stem}_본문복사용.md"
    copy_paste_path.write_text(copy_paste_text, encoding="utf-8")
    print(f"   📄 본문복사용 파일 생성: {copy_paste_path.name}")

    # 4. 스타일 가이드 파일 생성
    # [IMAGE: ...] 자리에 번호가 부여된 새 파일명 [📷 사진 N 첨부: 01_... (중앙 정렬)] 주석 삽입
    # [STICKER], [QUOTE], [DIVIDER]에 직관적 주석 배지 삽입
    style_guide_body = body_content

    # 이미지 치환
    img_counter = [0]
    def replace_img(m):
        img_counter[0] += 1
        orig_p = m.group(1).strip()
        new_name = image_mapping.get(orig_p, (f"{img_counter[0]:02d}_사진.png", ""))[0]
        return f"\n\n[📷 사진 {img_counter[0]} 첨부: `images/{new_name}` (중앙 정렬)]\n\n"

    style_guide_body = re.sub(r"\[IMAGE:\s*([^\]]+)\]", replace_img, style_guide_body)

    # 스티커 치환
    style_guide_body = re.sub(r"\[STICKER:\s*greeting\]", r"[🏷️ 스티커 삽입: 인사하는 캐릭터 스티커]", style_guide_body)
    style_guide_body = re.sub(r"\[STICKER:\s*cheering\]", r"[🏷️ 스티커 삽입: 응원/파이팅 캐릭터 스티커]", style_guide_body)
    style_guide_body = re.sub(r"\[STICKER:\s*emphasis\]", r"[🏷️ 스티커 삽입: 주의/강조 캐릭터 스티커]", style_guide_body)
    style_guide_body = re.sub(r"\[STICKER:[^\]]+\]", r"[🏷️ 스티커 삽입]", style_guide_body)

    # 구분선 치환
    style_guide_body = re.sub(r"\[DIVIDER\]", r"\n\n[➖ 구분선 삽입: 기본 가로선]\n\n", style_guide_body)

    # 인용구 치환
    style_guide_body = re.sub(r"\[QUOTE\]", r"\n[💬 인용구 적용 (따옴표 또는 버티컬 라인)]\n> ", style_guide_body)
    style_guide_body = re.sub(r"\[/QUOTE\]", r"\n", style_guide_body)

    # 소제목에 24pt / 굵게 표시
    style_guide_body = re.sub(r"^(#{2,3}\s+.*)$", r"[📌 글자 크기: 24pt / 굵게]\n\1", style_guide_body, flags=re.MULTILINE)

    style_guide_text = f"""<!-- 기능: 네이버 블로그 스마트에디터 ONE 편집 시 글자 크기(pt), 폰트, 사진(번호정렬), 인용구 스타일, 스티커 위치를 안내하는 시각 가이드 -->
<!-- 목적: output 폴더의 images/ 사진들과 1:1 매칭하여 1~2분 만에 완벽한 서식을 적용하도록 돕습니다. -->

# 🎨 {title} - 스마트에디터 ONE 스타일 가이드

> **💡 작업 팁**:
> 1. 같은 폴더의 `{copy_paste_path.name}` 파일 내용을 복사하여 네이버 스마트에디터 본문에 붙여넣습니다.
> 2. 전체 본문 선택(Ctrl+A) 후 글자 모양 **[나눔바른고딕]**(또는 **[나눔스퀘어]**), 글자 크기 **[16pt]** 지정.
> 3. 같은 폴더의 `images/` 폴더에서 **01_, 02_, 03_** 순서대로 사진을 드래그하여 배치합니다.

---

### ⚙️ [기본 설정]
- **글꼴(폰트)**: `나눔바른고딕` (권장) 또는 `나눔스퀘어`
- **기본 본문 크기**: `16pt` (소제목은 `24pt` 볼드, 강조는 `19pt` 볼드)
- **정렬**: 본문 좌측 정렬 (사진 및 슬로건은 중앙 정렬)
- **글 제목**: {title}
- **카테고리**: {category}
- **발행 태그 (드래그하여 바로 복사하세요)**:
```text
{tags_line}
```
*(쉼표 포함 한 줄 전체를 복사하여 네이버 발행 창 태그 입력칸에 붙여넣고 엔터를 치시면 한 번에 등록됩니다)*

---

### 🎨 [텍스트 서식 및 컬러 도구 가이드]
- **글자 색상 (`T.`)**:
  - 일반 본문: `기본 먹색/차콜` (장시간 읽기 편안함)
  - 문제점/경고/통증: `딥 레드/버건디` (팔레트 3열 4~5번째 칸)
  - 해결책/리무브 가치: `딥 그린/네이비` (팔레트 6~8열 4~5번째 칸)
- **글자 배경색 / 형광펜 (`[T]`)** - 글 전체에서 2~3회만 포인트 사용:
  - 핵심 결론 / 약속: `연노랑 (Pastel Yellow)` (팔레트 5열 1번째 칸)
  - 슬로건 / 전문성: `연민트/연두 (Pastel Mint)` (팔레트 6~7열 1번째 칸)
- **밑줄 (`U`)**: 문장 속 핵심 키워드나 수치(예: `연속 1시간`)에 굵게(B)와 함께 적용
- **기울임 (`I`)**: 본문에는 남발하지 않고, `(원장 독백/혼잣말)`이나 `*'환자 말씀 인용'*`에만 적용
- **취소선 (`T`)**: 기존의 잘못된 상식/오해를 반박할 때 사용 (예: ~~단순 마사지~~ -> 진짜 4단계 교정)

---

### 📜 [본문 스타일 편집 가이드]

{style_guide_body}
"""
    style_guide_path = post_output_dir / f"{stem}_스타일가이드.md"
    style_guide_path.write_text(style_guide_text, encoding="utf-8")
    print(f"   🎨 스타일가이드 파일 생성: {style_guide_path.name}")
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
        # 인자가 없으면 워크스페이스의 주요 포스트 마크다운 파일들을 탐색
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

    print("\n🎉 모든 포스트 패키징이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()
