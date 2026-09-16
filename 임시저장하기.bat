@echo off
rem 기능: 마크다운 원고를 네이버 스마트에디터 ONE에 주입하여 임시저장하는 실행 배치 파일
rem 목적: 더블클릭 한 번으로 최신 원고를 네이버 블로그에 단일 임시저장 (19pt, 스티커, 인용구, 사진 등)

chcp 65001 > nul
set PYTHONUTF8=1
echo ========================================================
echo    리무브 체형교정 네이버 블로그 자동 임시저장 도구
echo ========================================================
echo.

set TARGET=%~1

where py >nul 2>nul
if %errorlevel% equ 0 (
    set PYCMD=py -3
) else (
    set PYCMD=python
)

if "%TARGET%"=="" (
    echo [안내] 대상을 지정하지 않아 최신 패키징된 원고를 자동으로 임시저장합니다...
    %PYCMD% scripts\naver_bot.py draft --file "output"
) else (
    echo [안내] 대상 원고: %TARGET%
    %PYCMD% scripts\naver_bot.py draft --file "%TARGET%"
)

echo.
echo ========================================================
echo    임시저장 완료! 네이버 블로그 저장함에서 확인하세요.
echo ========================================================
pause
