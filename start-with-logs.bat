@echo off
REM ============================================
REM 熵舟·智能体工作台 - 一键启动（带日志终端）
REM ============================================
REM 双击此文件即可启动前后端，并打开两个终端窗口：
REM   - 后端日志窗口 (Flask :5000)
REM   - 前端日志窗口 (Vite  :5173)
REM ============================================

REM 确保 logs 目录存在
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM 调用 PowerShell 脚本
powershell -ExecutionPolicy Bypass -File "%~dp0start-with-logs.ps1"
