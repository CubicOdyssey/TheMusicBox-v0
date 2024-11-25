from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Callable
import threading
import queue
import time
import json
import os
import logging
import board
import busio
from pygame import mixer
from adafruit_pn532.i2c import PN532_I2C
import RPi.GPIO as GPIO
from rx.subject import Subject

class PlaybackState(Enum):
   STOPPED = "stopped"
   PLAYING = "playing" 
   PAUSED = "paused"

@dataclass
class AudioStatus:
   state: PlaybackState = PlaybackState.STOPPED
   volume: int = 50
   current_file: Optional[str] = None

class AudioPlayer:
   def __init__(self):
       mixer.init(frequency=44100, size=-16, channels=2)
       self.status = AudioStatus()
       self._command_queue = queue.Queue()
       self._state_lock = threading.RLock()
       
       self.on_start: Optional[Callable] = None
       self.on_stop: Optional[Callable] = None
       
       threading.Thread(target=self._process_commands, daemon=True).start()
   
   def _process_commands(self):
       while True:
           try:
               cmd, args = self._command_queue.get(timeout=0.5)
               with self._state_lock:
                   cmd(*args)
           except queue.Empty:
               continue
   
   def play(self, file_path: str):
       self._command_queue.put((self._play, [file_path]))
       
   def _play(self, file_path: str):
       try:
           if self.status.state != PlaybackState.STOPPED:
               mixer.music.stop()
               
           mixer.music.load(file_path)
           mixer.music.play()
           
           self.status.state = PlaybackState.PLAYING
           self.status.current_file = file_path
           
           if self.on_start:
               self.on_start()
               
       except Exception as e:
           logging.error(f"Play error: {e}")
           
   def stop(self):
       self._command_queue.put((self._stop, []))
       
   def _stop(self):
       if self.status.state != PlaybackState.STOPPED:
           mixer.music.stop()
           self.status.state = PlaybackState.STOPPED
           self.status.current_file = None
           
           if self.on_stop:
               self.on_stop()
               
   def pause(self):
       self._command_queue.put((self._pause, []))
       
   def _pause(self):
       if self.status.state == PlaybackState.PLAYING:
           mixer.music.pause()
           self.status.state = PlaybackState.PAUSED
           
   def resume(self):
       self._command_queue.put((self._resume, []))
       
   def _resume(self):
       if self.status.state == PlaybackState.PAUSED:
           mixer.music.unpause()
           self.status.state = PlaybackState.PLAYING
           
   def set_volume(self, volume: int):
       self._command_queue.put((self._set_volume, [volume]))
       
   def _set_volume(self, volume: int):
       self.status.volume = max(0, min(100, volume))
       mixer.music.set_volume(self.status.volume / 100)
       
   def cleanup(self):
       self.stop()
       mixer.quit()

class MusicBox:
   def __init__(self):
       self.logger = logging.getLogger("MusicBox")
       
       # Configuration des GPIO
       self.volume_pins = {'up': 22, 'down': 27, 'play': 17}
       self.button_cooldown = 0.3
       self.last_button_press = 0
       
       # Initialisation NFC
       self.i2c = busio.I2C(board.SCL, board.SDA)
       self.pn532 = PN532_I2C(self.i2c, debug=False)
       self.pn532.SAM_configuration()
       self.last_read = {'tag': None, 'time': 0}
       
       # Audio
       self.audio = AudioPlayer()
       
       # États et verrous
       self.running = True
       self._tag_subject = Subject()
       self._state_lock = threading.RLock()
       
       # Configuration GPIO
       GPIO.setmode(GPIO.BCM)
       for pin in self.volume_pins.values():
           GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
           
       # Chargement config
       self.nfc_data = self._load_nfc_data()
       
       # Démarrage threads
       self._start_threads()
       
   def _start_threads(self):
       self.nfc_thread = threading.Thread(target=self._nfc_loop, daemon=True)
       self.button_thread = threading.Thread(target=self._button_loop, daemon=True) 
       self.nfc_thread.start()
       self.button_thread.start()
       
   def _load_nfc_data(self) -> list:
       try:
           with open('nfc_data.json', 'r') as f:
               return json.load(f)
       except Exception as e:
           self.logger.error(f"Error loading NFC data: {e}")
           return []
           
   def _nfc_loop(self):
    while self.running:
        try:
            current_time = time.time()
            tag = self._read_tag()
            
            if tag:
                print(f"[NFC] Tag detected: {tag}")
                
                # Premier scan ou nouveau tag
                if tag != self.last_read['tag']:
                    print("[NFC] New tag - Starting playback")
                    self.last_read = {'tag': tag, 'time': current_time}
                    self._handle_tag(tag)
                    
                # Tag toujours présent    
                else:
                    print("[NFC] Tag still present - Continuing playback")
                time.sleep(1) # Vérification toutes les secondes si tag présent
                
            else:
                # Tag retiré
                if self.last_read['tag']:
                    print("[NFC] Tag removed - Stopping playback")
                    self.audio.stop()
                    self.last_read = {'tag': None, 'time': current_time}
                else:
                    print("[NFC] No tag detected")
                time.sleep(0.5) # Scan 2x par seconde si pas de tag
               
        except Exception as e:
            self.logger.error(f"NFC error: {e}")
            time.sleep(1)
            
   def _read_tag(self) -> Optional[str]:
       try:
           uid = self.pn532.read_passive_target(timeout=0.5)
           if uid:
               return ':'.join([hex(i)[2:].upper().zfill(2) for i in uid])
       except Exception as e:
           self.logger.error(f"Tag read error: {e}")
       return None
       
   def _handle_tag(self, tag: str):
        self._tag_subject.on_next(tag)
        audio_file = next((item['path'] for item in self.nfc_data 
                        if item['idtagnfc'] == tag), None) 
        
        if audio_file:
            print(f"[Player] Playing file: {audio_file}")
            self.audio.play(audio_file)
        else:
            print(f"[NFC] No audio file for tag: {tag}")
           
   def _button_loop(self):
    while self.running:
        current_time = time.time()
        if current_time - self.last_button_press >= self.button_cooldown:
            if not GPIO.input(self.volume_pins['up']):
                print(f"[Buttons] Volume up: {self.audio.status.volume + 10}")
                self.audio.set_volume(self.audio.status.volume + 10)
                self.last_button_press = current_time
            elif not GPIO.input(self.volume_pins['down']):
                print(f"[Buttons] Volume down: {self.audio.status.volume - 10}")
                self.audio.set_volume(self.audio.status.volume - 10) 
                self.last_button_press = current_time
            elif not GPIO.input(self.volume_pins['play']):
                state = "Pausing" if self.audio.status.state == PlaybackState.PLAYING else "Resuming"
                print(f"[Buttons] {state} playback")
                self._handle_play_button()
                self.last_button_press = current_time
        time.sleep(0.05)
           
   def _handle_play_button(self):
       if self.audio.status.state == PlaybackState.PLAYING:
           self.audio.pause()
       elif self.audio.status.state == PlaybackState.PAUSED:
           self.audio.resume()
           
   @property
   def tag_subject(self) -> Subject:
       return self._tag_subject
           
   def cleanup(self):
       self.logger.info("Cleaning up...")
       self.running = False
       self.audio.cleanup()
       GPIO.cleanup()
       self.logger.info("Cleanup complete")

if __name__ == "__main__":
   logging.basicConfig(level=logging.INFO)
   music_box = None
   
   try:
       music_box = MusicBox()
       while True:
           time.sleep(1)
           
   except KeyboardInterrupt:
       pass
       
   except Exception as e:
       logging.error(f"Fatal error: {e}")
       
   finally:
       if music_box:
           music_box.cleanup()