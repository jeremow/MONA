@ECHO OFF

:a
cmd /k "cd /d C:\Program Files (x86)\MONA_LISA\venv\Scripts & activate & cd /d C:\Program Files (x86)\MONA_LISA & python app.py"

PAUSE
goto a