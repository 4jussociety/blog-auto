"""
리무브 체형교정 - 네이버 블로그 스마트에디터 ONE 자동화 봇
기능:
1. login: 최초 1회 브라우저를 띄워 네이버 로그인 후 영구 프로필(.naver_session) 저장
2. draft: 작성된 마크다운 원고를 파싱하여 네이버 에디터에 제목/본문/사진/스티커/구분선/인용구/태그를 입력하고 [임시저장]
"""

import os
import sys
import time
import re
import argparse
from pathlib import Path

# Windows 콘솔 유니코드 인코딩 보정
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
SESSION_DIR = WORKSPACE_DIR / ".naver_session" / "profile"
BLOG_DIR = WORKSPACE_DIR / "블로그"


def parse_post(file_path: Path):
    """
    마크다운 포스팅 파일 파싱
    ---
    title: 제목
    category: 카테고리
    tags: [태그1, 태그2, ...]
    ---
    본문...
    """
    content = file_path.read_text(encoding="utf-8")
    
    # Frontmatter 추출
    title = ""
    category = "체형/통증 가이드"
    tags = []
    
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if fm_match:
        header, body = fm_match.group(1), fm_match.group(2)
        for line in header.splitlines():
            if line.startswith("title:"):
                raw_t = line.split("title:", 1)[1].strip()
                if (raw_t.startswith('"') and raw_t.endswith('"')) or (raw_t.startswith("'") and raw_t.endswith("'")):
                    title = raw_t[1:-1].strip()
                else:
                    title = raw_t
            elif line.startswith("category:"):
                category = line.split("category:", 1)[1].strip().strip('"\'')
            elif line.startswith("tags:"):
                tags_str = line.split("tags:", 1)[1].strip()
                # [태그1, 태그2] 또는 쉼표 구분
                tags_str = tags_str.strip("[]")
                tags = [t.strip().strip('"\'') for t in tags_str.split(",") if t.strip()]
    else:
        body = content
        # 첫 번째 # 제목을 타이틀로 사용
        first_line = body.strip().splitlines()[0] if body.strip() else "제목 없음"
        if first_line.startswith("#"):
            title = first_line.lstrip("#").strip()
            body = "\n".join(body.strip().splitlines()[1:])
        else:
            title = first_line
            
    return {
        "title": title,
        "category": category,
        "tags": tags,
        "body": body.strip()
    }


def login_helper():
    """최초 1회 로그인 도우미 (로그인 자동 감지)"""
    os.makedirs(SESSION_DIR, exist_ok=True)
    print("=" * 60)
    print(" [네이버 1회 로그인 안내]")
    print(" 브라우저가 열리면 네이버에 로그인해 주세요.")
    print(" 로그인이 완료되면 자동으로 감지하여 세션을 안전하게 저장합니다.")
    print("=" * 60)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://nid.naver.com/nidlogin.login")
        
        print("\n브라우저에서 로그인을 진행해 주세요... (로그인 완료 시 자동 감지됩니다)")
        
        # NID_AUT 쿠키 감지 대기 (최대 5분)
        logged_in = False
        for _ in range(300):
            try:
                cookies = context.cookies()
                if any(c["name"] == "NID_AUT" for c in cookies):
                    logged_in = True
                    break
            except Exception:
                pass
            time.sleep(1)
            
        if logged_in:
            print("\n[*] 네이버 로그인이 성공적으로 감지되었습니다!")
            # 내 블로그로 이동하여 blog_id 자동 추출
            try:
                page.goto("https://blog.naver.com/MyBlog.naver", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                current_url = page.url
                if "blog.naver.com/" in current_url:
                    blog_id = current_url.split("blog.naver.com/")[-1].split("/")[0].split("?")[0]
                    if blog_id and blog_id != "MyBlog.naver":
                        (SESSION_DIR / "blog_id.txt").write_text(blog_id, encoding="utf-8")
                        print(f"[*] 블로그 아이디 확인 완료: {blog_id}")
            except Exception as e:
                print(f"블로그 아이디 추출 건너뜀: {e}")
                
            page.wait_for_timeout(2000)
            print("[*] 로그인 세션이 성공적으로 저장되었습니다! 브라우저를 닫습니다.")
        else:
            print("\n[!] 시간 초과로 로그인이 완료되지 않았습니다.")
            
        context.close()


def draft_post(post_file: Path, category_override: str = None):
    """원고를 읽어 네이버 스마트에디터 ONE에 주입 후 [임시저장] 실행"""
    if not SESSION_DIR.exists():
        print("오류: 저장된 로그인 세션이 없습니다. 먼저 `python scripts/naver_bot.py login`을 실행해주세요.")
        sys.exit(1)

    post_data = parse_post(post_file)
    title = post_data["title"]
    category = category_override or post_data["category"]
    tags = post_data["tags"]
    body = post_data["body"]

    print(f"\n[임시저장 시작]")
    print(f"- 제목: {title}")
    print(f"- 카테고리: {category}")
    print(f"- 태그 ({len(tags)}개): {', '.join(tags[:5])}...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,  # 주입 과정을 눈으로 확인할 수 있도록 False 유지
            channel="chrome",
            viewport={"width": 1280, "height": 960},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        page = context.pages[0] if context.pages else context.new_page()

        # 블로그 아이디 확인
        blog_id = ""
        blog_id_file = SESSION_DIR / "blog_id.txt"
        if blog_id_file.exists():
            blog_id = blog_id_file.read_text(encoding="utf-8").strip()

        if not blog_id:
            print("블로그 아이디 확인 중...")
            page.goto("https://blog.naver.com/MyBlog.naver", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            if "blog.naver.com/" in page.url:
                blog_id = page.url.split("blog.naver.com/")[-1].split("/")[0].split("?")[0]
                if blog_id and blog_id != "MyBlog.naver":
                    blog_id_file.write_text(blog_id, encoding="utf-8")

        # 블로그 글쓰기 페이지로 이동
        print(f"네이버 블로그 에디터로 이동 중... (블로그: {blog_id or '기본'})")
        if blog_id and blog_id != "MyBlog.naver":
            write_url = f"https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}"
        else:
            write_url = "https://blog.naver.com/PostWriteForm.naver"

        page.goto(write_url, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # 팝업 처리 (작성 중인 글이 있습니다 / 도움말 팝업 등)
        try_close_popups(page)

        # 1. 카테고리 선택
        select_category(page, category)

        # 2. 제목 입력
        enter_title(page, title)

        # 3. 본문 및 서식(스티커, 인용구, 구분선, 사진) 입력
        enter_body(page, body)

        # 4. 태그 입력
        if tags:
            enter_tags(page, tags)

        # 5. [임시저장] 버튼 클릭
        save_draft(page)

        print("\n[임시저장 완료] 3초 후 브라우저를 닫습니다.")
        page.wait_for_timeout(3000)
        context.close()


def try_close_popups(page):
    """에디터 진입 시 뜨는 팝업창(작성 중인 글 취소, 도움말 등) 자동 닫기"""
    page.wait_for_timeout(1500)
    # '작성 중인 글이 있습니다' 팝업 -> '취소' 클릭하여 새 글 작성
    cancel_selectors = [
        ".se-popup-button-cancel",
        "button:has-text('취소')",
        ".se-dialog-button-cancel"
    ]
    for sel in cancel_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                print("이전 작성 중인 글 팝업 감지: '취소' 클릭 (새 글 작성)")
                btn.click()
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    # 도움말/튜토리얼 닫기 버튼
    help_close_selectors = [
        ".container__O3PGu button",
        ".se-help-panel-close-button",
        "button:has-text('닫기')",
        ".se-dialog-button-close",
        "button[aria-label='도움말 닫기']",
        ".se-help-title + button"
    ]
    for sel in help_close_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                btn.click(force=True)
                page.wait_for_timeout(500)
        except Exception:
            pass


def select_category(page, category_name: str):
    """카테고리 선택"""
    try:
        # 카테고리 버튼 찾기
        cat_btn = page.locator("button.se-category-button, .se-category-select, button:has-text('카테고리')").first
        if cat_btn.is_visible(timeout=2000):
            cat_btn.click()
            page.wait_for_timeout(1000)
            
            # 카테고리 목록에서 세부 카테고리 이름으로 검색하여 클릭
            # 예: '체형/통증 가이드 > 증상별 원인 분석' 인 경우 '증상별 원인 분석' 검색
            target_name = category_name.split(">")[-1].strip() if ">" in category_name else category_name.strip()
            
            item = page.locator(f"span:has-text('{target_name}'), li:has-text('{target_name}')").first
            if item.is_visible(timeout=2000):
                item.click()
                print(f"카테고리 선택 완료: {target_name}")
                page.wait_for_timeout(500)
            else:
                print(f"경고: 카테고리 '{target_name}' 항목을 찾지 못해 기본값 유지")
    except Exception as e:
        print(f"카테고리 선택 건너뜀: {e}")


def enter_title(page, title: str):
    """제목 입력"""
    try:
        # 스마트에디터 ONE 제목 영역 클릭
        title_area = page.locator(".se-documentTitle, .se-title-text, div[class*='documentTitle']").first
        if not title_area.is_visible(timeout=3000):
            # p.se-placeholder 또는 제목 영역 찾기
            title_area = page.locator("text='제목을 입력하세요'").first
            
        title_area.click()
        page.wait_for_timeout(500)
        page.keyboard.type(title, delay=20)
        print("제목 입력 완료")
        page.wait_for_timeout(500)
    except Exception as e:
        print(f"제목 입력 오류: {e}")


def enter_body(page, body: str):
    """본문 내용을 줄 단위 및 마커 단위로 파싱하여 에디터에 주입"""
    try:
        # 본문 영역 포커스 이동
        # 제목에서 Tab 키를 누르거나 본문 영역 클릭
        body_area = page.locator(".se-main-container, .se-content, div[class*='contentContainer']").first
        body_area.click()
        page.wait_for_timeout(500)
    except Exception:
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)

    lines = body.splitlines()
    in_quote = False
    quote_buffer = []

    for line in lines:
        stripped = line.strip()

        # 1. 인용구 시작/종료 처리
        if "[QUOTE]" in stripped:
            in_quote = True
            quote_text = stripped.replace("[QUOTE]", "").replace("[/QUOTE]", "").strip()
            if "[/QUOTE]" in stripped:
                # 한 줄 인용구
                insert_quote(page, quote_text)
                in_quote = False
            else:
                quote_buffer = [quote_text] if quote_text else []
            continue

        if in_quote:
            if "[/QUOTE]" in stripped:
                quote_buffer.append(stripped.replace("[/QUOTE]", "").strip())
                insert_quote(page, " ".join(quote_buffer))
                in_quote = False
                quote_buffer = []
            else:
                quote_buffer.append(stripped)
            continue

        # 2. 스티커 마커 처리
        if stripped.startswith("[STICKER:"):
            sticker_type = stripped.replace("[STICKER:", "").replace("]", "").strip()
            insert_sticker(page, sticker_type)
            continue

        # 3. 구분선 마커 처리
        if stripped == "[DIVIDER]":
            insert_divider(page)
            continue

        # 4. 이미지 마커 처리
        if stripped.startswith("[IMAGE:"):
            img_rel_path = stripped.replace("[IMAGE:", "").replace("]", "").strip()
            # 상대 경로를 절대 경로로 변환
            img_path = WORKSPACE_DIR / img_rel_path
            if not img_path.exists():
                # 혹시 블로그/images 안에 있는지 확인
                img_path = BLOG_DIR / "images" / Path(img_rel_path).name
            
            if img_path.exists():
                insert_image(page, img_path)
            else:
                print(f"경고: 이미지 파일을 찾을 수 없습니다: {img_rel_path}")
            continue

        # 5. 빈 줄 처리 (모바일 가독성을 위한 엔터)
        if not stripped:
            page.keyboard.press("Enter")
            page.wait_for_timeout(50)
            continue

        # 6. 일반 텍스트 및 서식(하이라이트, 볼드, 소제목) 처리
        # 소제목 (#, ##, ###)
        if stripped.startswith("#"):
            clean_heading = stripped.lstrip("#").strip()
            page.keyboard.type(clean_heading, delay=15)
            page.keyboard.press("Enter")
            page.wait_for_timeout(100)
            continue

        # 인라인 마커 클린업 및 타이핑
        clean_text = clean_inline_markers(stripped)
        page.keyboard.type(clean_text, delay=10)
        page.keyboard.press("Enter")
        page.wait_for_timeout(50)


def clean_inline_markers(text: str) -> str:
    """[HIGHLIGHT] 및 볼드 마크다운 등 텍스트 정리"""
    text = re.sub(r"\[HIGHLIGHT\](.*?)\[/HIGHLIGHT\]", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    return text


def insert_divider(page):
    """에디터 툴바의 구분선 삽입"""
    try:
        divider_btn = page.locator("button[data-name='line'], button[aria-label='구분선'], button.se-toolbar-item-line").first
        if divider_btn.is_visible(timeout=2000):
            divider_btn.click()
            print("구분선 삽입 완료")
            page.wait_for_timeout(500)
        else:
            # 툴바 못 찾을 시 키보드로 여백 추가
            page.keyboard.press("Enter")
    except Exception as e:
        print(f"구분선 삽입 건너뜀: {e}")


def insert_quote(page, quote_text: str):
    """에디터 툴바의 인용구 박스 삽입"""
    try:
        quote_btn = page.locator("button[data-name='quotation'], button[aria-label='인용구'], button.se-toolbar-item-quotation").first
        if quote_btn.is_visible(timeout=2000):
            quote_btn.click()
            page.wait_for_timeout(500)
            page.keyboard.type(quote_text, delay=15)
            page.wait_for_timeout(300)
            # 인용구 블록 밖으로 나가기 위해 아래 방향키 또는 엔터
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            print(f"인용구 삽입 완료: {quote_text[:20]}...")
        else:
            # 인용구 버튼이 안 보이면 강조 텍스트로 대체
            page.keyboard.type(f"💬 \"{quote_text}\"", delay=15)
            page.keyboard.press("Enter")
    except Exception as e:
        print(f"인용구 삽입 예외: {e}")


def insert_sticker(page, sticker_type: str = "greeting"):
    """에디터 툴바의 네이버 스티커 삽입"""
    try:
        sticker_btn = page.locator("button[data-name='sticker'], button[aria-label='스티커'], button.se-toolbar-item-sticker").first
        if sticker_btn.is_visible(timeout=2000):
            sticker_btn.click()
            page.wait_for_timeout(1000)
            
            # 스티커 팝업/패널에서 스티커 클릭
            # 첫 번째 또는 두 번째 스티커 아이템 클릭
            sticker_item = page.locator(".se-sticker-list button, .se-sticker-item, .se-popup-sticker img").first
            if sticker_item.is_visible(timeout=2000):
                sticker_item.click()
                print(f"스티커 삽입 완료 ({sticker_type})")
                page.wait_for_timeout(800)
            else:
                # 닫기
                sticker_btn.click()
    except Exception as e:
        print(f"스티커 삽입 건너뜀: {e}")


def insert_image(page, img_path: Path):
    """에디터에 사진 업로드 및 본문 삽입"""
    try:
        print(f"이미지 업로드 중: {img_path.name}...")
        
        # 파일 인풋 엘리먼트 찾기
        # SmartEditor ONE의 사진 파일 인풋
        file_input = page.locator("input[type='file'][accept*='image']").first
        if file_input.count() > 0:
            file_input.set_input_files(str(img_path))
            page.wait_for_timeout(3500)  # 업로드 및 렌더링 대기
            print(f"이미지 업로드 완료: {img_path.name}")
        else:
            # 파일 선택 창(File Chooser) 트리거
            photo_btn = page.locator("button[data-name='image'], button[aria-label='사진']").first
            with page.expect_file_chooser(timeout=5000) as fc_info:
                photo_btn.click()
            file_chooser = fc_info.value
            file_chooser.set_files(str(img_path))
            page.wait_for_timeout(3500)
            print(f"이미지 업로드 완료: {img_path.name}")
            
        page.keyboard.press("Enter")
    except Exception as e:
        print(f"이미지 업로드 오류 ({img_path.name}): {e}")


def enter_tags(page, tags: list):
    """태그 입력창에 해시태그 등록"""
    try:
        # 에디터 하단의 태그 입력창 찾기
        tag_input = page.locator("input.se-tag-input, input[placeholder*='태그'], .se-tag-input-area input").first
        if tag_input.is_visible(timeout=2000):
            tag_input.click()
            for t in tags[:15]:
                clean_tag = t.lstrip("#").strip()
                if clean_tag:
                    tag_input.fill(clean_tag)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(150)
            print(f"태그 {len(tags)}개 등록 완료")
    except Exception as e:
        print(f"태그 입력 건너뜀: {e}")


def save_draft(page):
    """[임시저장] (저장) 버튼 클릭"""
    try:
        # 도움말이나 오버레이가 있으면 닫기
        try_close_popups(page)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # 상단 헤더의 '저장' 버튼 (발행 버튼 옆)
        save_btn = page.locator("button[data-name='save'], button:has-text('저장'), button.save_btn__FuUyN").first
        if save_btn.is_visible(timeout=5000):
            save_btn.click(force=True)
            page.wait_for_timeout(2000)
            print("[*] [임시저장] 성공! 네이버 블로그에 초안이 저장되었습니다.")
        else:
            print("경고: '저장' 버튼을 찾지 못했습니다.")
    except Exception as e:
        print(f"임시저장 클릭 실패: {e}")


def main():
    parser = argparse.ArgumentParser(description="리무브 체형교정 네이버 블로그 자동화 봇")
    subparsers = parser.add_subparsers(dest="command")

    # login 명령
    subparsers.add_parser("login", help="최초 1회 네이버 로그인 및 세션 저장")

    # draft 명령
    draft_parser = subparsers.add_parser("draft", help="마크다운 원고를 네이버 에디터에 주입 후 임시저장")
    draft_parser.add_argument("--file", "-f", required=True, help="작성된 마크다운 포스트 파일 경로")
    draft_parser.add_argument("--category", "-c", help="카테고리명 오버라이드")

    args = parser.parse_args()

    if args.command == "login":
        login_helper()
    elif args.command == "draft":
        post_file = Path(args.file)
        if not post_file.is_absolute():
            post_file = WORKSPACE_DIR / post_file
        if not post_file.exists():
            print(f"오류: 파일을 찾을 수 없습니다: {post_file}")
            sys.exit(1)
        draft_post(post_file, args.category)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
