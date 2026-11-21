REM 查找 Python 安装路径
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
if defined PYTHON_PATH (
    set PYTHON_DIR=%~dp0
    set PYTHON_DIR=%PYTHON_DIR:~0,-1%
    echo 找到 Python: %PYTHON_PATH%
    
    REM 尝试多个可能的 Qt 插件路径
    set QT_PLUGIN_PATH1=%PYTHON_DIR%\Lib\site-packages\PyQt5\Qt\plugins\platforms\qwindows.dll
    set QT_PLUGIN_PATH2=%PYTHON_DIR%\Lib\site-packages\PyQt5\Qt5\plugins\platforms\qwindows.dll
    set QT_PLUGIN_PATH3=%PYTHON_DIR%\Lib\site-packages\PyQt5\plugins\platforms\qwindows.dll
    
    if exist "%QT_PLUGIN_PATH1%" (
        mkdir Program_Launcher.dist\PyQt5\Qt\plugins\platforms 2>nul
        copy "%QT_PLUGIN_PATH1%" Program_Launcher.dist\PyQt5\Qt\plugins\platforms\
        echo 成功复制 qwindows.dll
    ) else if exist "%QT_PLUGIN_PATH2%" (
        mkdir Program_Launcher.dist\PyQt5\Qt5\plugins\platforms 2>nul
        copy "%QT_PLUGIN_PATH2%" Program_Launcher.dist\PyQt5\Qt5\plugins\platforms\
        echo 成功复制 qwindows.dll
    ) else if exist "%QT_PLUGIN_PATH3%" (
        mkdir Program_Launcher.dist\PyQt5\plugins\platforms 2>nul
        copy "%QT_PLUGIN_PATH3%" Program_Launcher.dist\PyQt5\plugins\platforms\
        echo 成功复制 qwindows.dll
    ) else (
        echo 错误：找不到 qwindows.dll！
        echo 正在搜索可能的路径...
        dir /s "%PYTHON_DIR%\*qwindows.dll" 2>nul
    )
) else (
    echo 错误：找不到 Python 安装路径！
    echo 请手动复制 qwindows.dll 到 Program_Launcher.dist\PyQt5\Qt\plugins\platforms\
)

echo.
echo 编译完成！可执行文件位于 Program_Launcher.dist\Program_Launcher.exe