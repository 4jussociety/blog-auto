@echo off
rem 기능: 블로그 원고와 이미지를 output 폴더에 번호순으로 자동 패키징하는 실행 배치 파일
rem 목적: 더블클릭 한 번으로 md파일 2종과 정렬된 사진들을 output 폴더에 생성합니다.

chcp 65001 > nul
set PYTHONUTF8=1
echo ========================================================
echo    리무브 체형교정 네이버 블로그 포스트 패키징 도구
echo ========================================================
echo.
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 scripts\package_post.py
) else (
    python scripts\package_post.py
)
echo.

echo ========================================================
echo    패키징 완료! output 폴더를 확인하세요.
echo ========================================================
pause
