@echo off
"%FAKE_GH_PYTHON%" -X utf8 "%~dp0gh.py" %*
exit /b %ERRORLEVEL%
