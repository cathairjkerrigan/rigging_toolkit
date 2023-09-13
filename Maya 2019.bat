@echo off
setlocal

set MAYA_MODULE_PATH=%~dp0;

rem Install Python dependencies using pip
pip install -r requirements.txt

set MAYA_DISABLE_CLIC_IPM=1
set MAYA_DISABLE_CIP=1
set MAYA_DISABLE_CER=1 
set MAYA_VP2_DEVICE_OVERRIDE=VirtualDeviceDx11
set MAYA_VP2_WANT_OGS_WARNINGS=1
set MAYA_NO_WARNING_FOR_MISSING_DEFAULT_RENDERER=1
set MAYA_SKIP_USERSETUP_CHECK=1

rem Start Maya
start "" "C:\Program Files\Autodesk\Maya2019\bin\maya.exe" -hideConsole

endlocal