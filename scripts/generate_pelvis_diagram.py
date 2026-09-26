# -*- coding: utf-8 -*-
"""
골반 시소 회전 메커니즘 인포그래픽 카드 생성기
원장님의 손그림(척추-Sacrum-Ilium-Femur)을 3D 미니멀 블록 일러스트와 한글 인포그래픽 카드로 다듬어 제작합니다.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

WORKSPACE_DIR = Path(r"c:\Users\myrea\OneDrive\바탕 화면\개발\리무브체형교정\블로그")
OUTPUT_DIR = WORKSPACE_DIR / "output" / "2026-09-26_4편_골반틀어짐_다리길이차이_교정전후" / "images"
IMAGE_PATH = Path(r"C:\Users\myrea\.gemini\antigravity-ide\brain\3f5d24db-5c3b-4908-b118-ab0595c31854\pelvis_block_linkage_1790409279110.jpg")

# 폰트 로드
FONT_NOTO = "C:/Windows/Fonts/NotoSansKR-VF.ttf"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"

def make_diagram():
    # 1. 캔버스 준비 (1200 x 960)
    width, height = 1200, 960
    canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # 폰트 설정
    font_title = ImageFont.truetype(FONT_BOLD, 30)
    font_sub = ImageFont.truetype(FONT_BOLD, 16)
    font_tag = ImageFont.truetype(FONT_BOLD, 13)
    font_badge = ImageFont.truetype(FONT_BOLD, 15)
    font_desc = ImageFont.truetype(FONT_BOLD, 13)
    font_bottom_bold = ImageFont.truetype(FONT_BOLD, 16)
    font_bottom_norm = ImageFont.truetype(FONT_BOLD, 14)

    # 상단 태그
    tag_text = "BIOMECHANICS PRINCIPLE · 골반 생체역학"
    draw.rounded_rectangle([(60, 36), (330, 64)], radius=6, fill="#f0fdf4", outline="#bbf7d0", width=1)
    draw.text((75, 42), tag_text, font=font_tag, fill="#16a34a")

    # 상단 메인 타이틀
    title_text = "골반의 3차원 '회전 시소' 구조와 다리길이 차이 원리"
    draw.text((60, 76), title_text, font=font_title, fill="#0f172a")

    # 서브타이틀
    sub_text = "다리뼈(Femur)가 긴 게 아니라, 척추 아래 천골(Sacrum)에 매달린 장골(Ilium)이 비틀려 출발점이 내려온 것입니다."
    draw.text((60, 122), sub_text, font=font_sub, fill="#64748b")

    # 구분선
    draw.line([(60, 158), (1140, 158)], fill="#e2e8f0", width=1)

    # 중앙 일러스트 배치
    orig_img = Image.open(IMAGE_PATH).convert("RGBA")
    w_orig, h_orig = orig_img.size
    crop_box = (100, 30, w_orig - 100, h_orig - 30)
    cropped = orig_img.crop(crop_box)
    img_target_w = 640
    img_target_h = int(cropped.height * (img_target_w / cropped.width))
    resized_img = cropped.resize((img_target_w, img_target_h), Image.Resampling.LANCZOS)

    img_x = (width - img_target_w) // 2
    img_y = 175
    canvas.paste(resized_img, (img_x, img_y), resized_img)

    # 지시선 & 레이블 핀 헬퍼
    def draw_badge(x, y, w, h, title, subtitle, bg_color, border_color, text_color, sub_color):
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=8, fill=bg_color, outline=border_color, width=1)
        draw.text((x + 12, y + 8), title, font=font_badge, fill=text_color)
        draw.text((x + 12, y + 28), subtitle, font=font_desc, fill=sub_color)

    # 1. 척추 (상단 중앙)
    spine_target = (img_x + 320, img_y + 45)
    spine_pin = (img_x + 440, img_y + 35)
    draw.line([spine_target, spine_pin], fill="#94a3b8", width=2)
    draw.ellipse([(spine_target[0]-4, spine_target[1]-4), (spine_target[0]+4, spine_target[1]+4)], fill="#475569")
    draw_badge(spine_pin[0], spine_pin[1]-20, 200, 52, "척추 (Spine)", "체중 및 상체 하중 전달", "#f8fafc", "#cbd5e1", "#1e293b", "#64748b")

    # 2. 천골 (Sacrum) - 중앙 주황 블록
    sacrum_target = (img_x + 320, img_y + 160)
    sacrum_pin = (img_x + 460, img_y + 155)
    draw.line([sacrum_target, sacrum_pin], fill="#f97316", width=2)
    draw.ellipse([(sacrum_target[0]-4, sacrum_target[1]-4), (sacrum_target[0]+4, sacrum_target[1]+4)], fill="#ea580c")
    draw_badge(sacrum_pin[0], sacrum_pin[1]-20, 220, 52, "천골 (Sacrum)", "척추를 지탱하는 중심 지지대", "#fff7ed", "#fdba74", "#c2410c", "#9a3412")

    # 3. 좌측 장골 (Ilium) - 민트 블록
    ilium_l_target = (img_x + 130, img_y + 150)
    ilium_l_pin = (img_x - 120, img_y + 140)
    draw.line([ilium_l_target, ilium_l_pin], fill="#0284c7", width=2)
    draw.ellipse([(ilium_l_target[0]-4, ilium_l_target[1]-4), (ilium_l_target[0]+4, ilium_l_target[1]+4)], fill="#0369a1")
    draw_badge(ilium_l_pin[0]-80, ilium_l_pin[1]-20, 210, 52, "장골 (Ilium) - 정상측", "천골 양옆의 독립 회전 관절", "#f0f9ff", "#7dd3fc", "#0369a1", "#0284c7")

    # 4. 우측 장골 (Ilium) - 회전 변위측
    ilium_r_target = (img_x + 500, img_y + 200)
    ilium_r_pin = (img_x + 650, img_y + 240)
    draw.line([ilium_r_target, ilium_r_pin], fill="#e11d48", width=2)
    draw.ellipse([(ilium_r_target[0]-4, ilium_r_target[1]-4), (ilium_r_target[0]+4, ilium_r_target[1]+4)], fill="#be123c")
    draw_badge(ilium_r_pin[0], ilium_r_pin[1]-20, 240, 54, "장골 (Ilium) - 회전 변위측", "앞(전방)으로 회전하며 기울어짐", "#fff1f2", "#fecdd3", "#be123c", "#e11d48")

    # 5. 좌측 대퇴골 (Femur)
    femur_l_target = (img_x + 135, img_y + 350)
    femur_l_pin = (img_x - 120, img_y + 350)
    draw.line([femur_l_target, femur_l_pin], fill="#64748b", width=2)
    draw.ellipse([(femur_l_target[0]-4, femur_l_target[1]-4), (femur_l_target[0]+4, femur_l_target[1]+4)], fill="#475569")
    draw_badge(femur_l_pin[0]-80, femur_l_pin[1]-20, 210, 52, "대퇴골 (Femur)", "양쪽 다리뼈 길이는 동일함", "#f8fafc", "#cbd5e1", "#334155", "#64748b")

    # 6. 하단 다리길이 차이 기준선 표시
    left_foot_y = img_y + 440
    right_foot_y = img_y + 497

    # 좌측 수평 기준선 (파란색)
    draw.line([(img_x + 70, left_foot_y), (img_x + 560, left_foot_y)], fill="#0284c7", width=2)
    # 우측 수평 기준선 (빨간색)
    draw.line([(img_x + 430, right_foot_y), (img_x + 620, right_foot_y)], fill="#e11d48", width=2)

    # 편차 수직 화살표
    arrow_x = img_x + 550
    draw.line([(arrow_x, left_foot_y), (arrow_x, right_foot_y)], fill="#e11d48", width=2)
    draw.polygon([(arrow_x, right_foot_y), (arrow_x - 4, right_foot_y - 8), (arrow_x + 4, right_foot_y - 8)], fill="#e11d48")
    draw.polygon([(arrow_x, left_foot_y), (arrow_x - 4, left_foot_y + 8), (arrow_x + 4, left_foot_y + 8)], fill="#e11d48")

    # 편차 텍스트 뱃지
    draw_badge(arrow_x + 15, left_foot_y + 8, 230, 54, "다리길이 불일치 발생!", "고관절 소켓 하강으로 다리가 길어 보임", "#fff1f2", "#fda4af", "#9f1239", "#e11d48")

    # 하단 요약 박스 (소프트 라운드 카드)
    box_top = 750
    box_bottom = 910
    draw.rounded_rectangle([(60, box_top), (1140, box_bottom)], radius=12, fill="#f8fafc", outline="#e2e8f0", width=1)

    # 헤더 아이콘 배지 (파란 원형 태그)
    draw.ellipse([(85, box_top + 18), (105, box_top + 38)], fill="#0ea5e9")
    draw.text((92, box_top + 19), "i", font=font_badge, fill="#ffffff")
    draw.text((115, box_top + 18), "핵심 원리 요약 : 왜 다리 길이가 달라 보일까요?", font=font_bottom_bold, fill="#0f172a")
    
    line1 = "1. 골반은 통짜 뼈가 아니라, 척추를 지탱하는 천골(Sacrum)과 양쪽 다리를 잇는 장골(Ilium)이 만나는 회전 시소 구조입니다."
    line2 = "2. 짝다리나 다리 꼬기 습관으로 한쪽 장골이 앞(전방)으로 회전하면, 고관절 소켓 자체가 아래로 밀려 내려옵니다."
    line3 = "3. 결과적으로 다리뼈(Femur) 길이는 동일해도 시작점 높이가 달라져 심한 다리길이 비대칭이 발생하게 됩니다."

    draw.text((85, box_top + 50), line1, font=font_bottom_norm, fill="#334155")
    draw.text((85, box_top + 78), line2, font=font_bottom_norm, fill="#334155")
    draw.text((85, box_top + 106), line3, font=font_bottom_norm, fill="#334155")

    # 저장
    out_file = OUTPUT_DIR / "골반_회전시소_메커니즘.png"
    canvas.save(out_file, "PNG", quality=95)
    print(f"인포그래픽 카드 생성 완료: {out_file}")

if __name__ == "__main__":
    make_diagram()
