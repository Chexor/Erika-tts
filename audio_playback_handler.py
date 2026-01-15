import os
import sys
import time
import logging
import subprocess
import ctypes
from ctypes import wintypes

class AudioPlaybackHandler:
    def __init__(self):
        self.window_configured = False

    def configure_window(self):
        """Configure the console window (Title, Position, Size)."""
        if self.window_configured:
            return

        try:
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            
            # Define types for 64-bit safety
            hwnd_type = wintypes.HWND
            rect_type = ctypes.POINTER(wintypes.RECT)
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            
            kernel32.GetConsoleWindow.restype = hwnd_type
            kernel32.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
            
            user32.MoveWindow.argtypes = [hwnd_type, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
            # Use ctypes.c_uint for uFlags (item 7)
            user32.SetWindowPos.argtypes = [hwnd_type, hwnd_type, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            user32.GetWindowRect.argtypes = [hwnd_type, rect_type]
            user32.SetForegroundWindow.argtypes = [hwnd_type]
            user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
            user32.GetWindowTextW.argtypes = [hwnd_type, wintypes.LPWSTR, ctypes.c_int]

            # Set Title
            target_title = "Erika Talks"
            kernel32.SetConsoleTitleW(target_title)
            
            # Helper to find window by title
            found_kwnd = None
            
            def enum_window_callback(hwnd, lParam):
                nonlocal found_kwnd
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if buff.value == target_title:
                    found_kwnd = hwnd
                    return False # Stop enumeration
                return True # Continue
                
            enum_proc = WNDENUMPROC(enum_window_callback)

            # Retry loop to find window by TITLE
            hwnd = None
            for i in range(20): # Try for 2 seconds
                user32.EnumWindows(enum_proc, 0)
                if found_kwnd:
                    hwnd = found_kwnd
                    logging.info(f"Found window by title '{target_title}': {hwnd}")
                    break
                time.sleep(0.1)
                
            if hwnd:
                # Move and Resize using SetWindowPos
                # HWND_TOP = 0
                # Flags: SWP_SHOWWINDOW (0x0040)
                user32.SetWindowPos(hwnd, ctypes.cast(0, hwnd_type), 0, 0, 400, 200, 0x0040)
                logging.info("Called SetWindowPos(0, 0, 400, 200)")
                
                # Force focus (sometimes needed for new windows)
                user32.SetForegroundWindow(hwnd)  
            else:
                logging.warning("Could not find console window handle after retries.")
                
            # Re-open stdout/stderr to point to the new console window
            # This bypasses the parent's redirection to DEVNULL
            try:
                sys.stdout = open("CONOUT$", "w")
                sys.stderr = open("CONOUT$", "w")
            except Exception as e:
                logging.warning(f"Failed to reopen CONOUT$: {e}")
                
            self.window_configured = True
                
        except Exception as e:
            logging.error(f"Failed to configure console: {e}")

    def display_text(self, text):
        """Clears screen and displays text."""
        # Ensure window is configured before printing
        self.configure_window()
        
        try:
            os.system('cls')
            print("\n   Erika talks...\n")
            print("   " + "-" * 40)
            print(f"\n   {text}\n")
            print("   " + "-" * 40 + "\n")
        except Exception as e:
            logging.error(f"Failed to display text: {e}")

    def play_audio(self, file_path):
        """Plays audio using winsound (native Windows, headless)."""
        if not os.path.exists(file_path):
            logging.error(f"Audio file missing: {file_path}")
            return
            
        try:
            logging.info(f"Playing via winsound: {file_path}")
            import winsound
            # SND_FILENAME: The sound parameter is the name of a WAV file.
            # SND_NODEFAULT: No default sound event is used.
            winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
            logging.info("Playback finished.")
            
        except Exception as e:
            logging.error(f"Winsound playback error: {e}")
            # Fallback to os.startfile if winsound fails (unlikely for WAV)
            try:
                logging.info("Fallback to os.startfile")
                os.startfile(file_path)
            except:
                pass
