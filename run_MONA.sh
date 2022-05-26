#!/bin/bash

cd ~/MONA
source venv/bin/activate 
gnome-terminal -t 'SeedLink MONA' --tab -- python mona_sl_client.py
printf "\e]2;Dashboard MONA\a"
gunicorn -w 1 app:server -b:8050

