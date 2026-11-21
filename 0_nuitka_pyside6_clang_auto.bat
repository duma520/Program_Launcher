nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
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
    --output-dir=build_output ^
    Program_Launcher.py

