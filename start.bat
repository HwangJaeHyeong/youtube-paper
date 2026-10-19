@echo off
rem input/ -> output/ with a template picked in the terminal, then compose down.
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  템플릿을 선택하세요
echo    1. default    (민재 + 수빈 대화)
echo    2. shortform  (숏폼템플릿: 1인 + 데모 영상)
echo.
set "PICK="
set /p "PICK= 번호 입력 [1/2, 기본 1]: "
set "TEMPLATE=default"
if "%PICK%"=="2" set "TEMPLATE=shortform"
echo.
echo  TEMPLATE=%TEMPLATE% 로 시작합니다
docker compose up
docker compose down
pause
