@echo off
cd /d "%~dp0"

if not exist "node_modules" (
  echo [牛股计算器] 首次运行，正在安装依赖，请稍候...
  call npm install
)

echo [牛股计算器] 正在启动...
call npm start
