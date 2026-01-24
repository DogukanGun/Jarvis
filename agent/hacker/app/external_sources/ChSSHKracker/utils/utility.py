# -*- UTF-8 -*-
# utils/utility.py

import os


class Utility:
    def __init__(self) -> None:
        self.clear = 'cls' if os.name == 'nt' else 'clear'
     
    def clear_screen(self):
        os.system(self.clear)
    
    def format_duration(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        days = int(seconds) // 86400
        hours = (int(seconds) % 86400) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        return f"{days:02d}:{hours:02d}:{minutes:02d}:{secs:02d}"

utility = Utility()