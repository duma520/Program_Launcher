@echo off
echo ============================================
echo   Nuitka Debug Build - Console Enabled
echo   编译后请从命令行运行 exe 查看错误输出
echo ============================================

nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=attach ^
    --windows-icon-from-ico=icon.ico ^
    --include-data-files=icon.ico=icon.ico ^
    --include-data-dir=resource\icons=resource\icons ^
    --include-module=PySide6.QtSvg ^
    --include-module=pinyin ^
    --include-package=win32ctypes ^
    --include-module=threading ^
    --include-module=concurrent.futures ^
    --include-module=concurrent.futures.thread ^
    --include-module=concurrent.futures.process ^
    --include-module=queue ^
    --include-module=weakref ^
    --include-package-data=pinyin ^
    --follow-imports ^
    --jobs=4 ^
    --clang ^
    --remove-output ^
    --output-dir=build_output_debug ^
    Program_Launcher.py

echo.
echo ============================================
echo   Build完成！请运行:
echo   build_output_debug\Program_Launcher.dist\Program_Launcher.exe
echo   如果有错误会在控制台显示
echo ============================================
pause
