@echo off
title Backend Server

echo =========================
echo Starting Backend...
echo =========================

cd /d "D:\projectP\backend"

uvicorn app.main:app --reload

pause