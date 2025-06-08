#!/usr/bin/env python3
"""
Audio System Module for Wall-E
Handles sound effects, text-to-speech, and audio feedback
"""

import pygame
import os
import threading
import time
from typing import Dict, Optional

class AudioSystem:
    def __init__(self, sounds_dir='static/sounds', volume=0.7):
        """
        Initialize audio system
        
        Args:
            sounds_dir: Directory containing sound files
            volume: Master volume (0.0 to 1.0)
        """
        self.sounds_dir = sounds_dir
        self.volume = volume
        self.sounds = {}
        self.is_playing = False
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            print("✓ Audio system initialized")
            self.available = True
        except Exception as e:
            print(f"✗ Audio system failed to initialize: {e}")
            self.available = False
            return
        
        # Load sound effects
        self._load_sounds()
        
        # Create default sounds if they don't exist
        self._create_default_sounds()
    
    def _load_sounds(self):
        """Load all sound files from the sounds directory"""
        if not os.path.exists(self.sounds_dir):
            os.makedirs(self.sounds_dir, exist_ok=True)
            print(f"Created sounds directory: {self.sounds_dir}")
            return
        
        sound_files = [f for f in os.listdir(self.sounds_dir) if f.endswith(('.wav', '.mp3', '.ogg'))]
        
        for sound_file in sound_files:
            sound_name = os.path.splitext(sound_file)[0]
            sound_path = os.path.join(self.sounds_dir, sound_file)
            
            try:
                sound = pygame.mixer.Sound(sound_path)
                sound.set_volume(self.volume)
                self.sounds[sound_name] = sound
                print(f"Loaded sound: {sound_name}")
            except Exception as e:
                print(f"Failed to load sound {sound_file}: {e}")
        
        print(f"Loaded {len(self.sounds)} sound(s)")
    
    def _create_default_sounds(self):
        """Create default Wall-E sounds using simple tones"""
        if not self.available:
            return
        
        # Define Wall-E sound patterns (frequency, duration pairs)
        sound_patterns = {
            'startup': [(440, 0.2), (880, 0.3), (660, 0.4), (880, 0.5)],
            'curious': [(220, 0.1), (440, 0.1), (330, 0.2), (550, 0.3)],
            'happy': [(523, 0.15), (659, 0.15), (784, 0.15), (880, 0.3)],
            'worried': [(330, 0.2), (220, 0.3), (165, 0.4)],
            'beep': [(800, 0.1)],
            'error': [(200, 0.5), (150, 0.5)],
            'greeting': [(440, 0.2), (523, 0.2), (659, 0.3), (880, 0.4)]
        }
        
        for sound_name, pattern in sound_patterns.items():
            if sound_name not in self.sounds:
                try:
                    sound = self._generate_tone_sequence(pattern)
                    if sound:
                        self.sounds[sound_name] = sound
                        print(f"Generated sound: {sound_name}")
                except Exception as e:
                    print(f"Failed to generate sound {sound_name}: {e}")
    
    def _generate_tone_sequence(self, pattern):
        """Generate a sequence of tones"""
        try:
            sample_rate = 22050
            total_duration = sum(duration for freq, duration in pattern)
            total_samples = int(sample_rate * total_duration)
            
            import numpy as np
            waveform = np.zeros(total_samples, dtype=np.int16)
            
            current_sample = 0
            for frequency, duration in pattern:
                samples = int(sample_rate * duration)
                t = np.linspace(0, duration, samples, False)
                
                # Generate sine wave with fade in/out
                wave = np.sin(2 * np.pi * frequency * t)
                
                # Add fade in/out to prevent clicks
                fade_samples = min(samples // 10, 1000)
                if fade_samples > 0:
                    fade_in = np.linspace(0, 1, fade_samples)
                    fade_out = np.linspace(1, 0, fade_samples)
                    wave[:fade_samples] *= fade_in
                    wave[-fade_samples:] *= fade_out
                
                # Convert to 16-bit integers
                wave_int = (wave * 32767 * 0.3).astype(np.int16)
                
                end_sample = current_sample + samples
                if end_sample <= total_samples:
                    waveform[current_sample:end_sample] = wave_int
                
                current_sample = end_sample
            
            # Convert to stereo
            stereo_waveform = np.zeros((total_samples, 2), dtype=np.int16)
            stereo_waveform[:, 0] = waveform
            stereo_waveform[:, 1] = waveform
            
            return pygame.sndarray.make_sound(stereo_waveform)
            
        except ImportError:
            print("NumPy not available, cannot generate tones")
            return None
        except Exception as e:
            print(f"Error generating tone: {e}")
            return None
    
    def play_sound(self, sound_name: str, blocking=False) -> bool:
        """
        Play a sound effect
        
        Args:
            sound_name: Name of the sound to play
            blocking: If True, wait for sound to finish
            
        Returns:
            bool: True if sound played successfully
        """
        if not self.available:
            print(f"Audio not available, cannot play: {sound_name}")
            return False
        
        if sound_name not in self.sounds:
            print(f"Sound not found: {sound_name}")
            return False
        
        try:
            sound = self.sounds[sound_name]
            
            if blocking:
                self.is_playing = True
                sound.play()
                # Wait for sound to finish
                while pygame.mixer.get_busy():
                    time.sleep(0.1)
                self.is_playing = False
            else:
                sound.play()
            
            print(f"Playing sound: {sound_name}")
            return True
            
        except Exception as e:
            print(f"Error playing sound {sound_name}: {e}")
            return False
    
    def play_sequence(self, sound_names, delay=0.5):
        """
        Play a sequence of sounds with delays
        
        Args:
            sound_names: List of sound names to play
            delay: Delay between sounds in seconds
        """
        def play_sequence_thread():
            for sound_name in sound_names:
                self.play_sound(sound_name, blocking=True)
                if delay > 0:
                    time.sleep(delay)
        
        if self.available:
            thread = threading.Thread(target=play_sequence_thread, daemon=True)
            thread.start()
    
    def speak_text(self, text: str, blocking=False):
        """
        Convert text to speech (requires espeak or festival)
        
        Args:
            text: Text to speak
            blocking: If True, wait for speech to finish
        """
        def speak_thread():
            try:
                # Try using espeak first
                os.system(f'espeak "{text}" 2>/dev/null')
            except:
                try:
                    # Fallback to festival
                    os.system(f'echo "{text}" | festival --tts 2>/dev/null')
                except:
                    print(f"Text-to-speech not available for: {text}")
        
        if blocking:
            speak_thread()
        else:
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
    
    def stop_all_sounds(self):
        """Stop all currently playing sounds"""
        if self.available:
            pygame.mixer.stop()
            self.is_playing = False
    
    def set_volume(self, volume: float):
        """
        Set master volume
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        
        for sound in self.sounds.values():
            sound.set_volume(self.volume)
        
        print(f"Volume set to {self.volume:.1f}")
    
    def get_available_sounds(self):
        """Get list of available sound names"""
        return list(self.sounds.keys())
    
    def add_custom_sound(self, sound_name: str, file_path: str) -> bool:
        """
        Add a custom sound file
        
        Args:
            sound_name: Name to give the sound
            file_path: Path to the sound file
            
        Returns:
            bool: True if sound added successfully
        """
        if not self.available:
            return False
        
        try:
            sound = pygame.mixer.Sound(file_path)
            sound.set_volume(self.volume)
            self.sounds[sound_name] = sound
            print(f"Added custom sound: {sound_name}")
            return True
            
        except Exception as e:
            print(f"Failed to add custom sound {sound_name}: {e}")
            return False
    
    def play_wall_e_emotion(self, emotion: str):
        """
        Play appropriate sounds for Wall-E emotions
        
        Args:
            emotion: Emotion name (happy, sad, curious, excited, worried, etc.)
        """
        emotion_sounds = {
            'happy': ['happy'],
            'excited': ['happy', 'beep'],
            'curious': ['curious'],
            'worried': ['worried'],
            'sad': ['worried'],
            'greeting': ['greeting'],
            'startup': ['startup'],
            'error': ['error'],
            'surprised': ['curious', 'beep']
        }
        
        if emotion in emotion_sounds:
            sounds_to_play = emotion_sounds[emotion]
            if len(sounds_to_play) == 1:
                self.play_sound(sounds_to_play[0])
            else:
                self.play_sequence(sounds_to_play, delay=0.2)
        else:
            print(f"Unknown emotion: {emotion}")
    
    def cleanup(self):
        """Clean up audio system"""
        if self.available:
            self.stop_all_sounds()
            pygame.mixer.quit()
            print("Audio system cleaned up")

# Test function
def test_audio_system():
    """Test the audio system functionality"""
    print("Testing Audio System...")
    
    audio = AudioSystem()
    
    if not audio.available:
        print("Audio system not available for testing")
        return
    
    print(f"Available sounds: {audio.get_available_sounds()}")
    
    print("Testing Wall-E emotions...")
    emotions = ['startup', 'happy', 'curious', 'worried', 'greeting']
    
    for emotion in emotions:
        print(f"Playing {emotion}...")
        audio.play_wall_e_emotion(emotion)
        time.sleep(2)
    
    print("Testing sound sequence...")
    audio.play_sequence(['beep', 'happy', 'beep'], delay=0.5)
    time.sleep(3)
    
    audio.cleanup()
    print("Audio system test complete")

if __name__ == "__main__":
    test_audio_system()