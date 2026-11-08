#!/usr/bin/env python3
"""Wispbyte / Pterodactyl default 'bot.py' entrypoint wrapper."""
import os
import runpy

os.chdir(os.path.dirname(os.path.abspath(__file__)))
runpy.run_path("main.py", run_name="__main__")
