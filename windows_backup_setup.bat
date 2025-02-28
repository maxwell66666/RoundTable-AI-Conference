@echo off
REM 脚本用于在Windows系统上设置自动备份的计划任务

echo 设置RoundTable自动备份计划...

REM 获取当前目录
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM 创建备份脚本
set BACKUP_SCRIPT=%SCRIPT_DIR%\run_backup.bat
echo @echo off > "%BACKUP_SCRIPT%"
echo REM 自动备份脚本 >> "%BACKUP_SCRIPT%"
echo. >> "%BACKUP_SCRIPT%"
echo cd /d "%SCRIPT_DIR%" >> "%BACKUP_SCRIPT%"
echo. >> "%BACKUP_SCRIPT%"
echo REM 激活Python虚拟环境（如果有） >> "%BACKUP_SCRIPT%"
echo if exist venv\Scripts\activate.bat (call venv\Scripts\activate.bat) >> "%BACKUP_SCRIPT%"
echo. >> "%BACKUP_SCRIPT%"
echo REM 运行备份 >> "%BACKUP_SCRIPT%"
echo python backup.py create >> "%BACKUP_SCRIPT%"
echo. >> "%BACKUP_SCRIPT%"
echo REM 记录日志 >> "%BACKUP_SCRIPT%"
echo echo 备份已于 %%date%% %%time%% 完成 >> backup_cron.log >> "%BACKUP_SCRIPT%"

echo 已创建备份脚本: %BACKUP_SCRIPT%

REM 询问备份频率
echo 请选择备份频率:
echo 1) 每天
echo 2) 每周
echo 3) 每月
set /p FREQUENCY="请输入选项(1-3): "

REM 询问备份时间
set /p BACKUP_TIME="请输入备份时间 (24小时制，例如: 02:00): "

REM 解析时间
for /f "tokens=1,2 delims=:" %%a in ("%BACKUP_TIME%") do (
  set HOUR=%%a
  set MINUTE=%%b
)

REM 创建任务计划
set TASK_NAME=RoundTableBackup

REM 根据频率设置不同的任务
if "%FREQUENCY%"=="1" (
    set FREQ_DESC=每天 %BACKUP_TIME%
    schtasks /create /tn "%TASK_NAME%" /tr "%BACKUP_SCRIPT%" /sc DAILY /st %BACKUP_TIME% /f
) else if "%FREQUENCY%"=="2" (
    set FREQ_DESC=每周日 %BACKUP_TIME%
    schtasks /create /tn "%TASK_NAME%" /tr "%BACKUP_SCRIPT%" /sc WEEKLY /d SUN /st %BACKUP_TIME% /f
) else if "%FREQUENCY%"=="3" (
    set FREQ_DESC=每月1号 %BACKUP_TIME%
    schtasks /create /tn "%TASK_NAME%" /tr "%BACKUP_SCRIPT%" /sc MONTHLY /d 1 /st %BACKUP_TIME% /f
) else (
    echo 无效选项，使用默认设置：每天 02:00
    set FREQ_DESC=每天 02:00
    schtasks /create /tn "%TASK_NAME%" /tr "%BACKUP_SCRIPT%" /sc DAILY /st 02:00 /f
)

echo.
echo 计划任务已设置，将在%FREQ_DESC%执行备份
echo 备份脚本路径: %BACKUP_SCRIPT%
echo 备份日志: %SCRIPT_DIR%\backup_cron.log
echo.
echo 要查看当前的计划任务，请运行 'schtasks /query /tn %TASK_NAME%'
echo 要修改任务，请使用Windows的任务计划程序

pause 