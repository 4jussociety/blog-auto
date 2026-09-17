"""
리무브 체형교정 - 블로그 마크다운 원고 HTML 미리보기 생성기
기능:
1. 마크다운 원고(*.md)를 읽어 네이버 스마트에디터 ONE의 실제 화면과 100% 일치하는 프리뷰 HTML 생성
2. 모바일(430px) / 데스크톱(720px) 뷰 전환 토글 지원
3. 19pt 기본 본문 글꼴, 30pt 볼드 소제목, 중앙 정렬 여우 스티커(cafe_004), 인용구 박스, 이미지(대표 뱃지), 형광펜/글자색 시각화
4. 에디터원에 올리기 전 10초 만에 빠르게 훑어보고 점검하는 용도
"""

import os
import re
import sys
import html
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent

# 여우 스티커 URL 매핑 (cafe_004)
STICKER_URLS = {
    "greeting": "https://storep-phinf.pstatic.net/cafe_004/original_1.png",
    "hi": "https://storep-phinf.pstatic.net/cafe_004/original_1.png",
    "like": "https://storep-phinf.pstatic.net/cafe_004/original_4.png",
    "heart": "https://storep-phinf.pstatic.net/cafe_004/original_4.png",
    "cheering": "https://storep-phinf.pstatic.net/cafe_004/original_13.png",
    "fight": "https://storep-phinf.pstatic.net/cafe_004/original_13.png",
    "clap": "https://storep-phinf.pstatic.net/cafe_004/original_15.png",
    "ok": "https://storep-phinf.pstatic.net/cafe_004/original_27.png",
    "thumb": "https://storep-phinf.pstatic.net/cafe_004/original_27.png",
}

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


def parse_frontmatter(content: str):
    """Frontmatter 추출"""
    title = ""
    category = "ABOUT 리무브 > 센터/전문가 소개"
    tags = []
    
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if fm_match:
        header, body = fm_match.group(1), fm_match.group(2)
        for line in header.splitlines():
            if line.startswith("title:"):
                raw_t = line.split("title:", 1)[1].strip()
                title = raw_t.strip('"\'')
            elif line.startswith("category:"):
                category = line.split("category:", 1)[1].strip().strip('"\'')
            elif line.startswith("tags:"):
                tags_str = line.split("tags:", 1)[1].strip().strip("[]")
                tags = [t.strip().strip('"\'') for t in tags_str.split(",") if t.strip()]
        return title, category, tags, body.strip()
    else:
        lines = content.strip().splitlines()
        first_line = lines[0] if lines else "제목 없음"
        title = first_line.lstrip("#").strip()
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""
        return title, category, tags, body.strip()


def render_inline_formatting(text: str) -> str:
    """형광펜, 글자색, 볼드 마커를 HTML 인라인 스타일로 변환"""
    # 1. HTML 이스케이프 (태그 마커 보존을 위해 임시 토큰 처리 전 기본 텍스트 이스케이프)
    escaped = html.escape(text)

    # 2. [HIGHLIGHT:color] 또는 [HIGHLIGHT]
    def replace_highlight(m):
        color_name = m.group(1) or "yellow"
        bg_color = HL_MAP.get(color_name.lower(), "#fff8b2")
        inner = m.group(2)
        return f'<mark class="preview-highlight" style="background-color: {bg_color};">{inner}</mark>'

    escaped = re.sub(r"\[HIGHLIGHT(?::(\w+))?\](.*?)\[/HIGHLIGHT\]", replace_highlight, escaped)

    # 3. [COLOR:color]
    def replace_color(m):
        color_name = m.group(1)
        font_color = COLOR_MAP.get(color_name.lower(), color_name)
        inner = m.group(2)
        return f'<span class="preview-color" style="color: {font_color};">{inner}</span>'

    escaped = re.sub(r"\[COLOR:(\w+)\](.*?)\[/COLOR\]", replace_color, escaped)

    # 4. **볼드**
    escaped = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)

    # 5. ~~취소선~~
    escaped = re.sub(r"~~(.*?)~~", r"<del>\1</del>", escaped)

    return escaped


def generate_preview_html(md_file_path: Path, output_html_path: Path = None) -> Path:
    """마크다운 파일을 분석하여 프리뷰 HTML 생성 (항상 output/<포스트명>/ 폴더에 정리)"""
    content = md_file_path.read_text(encoding="utf-8")
    title, category, tags, body = parse_frontmatter(content)

    if not output_html_path:
        # 파일이 이미 output 폴더 하위에 있다면 3_미리보기.html로 생성
        if "output" in md_file_path.parts:
            output_html_path = md_file_path.parent / "3_미리보기.html"
        else:
            stem = md_file_path.stem
            target_dir = WORKSPACE_DIR / "output" / stem
            target_dir.mkdir(parents=True, exist_ok=True)
            output_html_path = target_dir / "3_미리보기.html"

    lines = body.splitlines()
    body_html_parts = []
    in_tag_quote = False
    in_md_quote = False
    quote_buffer = []
    image_count = 0

    def flush_quotes():
        nonlocal in_tag_quote, in_md_quote, quote_buffer
        if quote_buffer:
            quote_text = "<br>".join([render_inline_formatting(q) for q in quote_buffer])
            body_html_parts.append(f"""
            <div class="se-quote-box">
                <div class="quote-mark quote-open">“</div>
                <p class="quote-content">{quote_text}</p>
                <div class="quote-mark quote-close">”</div>
            </div>
            """)
            quote_buffer = []
        in_tag_quote = False
        in_md_quote = False

    for line in lines:
        stripped = line.strip()

        # 인용구 블록 [QUOTE]
        if "[QUOTE]" in stripped:
            flush_quotes()
            if "[/QUOTE]" in stripped:
                q_text = stripped.replace("[QUOTE]", "").replace("[/QUOTE]", "").strip()
                if q_text:
                    quote_buffer.append(q_text)
                flush_quotes()
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

        # 마크다운 > 인용구
        if stripped.startswith(">"):
            in_md_quote = True
            quote_buffer.append(stripped.lstrip("> ").strip())
            continue
        elif in_md_quote:
            flush_quotes()

        # 여우 스티커
        if stripped.startswith("[STICKER:"):
            sticker_key = stripped.replace("[STICKER:", "").replace("]", "").strip().lower()
            sticker_url = STICKER_URLS.get(sticker_key, STICKER_URLS["greeting"])
            body_html_parts.append(f"""
            <div class="se-sticker-wrapper">
                <img src="{sticker_url}" alt="여우 스티커 ({sticker_key})" class="se-sticker-img" />
            </div>
            """)
            continue

        # 구분선
        if stripped == "[DIVIDER]":
            body_html_parts.append('<hr class="se-divider" />')
            continue

        # 이미지
        if stripped.startswith("[IMAGE:"):
            image_count += 1
            img_rel_path = stripped.replace("[IMAGE:", "").replace("]", "").strip()
            # 상대 경로 그대로 사용 (HTML과 같은 폴더 또는 하위 images/ 폴더)
            is_rep = (image_count == 1)
            badge_html = '<span class="rep-badge">대표</span>' if is_rep else ''
            body_html_parts.append(f"""
            <div class="se-image-wrapper">
                <div class="image-container">
                    {badge_html}
                    <img src="{img_rel_path}" alt="본문 이미지 {image_count}" class="se-post-image" loading="lazy" />
                </div>
            </div>
            """)
            continue

        # 빈 줄 (모바일 문단 간격)
        if not stripped:
            body_html_parts.append('<div class="se-spacer"></div>')
            continue

        # 소제목 (#, ##, ###)
        if stripped.startswith("#"):
            clean_heading = stripped.lstrip("#").strip()
            rendered_h = render_inline_formatting(clean_heading)
            body_html_parts.append(f'<h3 class="se-section-title">{rendered_h}</h3>')
            continue

        # 일반 본문 문단 (19pt)
        rendered_p = render_inline_formatting(stripped)
        body_html_parts.append(f'<p class="se-paragraph">{rendered_p}</p>')

    flush_quotes()

    tags_html = "".join([f'<span class="tag-chip">#{t}</span>' for t in tags])
    rendered_body = "\n".join(body_html_parts)

    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[미리보기] {html.escape(title)}</title>
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
    <style>
        :root {{
            --font-main: "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Nanum Gothic", sans-serif;
            --bg-page: #f1f3f5;
            --bg-card: #ffffff;
            --primary-green: #00a84b;
            --primary-red: #ba0000;
            --primary-blue: #004e82;
            --text-title: #111827;
            --text-body: #222222;
            --border-light: #e5e7eb;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-page);
            font-family: var(--font-main);
            color: var(--text-body);
            -webkit-font-smoothing: antialiased;
            padding-bottom: 80px;
        }}

        /* 상단 제어 바 */
        .preview-topbar {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-light);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }}

        .topbar-info {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-badge {{
            background: #e8f7ee;
            color: var(--primary-green);
            font-size: 13px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
        }}

        .status-text {{
            font-size: 14px;
            color: #6b7280;
            font-weight: 500;
        }}

        .topbar-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .view-btn {{
            background: #f3f4f6;
            border: 1px solid var(--border-light);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            color: #4b5563;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .view-btn.active {{
            background: #111827;
            color: #ffffff;
            border-color: #111827;
        }}

        /* 메인 컨테이너 */
        .preview-layout {{
            max-width: 820px;
            margin: 30px auto;
            padding: 0 16px;
            transition: max-width 0.3s ease;
        }}

        .preview-layout.mobile-mode {{
            max-width: 440px;
        }}

        .post-card {{
            background: var(--bg-card);
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05);
            padding: 44px 36px;
            border: 1px solid var(--border-light);
        }}

        .preview-layout.mobile-mode .post-card {{
            padding: 30px 20px;
            border-radius: 24px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
        }}

        /* 헤더 영역 */
        .post-header {{
            border-bottom: 1px solid #f3f4f6;
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}

        .category-text {{
            font-size: 15px;
            color: #6b7280;
            font-weight: 600;
            margin-bottom: 12px;
        }}

        .post-title {{
            font-size: 28px;
            line-height: 1.4;
            font-weight: 800;
            color: var(--text-title);
            letter-spacing: -0.02em;
        }}

        .preview-layout.mobile-mode .post-title {{
            font-size: 23px;
        }}

        /* 본문 타이포그래피 (19pt 기본) */
        .post-content {{
            font-size: 19pt; /* 25px */
            line-height: 1.85;
            color: #222222;
            word-break: keep-all;
            overflow-wrap: break-word;
        }}

        .se-paragraph {{
            margin-bottom: 8px;
            font-size: 19pt;
            letter-spacing: -0.01em;
        }}

        .se-spacer {{
            height: 22px;
        }}

        /* 소제목 (30pt 볼드) */
        .se-section-title {{
            font-size: 30pt; /* 40px */
            font-weight: 800;
            line-height: 1.4;
            color: #111827;
            margin: 44px 0 18px 0;
            letter-spacing: -0.02em;
        }}

        .preview-layout.mobile-mode .se-section-title {{
            font-size: 24pt;
        }}

        /* 형광펜 */
        .preview-highlight {{
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            box-decoration-break: clone;
            -webkit-box-decoration-break: clone;
        }}

        /* 인라인 글자색 */
        .preview-color {{
            font-weight: 700;
        }}

        /* 스티커 (가운데 정렬) */
        .se-sticker-wrapper {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 28px 0;
        }}

        .se-sticker-img {{
            width: 170px;
            height: auto;
            display: block;
            filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.04));
        }}

        /* 인용구 박스 */
        .se-quote-box {{
            background: #fafafa;
            border: 1px solid #eeeeee;
            border-radius: 12px;
            padding: 24px 28px;
            margin: 30px 0;
            text-align: center;
            position: relative;
        }}

        .quote-mark {{
            font-size: 36px;
            line-height: 1;
            color: #c5cbd5;
            font-family: Georgia, serif;
            font-weight: 700;
        }}

        .quote-open {{
            margin-bottom: 6px;
        }}

        .quote-close {{
            margin-top: 6px;
        }}

        .quote-content {{
            font-size: 19pt;
            font-style: italic;
            color: #374151;
            line-height: 1.7;
            font-weight: 500;
        }}

        /* 이미지 컨테이너 */
        .se-image-wrapper {{
            display: flex;
            justify-content: center;
            margin: 32px 0;
        }}

        .image-container {{
            position: relative;
            max-width: 100%;
            display: inline-block;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
        }}

        .se-post-image {{
            max-width: 100%;
            height: auto;
            display: block;
        }}

        .rep-badge {{
            position: absolute;
            top: 12px;
            left: 12px;
            background: #03c75a;
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            letter-spacing: -0.02em;
        }}

        /* 구분선 */
        .se-divider {{
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 40px 0;
        }}

        /* 태그 영역 */
        .post-tags {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid #f3f4f6;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .tag-chip {{
            background: #f3f4f6;
            color: #4b5563;
            font-size: 14px;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 20px;
        }}

        /* 푸터 안내 */
        .preview-footer {{
            text-align: center;
            margin-top: 40px;
            color: #9ca3af;
            font-size: 14px;
        }}
    </style>
</head>
<body>

    <!-- 상단 툴바 -->
    <header class="preview-topbar">
        <div class="topbar-info">
            <span class="brand-badge">리무브 체형교정</span>
            <span class="status-text">네이버 스마트에디터 ONE 실시간 프리뷰 (19pt 기본글꼴)</span>
        </div>
        <div class="topbar-actions">
            <button id="btnPc" class="view-btn active" onclick="setViewMode('pc')">💻 데스크톱 (720px)</button>
            <button id="btnMobile" class="view-btn" onclick="setViewMode('mobile')">📱 모바일 (430px)</button>
        </div>
    </header>

    <!-- 프리뷰 본체 -->
    <main id="layoutContainer" class="preview-layout">
        <article class="post-card">
            <header class="post-header">
                <div class="category-text">📁 {html.escape(category)}</div>
                <h1 class="post-title">{html.escape(title)}</h1>
            </header>

            <div class="post-content">
                {rendered_body}
            </div>

            <footer class="post-tags">
                {tags_html}
            </footer>
        </article>

        <div class="preview-footer">
            🌿 리무브 체형교정 블로그 자동화 시스템 | 스마트에디터 ONE 주입 전 검토용 프리뷰
        </div>
    </main>

    <script>
        function setViewMode(mode) {{
            const layout = document.getElementById('layoutContainer');
            const btnPc = document.getElementById('btnPc');
            const btnMobile = document.getElementById('btnMobile');

            if (mode === 'mobile') {{
                layout.classList.add('mobile-mode');
                btnMobile.classList.add('active');
                btnPc.classList.remove('active');
            }} else {{
                layout.classList.remove('mobile-mode');
                btnPc.classList.add('active');
                btnMobile.classList.remove('active');
            }}
        }}
    </script>
</body>
</html>
"""

    output_html_path.write_text(html_template, encoding="utf-8")
    print(f"[*] 프리뷰 HTML 생성 완료: {output_html_path.name}")
    return output_html_path


import webbrowser


def main():
    should_open = "--open" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--open"]

    generated_paths = []
    if args:
        arg = args[0]
        if arg == "--all":
            # output 내 모든 활성 포스트에 대해 2_업로드용.md 우선 프리뷰 생성
            for p in (WORKSPACE_DIR / "output").glob("*"):
                if p.is_dir():
                    target_md = p / "2_업로드용.md"
                    if not target_md.exists():
                        candidates = [f for f in p.glob("*.md") if f.name != "1_순수원고.md" and f.name != "README.md"]
                        if candidates:
                            target_md = candidates[0]
                    if target_md and target_md.exists():
                        res = generate_preview_html(target_md)
                        generated_paths.append(res)
        else:
            p = Path(arg)
            if not p.is_absolute():
                p = WORKSPACE_DIR / p
            if p.is_dir():
                target_md = p / "2_업로드용.md"
                if not target_md.exists():
                    candidates = [f for f in p.glob("*.md") if f.name != "1_순수원고.md" and f.name != "README.md"]
                    if candidates:
                        target_md = candidates[0]
                if target_md and target_md.exists():
                    res = generate_preview_html(target_md)
                    generated_paths.append(res)
            elif p.is_file():
                res = generate_preview_html(p)
                generated_paths.append(res)
    else:
        # 기본: output 내 최신 포스트 대상 생성
        output_dirs = sorted([d for d in (WORKSPACE_DIR / "output").glob("*") if d.is_dir()], key=os.path.getmtime, reverse=True)
        target = None
        if output_dirs:
            p = output_dirs[0]
            target_md = p / "2_업로드용.md"
            if not target_md.exists():
                candidates = [f for f in p.glob("*.md") if f.name != "1_순수원고.md" and f.name != "README.md"]
                if candidates:
                    target_md = candidates[0]
            target = target_md

        if target and target.exists():
            res = generate_preview_html(target)
            generated_paths.append(res)
        else:
            print("사용법: python scripts/generate_preview.py <마크다운파일.md 또는 폴더> [--open]")

    if should_open and generated_paths:
        first_html = generated_paths[0].resolve()
        print(f"🌐 웹 브라우저에서 미리보기를 엽니다: {first_html.name}")
        webbrowser.open(first_html.as_uri())


if __name__ == "__main__":
    main()

