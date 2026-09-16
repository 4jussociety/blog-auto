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


COLOR_MAP = {
    "green": "#00a84b",
    "초록": "#00a84b",
    "red": "#ba0000",
    "빨강": "#ba0000",
    "blue": "#004e82",
    "파랑": "#004e82",
    "gray": "#777777",
    "회색": "#777777",
}

HL_MAP = {
    "yellow": "#fff8b2",
    "노랑": "#fff8b2",
    "green": "#c2f4db",
    "연두": "#c2f4db",
    "pink": "#ffcdc0",
    "핑크": "#ffcdc0",
}


def draft_post(post_file: Path, category_override: str = None, headless: bool = False):
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
    print(f"- 헤드리스 모드: {headless}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=headless,
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

        # 기존 동일 제목의 이전 초안이 있다면 정리하여 항상 1개의 초안만 유지
        clean_duplicate_drafts(page, title)

        # 1. 카테고리 선택
        select_category(page, category)

        # 2. 제목 입력
        enter_title(page, title)

        # 3. 본문 및 서식(19pt 기본크기, 스티커, 인용구, 구분선, 사진, 형광펜, 글자색) 입력
        enter_body(page, body, post_dir=post_file.parent)

        # 4. 태그 입력
        if tags:
            enter_tags(page, tags)

        # 5. [임시저장] 버튼 단 1회 클릭
        save_draft(page)

        print("\n[임시저장 완료] 3초 후 브라우저를 닫습니다.")
        page.wait_for_timeout(3000)
        context.close()


def clean_duplicate_drafts(page, title: str):
    """기존 임시저장 목록에서 동일한 제목을 가진 이전 초안들을 정리하여 글이 중복 누적되지 않고 1개만 깔끔하게 유지되도록 합니다."""
    try:
        save_count_btn = page.locator("button[class*='save_count']").first
        if not save_count_btn.is_visible(timeout=2000):
            return
        save_count_btn.click()
        page.wait_for_timeout(1500)

        # 특수문자/따옴표 제거 후 첫 2개 단어로 안전하게 검색
        clean_words = re.sub(r"[^\w\s가-힣]", " ", title).split()
        search_kw = " ".join(clean_words[:2]) if clean_words else ""
        
        if search_kw:
            matching_rows = page.locator("li.item__k1QHQ, li[class*='item']").filter(has_text=search_kw)
            del_buttons = matching_rows.locator("button.delete_button__uksCg, button[class*='delete']").all()
            if del_buttons:
                print(f"[*] 기존 동일 포스트의 이전 초안 {len(del_buttons)}건 발견: 중복 정리합니다.")
                for b in del_buttons:
                    try:
                        b.click(force=True)
                        page.wait_for_timeout(400)
                        confirm = page.locator(".se-popup-button-confirm, button:has-text('확인'), button:has-text('삭제')").first
                        if confirm.is_visible(timeout=1000):
                            confirm.click(force=True)
                            page.wait_for_timeout(400)
                    except Exception:
                        pass
    except Exception as e:
        print(f"임시저장 초안 정리 건너뜀: {e}")
    finally:
        # 팝업이 열려있다면 반드시 닫고 포커스를 본문으로 복귀
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            close_btn = page.locator("button.popup_close_button, .layer_popup button[class*='close'], button[aria-label='닫기'], .popup_container button[class*='close']").first
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click(force=True)
                page.wait_for_timeout(300)
            # dimmed 오버레이가 사라질 때까지 대기
            dimmed = page.locator(".dimmed__QzVgp, .layer_popup__MFPwH")
            if dimmed.count() > 0 and dimmed.first.is_visible():
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        except Exception:
            pass


def try_close_popups(page):
    """에디터 진입 시 뜨는 팝업창(작성 중인 글 취소, 도움말 등) 자동 닫기"""
    page.wait_for_timeout(1500)
    # '작성 중인 글이 있습니다' 팝업 -> '취소' 클릭하여 새 글 작성
    cancel_selectors = [
        ".se-popup-button-cancel",
        ".se-popup-alert button:has-text('취소')",
        ".se-dialog-button-cancel"
    ]
    for sel in cancel_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                print("이전 작성 중인 글 팝업 감지: '취소' 클릭 (새 글 작성)")
                btn.click(force=True)
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    # 도움말/튜토리얼 닫기 버튼
    help_close_selectors = [
        "button[aria-label='도움말 닫기']",
        ".se-help-panel-close-button",
        ".container__O3PGu button",
        ".se-dialog-button-close"
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
        cat_btn = page.locator("button.se-category-button, .se-category-select, button:has-text('카테고리')").first
        if cat_btn.is_visible(timeout=2000):
            cat_btn.click()
            page.wait_for_timeout(1000)
            
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
        title_area = page.locator(".se-documentTitle, .se-title-text, div[class*='documentTitle']").first
        if not title_area.is_visible(timeout=3000):
            title_area = page.locator("text='제목을 입력하세요'").first
            
        title_area.click()
        page.wait_for_timeout(500)
        page.keyboard.type(title, delay=20)
        print("제목 입력 완료")
        page.wait_for_timeout(500)
    except Exception as e:
        print(f"제목 입력 오류: {e}")


def parse_line_segments(line: str):
    """
    문자열 내의 [HIGHLIGHT], [HIGHLIGHT:색상], [COLOR:색상], **볼드** 태그를 파싱하여
    (text, hl_color, font_color, is_bold) 세그먼트 튜플 리스트로 반환
    """
    pattern = re.compile(
        r'(\[HIGHLIGHT(?::(\w+))?\](.*?)\[/HIGHLIGHT\]|\[COLOR:(\w+)\](.*?)\[/COLOR\]|\*\*(.*?)\*\*)'
    )
    
    tokens = []
    last_idx = 0
    for m in pattern.finditer(line):
        start, end = m.span()
        if start > last_idx:
            tokens.append((line[last_idx:start], None, None, False))
        
        full_match = m.group(0)
        if full_match.startswith('[HIGHLIGHT'):
            hl_name = m.group(2) or "yellow"
            hl_color = HL_MAP.get(hl_name.lower(), hl_name)
            inner = m.group(3)
            font_color = None
            col_match = re.match(r'\[COLOR:(\w+)\](.*?)\[/COLOR\]', inner)
            if col_match:
                font_color = COLOR_MAP.get(col_match.group(1).lower(), col_match.group(1))
                inner = col_match.group(2)
            is_bold = inner.startswith('**') and inner.endswith('**')
            inner_clean = inner.strip('*')
            tokens.append((inner_clean, hl_color, font_color, is_bold))

        elif full_match.startswith('[COLOR'):
            color_name = m.group(4)
            font_color = COLOR_MAP.get(color_name.lower(), color_name)
            inner = m.group(5)
            hl_color = None
            hl_match = re.match(r'\[HIGHLIGHT(?::(\w+))?\](.*?)\[/HIGHLIGHT\]', inner)
            if hl_match:
                hl_name = hl_match.group(1) or "yellow"
                hl_color = HL_MAP.get(hl_name.lower(), hl_name)
                inner = hl_match.group(2)
            is_bold = inner.startswith('**') and inner.endswith('**')
            inner_clean = inner.strip('*')
            tokens.append((inner_clean, hl_color, font_color, is_bold))

        elif full_match.startswith('**'):
            inner = m.group(6)
            tokens.append((inner, None, None, True))
        
        last_idx = end
        
    if last_idx < len(line):
        tokens.append((line[last_idx:], None, None, False))
        
    return tokens


def type_rich_paragraph(page, segments):
    """(text, hl_color, font_color, is_bold) 세그먼트를 19pt 단락에 입력하고 서식 적용"""
    try:
        last_p = page.locator("p.se-text-paragraph").last
        last_p.click(force=True, timeout=2000)
    except Exception:
        page.keyboard.press("Escape")
        try:
            page.locator(".se-canvas, .se-body").first.click(position={"x": 300, "y": 900}, force=True)
        except Exception:
            pass

    page.wait_for_timeout(80)

    for text, hl_color, font_color, is_bold in segments:
        if not text:
            continue
        page.keyboard.type(text, delay=8)
        page.wait_for_timeout(60)

        if hl_color or font_color or is_bold:
            # 방금 입력한 글자 수만큼 Shift+ArrowLeft로 선택
            for _ in range(len(text)):
                page.keyboard.press("Shift+ArrowLeft")
            page.wait_for_timeout(100)

            # 1. 형광펜 적용
            if hl_color:
                try:
                    page.locator("button.se-background-color-toolbar-button").first.click()
                    page.wait_for_timeout(150)
                    page.locator(f"button.se-color-palette[data-color='{hl_color}']").first.click()
                    page.wait_for_timeout(150)
                except Exception:
                    pass

            # 2. 글자색 적용
            if font_color:
                try:
                    page.locator("button.se-font-color-toolbar-button").first.click()
                    page.wait_for_timeout(150)
                    page.locator(f"button.se-color-palette[data-color='{font_color}']").first.click()
                    page.wait_for_timeout(150)
                except Exception:
                    pass

            # 3. 볼드 적용
            if is_bold:
                page.keyboard.press("Control+b")
                page.wait_for_timeout(80)

            # 선택 해제
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(80)

            # 후속 일반 글자를 위한 서식 리셋
            if is_bold:
                page.keyboard.press("Control+b")
            if hl_color:
                try:
                    page.locator("button.se-background-color-toolbar-button").first.click()
                    page.wait_for_timeout(100)
                    page.locator("button.se-color-palette-no-color").first.click()
                    page.wait_for_timeout(100)
                except Exception:
                    pass
            if font_color:
                try:
                    page.locator("button.se-font-color-toolbar-button").first.click()
                    page.wait_for_timeout(100)
                    page.locator("button.se-color-palette[data-color='#000000']").first.click()
                    page.wait_for_timeout(100)
                except Exception:
                    pass

    page.keyboard.press("Enter")
    page.wait_for_timeout(80)


def resolve_image_path(rel_path_str: str, post_dir: Path = None) -> Path | None:
    """assets, images, assests 폴더 등에서 파일 이름 및 경로로 이미지를 검색합니다."""
    clean_name = Path(rel_path_str).name
    # 0. 포스트 원고 파일이 위치한 폴더 기준 상대경로 우선 탐색
    if post_dir:
        candidate = post_dir / rel_path_str
        if candidate.exists() and candidate.is_file():
            return candidate
        candidate_img = post_dir / "images" / clean_name
        if candidate_img.exists() and candidate_img.is_file():
            return candidate_img

    direct = WORKSPACE_DIR / rel_path_str
    if direct.exists() and direct.is_file():
        return direct
    
    candidates = [
        WORKSPACE_DIR / "images" / clean_name,
        WORKSPACE_DIR / "assets" / clean_name,
        WORKSPACE_DIR / "assets" / "리뷰" / clean_name,
        WORKSPACE_DIR / "assests" / clean_name,
        WORKSPACE_DIR / "assests" / "리뷰" / clean_name,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
            
    for p in WORKSPACE_DIR.rglob(clean_name):
        if p.is_file():
            return p
            
    return None


def enter_body(page, body: str, post_dir: Path = None):
    """본문 내용을 줄 단위 및 마커 단위로 파싱하여 에디터에 주입 (기본 글자 크기 19pt 적용)"""
    try:
        body_area = page.locator(".se-main-container, .se-content, div[class*='contentContainer']").first
        body_area.click()
        page.wait_for_timeout(500)
    except Exception:
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)

    # 본문 기본 글자 크기를 19pt로 설정
    try:
        fs_btn = page.locator("button[data-name='font-size']").first
        if fs_btn.is_visible(timeout=2500):
            fs_btn.click()
            page.wait_for_timeout(300)
            opt19 = page.locator("button.se-toolbar-option-font-size-code-fs19-button, button:has-text('19')").first
            if opt19.is_visible(timeout=2000):
                opt19.click()
                page.wait_for_timeout(300)
                print("[*] 본문 기본 글자 크기: 19pt 설정 완료")
    except Exception as e:
        print(f"19pt 폰트 설정 건너뜀: {e}")

    lines = body.splitlines()
    in_tag_quote = False
    in_md_quote = False
    quote_buffer = []

    def flush_quotes():
        nonlocal in_tag_quote, in_md_quote, quote_buffer
        if quote_buffer:
            insert_quote(page, "\n".join(quote_buffer))
            quote_buffer = []
        in_tag_quote = False
        in_md_quote = False

    for line in lines:
        stripped = line.strip()

        # 1-A. [QUOTE] 태그 블록 처리
        if "[QUOTE]" in stripped:
            flush_quotes()
            if "[/QUOTE]" in stripped:
                q_text = stripped.replace("[QUOTE]", "").replace("[/QUOTE]", "").strip()
                if q_text:
                    insert_quote(page, q_text)
                continue
            else:
                in_tag_quote = True
                q_text = stripped.replace("[QUOTE]", "").strip()
                if q_text:
                    quote_buffer.append(q_text)
                continue

        if in_tag_quote:
            if "[/QUOTE]" in stripped:
                q_text = stripped.replace("[/QUOTE]", "").strip()
                if q_text:
                    quote_buffer.append(q_text)
                flush_quotes()
                continue
            else:
                if stripped:
                    quote_buffer.append(stripped)
                continue

        # 1-B. 마크다운 > 블록 처리
        if stripped.startswith(">"):
            in_md_quote = True
            quote_buffer.append(stripped.lstrip("> ").strip())
            continue
        elif in_md_quote:
            flush_quotes()

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
            img_path = resolve_image_path(img_rel_path, post_dir=post_dir)
            if img_path and img_path.exists():
                insert_image(page, img_path)
            else:
                print(f"경고: 이미지 파일을 찾을 수 없습니다: {img_rel_path}")
            continue

        # 5. 빈 줄 처리 (모바일 가독성 엔터)
        if not stripped:
            page.keyboard.press("Enter")
            page.wait_for_timeout(50)
            continue

        # 6. 소제목 (#, ##, ###) 처리 -> 30pt 소제목 서식 적용
        if stripped.startswith("#"):
            clean_heading = stripped.lstrip("#").strip()
            insert_heading(page, clean_heading)
            continue

        # 7. 본문 텍스트 타이핑 (19pt 기본 + 인라인 형광펜/글자색/볼드 자동 적용)
        segments = parse_line_segments(stripped)
        type_rich_paragraph(page, segments)

    # 본문 끝에 남아있는 인용구 플러시
    flush_quotes()


def insert_heading(page, heading_text: str):
    """소제목 타이핑 후 툴바에서 [소제목] 30pt 서식 직접 클릭 적용 및 다음 본문 19pt 복원"""
    try:
        segments = parse_line_segments(heading_text)
        # 소제목 텍스트 타이핑
        last_p = page.locator("p.se-text-paragraph").last
        last_p.click(force=True, timeout=2000)
        clean_text = "".join(s[0] for s in segments)
        page.keyboard.type(clean_text, delay=10)
        page.wait_for_timeout(200)

        # 툴바 문단 서식 드롭다운 클릭 -> [소제목] 30pt 클릭
        heading_btn = page.locator(".se-text-format-toolbar-button").first
        heading_btn.click()
        page.wait_for_timeout(350)

        subtitle_btn = page.locator("button.se-toolbar-option-text-format-sectionTitle-button").first
        subtitle_btn.click()
        page.wait_for_timeout(350)

        page.keyboard.press("Enter")
        page.wait_for_timeout(200)

        # 소제목 엔터 후 다음 본문 문단 글자 크기를 19pt로 복원
        fs_btn = page.locator("button[data-name='font-size']").first
        if fs_btn.is_visible(timeout=1500):
            fs_btn.click()
            page.wait_for_timeout(250)
            opt19 = page.locator("button.se-toolbar-option-font-size-code-fs19-button, button:has-text('19')").first
            if opt19.is_visible(timeout=1500):
                opt19.click()
                page.wait_for_timeout(200)

        print(f"소제목 적용 완료 (30pt): {heading_text[:20]}...")
    except Exception as e:
        print(f"소제목 서식 적용 예외: {e}")
        page.keyboard.press("Enter")


def insert_divider(page):
    """에디터 툴바의 정품 가로 구분선 삽입"""
    try:
        div_btn = page.locator("button.se-insert-horizontal-line-default-toolbar-button, button:has-text('구분선')").first
        if div_btn.is_visible(timeout=2000):
            div_btn.click()
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)
            print("구분선 삽입 완료")
        else:
            page.keyboard.press("Enter")
    except Exception as e:
        print(f"구분선 삽입 건너뜀: {e}")


def insert_quote(page, quote_text: str):
    """에디터 툴바의 인용구 박스 컴포넌트 삽입"""
    try:
        quote_btn = page.locator("button[data-name='quotation'], button[aria-label='인용구']").first
        if quote_btn.is_visible(timeout=2000):
            quote_btn.click()
            page.wait_for_timeout(500)
            page.keyboard.type(quote_text, delay=15)
            page.wait_for_timeout(300)
            # 인용구 블록 탈출 및 선택 해제
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            page.wait_for_timeout(200)
            try:
                page.locator(".se-canvas, .se-body").first.click(position={"x": 300, "y": 900}, force=True)
            except Exception:
                pass
            page.wait_for_timeout(200)
            print(f"인용구 삽입 완료: {quote_text[:20]}...")
        else:
            page.keyboard.type(f"💬 \"{quote_text}\"", delay=15)
            page.keyboard.press("Enter")
    except Exception as e:
        print(f"인용구 삽입 예외: {e}")


def insert_sticker(page, sticker_type: str = "greeting"):
    """원장님 지정 여우 스티커 팩(cafe_004)에서 스티커 자동 선택 삽입"""
    INDEX_MAP = {
        "greeting": 0,    # HI~ 인사하는 여우
        "hi": 0,
        "like": 3,        # 좋아요 하트 여우
        "heart": 3,
        "cheering": 12,   # 양손 치어리딩 응원 여우
        "fight": 12,
        "clap": 14,       # 짝짝짝 박수 여우
        "ok": 26,         # NO PROBLEM 엄지척 여우
        "thumb": 26,
    }
    idx = INDEX_MAP.get(sticker_type.lower(), 0)

    try:
        print(f"여우 스티커 삽입 시도: [{sticker_type}] (index: {idx})...")
        sticker_btn = page.locator("button[data-name='sticker']").first
        sticker_btn.click()
        page.wait_for_timeout(1500)

        # 4번째 탭 (여우 스티커 팩 cafe_004) 클릭
        fox_tab = page.locator(".se-tab-item button, .se-sticker-tab-button").nth(3)
        if fox_tab.is_visible(timeout=2000):
            fox_tab.click()
            page.wait_for_timeout(800)

        # 지정 인덱스 스티커 아이템 클릭
        target_item = page.locator(f"button.se-sidebar-element-sticker[data-index='{idx}']").first
        if target_item.is_visible(timeout=2000):
            target_item.click()
            page.wait_for_timeout(1000)
            print(f"여우 스티커 삽입 완료 ({sticker_type})")
        else:
            print(f"경고: 스티커 index {idx}를 찾지 못했습니다.")

        # 사이드바 닫기
        close_btn = page.locator("button.se-sidebar-close-button").first
        if close_btn.is_visible(timeout=2000):
            close_btn.click()
            page.wait_for_timeout(500)

        # 스티커 항상 가운데 정렬 적용
        sticker_el = page.locator(".se-component-sticker, .se-sticker").last
        if sticker_el.count() > 0:
            sticker_el.click(force=True)
            page.wait_for_timeout(300)
            center_btn = page.locator("button.se-align-center-toolbar-button").first
            if center_btn.is_visible(timeout=1500):
                center_btn.click(force=True)
                page.wait_for_timeout(300)
                print(f"스티커 가운데 정렬 적용 완료 ({sticker_type})")

        # 캔버스 아래 클릭하여 포커스 복원 및 선택 해제
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        try:
            page.locator(".se-canvas, .se-body").first.click(position={"x": 300, "y": 900}, force=True)
        except Exception:
            pass
        page.wait_for_timeout(200)
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
    except Exception as e:
        print(f"스티커 삽입 예외: {e}")


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
    draft_parser.add_argument("--headless", action="store_true", help="브라우저 창을 띄우지 않고 백그라운드에서 실행")

    args = parser.parse_args()

    if args.command == "login":
        login_helper()
    elif args.command == "draft":
        target_path = Path(args.file)
        if not target_path.is_absolute():
            target_path = WORKSPACE_DIR / target_path
        if not target_path.exists():
            print(f"오류: 파일을 찾을 수 없습니다: {target_path}")
            sys.exit(1)

        if target_path.is_dir():
            md_files = [f for f in target_path.glob("*.md") if not f.name.startswith(".") and f.name != "README.md"]
            if not md_files:
                # 하위 폴더 중 최신 수정된 폴더의 md 검색
                sub_dirs = sorted([d for d in target_path.glob("*") if d.is_dir()], key=os.path.getmtime, reverse=True)
                for sd in sub_dirs:
                    sub_mds = [f for f in sd.glob("*.md") if not f.name.startswith(".") and f.name != "README.md"]
                    if sub_mds:
                        md_files = sub_mds
                        break

            if not md_files:
                print(f"오류: 해당 디렉터리 내에 마크다운 포스트(.md) 파일이 없습니다: {target_path}")
                sys.exit(1)
            post_file = md_files[0]
            print(f"[*] 대상 원고 자동 감지: {post_file.name}")
        else:
            post_file = target_path

        draft_post(post_file, args.category, headless=args.headless)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
