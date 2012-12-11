@echo off
:: finds the Spacetime installation folder and uses the Python distribution located there
FOR /F "skip=4 tokens=3 delims=	" %%A IN ('REG QUERY HKCU\Software\Spacetime /ve') DO SET STFOLDER=%%A
"%STFOLDER%\python" spacetime %*
