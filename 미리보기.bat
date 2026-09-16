@echo off
rem 기능: 마크다운 원고를 스마트에디터 ONE 스타일 HTML로 변환하여 기본 웹 브라우저에서 즉시 열어주는 도구
rem 목적: 에디터원에 올리기 전 10초 만에 브라우저에서 훑어보고 점검(19pt, 모바일뷰, 스티커, 인용구 등)

chcp 65001 > nul
set PYTHONUTF8=1
echo ========================================================
echo    리무브 체형교정 블로그 HTML 미리보기 도구
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
    echo [안내] 대상을 지정하지 않아 최신 포스트를 브라우저에서 엽니다...
    %PYCMD% scripts\generate_preview.py --open
) else (
    echo [안내] 대상 원고: %TARGET%
    %PYCMD% scripts\generate_preview.py "%TARGET%" --open
)

echo.
echo ========================================================
echo    미리보기가 브라우저에 열렸습니다! 창을 닫으셔도 됩니다.
echo ========================================================
pause
