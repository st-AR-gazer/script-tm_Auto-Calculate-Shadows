@echo off
setlocal enabledelayedexpansion

tasklist /FI "IMAGENAME eq Trackmania.exe" 2>NUL | find /I /N "Trackmania.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Trackmania is currently running. Attempting to close it...
    taskkill /F /IM "Trackmania.exe"
    echo Trackmania has been closed. Continuing with the script...
    timeout /t 3 >nul
)

set mapsDir=%~dp0
set mapsDir=%mapsDir:~0,-1%
for %%A in ("%mapsDir%") do set folderName=%%~nxA

if not "%folderName%"=="Maps" (
    echo This script must be run from a folder named 'Maps'
    pause
    exit /b
)

if exist "%mapsDir%\count.txt" (
    set /p count=<"%mapsDir%\count.txt"
    for /f "skip=1 delims=" %%i in (%mapsDir%\count.txt) do (set "tmPath=%%i" & goto nextline)
    :nextline
    if exist "!tmPath!" (
        goto useSavedPath
    )
)

echo Would you like the script to attempt to find the Trackmania.exe path automatically? (Y/N)
set /p userChoice=
if /i "%userChoice%"=="Y" (
    echo Searching for Trackmania.exe, this process can take some time, the script is currently trying to find tm :]
    set count=0
    for %%d in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        if exist %%d:\ (
            echo Checking drive %%d: ...
            for /f "delims=" %%i in ('dir %%d:\Trackmania.exe /s /b 2^>nul') do (
                set /a count+=1
                set tmPath[!count!]=%%i
            )
        )
    )
    if !count!==0 (
        echo Could not find Trackmania.exe. Please set the path manually.
        pause
        exit /b
    ) else if !count!==1 (
        echo Found Trackmania.exe at !tmPath[1]!
        set tmPath=!tmPath[1]!
    ) else (
        echo Multiple instances of Trackmania.exe found. Please choose one:
        for /l %%j in (1,1,!count!) do (
            echo %%j. !tmPath[%%j]!
        )
        set /p choice=Enter the number corresponding to the desired path: 
        set tmPath=!tmPath[%choice%]!
    )
) else (
    echo Please manually add the full path to Trackmania.exe in the following prompt:
    set /p tmPath=Enter full path to Trackmania.exe: 
)

echo %count% > "%mapsDir%\count.txt"
echo %tmPath% >> "%mapsDir%\count.txt"
goto afterPath

:useSavedPath
echo Using saved path to Trackmania.exe from count.txt

:afterPath
set /P "excludeDir=Please enter the name of the folder you want to calc the shadows for: "

start "" "%tmPath%" /computeallshadows="%excludeDir%" /useronly /collections=Stadium /LmQuality=High

:wait
timeout /t 1 >nul
tasklist /FI "IMAGENAME eq Trackmania.exe" 2>NUL | find /I /N "Trackmania.exe">NUL
if "%ERRORLEVEL%"=="0" goto wait

@echo on
endlocal
