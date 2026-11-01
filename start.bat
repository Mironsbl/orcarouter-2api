@echo off
chcp 65001 > nul
title OrcaRouter 2API Gateway (:8095)

echo =========================================================
echo   OrcaRouter 2API Gateway (:8095)
echo   Flagship Model: tencent/hy4-preview-free (770B MoE, 1M)
echo =========================================================

py -3.12 server.py
if %ERRORLEVEL% NEQ 0 (
    python server.py
)
pause
