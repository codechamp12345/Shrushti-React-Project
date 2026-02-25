# analyze_audio.py - Enhanced Version
import os
import subprocess
import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr
import math
import wave
import tempfile
import json
from datetime import datetime
from scipy import signal
from scipy.signal import find_peaks
import librosa
import noisereduce as nr

import sys
import os

# Fix for Windows Unicode
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    
class EnhancedAudioAnalyzer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        
    def extract_audio(self, video_path, audio_path=None):
        """Extract audio from video using ffmpeg with better parameters"""
        try:
            if audio_path is None:
                audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
            
            command = [
                "ffmpeg", "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
                "-ar", "44100",  # Sample rate
                "-ac", "1",  # Mono channel
                "-af", "silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-30dB",  # Remove silence
                audio_path,
                "-y"  # Overwrite output file
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                return audio_path
            else:
                print(f"FFmpeg error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return None
    
    def analyze_audio_signal(self, audio_path):
        """Analyze audio signal characteristics"""
        try:
            # Load audio file
            sample_rate, data = wav.read(audio_path)
            
            if len(data) == 0:
                return self.get_default_signal_metrics()
            
            # Convert to float for processing
            data_float = data.astype(np.float32) / 32768.0
            
            # Calculate RMS Energy (Volume)
            rms = np.sqrt(np.mean(data_float**2))
            
            # Convert to dBFS
            if rms > 0:
                db_level = 20 * math.log10(rms)
            else:
                db_level = -96  # Silence
            
            # Calculate dynamic range
            peak_value = np.max(np.abs(data_float))
            peak_db = 20 * math.log10(peak_value) if peak_value > 0 else -96
            dynamic_range = peak_db - db_level
            
            # Calculate zero-crossing rate (speech vs silence)
            zero_crossings = np.sum(np.diff(np.sign(data_float)) != 0)
            zcr = zero_crossings / len(data_float)
            
            # Calculate spectral features using librosa
            y, sr = librosa.load(audio_path, sr=None)
            
            # Calculate spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            avg_spectral_centroid = np.mean(spectral_centroid)
            
            # Calculate spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
            avg_spectral_bandwidth = np.mean(spectral_bandwidth)
            
            # Calculate pitch (fundamental frequency)
            try:
                f0, voiced_flag, voiced_probs = librosa.pyin(
                    y, 
                    fmin=librosa.note_to_hz('C2'), 
                    fmax=librosa.note_to_hz('C7'),
                    sr=sr
                )
                f0_voiced = f0[voiced_flag]
                if len(f0_voiced) > 0:
                    avg_pitch = np.nanmean(f0_voiced)
                    pitch_std = np.nanstd(f0_voiced)
                else:
                    avg_pitch = 0
                    pitch_std = 0
            except:
                avg_pitch = 0
                pitch_std = 0
            
            # Calculate signal-to-noise ratio approximation
            # Simple approach: assume noise is in silent parts
            silent_threshold = 0.01
            speech_segments = np.where(np.abs(data_float) > silent_threshold)[0]
            noise_segments = np.where(np.abs(data_float) <= silent_threshold)[0]
            
            if len(speech_segments) > 100 and len(noise_segments) > 100:
                speech_energy = np.mean(data_float[speech_segments]**2)
                noise_energy = np.mean(data_float[noise_segments]**2)
                if noise_energy > 0:
                    snr = 10 * math.log10(speech_energy / noise_energy)
                else:
                    snr = 50  # Very high SNR
            else:
                snr = 30  # Default moderate SNR
            
            return {
                'rms_energy': float(rms),
                'db_level': float(db_level),
                'peak_db': float(peak_db),
                'dynamic_range': float(dynamic_range),
                'zero_crossing_rate': float(zcr),
                'sample_rate': int(sample_rate),
                'duration_seconds': len(data_float) / sample_rate,
                'avg_spectral_centroid': float(avg_spectral_centroid),
                'avg_spectral_bandwidth': float(avg_spectral_bandwidth),
                'avg_pitch_hz': float(avg_pitch),
                'pitch_variation': float(pitch_std),
                'estimated_snr_db': float(snr)
            }
            
        except Exception as e:
            print(f"Signal analysis error: {e}")
            return self.get_default_signal_metrics()
    
    def analyze_speech_content(self, audio_path):
        """Analyze speech content and quality"""
        try:
            # Load and preprocess audio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Apply noise reduction
            y_clean = nr.reduce_noise(y=y, sr=sr)
            
            # Save cleaned audio temporarily
            temp_clean_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
            wav.write(temp_clean_path, sr, (y_clean * 32767).astype(np.int16))
            
            # Transcribe with multiple attempts for better accuracy
            transcriptions = []
            confidences = []
            
            with sr.AudioFile(temp_clean_path) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Read the entire audio file
                audio = self.recognizer.record(source)
                
                # Try Google Speech Recognition
                try:
                    transcription = self.recognizer.recognize_google(audio, show_all=True)
                    if isinstance(transcription, dict) and 'alternative' in transcription:
                        for alt in transcription['alternative']:
                            if 'transcript' in alt:
                                transcriptions.append(alt['transcript'])
                                confidences.append(alt.get('confidence', 0.7))
                    else:
                        transcriptions.append(str(transcription))
                        confidences.append(0.7)
                except sr.UnknownValueError:
                    transcriptions.append("")
                    confidences.append(0.0)
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service: {e}")
                    transcriptions.append("")
                    confidences.append(0.0)
            
            # Clean up temporary file
            os.unlink(temp_clean_path)
            
            # Use the best transcription
            if transcriptions and confidences:
                best_idx = np.argmax(confidences)
                transcription = transcriptions[best_idx]
                confidence = confidences[best_idx]
            else:
                transcription = ""
                confidence = 0.0
            
            # Analyze transcription
            words = transcription.split()
            sentences = [s.strip() for s in transcription.split('.') if s.strip()]
            
            # Calculate speech rate
            duration = len(y) / sr
            if duration > 0:
                wpm = len(words) / (duration / 60)
            else:
                wpm = 0
            
            # Calculate pause analysis
            pause_analysis = self.analyze_pauses(y_clean, sr)
            
            # Analyze filler words
            filler_words = ['um', 'uh', 'like', 'you know', 'sort of', 'kind of', 
                          'actually', 'basically', 'literally', 'i mean']
            filler_count = sum(transcription.lower().count(filler) for filler in filler_words)
            
            # Calculate vocabulary diversity
            if words:
                unique_words = set([w.lower() for w in words])
                vocab_ratio = len(unique_words) / len(words)
            else:
                vocab_ratio = 0
            
            # Analyze sentence complexity
            if sentences:
                avg_sentence_length = np.mean([len(s.split()) for s in sentences])
                sentence_complexity = self.assess_sentence_complexity(avg_sentence_length)
            else:
                avg_sentence_length = 0
                sentence_complexity = "Basic"
            
            # Analyze confident language markers
            confident_markers = ['definitely', 'certainly', 'clearly', 'obviously', 
                               'without doubt', 'confidently', 'assuredly']
            confident_count = sum(transcription.lower().count(marker) for marker in confident_markers)
            
            # Calculate grammar score approximation
            grammar_score = self.estimate_grammar_score(transcription)
            
            return {
                'transcription': transcription,
                'confidence': float(confidence),
                'word_count': len(words),
                'sentence_count': len(sentences),
                'speech_rate_wpm': float(wpm),
                'vocabulary_diversity': float(vocab_ratio),
                'filler_word_count': filler_count,
                'filler_word_ratio': filler_count / len(words) if words else 0,
                'avg_sentence_length': float(avg_sentence_length),
                'sentence_complexity': sentence_complexity,
                'confident_marker_count': confident_count,
                'estimated_grammar_score': float(grammar_score),
                **pause_analysis
            }
            
        except Exception as e:
            print(f"Speech content analysis error: {e}")
            return self.get_default_speech_metrics()
    
    def analyze_pauses(self, audio_signal, sample_rate):
        """Analyze pause patterns in speech"""
        try:
            # Calculate energy envelope
            frame_length = int(0.025 * sample_rate)  # 25ms frames
            hop_length = int(0.010 * sample_rate)    # 10ms hop
            
            rms = librosa.feature.rms(y=audio_signal, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Normalize RMS
            rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
            
            # Detect speech regions (above threshold)
            speech_threshold = 0.1
            speech_frames = rms_norm > speech_threshold
            pause_frames = rms_norm <= speech_threshold
            
            # Calculate statistics
            total_frames = len(rms_norm)
            speech_frame_count = np.sum(speech_frames)
            pause_frame_count = np.sum(pause_frames)
            
            # Convert frames to seconds
            frame_duration = hop_length / sample_rate
            total_duration = total_frames * frame_duration
            speech_duration = speech_frame_count * frame_duration
            pause_duration = pause_frame_count * frame_duration
            
            # Find pause segments
            pause_indices = np.where(pause_frames)[0]
            if len(pause_indices) > 0:
                pause_groups = np.split(pause_indices, np.where(np.diff(pause_indices) > 1)[0] + 1)
                pause_lengths = [len(group) * frame_duration for group in pause_groups]
                
                if pause_lengths:
                    avg_pause_length = np.mean(pause_lengths)
                    max_pause_length = np.max(pause_lengths)
                    pause_count = len(pause_lengths)
                else:
                    avg_pause_length = 0
                    max_pause_length = 0
                    pause_count = 0
            else:
                avg_pause_length = 0
                max_pause_length = 0
                pause_count = 0
            
            # Calculate speech-pause ratio
            if pause_duration > 0:
                speech_pause_ratio = speech_duration / pause_duration
            else:
                speech_pause_ratio = float('inf')
            
            # Assess pause quality
            pause_quality = self.assess_pause_quality(avg_pause_length, pause_count, total_duration)
            
            return {
                'total_duration_seconds': float(total_duration),
                'speech_duration_seconds': float(speech_duration),
                'pause_duration_seconds': float(pause_duration),
                'pause_percentage': float((pause_duration / total_duration) * 100) if total_duration > 0 else 0,
                'avg_pause_length_seconds': float(avg_pause_length),
                'max_pause_length_seconds': float(max_pause_length),
                'pause_count': pause_count,
                'speech_pause_ratio': float(speech_pause_ratio),
                'pause_quality': pause_quality
            }
            
        except Exception as e:
            print(f"Pause analysis error: {e}")
            return {
                'total_duration_seconds': 0,
                'speech_duration_seconds': 0,
                'pause_duration_seconds': 0,
                'pause_percentage': 0,
                'avg_pause_length_seconds': 0,
                'max_pause_length_seconds': 0,
                'pause_count': 0,
                'speech_pause_ratio': 0,
                'pause_quality': 'Unknown'
            }
    
    def assess_sentence_complexity(self, avg_sentence_length):
        """Assess sentence complexity based on average length"""
        if avg_sentence_length >= 20:
            return "Complex"
        elif avg_sentence_length >= 12:
            return "Moderate"
        elif avg_sentence_length >= 5:
            return "Simple"
        else:
            return "Fragmentary"
    
    def assess_pause_quality(self, avg_pause_length, pause_count, total_duration):
        """Assess the quality of pauses in speech"""
        if total_duration == 0:
            return "Unknown"
        
        pauses_per_minute = (pause_count / total_duration) * 60
        
        if 1.0 <= avg_pause_length <= 2.5 and 2 <= pauses_per_minute <= 6:
            return "Excellent"
        elif 0.5 <= avg_pause_length <= 3.0 and 1 <= pauses_per_minute <= 8:
            return "Good"
        elif avg_pause_length > 4.0 or pauses_per_minute > 10:
            return "Too many/long pauses"
        elif avg_pause_length < 0.3 or pauses_per_minute < 1:
            return "Rushed/No pauses"
        else:
            return "Adequate"
    
    def estimate_grammar_score(self, text):
        """Simple grammar score estimation based on text patterns"""
        if not text:
            return 5.0
        
        words = text.split()
        if len(words) < 5:
            return 5.0
        
        # Basic grammar indicators
        score = 7.0  # Base score
        
        # Check for proper capitalization
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if sentences:
            properly_capitalized = sum(1 for s in sentences if s and s[0].isupper())
            score += (properly_capitalized / len(sentences)) * 1.0
        
        # Check for sentence-ending punctuation
        proper_ends = sum(1 for s in sentences if s and s[-1] in '.!?')
        score += (proper_ends / len(sentences)) * 1.0
        
        # Simple word count heuristic
        if len(words) > 50:
            score += 1.0
        
        return min(10.0, score)
    
    def calculate_scores(self, signal_metrics, speech_metrics):
        """Calculate overall scores based on metrics"""
        
        # Voice Quality Score (0-100)
        voice_score = 70  # Base
        
        # Volume contribution (20%)
        db_level = signal_metrics.get('db_level', -96)
        if db_level > -25:
            voice_score += 10
        elif db_level > -35:
            voice_score += 15  # Optimal range
        elif db_level > -45:
            voice_score += 5
        else:
            voice_score -= 10
        
        # Clarity contribution (30%)
        snr = signal_metrics.get('estimated_snr_db', 30)
        if snr > 25:
            voice_score += 20
        elif snr > 15:
            voice_score += 10
        else:
            voice_score -= 10
        
        # Speech rate contribution (20%)
        wpm = speech_metrics.get('speech_rate_wpm', 0)
        if 120 <= wpm <= 160:
            voice_score += 15
        elif 100 <= wpm < 120 or 160 < wpm <= 180:
            voice_score += 5
        elif wpm < 60 or wpm > 200:
            voice_score -= 10
        
        # Pause quality contribution (15%)
        pause_quality = speech_metrics.get('pause_quality', 'Unknown')
        if pause_quality == "Excellent":
            voice_score += 10
        elif pause_quality == "Good":
            voice_score += 5
        elif pause_quality in ["Too many/long pauses", "Rushed/No pauses"]:
            voice_score -= 5
        
        # Filler words contribution (15%)
        filler_ratio = speech_metrics.get('filler_word_ratio', 0)
        if filler_ratio < 0.02:
            voice_score += 10
        elif filler_ratio < 0.05:
            voice_score += 5
        elif filler_ratio > 0.10:
            voice_score -= 10
        
        # Ensure score is within bounds
        voice_score = max(0, min(100, voice_score))
        
        # Language Quality Score (0-100)
        language_score = 70  # Base
        
        # Grammar contribution (30%)
        grammar_score = speech_metrics.get('estimated_grammar_score', 5.0)
        language_score += (grammar_score - 5.0) * 3
        
        # Vocabulary diversity contribution (25%)
        vocab_ratio = speech_metrics.get('vocabulary_diversity', 0)
        if vocab_ratio > 0.7:
            language_score += 15
        elif vocab_ratio > 0.5:
            language_score += 5
        elif vocab_ratio < 0.3:
            language_score -= 10
        
        # Sentence complexity contribution (25%)
        complexity = speech_metrics.get('sentence_complexity', 'Simple')
        if complexity == "Complex":
            language_score += 15
        elif complexity == "Moderate":
            language_score += 10
        elif complexity == "Simple":
            language_score += 5
        
        # Confident markers contribution (20%)
        confident_count = speech_metrics.get('confident_marker_count', 0)
        word_count = speech_metrics.get('word_count', 1)
        if confident_count > 0:
            language_score += min(10, confident_count * 2)
        
        # Ensure score is within bounds
        language_score = max(0, min(100, language_score))
        
        # Overall Audio Score (weighted average)
        overall_score = (voice_score * 0.6) + (language_score * 0.4)
        
        return {
            'voice_score_100': round(voice_score, 1),
            'voice_score_10': round(voice_score / 10, 1),
            'language_score_100': round(language_score, 1),
            'language_score_10': round(language_score / 10, 1),
            'overall_audio_score_100': round(overall_score, 1),
            'overall_audio_score_10': round(overall_score / 10, 1)
        }
    
    def get_verdicts_and_recommendations(self, scores, metrics):
        """Generate verdicts and recommendations based on scores and metrics"""
        
        voice_verdict = "Exceptional" if scores['voice_score_100'] >= 90 else \
                       "Excellent" if scores['voice_score_100'] >= 80 else \
                       "Good" if scores['voice_score_100'] >= 70 else \
                       "Acceptable" if scores['voice_score_100'] >= 60 else \
                       "Needs Improvement"
        
        language_verdict = "Exceptional" if scores['language_score_100'] >= 90 else \
                          "Excellent" if scores['language_score_100'] >= 80 else \
                          "Good" if scores['language_score_100'] >= 70 else \
                          "Acceptable" if scores['language_score_100'] >= 60 else \
                          "Needs Improvement"
        
        # Voice recommendations
        voice_recommendations = []
        
        db_level = metrics['signal'].get('db_level', -96)
        if db_level < -40:
            voice_recommendations.append("Increase volume - speak closer to the microphone")
        elif db_level > -20:
            voice_recommendations.append("Reduce volume - you're too close to the microphone")
        
        wpm = metrics['speech'].get('speech_rate_wpm', 0)
        if wpm < 100:
            voice_recommendations.append("Increase speaking pace for better engagement")
        elif wpm > 180:
            voice_recommendations.append("Slow down your speaking rate for better clarity")
        
        filler_ratio = metrics['speech'].get('filler_word_ratio', 0)
        if filler_ratio > 0.05:
            voice_recommendations.append(f"Reduce filler words (current: {filler_ratio:.1%})")
        
        pause_quality = metrics['speech'].get('pause_quality', 'Unknown')
        if pause_quality in ["Too many/long pauses", "Rushed/No pauses"]:
            voice_recommendations.append(f"Work on pause timing ({pause_quality.lower()})")
        
        # Language recommendations
        language_recommendations = []
        
        vocab_ratio = metrics['speech'].get('vocabulary_diversity', 0)
        if vocab_ratio < 0.4:
            language_recommendations.append("Use more varied vocabulary")
        
        sentence_complexity = metrics['speech'].get('sentence_complexity', 'Simple')
        if sentence_complexity == "Fragmentary":
            language_recommendations.append("Use complete sentences")
        elif sentence_complexity == "Simple":
            language_recommendations.append("Vary sentence structure for better engagement")
        
        confident_count = metrics['speech'].get('confident_marker_count', 0)
        if confident_count == 0 and metrics['speech'].get('word_count', 0) > 50:
            language_recommendations.append("Use more confident language markers")
        
        return {
            'voice_verdict': voice_verdict,
            'language_verdict': language_verdict,
            'voice_recommendations': voice_recommendations[:3],  # Top 3
            'language_recommendations': language_recommendations[:3],
            'voice_summary': self.generate_voice_summary(metrics),
            'language_summary': self.generate_language_summary(metrics)
        }
    
    def generate_voice_summary(self, metrics):
        """Generate voice analysis summary"""
        signal = metrics['signal']
        speech = metrics['speech']
        
        volume_desc = "too soft" if signal.get('db_level', -96) < -40 else \
                     "too loud" if signal.get('db_level', -96) > -20 else \
                     "appropriate"
        
        pace_desc = "slow" if speech.get('speech_rate_wpm', 0) < 100 else \
                   "fast" if speech.get('speech_rate_wpm', 0) > 180 else \
                   "optimal"
        
        clarity_desc = "excellent" if signal.get('estimated_snr_db', 30) > 25 else \
                      "good" if signal.get('estimated_snr_db', 30) > 15 else \
                      "needs improvement"
        
        return f"Voice analysis shows {volume_desc} volume with {pace_desc} speaking pace. Audio clarity is {clarity_desc}. Detected {speech.get('filler_word_count', 0)} filler words."
    
    def generate_language_summary(self, metrics):
        """Generate language analysis summary"""
        speech = metrics['speech']
        
        complexity = speech.get('sentence_complexity', 'Simple').lower()
        vocabulary = "varied" if speech.get('vocabulary_diversity', 0) > 0.6 else \
                    "adequate" if speech.get('vocabulary_diversity', 0) > 0.4 else \
                    "limited"
        
        return f"Language analysis shows {complexity} sentence structure with {vocabulary} vocabulary. Speech contains {speech.get('filler_word_count', 0)} filler words over {speech.get('word_count', 0)} total words."
    
    def get_default_signal_metrics(self):
        """Return default signal metrics"""
        return {
            'rms_energy': 0.0,
            'db_level': -96.0,
            'peak_db': -96.0,
            'dynamic_range': 0.0,
            'zero_crossing_rate': 0.0,
            'sample_rate': 44100,
            'duration_seconds': 0.0,
            'avg_spectral_centroid': 0.0,
            'avg_spectral_bandwidth': 0.0,
            'avg_pitch_hz': 0.0,
            'pitch_variation': 0.0,
            'estimated_snr_db': 0.0
        }
    
    def get_default_speech_metrics(self):
        """Return default speech metrics"""
        return {
            'transcription': "",
            'confidence': 0.0,
            'word_count': 0,
            'sentence_count': 0,
            'speech_rate_wpm': 0.0,
            'vocabulary_diversity': 0.0,
            'filler_word_count': 0,
            'filler_word_ratio': 0.0,
            'avg_sentence_length': 0.0,
            'sentence_complexity': "Fragmentary",
            'confident_marker_count': 0,
            'estimated_grammar_score': 5.0,
            'total_duration_seconds': 0.0,
            'speech_duration_seconds': 0.0,
            'pause_duration_seconds': 0.0,
            'pause_percentage': 0.0,
            'avg_pause_length_seconds': 0.0,
            'max_pause_length_seconds': 0.0,
            'pause_count': 0,
            'speech_pause_ratio': 0.0,
            'pause_quality': 'Unknown'
        }
    
    def analyze_audio_content(self, video_path):
        """
        Main function to analyze audio from video.
        Returns comprehensive voice and language analysis.
        """
        # Default result structure
        default_result = {
            "voice": {
                "score_100": 0.0, 
                "score_10": 0.0, 
                "verdict": "No Audio",
                "clarity": "None", 
                "pace": "None", 
                "volume": "Silent",
                "summary": "No audio detected or could not analyze.",
                "recommendations": ["Ensure microphone is properly connected", "Check audio settings"],
                "confidence": 0.0,
                "detailed_params": {}
            },
            "language": {
                "score_100": 0.0, 
                "score_10": 0.0,
                "grammar_score": 0.0, 
                "vocabulary_score": 0.0,
                "filler_words": 0, 
                "sentence_structure": "None",
                "articulation": "None",
                "summary": "No speech detected or could not transcribe.",
                "recommendations": ["Ensure you are speaking clearly", "Check microphone placement"],
                "confidence": 0.0,
                "transcription_snippet": ""
            },
            "overall_audio": {
                "score_100": 0.0,
                "score_10": 0.0,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return default_result
        
        try:
            print(f"Starting audio analysis for: {video_path}")
            
            # Extract audio
            audio_path = self.extract_audio(video_path)
            if not audio_path or not os.path.exists(audio_path):
                print("Failed to extract audio")
                return default_result
            
            print("Audio extracted successfully")
            
            # Analyze audio signal
            signal_metrics = self.analyze_audio_signal(audio_path)
            print("Signal analysis completed")
            
            # Analyze speech content
            speech_metrics = self.analyze_speech_content(audio_path)
            print("Speech analysis completed")
            
            # Clean up extracted audio file
            try:
                os.unlink(audio_path)
            except:
                pass
            
            # Check if there's meaningful audio
            if signal_metrics['duration_seconds'] < 1.0 or speech_metrics['word_count'] < 3:
                print("Insufficient audio content for analysis")
                return default_result
            
            # Calculate scores
            scores = self.calculate_scores(signal_metrics, speech_metrics)
            print(f"Scores calculated: {scores}")
            
            # Generate verdicts and recommendations
            metrics = {'signal': signal_metrics, 'speech': speech_metrics}
            verdicts = self.get_verdicts_and_recommendations(scores, metrics)
            print("Verdicts generated")
            
            # Determine clarity based on SNR
            snr = signal_metrics.get('estimated_snr_db', 0)
            clarity = "Excellent" if snr > 25 else "Good" if snr > 15 else "Needs Improvement"
            
            # Determine pace based on WPM
            wpm = speech_metrics.get('speech_rate_wpm', 0)
            pace = "Slow" if wpm < 100 else "Fast" if wpm > 180 else "Optimal"
            
            # Determine volume based on dB level
            db_level = signal_metrics.get('db_level', -96)
            volume = "Perfect" if -35 <= db_level <= -25 else \
                    "Appropriate" if -45 <= db_level < -25 else \
                    "Too Soft" if db_level < -45 else "Too Loud"
            
            # Construct final results
            voice_result = {
                "score_100": scores['voice_score_100'],
                "score_10": scores['voice_score_10'],
                "verdict": verdicts['voice_verdict'],
                "clarity": clarity,
                "pace": pace,
                "volume": volume,
                "summary": verdicts['voice_summary'],
                "recommendations": verdicts['voice_recommendations'],
                "confidence": min(0.99, speech_metrics.get('confidence', 0.0)),
                "detailed_params": {
                    "avg_energy_db": round(signal_metrics.get('db_level', -96), 1),
                    "avg_speech_rate_wpm": round(speech_metrics.get('speech_rate_wpm', 0), 1),
                    "word_count": speech_metrics.get('word_count', 0),
                    "pause_percentage": round(speech_metrics.get('pause_percentage', 0), 1),
                    "filler_word_count": speech_metrics.get('filler_word_count', 0),
                    "estimated_snr_db": round(signal_metrics.get('estimated_snr_db', 0), 1),
                    "pitch_stability": round(signal_metrics.get('pitch_variation', 0), 1)
                }
            }
            
            # Determine articulation based on confidence and filler words
            articulation = "Clear" if speech_metrics.get('confidence', 0) > 0.7 else "Unclear"
            if speech_metrics.get('filler_word_ratio', 0) > 0.1:
                articulation = "Needs Improvement"
            
            language_result = {
                "score_100": scores['language_score_100'],
                "score_10": scores['language_score_10'],
                "grammar_score": round(speech_metrics.get('estimated_grammar_score', 5.0), 1),
                "vocabulary_score": round(min(10.0, speech_metrics.get('vocabulary_diversity', 0) * 10 + 2), 1),
                "filler_words": speech_metrics.get('filler_word_count', 0),
                "sentence_structure": speech_metrics.get('sentence_complexity', 'Simple'),
                "articulation": articulation,
                "summary": verdicts['language_summary'],
                "recommendations": verdicts['language_recommendations'],
                "confidence": min(0.99, speech_metrics.get('confidence', 0.0)),
                "transcription_snippet": speech_metrics.get('transcription', '')[:200] + '...' 
                if len(speech_metrics.get('transcription', '')) > 200 
                else speech_metrics.get('transcription', '')
            }
            
            overall_result = {
                "voice": voice_result,
                "language": language_result,
                "overall_audio": {
                    "score_100": scores['overall_audio_score_100'],
                    "score_10": scores['overall_audio_score_10'],
                    "timestamp": datetime.now().isoformat(),
                    "analysis_version": "2.0"
                }
            }
            
            print("Audio analysis completed successfully")
            return overall_result
            
        except Exception as e:
            print(f"Audio analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return default_result


# Main function for backward compatibility
def analyze_audio_content(video_path):
    """
    Legacy function for backward compatibility.
    Analyzes audio from video and returns comprehensive results.
    """
    analyzer = EnhancedAudioAnalyzer()
    return analyzer.analyze_audio_content(video_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        result = analyze_audio_content(video_path)
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({
            "error": "No video path provided",
            "usage": "python analyze_audio.py <video_file_path>"
        }, indent=2))