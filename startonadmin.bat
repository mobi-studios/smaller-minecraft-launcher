@echo off
%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/k %~s0 ::","","runas",1)(window.close)&&exit
cd /d "%~dp0"
mcl.exe