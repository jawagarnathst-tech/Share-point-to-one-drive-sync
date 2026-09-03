@echo off
cd /d "c:\Users\c1822\sharepoint to one drive"
call ".venv\Scripts\activate.bat"
python -m app.cli sync-once >> sync_log.txt 2>&1
