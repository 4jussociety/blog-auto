# -*- coding: utf-8 -*-
"""
골반 측면 회전(전방/후방)에 따른 다리길이 변화 - 절대 정밀 기하학 마스터피스 (v3)
디테일 보강:
1. 소켓 주변 골반 뼈 네모난 잘림 제거 (샤프트만 정밀 삭제하여 뼈 질감 100% 보존)
2. 왼쪽/오른쪽 femur head 최상단 접선 1px 초정밀 밀착
3. 동일 대퇴골(480px) 1:1 복제 결합
4. 헤드 상승(Δh) = 다리 단축(Δh) 기하학적 완벽 일치
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

WORKSPACE_DIR = Path(r"c:\Users\myrea\OneDrive\바탕 화면\개발\리무브체형교정\블로그")
OUTPUT_DIR = WORKSPACE_DIR / "output" / "2026-09-26_4편_골반틀어짐_다리길이차이_교정전후" / "images"
RAW_IMG_PATH = Path(r"C:\Users\myrea\.gemini\antigravity-ide\brain\3f5d24db-5c3b-4908-b118-ab0595c31854\pelvis_exaggerated_rotation_1790410891490.jpg")
FEMUR_ASSET_PATH = WORKSPACE_DIR / "assets" / "images" / "해부학_다이어그램" / "femur_pure_perfect.png"

FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"

def generate_perfect_v3():
    # 1. 원본 뼈 이미지 로드 (1376 x 768)
    base_img = Image.open(RAW_IMG_PATH).convert("RGB")
    d_base = ImageDraw.Draw(base_img)

    # 2. 기존 하단 빨간 점선 완전 삭제
    d_base.rectangle([(0, 720), (1376, 768)], fill=(255, 255, 255))

    # 3. 골반 소켓 뼈를 깎지 않고, 샤프트(기둥) 아래쪽만 흰색으로 지우기!
    # 왼쪽 샤프트 (y: 360~720, x: 360~415)
    d_base.rectangle([(360, 360), (415, 720)], fill=(255, 255, 255))
    # 오른쪽 샤프트 (y: 350~720, x: 965~1015)
    d_base.rectangle([(965, 350), (1015, 720)], fill=(255, 255, 255))

    # 4. 마스터 대퇴골 로드 (길이: 480px, head top: y=9, bottom: y=489)
    femur = Image.open(FEMUR_ASSET_PATH).convert("RGBA")
    FEMUR_LEN = 480

    # 5. 양쪽에 100% 동일한 대퇴골(Twin Femur) 결합
    # 왼쪽 소켓 아치: y = 262에 헤드 꼭대기 밀착
    # 부착 좌표: x = 389 - 42 = 347, y = 262 - 9 = 253
    base_img.paste(femur, (347, 253), femur)

    # 오른쪽 소켓 아치: y = 222에 헤드 꼭대기 밀착 (정확히 40px 상승!)
    # 부착 좌표: x = 1001 - 42 = 959, y = 222 - 9 = 213
    base_img.paste(femur, (959, 213), femur)

    # 6. 캔버스 확장 (1376 x 840)
    y_offset = 20
    canvas = Image.new("RGB", (1376, 840), (255, 255, 255))
    canvas.paste(base_img, (0, y_offset))
    draw = ImageDraw.Draw(canvas)

    # 폰트
    font_chip = ImageFont.truetype(FONT_BOLD, 14)
    font_measure = ImageFont.truetype(FONT_BOLD, 13)
    font_result = ImageFont.truetype(FONT_BOLD, 15)
    font_delta = ImageFont.truetype(FONT_BOLD, 12)

    # 7. 상단 캡슐 칩 라벨
    draw.rounded_rectangle([(300, 14), (480, 46)], radius=16, fill="#fff1f2", outline="#f43f5e", width=1)
    draw.text((325, 20), "골반 전방 회전", font=font_chip, fill="#e11d48")

    draw.rounded_rectangle([(910, 14), (1090, 46)], radius=16, fill="#eff6ff", outline="#3b82f6", width=1)
    draw.text((935, 20), "골반 후방 회전", font=font_chip, fill="#2563eb")

    # 기하학적 Y 좌표 (y_offset=20 반영)
    L_HEAD_Y = 262 + y_offset # 282 (대퇴골두 최상단 꼭대기 칼밀착)
    L_FOOT_Y = L_HEAD_Y + FEMUR_LEN # 762 (다리 하단 끝)
    DELTA_H = 40
    R_HEAD_Y = L_HEAD_Y - DELTA_H # 242 (대퇴골두 최상단 꼭대기 칼밀착)
    R_FOOT_Y = R_HEAD_Y + FEMUR_LEN # 722 (다리 하단 끝)

    # 8. 대퇴골두(Femur Head) 최상단 기준선 & 헤드 상승분(Δh) 표시
    # 왼쪽 헤드 최상단 접선
    draw.line([(345, L_HEAD_Y), (485, L_HEAD_Y)], fill="#0284c7", width=1)
    # 오른쪽 헤드 최상단 접선
    draw.line([(895, R_HEAD_Y), (1045, R_HEAD_Y)], fill="#0284c7", width=1)
    # 비교 가이드 점선 (중간)
    for dot_x in range(680, 900, 10):
        draw.line([(dot_x, L_HEAD_Y), (dot_x + 5, L_HEAD_Y)], fill="#cbd5e1", width=1)
        draw.line([(dot_x, R_HEAD_Y), (dot_x + 5, R_HEAD_Y)], fill="#cbd5e1", width=1)

    # 헤드 상승분 (Δh = 40px) 양방향 화살표 (x=790)
    arrow_mid_x = 790
    draw.line([(arrow_mid_x, R_HEAD_Y), (arrow_mid_x, L_HEAD_Y)], fill="#0284c7", width=2)
    draw.polygon([(arrow_mid_x, R_HEAD_Y), (arrow_mid_x - 3, R_HEAD_Y + 6), (arrow_mid_x + 3, R_HEAD_Y + 6)], fill="#0284c7")
    draw.polygon([(arrow_mid_x, L_HEAD_Y), (arrow_mid_x - 3, L_HEAD_Y - 6), (arrow_mid_x + 3, L_HEAD_Y - 6)], fill="#0284c7")
    # 헤드 상승 칩
    draw.rounded_rectangle([(arrow_mid_x + 10, R_HEAD_Y + 8), (arrow_mid_x + 125, R_HEAD_Y + 32)], radius=4, fill="#f0f9ff", outline="#7dd3fc", width=1)
    draw.text((arrow_mid_x + 18, R_HEAD_Y + 12), "헤드 상승 (Δh)", font=font_delta, fill="#0369a1")

    # 9. [동일 길이 L] 치수선 브래킷 (Femur Head 최상단 접선부터 다리끝 접선까지 1px 오차 없이 칼밀착!)
    # 왼쪽 치수선 (x=455)
    draw.line([(445, L_HEAD_Y), (460, L_HEAD_Y)], fill="#475569", width=2)       # 헤드 꼭대기 접선
    draw.line([(445, L_FOOT_Y), (460, L_FOOT_Y)], fill="#475569", width=2)       # 다리 끝단 접선
    draw.line([(455, L_HEAD_Y), (455, L_FOOT_Y)], fill="#64748b", width=1)       # 세로선
    l_mid = (L_HEAD_Y + L_FOOT_Y) // 2
    draw.rounded_rectangle([(465, l_mid - 13), (575, l_mid + 13)], radius=4, fill="#f8fafc", outline="#cbd5e1", width=1)
    draw.text((475, l_mid - 9), "동일 길이 [ L ]", font=font_measure, fill="#334155")

    # 오른쪽 치수선 (x=1055)
    draw.line([(1045, R_HEAD_Y), (1060, R_HEAD_Y)], fill="#475569", width=2)     # 헤드 꼭대기 접선
    draw.line([(1045, R_FOOT_Y), (1060, R_FOOT_Y)], fill="#475569", width=2)     # 다리 끝단 접선
    draw.line([(1055, R_HEAD_Y), (1055, R_FOOT_Y)], fill="#64748b", width=1)     # 세로선
    r_mid = (R_HEAD_Y + R_FOOT_Y) // 2
    draw.rounded_rectangle([(1065, r_mid - 13), (1175, r_mid + 13)], radius=4, fill="#f8fafc", outline="#cbd5e1", width=1)
    draw.text((1075, r_mid - 9), "동일 길이 [ L ]", font=font_measure, fill="#334155")

    # 10. 하단 다리 끝 기준선 및 단축분(Δh) 표시
    # 바닥 빨간 점선 (y = L_FOOT_Y = 762) - 단 1개만 선명하게 그리기!
    for dash_x in range(120, 1260, 20):
        draw.line([(dash_x, L_FOOT_Y), (dash_x + 12, L_FOOT_Y)], fill="#dc2626", width=2)

    # 오른쪽 다리 끝 수평 보조선 (y = R_FOOT_Y = 722)
    draw.line([(960, R_FOOT_Y), (1045, R_FOOT_Y)], fill="#93c5fd", width=1)

    # 붕 뜬 간격 치수 화살표 (x=1035)
    gap_x = 1035
    draw.line([(gap_x, R_FOOT_Y), (gap_x, L_FOOT_Y)], fill="#e11d48", width=2)
    draw.polygon([(gap_x, R_FOOT_Y), (gap_x - 3, R_FOOT_Y + 6), (gap_x + 3, R_FOOT_Y + 6)], fill="#e11d48")
    draw.polygon([(gap_x, L_FOOT_Y), (gap_x - 3, L_FOOT_Y - 6), (gap_x + 3, L_FOOT_Y - 6)], fill="#e11d48")

    # 다리 단축 칩
    draw.rounded_rectangle([(gap_x + 12, R_FOOT_Y + 8), (gap_x + 135, R_FOOT_Y + 32)], radius=4, fill="#fff1f2", outline="#fda4af", width=1)
    draw.text((gap_x + 20, R_FOOT_Y + 12), "다리 단축 (Δh)", font=font_delta, fill="#be123c")

    # 11. 최종 결과 뱃지 (미니멀)
    draw.rounded_rectangle([(325, 785), (455, 818)], radius=6, fill="#be123c")
    draw.text((345, 793), "다리 길어짐", font=font_result, fill="#ffffff")

    draw.rounded_rectangle([(925, 785), (1055, 818)], radius=6, fill="#1d4ed8")
    draw.text((945, 793), "다리 짧아짐", font=font_result, fill="#ffffff")

    # 저장
    out_file = OUTPUT_DIR / "골반_측면회전_다리길이변화.png"
    canvas.save(out_file, "PNG", quality=95)
    print(f"절대 정밀 기하학 인포그래픽 v3 완성: {out_file}")

if __name__ == "__main__":
    generate_perfect_v3()
