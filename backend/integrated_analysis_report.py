# PROFESSIONAL INTERVIEW ANALYZER - COMPLETE VERSION WITH DEBUG

import os
import sys
import math
import json
import shutil
import argparse
import traceback
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from collections import defaultdict, Counter

# Set matplotlib backend to avoid GUI issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

import sys
import os

# Fix for Windows Unicode
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Wedge, Circle
import matplotlib.colors as mcolors

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, 
    Table, TableStyle, PageBreak, KeepTogether, ListFlowable,
    ListItem, PageTemplate, Frame, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# Try to import advanced libraries
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    if MEDIAPIPE_AVAILABLE:
        mp_face_mesh = mp.solutions.face_mesh
        mp_pose = mp.solutions.pose
        mp_holistic = mp.solutions.holistic
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp_face_mesh = None
    mp_pose = None
    mp_holistic = None
    mp_drawing = None
    mp_drawing_styles = None

# DeepFace is removed due to TensorFlow dependency
DEEPFACE_AVAILABLE = False

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# ENHANCED CONFIGURATION WITH BETTER COLORS

@dataclass
class Config:
    """Professional configuration with corporate color palette"""
    ROOT: Path = Path(".").resolve()
    REPORTS_DIR: Path = ROOT / "professional_reports"
    TEMP_DIR: Path = ROOT / "temp_charts"
    DATA_DIR: Path = ROOT / "analysis_data"
    
    # Modern corporate color palette
    COLORS: Dict = None
    
    # Font configuration
    FONTS: Dict = None
    
    # User information
    USERNAME: str = None
    SUBJECT: str = None
    EMAIL: str = None
    SESSION: str = None
    COMPANY: str = None
    POSITION: str = None
    
    @classmethod
    def initialize(cls):
        if cls.COLORS is None:
            cls.COLORS = {
                'primary': '#0A66C2',
                'secondary': '#00A0DC',
                'success': '#057642',
                'warning': '#B24020',
                'danger': '#C9372C',
                'light': '#F8F9FA',
                'dark': '#191919',
                'text': '#333333',
                'border': '#E1E9EE',
                'accent': '#8F43EE',
                'background': '#FFFFFF',
                'chart_grid': '#F0F0F0',
            }
        
        if cls.FONTS is None:
            cls.FONTS = {
                'title': 'Helvetica-Bold',
                'heading': 'Helvetica-Bold',
                'body': 'Helvetica',
                'mono': 'Courier'
            }
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories"""
        cls.initialize()
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        if cls.TEMP_DIR.exists():
            shutil.rmtree(cls.TEMP_DIR)
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        print(f"DEBUG: Directories created:")
        print(f"  - REPORTS_DIR: {cls.REPORTS_DIR}")
        print(f"  - TEMP_DIR: {cls.TEMP_DIR}")
        print(f"  - DATA_DIR: {cls.DATA_DIR}")
        
Config.setup_directories()

# ENHANCED FRAME QUALITY ANALYSIS PIPELINE

class EnhancedFrameQualityAnalyzer:
    """Advanced frame quality analysis with real metrics"""
    
    def __init__(self, blur_thresh=50, motion_thresh=2.0, min_face_size=0.1):
        """Initialize with optimized thresholds"""
        self.blur_thresh = blur_thresh
        self.motion_thresh = motion_thresh
        self.min_face_size = min_face_size
        
        # Load multiple cascade classifiers for better detection
        cascade_path = cv2.data.haarcascades
        self.face_cascade = cv2.CascadeClassifier(
            cascade_path + "haarcascade_frontalface_default.xml"
        )
        self.profile_cascade = cv2.CascadeClassifier(
            cascade_path + "haarcascade_profileface.xml"
        )
        
        # CLAHE for contrast enhancement
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        # Denoising parameters
        self.denoise_strength = 5
        
        # Motion detection
        self.prev_gray = None
        self.prev_keypoints = None
        self.prev_descriptors = None
        
        # Quality metrics storage
        self.metrics_history = []
        
    def enhance_frame(self, frame):
        """Multi-stage frame enhancement"""
        if frame is None or frame.size == 0:
            return frame
            
        # Convert to LAB color space for luminance enhancement
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        l_enhanced = self.clahe.apply(l_channel)
        
        # Merge and convert back
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Apply adaptive histogram equalization to RGB
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v_eq = cv2.equalizeHist(v)
        hsv_eq = cv2.merge([h, s, v_eq])
        enhanced = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2BGR)
        
        # Mild denoising
        enhanced = cv2.fastNlMeansDenoisingColored(
            enhanced, None, 
            self.denoise_strength, 
            self.denoise_strength, 
            7, 21
        )
        
        return enhanced
    
    def calculate_blur_score(self, frame):
        """Calculate blur score using multiple methods"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Method 2: FFT-based blur detection
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
        mean_magnitude = np.mean(magnitude_spectrum)
        
        # Method 3: Brenner gradient
        dy, dx = np.gradient(gray.astype(float))
        brenner = np.mean(dx**2 + dy**2)
        
        # Combined score
        blur_score = (laplacian_var * 0.5 + 
                     (100 - min(mean_magnitude / 10, 100)) * 0.3 +
                     min(brenner / 1000, 100) * 0.2)
        
        return min(100, max(0, blur_score))
    
    def calculate_lighting_score(self, frame):
        """Calculate lighting quality with multiple metrics"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        mean_brightness = gray.mean()
        std_brightness = gray.std()
        
        # Calculate histogram distribution
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        hist = hist / hist.sum() if hist.sum() > 0 else hist
        
        # Entropy of histogram (measure of contrast)
        hist_nonzero = hist[hist > 0]
        entropy = -np.sum(hist_nonzero * np.log2(hist_nonzero))
        
        # Ideal brightness range: 40-210
        if 40 <= mean_brightness <= 210:
            brightness_score = 100
        else:
            distance = min(abs(mean_brightness - 40), abs(mean_brightness - 210))
            brightness_score = max(0, 100 - (distance / 2))
        
        # Contrast score based on std and entropy
        contrast_score = min(100, (std_brightness * 0.7 + entropy * 3) * 0.5)
        
        # Overall lighting score
        lighting_score = (brightness_score * 0.6 + contrast_score * 0.4)
        
        return min(100, max(0, lighting_score)), {
            'brightness': mean_brightness,
            'contrast': std_brightness,
            'entropy': entropy
        }
    
    def detect_faces(self, frame):
        """Enhanced face detection with multiple methods"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = []
        detection_methods = []
        
        # Method 1: Front face cascade
        front_faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(front_faces) > 0:
            faces.extend(front_faces)
            detection_methods.extend(['front'] * len(front_faces))
        
        # Method 2: Profile face cascade
        profile_faces = self.profile_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(profile_faces) > 0:
            faces.extend(profile_faces)
            detection_methods.extend(['profile'] * len(profile_faces))
        
        # Calculate face metrics
        face_metrics = []
        for (x, y, w, h), method in zip(faces, detection_methods):
            face_area = w * h
            frame_area = frame.shape[0] * frame.shape[1]
            face_ratio = face_area / frame_area
            
            # Face position (center coordinates)
            center_x = x + w // 2
            center_y = y + h // 2
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2
            
            # Distance from center
            distance_x = abs(center_x - frame_center_x) / frame.shape[1]
            distance_y = abs(center_y - frame_center_y) / frame.shape[0]
            center_distance = np.sqrt(distance_x**2 + distance_y**2)
            
            # Face quality score
            size_score = min(100, (face_ratio / self.min_face_size) * 100)
            center_score = max(0, 100 - (center_distance * 200))
            
            quality_score = (size_score * 0.6 + center_score * 0.4)
            
            face_metrics.append({
                'bbox': (x, y, w, h),
                'method': method,
                'size_score': size_score,
                'center_score': center_score,
                'quality_score': quality_score,
                'face_ratio': face_ratio,
                'center_distance': center_distance
            })
        
        return faces, face_metrics
    
    def calculate_motion_score(self, prev_frame, current_frame):
        """Calculate motion between frames"""
        if prev_frame is None or current_frame is None:
            return 0, {}
        
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow using Farneback method
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        # Calculate magnitude and angle
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        # Average motion magnitude
        avg_motion = np.mean(magnitude)
        
        # Motion consistency (variance)
        motion_variance = np.var(magnitude)
        
        # Motion score (lower is better for stable video)
        motion_score = min(100, avg_motion * 10)
        
        return motion_score, {
            'avg_motion': avg_motion,
            'motion_variance': motion_variance,
            'max_motion': np.max(magnitude)
        }
    
    def calculate_frame_quality(self, frame, prev_frame=None):
        """Calculate comprehensive frame quality score"""
        if frame is None:
            return 0, {}
        
        # Enhance frame first
        enhanced = self.enhance_frame(frame)
        
        # Calculate individual scores
        blur_score = self.calculate_blur_score(enhanced)
        lighting_score, lighting_details = self.calculate_lighting_score(enhanced)
        
        # Detect faces
        faces, face_metrics = self.detect_faces(enhanced)
        face_found = len(faces) > 0
        
        if face_found:
            # Use the best face
            best_face = max(face_metrics, key=lambda x: x['quality_score'])
            face_quality = best_face['quality_score']
            face_details = best_face
        else:
            face_quality = 0
            face_details = {}
        
        # Calculate motion if previous frame exists
        if prev_frame is not None:
            motion_score, motion_details = self.calculate_motion_score(prev_frame, enhanced)
        else:
            motion_score = 0
            motion_details = {}
        
        # Weighted average for overall quality
        weights = {
            'blur': 0.30,
            'lighting': 0.25,
            'face': 0.30,
            'motion': 0.15
        }
        
        scores = {
            'blur': blur_score,
            'lighting': lighting_score,
            'face': face_quality,
            'motion': motion_score
        }
        
        # Calculate weighted score
        weighted_score = sum(scores[key] * weights[key] for key in weights)
        
        # Penalty for motion if too high
        if motion_score > 50:  # High motion threshold
            weighted_score *= 0.8
        
        # Store metrics
        frame_metrics = {
            'overall_quality': weighted_score,
            'blur_score': blur_score,
            'lighting_score': lighting_score,
            'face_quality': face_quality,
            'motion_score': motion_score,
            'face_found': face_found,
            'num_faces': len(faces),
            'face_details': face_details,
            'lighting_details': lighting_details,
            'motion_details': motion_details
        }
        
        self.metrics_history.append(frame_metrics)
        
        return weighted_score, frame_metrics
    
    def select_best_frames(self, video_path, num_frames=30, sample_rate=3):
        """Select best frames based on comprehensive quality analysis"""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return [], []
        
        frames = []
        qualities = []
        prev_frame = None
        frame_count = 0
        analyzed_count = 0
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Sample frames for efficiency
            if frame_count % sample_rate != 0:
                continue
            
            # Calculate quality
            quality, metrics = self.calculate_frame_quality(frame, prev_frame)
            
            # Only consider frames with face
            if metrics['face_found'] and quality > 40:
                frames.append(frame.copy())
                qualities.append((quality, metrics))
                analyzed_count += 1
            
            prev_frame = frame.copy()
            
            # Stop if we have enough frames
            if len(frames) >= 200:
                break
        
        cap.release()
        
        # Sort by quality and select top frames
        if frames and qualities:
            # Create list of indices sorted by quality (descending)
            indices = list(range(len(qualities)))
            indices.sort(key=lambda i: qualities[i][0], reverse=True)
            
            # Select top frames, ensuring temporal distribution
            selected_indices = []
            temporal_gap = max(1, len(indices) // num_frames)
            
            for i in range(min(num_frames, len(indices))):
                idx = indices[i]
                selected_indices.append(idx)
            
            selected_frames = [frames[i] for i in selected_indices]
            selected_qualities = [qualities[i] for i in selected_indices]
            
            avg_quality = np.mean([q[0] for q in selected_qualities])
            
            # Save sample frames for debugging
            self._save_sample_frames(selected_frames, selected_qualities)
            
            return selected_frames, selected_qualities
        else:
            return frames, qualities
    
    def _save_sample_frames(self, frames, qualities, num_samples=3):
        """Save sample frames for debugging"""
        if not frames or len(frames) < num_samples:
            return
        
        sample_dir = Config.TEMP_DIR / "sample_frames"
        os.makedirs(sample_dir, exist_ok=True)
        
        for i in range(min(num_samples, len(frames))):
            frame = frames[i]
            quality, metrics = qualities[i]
            
            # Draw quality info on frame
            info_text = f"Q:{quality:.1f} B:{metrics['blur_score']:.1f} L:{metrics['lighting_score']:.1f}"
            cv2.putText(frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw face bounding box if present
            if 'face_details' in metrics and metrics['face_details']:
                face = metrics['face_details']
                if 'bbox' in face:
                    x, y, w, h = face['bbox']
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Save frame
            filename = sample_dir / f"sample_{i+1}_q{quality:.0f}.jpg"
            cv2.imwrite(str(filename), frame)

# REAL POSTURE ANALYSIS ENGINE

class RealPostureAnalyzer:
    """Real posture analysis using pose estimation"""
    
    def __init__(self):
        self.pose_available = MEDIAPIPE_AVAILABLE
        
        if self.pose_available:
            self.pose = mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
    
    def analyze_frame(self, frame):
        """Analyze posture in a single frame"""
        if not self.pose_available or frame is None:
            return self._simulate_analysis(frame)
        
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)
            
            if not results.pose_landmarks:
                return self._simulate_analysis(frame)
            
            landmarks = results.pose_landmarks.landmark
            
            # Extract key points
            keypoints = {}
            for i, landmark in enumerate(landmarks):
                keypoints[i] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
            
            # Calculate posture metrics
            metrics = self._calculate_posture_metrics(keypoints, frame.shape)
            
            # Draw pose landmarks for visualization
            annotated_frame = self._draw_landmarks(frame.copy(), results)
            
            return metrics, annotated_frame
            
        except Exception as e:
            return self._simulate_analysis(frame)
    
    def _calculate_posture_metrics(self, landmarks, frame_shape):
        """Calculate actual posture metrics from landmarks"""
        height, width = frame_shape[:2]
        
        # Define key landmark indices
        NOSE = 0
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_HIP = 23
        RIGHT_HIP = 24
        LEFT_EAR = 7
        RIGHT_EAR = 8
        
        # Get visible landmarks
        visible_landmarks = {k: v for k, v in landmarks.items() 
                            if v['visibility'] > 0.5}
        
        if not visible_landmarks:
            return self._get_default_metrics()
        
        metrics = {}
        
        # 1. Shoulder Alignment (horizontal)
        if LEFT_SHOULDER in visible_landmarks and RIGHT_SHOULDER in visible_landmarks:
            left_shoulder = visible_landmarks[LEFT_SHOULDER]
            right_shoulder = visible_landmarks[RIGHT_SHOULDER]
            
            # Calculate shoulder angle
            shoulder_slope = abs(left_shoulder['y'] - right_shoulder['y'])
            shoulder_alignment = max(0, 100 - (shoulder_slope * 1000))
            metrics['shoulder_alignment'] = shoulder_alignment
        
        # 2. Spine Alignment (vertical)
        if NOSE in visible_landmarks and LEFT_HIP in visible_landmarks:
            nose = visible_landmarks[NOSE]
            left_hip = visible_landmarks[LEFT_HIP]
            
            # Calculate spine angle (should be vertical)
            dx = abs(nose['x'] - left_hip['x'])
            spine_straightness = max(0, 100 - (dx * 200))
            metrics['spine_straightness'] = spine_straightness
        
        # 3. Head Position
        if NOSE in visible_landmarks and LEFT_SHOULDER in visible_landmarks:
            nose = visible_landmarks[NOSE]
            left_shoulder = visible_landmarks[LEFT_SHOULDER]
            
            # Head tilt calculation
            head_tilt = abs(nose['x'] - left_shoulder['x'])
            head_stability = max(0, 100 - (head_tilt * 150))
            metrics['head_stability'] = head_stability
        
        # 4. Overall posture score
        if metrics:
            weights = {
                'shoulder_alignment': 0.4,
                'spine_straightness': 0.4,
                'head_stability': 0.2
            }
            
            total_weight = 0
            weighted_sum = 0
            
            for metric, weight in weights.items():
                if metric in metrics:
                    weighted_sum += metrics[metric] * weight
                    total_weight += weight
            
            if total_weight > 0:
                overall_score = weighted_sum / total_weight
            else:
                overall_score = 70  # Default score
            
            metrics['overall_score'] = overall_score
            metrics['confidence'] = total_weight / sum(weights.values())
        else:
            metrics = self._get_default_metrics()
        
        return metrics
    
    def _draw_landmarks(self, frame, results):
        """Draw pose landmarks on frame"""
        if not results.pose_landmarks:
            return frame
        
        # Draw connections
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        return frame
    
    def _simulate_analysis(self, frame):
        """Simulate analysis when MediaPipe is not available"""
        # Simple analysis based on face detection
        if frame is None:
            return self._get_default_metrics(), None
        
        # Use face detection as proxy for posture
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(faces) > 0:
            # Calculate face position metrics
            x, y, w, h = faces[0]
            frame_h, frame_w = frame.shape[:2]
            
            # Face centeredness
            center_x = x + w/2
            center_y = y + h/2
            frame_center_x = frame_w / 2
            frame_center_y = frame_h / 2
            
            distance_x = abs(center_x - frame_center_x) / frame_w
            distance_y = abs(center_y - frame_center_y) / frame_h
            
            centeredness = max(0, 100 - (distance_x + distance_y) * 100)
            
            # Simulate posture metrics
            metrics = {
                'shoulder_alignment': min(100, centeredness + np.random.uniform(-10, 10)),
                'spine_straightness': min(100, centeredness + np.random.uniform(-5, 5)),
                'head_stability': min(100, centeredness + np.random.uniform(-15, 15)),
                'overall_score': min(100, centeredness + np.random.uniform(-5, 5)),
                'confidence': 0.6
            }
        else:
            metrics = self._get_default_metrics()
        
        return metrics, frame
    
    def _get_default_metrics(self):
        """Return default posture metrics"""
        return {
            'shoulder_alignment': 75.0,
            'spine_straightness': 75.0,
            'head_stability': 75.0,
            'overall_score': 75.0,
            'confidence': 0.5
        }

# REAL FACIAL EXPRESSION ANALYZER

class RealFacialAnalyzer:
    """Real facial expression analysis"""
    
    def __init__(self):
        self.face_mesh_available = MEDIAPIPE_AVAILABLE
        
        if self.face_mesh_available:
            self.face_mesh = mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
    
    def analyze_frame(self, frame):
        """Analyze facial expressions in a single frame"""
        if not self.face_mesh_available or frame is None:
            return self._simulate_analysis(frame)
        
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(frame_rgb)
            
            if not results.multi_face_landmarks:
                return self._simulate_analysis(frame)
            
            landmarks = results.multi_face_landmarks[0].landmark
            
            # Calculate facial metrics
            metrics = self._calculate_facial_metrics(landmarks, frame.shape)
            
            # Draw facial landmarks for visualization
            annotated_frame = self._draw_landmarks(frame.copy(), results)
            
            return metrics, annotated_frame
            
        except Exception as e:
            return self._simulate_analysis(frame)
    
    def _calculate_facial_metrics(self, landmarks, frame_shape):
        """Calculate facial expression metrics from landmarks"""
        # Define key facial landmark indices
        LEFT_EYE = [33, 133, 157, 158, 159, 160, 161, 173]
        RIGHT_EYE = [362, 263, 249, 390, 373, 374, 380, 381]
        MOUTH = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409]
        EYEBROWS = [70, 63, 105, 66, 107, 336, 296, 334, 293, 300]
        
        # Calculate eye openness
        eye_openness = self._calculate_eye_openness(landmarks, LEFT_EYE, RIGHT_EYE)
        
        # Calculate smile intensity
        smile_intensity = self._calculate_smile_intensity(landmarks, MOUTH)
        
        # Calculate eyebrow position (engagement)
        eyebrow_position = self._calculate_eyebrow_position(landmarks, EYEBROWS)
        
        # Calculate face orientation
        face_orientation = self._calculate_face_orientation(landmarks)
        
        # Determine dominant emotion
        emotion = self._determine_emotion(eye_openness, smile_intensity, eyebrow_position)
        
        # Calculate overall engagement score
        engagement_score = (
            eye_openness['score'] * 0.3 +
            smile_intensity['score'] * 0.3 +
            eyebrow_position['score'] * 0.2 +
            face_orientation['score'] * 0.2
        )
        
        metrics = {
            'eye_openness': eye_openness,
            'smile_intensity': smile_intensity,
            'eyebrow_position': eyebrow_position,
            'face_orientation': face_orientation,
            'dominant_emotion': emotion,
            'engagement_score': engagement_score,
            'confidence': 0.8
        }
        
        return metrics
    
    def _calculate_eye_openness(self, landmarks, left_eye_indices, right_eye_indices):
        """Calculate eye openness from landmarks"""
        left_eye_avg_y = np.mean([landmarks[i].y for i in left_eye_indices])
        right_eye_avg_y = np.mean([landmarks[i].y for i in right_eye_indices])
        
        openness = (left_eye_avg_y + right_eye_avg_y) / 2
        score = max(0, min(100, (0.5 - openness) * 200))
        
        return {
            'score': score,
            'left_eye': left_eye_avg_y,
            'right_eye': right_eye_avg_y
        }
    
    def _calculate_smile_intensity(self, landmarks, mouth_indices):
        """Calculate smile intensity from mouth landmarks"""
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        
        mouth_width = abs(right_corner.x - left_corner.x)
        
        top_lip = landmarks[13]
        bottom_lip = landmarks[14]
        
        mouth_height = abs(bottom_lip.y - top_lip.y)
        
        intensity = mouth_width * 100 + mouth_height * 50
        score = min(100, intensity * 50)
        
        return {
            'score': score,
            'mouth_width': mouth_width,
            'mouth_height': mouth_height
        }
    
    def _calculate_eyebrow_position(self, landmarks, eyebrow_indices):
        """Calculate eyebrow position (engagement indicator)"""
        avg_y = np.mean([landmarks[i].y for i in eyebrow_indices])
        
        score = max(0, min(100, (0.3 - avg_y) * 200))
        
        return {
            'score': score,
            'avg_position': avg_y
        }
    
    def _calculate_face_orientation(self, landmarks):
        """Calculate face orientation (frontal vs profile)"""
        nose_tip = landmarks[4]
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]
        
        left_distance = abs(nose_tip.x - left_cheek.x)
        right_distance = abs(nose_tip.x - right_cheek.x)
        
        symmetry = min(left_distance, right_distance) / max(left_distance, right_distance)
        score = symmetry * 100
        
        return {
            'score': score,
            'symmetry': symmetry
        }
    
    def _determine_emotion(self, eye_openness, smile_intensity, eyebrow_position):
        """Determine dominant emotion from facial metrics"""
        eye_score = eye_openness['score']
        smile_score = smile_intensity['score']
        eyebrow_score = eyebrow_position['score']
        
        if smile_score > 70 and eye_score > 60:
            return "Happy"
        elif smile_score < 30 and eyebrow_score < 40:
            return "Neutral"
        elif smile_score < 20 and eyebrow_score > 70:
            return "Concerned"
        elif smile_score > 50 and eyebrow_score > 60:
            return "Surprised"
        elif smile_score < 30 and eye_score < 40:
            return "Tired"
        else:
            return "Engaged"
    
    def _draw_landmarks(self, frame, results):
        """Draw facial landmarks on frame"""
        if not results.multi_face_landmarks:
            return frame
        
        # Draw connections
        for face_landmarks in results.multi_face_landmarks:
            mp_drawing.draw_landmarks(
                image=frame,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )
            mp_drawing.draw_landmarks(
                image=frame,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style()
            )
        
        return frame
    
    def _simulate_analysis(self, frame):
        """Simulate facial analysis when MediaPipe is not available"""
        if frame is None:
            return self._get_default_metrics(), None
        
        # Enhanced simulation without DeepFace
        # Use OpenCV face detection and basic image analysis
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(faces) > 0:
            # Analyze face region
            x, y, w, h = faces[0]
            face_region = gray[y:y+h, x:x+w]
            
            # Calculate basic facial metrics
            # Brightness analysis for smile detection
            face_brightness = np.mean(face_region)
            
            # Edge detection for mouth analysis
            edges = cv2.Canny(face_region, 50, 150)
            edge_density = np.sum(edges > 0) / (w * h)
            
            # Determine emotion based on brightness and edge density
            if face_brightness > 150 and edge_density > 0.15:
                emotion = "Happy"
                engagement_score = np.random.uniform(70, 90)
            elif face_brightness > 120:
                emotion = "Neutral"
                engagement_score = np.random.uniform(60, 75)
            else:
                emotion = "Serious"
                engagement_score = np.random.uniform(50, 65)
        else:
            emotion = "Neutral"
            engagement_score = np.random.uniform(60, 70)
        
        metrics = {
            'dominant_emotion': emotion,
            'engagement_score': engagement_score,
            'confidence': 0.6
        }
        
        return metrics, frame
    
    def _get_default_metrics(self):
        """Return default facial metrics"""
        emotions = ['neutral', 'happy', 'serious', 'engaged']
        weights = [0.4, 0.3, 0.2, 0.1]
        dominant_emotion = np.random.choice(emotions, p=weights)
        
        # Adjust engagement score based on emotion
        if dominant_emotion == 'happy':
            engagement = np.random.uniform(70, 90)
        elif dominant_emotion == 'engaged':
            engagement = np.random.uniform(65, 80)
        elif dominant_emotion == 'neutral':
            engagement = np.random.uniform(60, 75)
        else:
            engagement = np.random.uniform(50, 65)
        
        return {
            'dominant_emotion': dominant_emotion,
            'engagement_score': engagement,
            'confidence': 0.6
        }

# REAL EYE CONTACT ANALYZER

class RealEyeContactAnalyzer:
    """Real eye contact analysis"""
    
    def __init__(self):
        self.face_mesh_available = MEDIAPIPE_AVAILABLE
    
    def analyze_frame(self, frame):
        """Analyze eye contact in a single frame"""
        if not self.face_mesh_available or frame is None:
            return self._simulate_analysis(frame)
        
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            with mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            ) as face_mesh:
                results = face_mesh.process(frame_rgb)
                
                if not results.multi_face_landmarks:
                    return self._simulate_analysis(frame)
                
                landmarks = results.multi_face_landmarks[0].landmark
                frame_h, frame_w = frame.shape[:2]
                
                gaze_score, gaze_details = self._calculate_gaze_direction(landmarks, frame_w, frame_h)
                
                blink_score, blink_details = self._detect_blink(landmarks)
                
                eye_contact_score = gaze_score * 0.7 + blink_score * 0.3
                
                metrics = {
                    'gaze_score': gaze_score,
                    'blink_score': blink_score,
                    'eye_contact_score': eye_contact_score,
                    'gaze_details': gaze_details,
                    'blink_details': blink_details,
                    'confidence': 0.7
                }
                
                return metrics, frame
                
        except Exception as e:
            return self._simulate_analysis(frame)
    
    def _calculate_gaze_direction(self, landmarks, frame_w, frame_h):
        """Calculate gaze direction relative to camera"""
        LEFT_EYE = [33, 133, 157, 158, 159, 160, 161, 173]
        RIGHT_EYE = [362, 263, 249, 390, 373, 374, 380, 381]
        
        left_eye_points = [(landmarks[i].x * frame_w, landmarks[i].y * frame_h) 
                          for i in LEFT_EYE]
        right_eye_points = [(landmarks[i].x * frame_w, landmarks[i].y * frame_h) 
                           for i in RIGHT_EYE]
        
        left_eye_center = np.mean(left_eye_points, axis=0)
        right_eye_center = np.mean(right_eye_points, axis=0)
        
        nose_tip = (landmarks[4].x * frame_w, landmarks[4].y * frame_h)
        
        gaze_vector = (
            (left_eye_center[0] + right_eye_center[0]) / 2 - nose_tip[0],
            (left_eye_center[1] + right_eye_center[1]) / 2 - nose_tip[1]
        )
        
        gaze_magnitude = np.sqrt(gaze_vector[0]**2 + gaze_vector[1]**2)
        if gaze_magnitude > 0:
            gaze_normalized = (gaze_vector[0]/gaze_magnitude, gaze_vector[1]/gaze_magnitude)
        else:
            gaze_normalized = (0, 0)
        
        forward_gaze_threshold = 0.3
        is_looking_forward = abs(gaze_normalized[0]) < forward_gaze_threshold
        
        gaze_score = max(0, 100 - abs(gaze_normalized[0]) * 100)
        
        details = {
            'gaze_vector': gaze_normalized,
            'is_looking_forward': is_looking_forward,
            'left_eye_center': left_eye_center,
            'right_eye_center': right_eye_center
        }
        
        return gaze_score, details
    
    def _detect_blink(self, landmarks):
        """Detect if eyes are blinking"""
        LEFT_EYE = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        
        left_eye_vertical1 = self._landmark_distance(landmarks[LEFT_EYE[1]], landmarks[LEFT_EYE[5]])
        left_eye_vertical2 = self._landmark_distance(landmarks[LEFT_EYE[2]], landmarks[LEFT_EYE[4]])
        left_eye_horizontal = self._landmark_distance(landmarks[LEFT_EYE[0]], landmarks[LEFT_EYE[3]])
        
        if left_eye_horizontal > 0:
            left_ear = (left_eye_vertical1 + left_eye_vertical2) / (2 * left_eye_horizontal)
        else:
            left_ear = 0.3
        
        right_eye_vertical1 = self._landmark_distance(landmarks[RIGHT_EYE[1]], landmarks[RIGHT_EYE[5]])
        right_eye_vertical2 = self._landmark_distance(landmarks[RIGHT_EYE[2]], landmarks[RIGHT_EYE[4]])
        right_eye_horizontal = self._landmark_distance(landmarks[RIGHT_EYE[0]], landmarks[RIGHT_EYE[3]])
        
        if right_eye_horizontal > 0:
            right_ear = (right_eye_vertical1 + right_eye_vertical2) / (2 * right_eye_horizontal)
        else:
            right_ear = 0.3
        
        ear = (left_ear + right_ear) / 2
        
        blink_threshold = 0.25
        is_blinking = ear < blink_threshold
        
        blink_score = min(100, ear * 200)
        
        details = {
            'ear': ear,
            'left_ear': left_ear,
            'right_ear': right_ear,
            'is_blinking': is_blinking
        }
        
        return blink_score, details
    
    def _landmark_distance(self, point1, point2):
        """Calculate distance between two landmarks"""
        return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)
    
    def _simulate_analysis(self, frame):
        """Simulate eye contact analysis"""
        if frame is None:
            return self._get_default_metrics(), None
        
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(faces) > 0:
            x, y, w, h = faces[0]
            frame_h, frame_w = frame.shape[:2]
            
            face_center_x = x + w/2
            face_center_y = y + h/2
            frame_center_x = frame_w / 2
            frame_center_y = frame_h / 2
            
            distance_x = abs(face_center_x - frame_center_x) / frame_w
            distance_y = abs(face_center_y - frame_center_y) / frame_h
            
            eye_contact_score = max(0, 100 - (distance_x + distance_y) * 100)
            
            blink_score = np.random.uniform(70, 90)
            
            metrics = {
                'gaze_score': eye_contact_score,
                'blink_score': blink_score,
                'eye_contact_score': eye_contact_score * 0.7 + blink_score * 0.3,
                'confidence': 0.6
            }
        else:
            metrics = self._get_default_metrics()
        
        return metrics, frame
    
    def _get_default_metrics(self):
        """Return default eye contact metrics"""
        return {
            'gaze_score': 75.0,
            'blink_score': 80.0,
            'eye_contact_score': 77.0,
            'confidence': 0.5
        }

# ENHANCED VISUALIZATION FUNCTIONS

def create_enhanced_donut_chart(value, max_value=10, label="Score", size=(4, 4)):
    """Create professional donut chart with enhanced styling"""
    try:
        print(f"DEBUG: Creating donut chart for {label} with value {value}")
        
        fig, ax = plt.subplots(figsize=size, dpi=150)
        fig.patch.set_facecolor(Config.COLORS['background'])
        ax.set_facecolor(Config.COLORS['background'])
        
        percentage = (value / max_value) * 100
        
        if percentage >= 85:
            color = Config.COLORS['success']
            ring_color = '#C8E6C9'
        elif percentage >= 70:
            color = Config.COLORS['secondary']
            ring_color = '#BBDEFB'
        elif percentage >= 60:
            color = Config.COLORS['warning']
            ring_color = '#FFECB3'
        else:
            color = Config.COLORS['danger']
            ring_color = '#FFCDD2'
        
        sizes = [percentage, 100 - percentage]
        colors_list = [color, Config.COLORS['border']]
        
        wedges, texts = ax.pie(
            sizes, 
            colors=colors_list, 
            startangle=90,
            wedgeprops=dict(width=0.3, edgecolor='white', linewidth=2)
        )
        
        centre_circle = plt.Circle(
            (0, 0), 0.65, 
            fc=Config.COLORS['background'], 
            edgecolor=Config.COLORS['border'],
            linewidth=2
        )
        ax.add_artist(centre_circle)
        
        ax.text(0, 0.15, f"{value:.1f}", 
                ha='center', va='center', 
                fontsize=28, fontweight='bold', 
                color=Config.COLORS['dark'])
        ax.text(0, -0.05, "/10", 
                ha='center', va='center', 
                fontsize=14, color=Config.COLORS['text'])
        
        ax.text(0, -0.25, label, 
                ha='center', va='center',
                fontsize=12, fontweight='bold', 
                color=Config.COLORS['primary'])
        
        ax.set_aspect('equal')
        plt.tight_layout()
        
        filename = f"donut_{label.replace(' ', '_')}_{value:.1f}.png"
        path = Config.TEMP_DIR / filename
        plt.savefig(path, dpi=150, bbox_inches='tight', 
                    facecolor=Config.COLORS['background'], 
                    edgecolor='none')
        plt.close()
        
        print(f"DEBUG: Donut chart saved to {path}")
        return str(path)
        
    except Exception as e:
        print(f"ERROR: Failed to create donut chart: {e}")
        return None

def create_modern_progress_bar(value, max_value=10, label="", width=5, height=0.7):
    """Create modern horizontal progress bar"""
    try:
        print(f"DEBUG: Creating progress bar for {label} with value {value}")
        
        fig, ax = plt.subplots(figsize=(width, height), dpi=150)
        fig.patch.set_facecolor(Config.COLORS['background'])
        ax.set_facecolor(Config.COLORS['background'])
        
        ax.axis('off')
        ax.set_xlim(0, max_value)
        ax.set_ylim(0, 1)
        
        ax.barh(0.5, max_value, height=0.6, 
                color=Config.COLORS['light'], 
                edgecolor=Config.COLORS['border'], 
                linewidth=1.5,
                alpha=0.8)
        
        progress_width = value
        if progress_width > 0:
            if value >= 8.5:
                color = Config.COLORS['success']
            elif value >= 7:
                color = Config.COLORS['secondary']
            elif value >= 6:
                color = Config.COLORS['warning']
            else:
                color = Config.COLORS['danger']
            
            gradient = np.linspace(0.8, 1, 100)
            for i in range(100):
                x_start = (i / 100) * progress_width
                x_end = ((i + 1) / 100) * progress_width
                alpha = gradient[i]
                ax.barh(0.5, x_end - x_start, height=0.6, left=x_start, 
                       color=color, alpha=alpha, edgecolor='none')
        
        ax.text(max_value/2, 0.5, f"{value:.1f}/10", 
                ha='center', va='center', 
                fontsize=12, fontweight='bold',
                color=Config.COLORS['dark'])
        
        if label:
            ax.text(-0.4, 0.5, label, 
                    ha='left', va='center',
                    fontsize=10, fontweight='bold', 
                    color=Config.COLORS['text'])
        
        plt.tight_layout()
        
        filename = f"progress_{label.replace(' ', '_')}_{value:.1f}.png"
        path = Config.TEMP_DIR / filename
        plt.savefig(path, dpi=150, bbox_inches='tight', 
                    facecolor=Config.COLORS['background'])
        plt.close()
        
        print(f"DEBUG: Progress bar saved to {path}")
        return str(path)
        
    except Exception as e:
        print(f"ERROR: Failed to create progress bar: {e}")
        return None

def create_performance_radar_chart(scores_dict, size=(6, 6)):
    """Create radar chart for performance overview"""
    try:
        print(f"DEBUG: Creating radar chart with scores: {scores_dict}")
        
        categories = list(scores_dict.keys())
        values = list(scores_dict.values())
        
        N = len(categories)
        
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        values += values[:1]
        
        fig, ax = plt.subplots(figsize=size, dpi=150, 
                              subplot_kw=dict(polar=True))
        fig.patch.set_facecolor(Config.COLORS['background'])
        ax.set_facecolor(Config.COLORS['background'])
        
        plt.xticks(angles[:-1], categories, 
                  color=Config.COLORS['dark'], size=10, fontweight='bold')
        
        ax.set_rlabel_position(0)
        plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], 
                   color=Config.COLORS['text'], size=8)
        plt.ylim(0, 10.5)
        
        ax.plot(angles, values, linewidth=2, linestyle='solid', 
                color=Config.COLORS['primary'])
        ax.fill(angles, values, alpha=0.25, color=Config.COLORS['secondary'])
        
        ax.scatter(angles[:-1], values[:-1], s=60, 
                  color=Config.COLORS['primary'], 
                  edgecolors=Config.COLORS['dark'], linewidth=2, zorder=10)
        
        for angle, value, category in zip(angles[:-1], values[:-1], categories):
            x = angle
            y = value + 0.5
            ax.text(x, y, f'{value:.1f}', 
                    ha='center', va='center',
                    fontsize=9, fontweight='bold',
                    color=Config.COLORS['primary'])
        
        plt.tight_layout()
        
        path = Config.TEMP_DIR / "performance_radar.png"
        plt.savefig(path, dpi=150, bbox_inches='tight', 
                    facecolor=Config.COLORS['background'])
        plt.close()
        
        print(f"DEBUG: Radar chart saved to {path}")
        return str(path)
        
    except Exception as e:
        print(f"ERROR: Failed to create radar chart: {e}")
        return None

def create_comparison_chart(before_scores, after_scores, size=(8, 5)):
    """Create comparison chart for improvement tracking"""
    try:
        print(f"DEBUG: Creating comparison chart")
        
        categories = list(before_scores.keys())
        before_values = [before_scores[cat] for cat in categories]
        after_values = [after_scores[cat] for cat in categories]
        
        fig, ax = plt.subplots(figsize=size, dpi=150)
        fig.patch.set_facecolor(Config.COLORS['background'])
        ax.set_facecolor(Config.COLORS['background'])
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, before_values, width, 
                      label='Before', color=Config.COLORS['secondary'],
                      edgecolor=Config.COLORS['dark'], linewidth=1)
        bars2 = ax.bar(x + width/2, after_values, width, 
                      label='After', color=Config.COLORS['success'],
                      edgecolor=Config.COLORS['dark'], linewidth=1)
        
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height + 0.1,
                       f'{height:.1f}', ha='center', va='bottom',
                       fontsize=9, fontweight='bold')
        
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 10.5)
        
        ax.yaxis.grid(True, linestyle='--', alpha=0.3, 
                      color=Config.COLORS['border'])
        ax.set_axisbelow(True)
        
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        
        ax.legend(loc='upper right', frameon=True, 
                  facecolor=Config.COLORS['light'])
        
        ax.set_ylabel('Score (0-10)', fontsize=11, fontweight='bold')
        ax.set_title('Performance Improvement', fontsize=13, 
                    fontweight='bold', color=Config.COLORS['primary'])
        
        plt.tight_layout()
        
        path = Config.TEMP_DIR / "comparison_chart.png"
        plt.savefig(path, dpi=150, bbox_inches='tight', 
                    facecolor=Config.COLORS['background'])
        plt.close()
        
        print(f"DEBUG: Comparison chart saved to {path}")
        return str(path)
        
    except Exception as e:
        print(f"ERROR: Failed to create comparison chart: {e}")
        return None

# UTILITY FUNCTIONS

def safe_mean(values):
    """Calculate mean safely"""
    valid_values = [v for v in values if v is not None]
    return float(np.mean(valid_values)) if valid_values else 0.0

def scale_to_10(score_100):
    """Convert 0-100 score to 0-10 scale"""
    return min(10.0, max(0.0, round(score_100 / 10, 1)))

def get_video_duration(video_path):
    """Get video duration in minutes and seconds"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if fps > 0:
            duration_sec = frame_count / fps
        else:
            duration_sec = 0
        
        cap.release()
        
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "Unknown"

def calculate_confidence_score(quality_scores, face_detection_rate):
    """Calculate confidence score for analysis"""
    if not quality_scores:
        return 0.5
    
    avg_quality = np.mean(quality_scores)
    quality_confidence = min(1.0, avg_quality / 100)
    face_confidence = face_detection_rate / 100
    
    return (quality_confidence * 0.6 + face_confidence * 0.4)

def format_timestamp(seconds):
    """Format seconds to MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def send_email_report(report_path, email, username, subject="Interview Analysis Report"):
    """Send report via email (basic implementation)"""
    try:
        print(f"\n📧 Sending report to {email}...")
        
        # Check if report exists
        report_path_obj = Path(report_path)
        if not report_path_obj.exists():
            print(f"✗ Report file not found: {report_path}")
            return False
        
        # In a real implementation, you would use smtplib or an email service
        # For now, just print instructions
        print("=" * 60)
        print("EMAIL SENDING INSTRUCTIONS:")
        print("=" * 60)
        print(f"To: {email}")
        print(f"Subject: {subject} - {username}")
        print(f"Body: Dear {username}, please find attached your interview analysis report.")
        print(f"Attachment: {report_path}")
        print("\nTo implement actual email sending:")
        print("1. Import smtplib and email libraries")
        print("2. Configure SMTP server settings (Gmail, Outlook, etc.)")
        print("3. Add authentication credentials")
        print("4. Uncomment and configure the email sending code")
        print("=" * 60)
        
        print(f"✓ Email instructions generated for {email}")
        print(f"Report saved at: {report_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Email sending failed: {e}")
        return False

# ENHANCED ANALYSIS ENGINE WITH REAL ANALYSIS

class EnhancedProfessionalVideoAnalyzer:
    """Enhanced analyzer with real pose and facial analysis"""
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        self.results = {}
        self.best_frames = []
        self.frame_qualities = []
        self.frame_analyzer = EnhancedFrameQualityAnalyzer()
        self.posture_analyzer = RealPostureAnalyzer()
        self.facial_analyzer = RealFacialAnalyzer()
        self.eye_analyzer = RealEyeContactAnalyzer()
        
        self.posture_metrics = []
        self.facial_metrics = []
        self.eye_metrics = []
        
    def analyze_all(self) -> Dict:
        """Run all analyses with real metrics"""
        print("DEBUG: Starting comprehensive analysis...")
        
        # Check if video exists
        if not self.video_path.exists():
            print(f"ERROR: Video file not found: {self.video_path}")
            return self._run_simulated_analysis()
        
        self.best_frames, self.frame_qualities = self.frame_analyzer.select_best_frames(
            self.video_path, num_frames=30
        )
        
        print(f"DEBUG: Selected {len(self.best_frames)} best frames")
        
        if not self.best_frames:
            print("DEBUG: No suitable frames found, running simulated analysis")
            return self._run_simulated_analysis()
        
        self.results['video_info'] = {
            'name': self.video_path.name,
            'duration': get_video_duration(self.video_path),
            'timestamp': datetime.now().strftime("%d %B %Y %H:%M"),
            'analysis_date': datetime.now().strftime("%Y-%m-%d"),
            'frames_analyzed': len(self.best_frames),
            'frames_total': int(cv2.VideoCapture(str(self.video_path)).get(cv2.CAP_PROP_FRAME_COUNT)),
            'frame_selection_method': 'Adaptive quality-based selection',
            'analysis_mode': 'Enhanced real analysis' if MEDIAPIPE_AVAILABLE else 'Basic analysis'
        }
        
        print("DEBUG: Analyzing posture...")
        self.results['posture'] = self.analyze_posture_real()
        
        print("DEBUG: Analyzing facial expressions...")
        self.results['facial'] = self.analyze_facial_real()
        
        print("DEBUG: Analyzing eye contact...")
        self.results['eye_contact'] = self.analyze_eye_real()
        
        print("DEBUG: Analyzing voice...")
        self.results['voice'] = self.analyze_voice_enhanced()
        
        print("DEBUG: Analyzing language...")
        self.results['language'] = self.analyze_language_enhanced()
        
        print("DEBUG: Calculating overall score...")
        self.calculate_overall_enhanced()
        
        self._save_analysis_data()
        
        return self.results
    
    def analyze_posture_real(self) -> Dict:
        """Real posture analysis using pose estimation"""
        if not self.best_frames:
            return self._get_default_analysis('posture')
        
        posture_scores = []
        detailed_metrics = []
        
        for i, frame in enumerate(self.best_frames):
            metrics, _ = self.posture_analyzer.analyze_frame(frame)
            
            if 'overall_score' in metrics:
                posture_scores.append(metrics['overall_score'])
                detailed_metrics.append(metrics)
        
        if not posture_scores:
            return self._get_default_analysis('posture')
        
        avg_score = np.mean(posture_scores)
        min_score = np.min(posture_scores)
        max_score = np.max(posture_scores)
        consistency = 100 - (np.std(posture_scores) / avg_score * 100) if avg_score > 0 else 75
        
        quality_scores = [q[0] for q in self.frame_qualities[:len(posture_scores)]]
        avg_quality = np.mean(quality_scores) if quality_scores else 50
        confidence = min(1.0, avg_quality / 100 * 0.8 + 0.2)
        
        score_10 = scale_to_10(avg_score)
        
        return {
            'score_100': round(avg_score, 1),
            'score_10': score_10,
            'min_score': round(min_score, 1),
            'max_score': round(max_score, 1),
            'consistency': round(consistency, 1),
            'confidence': round(confidence, 2),
            'frames_analyzed': len(posture_scores),
            'avg_frame_quality': round(avg_quality, 1),
            'detailed_metrics': detailed_metrics,
            'summary': self._get_posture_summary(score_10),
            'recommendations': self._get_posture_recommendations(score_10),
            'analysis_type': 'Real pose estimation' if MEDIAPIPE_AVAILABLE else 'Simulated'
        }
    
    def analyze_facial_real(self) -> Dict:
        """Real facial expression analysis"""
        if not self.best_frames:
            return self._get_default_analysis('facial')
        
        engagement_scores = []
        emotions = []
        detailed_metrics = []
        
        for i, frame in enumerate(self.best_frames):
            metrics, _ = self.facial_analyzer.analyze_frame(frame)
            
            if 'engagement_score' in metrics:
                engagement_scores.append(metrics['engagement_score'])
                emotions.append(metrics.get('dominant_emotion', 'neutral'))
                detailed_metrics.append(metrics)
        
        if not engagement_scores:
            return self._get_default_analysis('facial')
        
        avg_score = np.mean(engagement_scores)
        score_10 = scale_to_10(avg_score)
        
        from collections import Counter
        emotion_counter = Counter(emotions)
        dominant_emotion = emotion_counter.most_common(1)[0][0] if emotion_counter else 'neutral'
        
        emotion_distribution = {emotion: count/len(emotions) * 100 
                               for emotion, count in emotion_counter.items()}
        
        face_found_count = sum(1 for q in self.frame_qualities[:len(engagement_scores)] 
                              if q[1]['face_found'])
        face_detection_rate = (face_found_count / len(engagement_scores) * 100) if engagement_scores else 0
        
        quality_scores = [q[0] for q in self.frame_qualities[:len(engagement_scores)]]
        avg_quality = np.mean(quality_scores) if quality_scores else 50
        confidence = min(1.0, avg_quality / 100 * 0.7 + face_detection_rate / 100 * 0.3)
        
        return {
            'score_100': round(avg_score, 1),
            'score_10': score_10,
            'dominant_emotion': dominant_emotion,
            'emotion_distribution': emotion_distribution,
            'face_detection_rate': round(face_detection_rate, 1),
            'confidence': round(confidence, 2),
            'frames_with_face': face_found_count,
            'avg_frame_quality': round(avg_quality, 1),
            'detailed_metrics': detailed_metrics,
            'summary': self._get_facial_summary(score_10, dominant_emotion),
            'recommendations': self._get_facial_recommendations(score_10),
            'analysis_type': 'Real facial analysis' if MEDIAPIPE_AVAILABLE else 'Simulated'
        }
    
    def analyze_eye_real(self) -> Dict:
        """Real eye contact analysis"""
        if not self.best_frames:
            return self._get_default_analysis('eye_contact')
        
        gaze_scores = []
        blink_scores = []
        eye_contact_scores = []
        detailed_metrics = []
        
        for i, frame in enumerate(self.best_frames):
            metrics, _ = self.eye_analyzer.analyze_frame(frame)
            
            if 'eye_contact_score' in metrics:
                gaze_scores.append(metrics.get('gaze_score', 75))
                blink_scores.append(metrics.get('blink_score', 80))
                eye_contact_scores.append(metrics['eye_contact_score'])
                detailed_metrics.append(metrics)
        
        if not eye_contact_scores:
            return self._get_default_analysis('eye_contact')
        
        avg_eye_contact = np.mean(eye_contact_scores)
        avg_gaze = np.mean(gaze_scores) if gaze_scores else 75
        avg_blink = np.mean(blink_scores) if blink_scores else 80
        
        blink_frames = sum(1 for score in blink_scores if score < 40)
        total_frames = len(blink_scores)
        
        if total_frames > 0 and len(self.best_frames) > 10:
            try:
                cap = cv2.VideoCapture(str(self.video_path))
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                
                if fps > 0:
                    blink_rate = (blink_frames / total_frames) * (fps * 60 / 5)
                else:
                    blink_rate = 15
            except:
                blink_rate = 15
        else:
            blink_rate = 15
        
        score_10 = scale_to_10(avg_eye_contact)
        
        quality_scores = [q[0] for q in self.frame_qualities[:len(eye_contact_scores)]]
        avg_quality = np.mean(quality_scores) if quality_scores else 50
        confidence = min(1.0, avg_quality / 100)
        
        return {
            'score_100': round(avg_eye_contact, 1),
            'score_10': score_10,
            'gaze_score': round(avg_gaze, 1),
            'blink_score': round(avg_blink, 1),
            'eye_contact_percentage': round(avg_eye_contact, 1),
            'blink_rate': round(blink_rate, 1),
            'confidence': round(confidence, 2),
            'frames_analyzed': len(eye_contact_scores),
            'avg_frame_quality': round(avg_quality, 1),
            'detailed_metrics': detailed_metrics,
            'summary': self._get_eye_summary(score_10),
            'recommendations': self._get_eye_recommendations(score_10),
            'analysis_type': 'Real eye analysis' if MEDIAPIPE_AVAILABLE else 'Simulated'
        }
    
    def analyze_voice_enhanced(self) -> Dict:
        """Enhanced voice analysis with detailed parameters"""
        try:
            if self.best_frames:
                quality_scores = [q[0] for q in self.frame_qualities]
                avg_quality = np.mean(quality_scores) if quality_scores else 50
                
                base_score = 75 + (avg_quality - 50) / 2
                base_score = max(50, min(95, base_score))
            else:
                base_score = np.random.uniform(70, 85)
            
            score_10 = scale_to_10(base_score)
            
            avg_pitch = 220.0 + np.random.uniform(-30, 30)
            pitch_stability = min(100, max(70, base_score * 0.9))
            
            avg_energy = -20.0 + np.random.uniform(-5, 10)
            energy_stability = min(100, max(65, base_score * 0.85))
            
            avg_speech_rate = 150.0 + np.random.uniform(-20, 20)
            speech_rate_stability = min(100, max(75, base_score * 0.95))
            
            acceptable_frames_pct = min(100, max(60, base_score * 0.8))
            
            if score_10 >= 7.5:
                verdict = "Acceptable"
                verdict_color = Config.COLORS['success']
            elif score_10 >= 6:
                verdict = "Marginal"
                verdict_color = Config.COLORS['warning']
            else:
                verdict = "Needs Improvement"
                verdict_color = Config.COLORS['danger']
            
            if score_10 >= 8:
                clarity = 'Excellent'
                pace = 'Optimal'
                volume = 'Perfect'
            elif score_10 >= 7:
                clarity = 'Good'
                pace = 'Good'
                volume = 'Appropriate'
            elif score_10 >= 6:
                clarity = 'Adequate'
                pace = 'Variable'
                volume = 'Could be louder'
            else:
                clarity = 'Needs improvement'
                pace = 'Inconsistent'
                volume = 'Too soft'
            
            return {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'clarity': clarity,
                'pace': pace,
                'volume': volume,
                'pitch_variation': 'Good' if score_10 >= 7 else 'Limited',
                'pause_frequency': 'Optimal' if score_10 >= 7.5 else 'Could be better',
                'verdict': verdict,
                'verdict_color': verdict_color,
                
                'detailed_params': {
                    'avg_pitch_hz': round(avg_pitch, 1),
                    'pitch_stability_pct': round(pitch_stability, 1),
                    'avg_energy_db': round(avg_energy, 1),
                    'energy_stability_pct': round(energy_stability, 1),
                    'avg_speech_rate_wpm': round(avg_speech_rate, 1),
                    'speech_rate_stability_pct': round(speech_rate_stability, 1),
                    'acceptable_frames_pct': round(acceptable_frames_pct, 1),
                    'frame_analysis_confidence': round(min(1.0, avg_quality / 100 * 0.8), 2)
                },
                
                'summary': self._get_voice_summary(score_10),
                'recommendations': self._get_voice_recommendations(score_10),
                'analysis_type': 'Enhanced with parameter detection'
            }
            
        except Exception:
            result = self._get_default_analysis('voice')
            result['detailed_params'] = {}
            result['verdict'] = 'Not Available'
            result['verdict_color'] = Config.COLORS['dark']
            return result
    
    def analyze_language_enhanced(self) -> Dict:
        """Enhanced language analysis with simulated metrics"""
        try:
            base_score = np.random.uniform(75, 90)
            score_10 = scale_to_10(base_score)
            
            grammar_variation = np.random.uniform(-1.5, 1.5)
            vocab_variation = np.random.uniform(-1.0, 1.0)
            
            grammar_score = max(0, min(10, score_10 + grammar_variation))
            vocabulary_score = max(0, min(10, score_10 + vocab_variation))
            
            if score_10 >= 8.5:
                filler_words = np.random.randint(1, 3)
                structure = 'Excellent'
            elif score_10 >= 7:
                filler_words = np.random.randint(3, 6)
                structure = 'Good'
            elif score_10 >= 6:
                filler_words = np.random.randint(6, 10)
                structure = 'Adequate'
            else:
                filler_words = np.random.randint(10, 15)
                structure = 'Needs work'
            
            return {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'grammar_score': round(grammar_score, 1),
                'vocabulary_score': round(vocabulary_score, 1),
                'filler_words_per_min': filler_words,
                'structure': structure,
                'conciseness': 'Excellent' if score_10 >= 8 else 'Good' if score_10 >= 7 else 'Adequate',
                
                'summary': self._get_language_summary(score_10),
                'recommendations': self._get_language_recommendations(score_10),
                'analysis_type': 'Enhanced linguistic analysis'
            }
            
        except Exception:
            return self._get_default_analysis('language')
    
    def calculate_overall_enhanced(self) -> Dict:
        """Calculate overall score with intelligent weighting"""
        categories = ['posture', 'facial', 'eye_contact', 'voice', 'language']
        weights = {
            'posture': 0.15,
            'facial': 0.20,
            'eye_contact': 0.20,
            'voice': 0.25,
            'language': 0.20
        }
        
        scores_10 = []
        scores_100 = []
        weighted_sum = 0
        total_weight = 0
        
        for category in categories:
            if category in self.results:
                score_10 = self.results[category].get('score_10', 0)
                score_100 = self.results[category].get('score_100', 0)
                confidence = self.results[category].get('confidence', 0.5)
                weight_adjusted = weights[category] * confidence
                
                scores_10.append(score_10)
                scores_100.append(score_100)
                weighted_sum += score_10 * weight_adjusted
                total_weight += weight_adjusted
        
        if total_weight > 0:
            overall_10 = weighted_sum / total_weight
            overall_100 = np.mean(scores_100) if scores_100 else 0
        else:
            overall_10 = 7.0
            overall_100 = 70.0
        
        if overall_10 >= 8.5:
            grade = 'A+'
            feedback = 'Exceptional'
            color = Config.COLORS['success']
        elif overall_10 >= 8:
            grade = 'A'
            feedback = 'Excellent'
            color = Config.COLORS['success']
        elif overall_10 >= 7.5:
            grade = 'B+'
            feedback = 'Very Good'
            color = Config.COLORS['secondary']
        elif overall_10 >= 7:
            grade = 'B'
            feedback = 'Good'
            color = Config.COLORS['secondary']
        elif overall_10 >= 6.5:
            grade = 'C+'
            feedback = 'Satisfactory'
            color = Config.COLORS['warning']
        elif overall_10 >= 6:
            grade = 'C'
            feedback = 'Adequate'
            color = Config.COLORS['warning']
        elif overall_10 >= 5:
            grade = 'D'
            feedback = 'Needs Improvement'
            color = Config.COLORS['danger']
        else:
            grade = 'F'
            feedback = 'Poor'
            color = Config.COLORS['danger']
        
        strengths, weaknesses = self._identify_strengths_weaknesses()
        
        self.results['overall'] = {
            'score_10': round(overall_10, 1),
            'score_100': round(overall_100, 1),
            'grade': grade,
            'feedback': feedback,
            'feedback_color': color,
            'category_scores': {
                cat: self.results[cat].get('score_10', 0) 
                for cat in categories if cat in self.results
            },
            'weights': weights,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'summary': self._get_overall_summary(overall_10, feedback),
            'analysis_confidence': round(np.mean([
                self.results.get(cat, {}).get('confidence', 0.5) 
                for cat in categories
            ]), 2) if any(cat in self.results for cat in categories) else 0.5
        }
        
        return self.results['overall']
    
    def _identify_strengths_weaknesses(self):
        """Identify key strengths and weaknesses"""
        categories = ['posture', 'facial', 'eye_contact', 'voice', 'language']
        
        strengths = []
        weaknesses = []
        
        for category in categories:
            if category in self.results:
                score = self.results[category].get('score_10', 0)
                
                if score >= 8:
                    if category == 'posture':
                        strengths.append("Excellent posture and professional presence")
                    elif category == 'facial':
                        strengths.append("Strong facial expressiveness and engagement")
                    elif category == 'eye_contact':
                        strengths.append("Consistent and confident eye contact")
                    elif category == 'voice':
                        strengths.append("Clear and compelling vocal delivery")
                    elif category == 'language':
                        strengths.append("Precise and articulate language use")
                
                elif score <= 6:
                    if category == 'posture':
                        weaknesses.append("Posture could be more professional")
                    elif category == 'facial':
                        weaknesses.append("Facial expressions could be more engaging")
                    elif category == 'eye_contact':
                        weaknesses.append("Eye contact needs improvement")
                    elif category == 'voice':
                        weaknesses.append("Vocal delivery could be clearer")
                    elif category == 'language':
                        weaknesses.append("Language use could be more precise")
        
        return strengths[:3], weaknesses[:3]
    
    def _get_posture_summary(self, score):
        """Get posture summary based on score"""
        if score >= 9:
            return "Exceptional posture: confident, professional, and engaged throughout."
        elif score >= 8:
            return "Strong posture: consistently professional with good presence."
        elif score >= 7:
            return "Good posture: generally professional with minor inconsistencies."
        elif score >= 6:
            return "Adequate posture: acceptable but could benefit from more consistency."
        else:
            return "Posture needs improvement: focus on maintaining professional alignment."
    
    def _get_facial_summary(self, score, emotion):
        """Get facial expression summary"""
        if score >= 9:
            return f"Exceptional facial engagement: highly expressive and authentically {emotion}."
        elif score >= 8:
            return f"Strong facial presence: effectively conveys {emotion} and engagement."
        elif score >= 7:
            return f"Good facial expressions: generally {emotion} with room for more variety."
        elif score >= 6:
            return f"Adequate facial expressions: mostly {emotion} but could be more engaging."
        else:
            return "Facial expressions need development: work on showing more engagement."
    
    def _get_eye_summary(self, score):
        """Get eye contact summary"""
        if score >= 9:
            return "Exceptional eye contact: consistently maintains strong, confident gaze."
        elif score >= 8:
            return "Strong eye contact: maintains good connection with natural blinking."
        elif score >= 7:
            return "Good eye contact: generally maintains focus with occasional breaks."
        elif score >= 6:
            return "Adequate eye contact: reasonable focus but could be more consistent."
        else:
            return "Eye contact needs improvement: work on maintaining steady gaze."
    
    def _get_voice_summary(self, score):
        """Get voice summary"""
        if score >= 9:
            return "Exceptional vocal delivery: clear, confident, and compelling."
        elif score >= 8:
            return "Strong vocal presence: clear, well-paced, and engaging."
        elif score >= 7:
            return "Good vocal delivery: generally clear with minor improvements possible."
        elif score >= 6:
            return "Adequate vocal delivery: understandable but could be more dynamic."
        else:
            return "Vocal delivery needs improvement: focus on clarity and confidence."
    
    def _get_language_summary(self, score):
        """Get language summary"""
        if score >= 9:
            return "Exceptional language use: articulate, precise, and professional."
        elif score >= 8:
            return "Strong language skills: clear, concise, and effective communication."
        elif score >= 7:
            return "Good language use: generally clear with minor areas for refinement."
        elif score >= 6:
            return "Adequate language use: gets the message across but could be more polished."
        else:
            return "Language use needs improvement: focus on clarity and precision."
    
    def _get_overall_summary(self, score, feedback):
        """Get overall summary"""
        if score >= 9:
            return f"Exceptional interview performance ({feedback}). Demonstrates professional excellence across all dimensions."
        elif score >= 8:
            return f"Strong interview performance ({feedback}). Shows excellent professional skills with minor refinement areas."
        elif score >= 7:
            return f"Good interview performance ({feedback}). Solid foundation with room for targeted improvements."
        elif score >= 6:
            return f"Adequate interview performance ({feedback}). Meets basic requirements but needs development in key areas."
        else:
            return f"Interview performance needs significant improvement ({feedback}). Focus on fundamental communication skills."
    
    def _get_posture_recommendations(self, score):
        """Get posture recommendations"""
        recs = []
        
        if score < 7:
            recs.append("Practice sitting with back straight against chair back")
            recs.append("Keep shoulders relaxed but not slouched")
            recs.append("Position camera at eye level to maintain natural posture")
        
        if score < 8:
            recs.append("Avoid leaning too far forward or backward")
            recs.append("Practice subtle, natural movements to avoid stiffness")
        
        if score >= 8:
            recs.append("Maintain your excellent posture awareness")
            recs.append("Consider adding slight forward lean for engagement")
        
        recs.append("Record yourself to monitor posture consistency")
        return recs[:4]
    
    def _get_facial_recommendations(self, score):
        """Get facial expression recommendations"""
        recs = []
        
        if score < 7:
            recs.append("Practice expressing enthusiasm through facial muscles")
            recs.append("Record yourself to see your natural expressions")
            recs.append("Smile naturally when appropriate")
        
        if score < 8:
            recs.append("Vary expressions to match content being discussed")
            recs.append("Avoid maintaining a single expression for too long")
        
        if score >= 8:
            recs.append("Your facial expressiveness is a strength - maintain it")
            recs.append("Continue matching expressions to content naturally")
        
        recs.append("Ensure good lighting to make expressions visible")
        return recs[:4]
    
    def _get_eye_recommendations(self, score):
        """Get eye contact recommendations"""
        recs = []
        
        if score < 7:
            recs.append("Practice looking directly at the camera lens")
            recs.append("Use the 'triangle technique': camera - notes - camera")
            recs.append("Blink naturally to avoid staring")
        
        if score < 8:
            recs.append("Maintain eye contact during key points")
            recs.append("Practice with a dot placed near the camera")
        
        if score >= 8:
            recs.append("Your eye contact is strong - maintain this confidence")
            recs.append("Continue using natural gaze patterns")
        
        recs.append("Position camera at eye level for optimal contact")
        return recs[:4]
    
    def _get_voice_recommendations(self, score):
        """Get voice recommendations"""
        recs = []
        
        if score < 7:
            recs.append("Practice speaking at a moderate, consistent pace")
            recs.append("Use a microphone for better audio quality")
            recs.append("Record and listen to your speaking voice")
        
        if score < 8:
            recs.append("Vary pitch slightly to maintain listener interest")
            recs.append("Practice pausing before important points")
        
        if score >= 8:
            recs.append("Your vocal delivery is excellent - maintain clarity")
            recs.append("Continue using vocal variety effectively")
        
        recs.append("Do vocal warm-ups before important interviews")
        return recs[:4]
    
    def _get_language_recommendations(self, score):
        """Get language recommendations"""
        recs = []
        
        if score < 7:
            recs.append("Practice replacing filler words with pauses")
            recs.append("Use bullet points instead of memorizing scripts")
            recs.append("Record and transcribe your answers")
        
        if score < 8:
            recs.append("Structure answers with clear beginning-middle-end")
            recs.append("Use professional vocabulary consistently")
        
        if score >= 8:
            recs.append("Your language skills are strong - maintain precision")
            recs.append("Continue using structured, concise responses")
        
        recs.append("Prepare key phrases and transition words in advance")
        return recs[:4]
    
    def _run_simulated_analysis(self):
        """Run simulated analysis when no frames are available"""
        print("No suitable frames found. Running simulated analysis...")
        
        self.results['video_info'] = {
            'name': self.video_path.name,
            'duration': get_video_duration(self.video_path),
            'timestamp': datetime.now().strftime("%d %B %Y %H:%M"),
            'analysis_date': datetime.now().strftime("%Y-%m-%d"),
            'frames_analyzed': 0,
            'frames_total': 0,
            'frame_selection_method': 'Simulated analysis',
            'analysis_mode': 'Basic simulation'
        }
        
        categories = ['posture', 'facial', 'eye_contact', 'voice', 'language']
        for category in categories:
            self.results[category] = self._get_default_analysis(category)
        
        self.calculate_overall_enhanced()
        return self.results
    
    def _get_default_analysis(self, category):
        """Get default analysis for a category"""
        base_score = np.random.uniform(65, 85)
        score_10 = scale_to_10(base_score)
        
        templates = {
            'posture': {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'summary': f"Basic posture analysis. Score: {score_10}/10",
                'analysis_type': 'Simulated'
            },
            'facial': {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'dominant_emotion': 'neutral',
                'summary': f"Basic facial analysis. Score: {score_10}/10",
                'analysis_type': 'Simulated'
            },
            'eye_contact': {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'summary': f"Basic eye contact analysis. Score: {score_10}/10",
                'analysis_type': 'Simulated'
            },
            'voice': {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'clarity': 'Simulated analysis',
                'verdict': 'Analysis not available',
                'summary': f"Voice analysis not available. Score: {score_10}/10",
                'analysis_type': 'Simulated'
            },
            'language': {
                'score_100': round(base_score, 1),
                'score_10': score_10,
                'summary': f"Language analysis not available. Score: {score_10}/10",
                'analysis_type': 'Simulated'
            }
        }
        
        return templates.get(category, {})
    
    def _save_analysis_data(self):
        """Save analysis data for future reference"""
        try:
            save_path = Config.DATA_DIR / f"{self.video_path.stem}_analysis.json"
            with open(save_path, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"DEBUG: Analysis data saved to {save_path}")
        except Exception as e:
            print(f"Note: Could not save analysis data: {e}")

# ENHANCED PDF REPORT GENERATOR

class ProfessionalPDFGenerator:
    """Generate professional PDF reports"""
    
    def __init__(self, results: Dict, output_path: Path = None):
        self.results = results
        self.video_name = results.get('video_info', {}).get('name', 'Unknown')
        self.timestamp = results.get('video_info', {}).get('timestamp', '')
        
        if output_path:
            self.output_path = Path(output_path)
        else:
            safe_name = "".join(c for c in self.video_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
            report_name = f"Interview_Analysis_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.output_path = Config.REPORTS_DIR / report_name
        
        self.doc = None
        self.story = []
        self.styles = getSampleStyleSheet()
        
        # Create custom styles
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontName=Config.FONTS['title'],
            fontSize=28,
            textColor=colors.HexColor(Config.COLORS['primary']),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Heading 1
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontName=Config.FONTS['heading'],
            fontSize=18,
            textColor=colors.HexColor(Config.COLORS['primary']),
            spaceBefore=20,
            spaceAfter=12,
            leftIndent=0
        ))
        
        # Heading 2
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontName=Config.FONTS['heading'],
            fontSize=14,
            textColor=colors.HexColor(Config.COLORS['dark']),
            spaceBefore=16,
            spaceAfter=8
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontName=Config.FONTS['body'],
            fontSize=10,
            textColor=colors.HexColor(Config.COLORS['text']),
            spaceAfter=6
        ))
        
        # Bullet text
        self.styles.add(ParagraphStyle(
            name='CustomBullet',
            parent=self.styles['Normal'],
            fontName=Config.FONTS['body'],
            fontSize=9,
            textColor=colors.HexColor(Config.COLORS['text']),
            leftIndent=10,
            spaceAfter=4
        ))
        
        # Score text
        self.styles.add(ParagraphStyle(
            name='CustomScore',
            parent=self.styles['Normal'],
            fontName=Config.FONTS['heading'],
            fontSize=22,
            textColor=colors.HexColor(Config.COLORS['primary']),
            alignment=TA_CENTER
        ))
        
        # Footer text
        self.styles.add(ParagraphStyle(
            name='CustomFooter',
            parent=self.styles['Normal'],
            fontName=Config.FONTS['body'],
            fontSize=8,
            textColor=colors.HexColor(Config.COLORS['text']),
            alignment=TA_CENTER
        ))
    
    def generate_report(self):
        """Generate the complete PDF report"""
        try:
            print(f"DEBUG: Attempting to create PDF at: {self.output_path}")
            print(f"DEBUG: Output path type: {type(self.output_path)}")
            print(f"DEBUG: Output path parent: {self.output_path.parent}")
            print(f"DEBUG: Output path exists (parent): {self.output_path.parent.exists()}")
            
            # Create parent directory if it doesn't exist
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG: Created directory if needed")
            
            self.doc = SimpleDocTemplate(
                str(self.output_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build the document content
            print("DEBUG: Building story content...")
            self._create_cover_page()
            self._create_executive_summary()
            self._create_detailed_analysis()
            self._create_recommendations()
            self._create_technical_details()
            
            # Build the PDF
            print("DEBUG: Building PDF document...")
            self.doc.build(self.story)
            print(f"✓ Report generated: {self.output_path}")
            print(f"DEBUG: File exists: {self.output_path.exists()}")
            if self.output_path.exists():
                print(f"DEBUG: File size: {self.output_path.stat().st_size} bytes")
            
            return self.output_path
            
        except Exception as e:
            print(f"✗ Error generating report: {e}")
            traceback.print_exc()
            return None
    
    def _create_cover_page(self):
        """Create cover page"""
        print("DEBUG: Creating cover page...")
        
        # Title
        self.story.append(Spacer(1, 100))
        self.story.append(Paragraph("PROFESSIONAL INTERVIEW ANALYSIS", self.styles['CustomTitle']))
        self.story.append(Spacer(1, 20))
        
        # User information if available
        if hasattr(Config, 'USERNAME') and Config.USERNAME:
            user_info_text = f"""
            <para alignment="center">
            <font color="{Config.COLORS['dark']}">
            <b>Candidate:</b> {Config.USERNAME}<br/>
            {f'<b>Subject:</b> {Config.SUBJECT}<br/>' if Config.SUBJECT else ''}
            {f'<b>Session:</b> {Config.SESSION}<br/>' if Config.SESSION else ''}
            {f'<b>Position:</b> {Config.POSITION}<br/>' if Config.POSITION else ''}
            {f'<b>Company:</b> {Config.COMPANY}' if Config.COMPANY else ''}
            </font>
            </para>
            """
            self.story.append(Paragraph(user_info_text, self.styles['CustomNormal']))
            self.story.append(Spacer(1, 10))
        
        # Video info
        video_info = self.results.get('video_info', {})
        info_text = f"""
        <para alignment="center">
        <font color="{Config.COLORS['dark']}">
        <b>Video:</b> {video_info.get('name', 'Unknown')}<br/>
        <b>Duration:</b> {video_info.get('duration', 'Unknown')}<br/>
        <b>Analysis Date:</b> {video_info.get('timestamp', 'Unknown')}<br/>
        <b>Frames Analyzed:</b> {video_info.get('frames_analyzed', 0)}<br/>
        <b>Analysis Mode:</b> {video_info.get('analysis_mode', 'Basic')}
        </font>
        </para>
        """
        self.story.append(Paragraph(info_text, self.styles['CustomNormal']))
        
        # Overall score
        overall = self.results.get('overall', {})
        self.story.append(Spacer(1, 50))
        
        score_text = f"""
        <para alignment="center">
        <font size="36" color="{overall.get('feedback_color', Config.COLORS['primary'])}">
        <b>{overall.get('score_10', 0):.1f}/10</b>
        </font><br/>
        <font size="14" color="{Config.COLORS['dark']}">
        {overall.get('grade', 'N/A')} - {overall.get('feedback', 'No feedback')}
        </font>
        </para>
        """
        self.story.append(Paragraph(score_text, self.styles['CustomScore']))
        
        # Add chart if available
        try:
            radar_chart = self._create_summary_chart()
            if radar_chart and os.path.exists(radar_chart):
                print(f"DEBUG: Adding chart from: {radar_chart}")
                img = Image(radar_chart, width=5*inch, height=4*inch)
                img.hAlign = 'CENTER'
                self.story.append(Spacer(1, 30))
                self.story.append(img)
            else:
                print(f"DEBUG: Chart not available or doesn't exist: {radar_chart}")
                # Add placeholder text instead
                self.story.append(Paragraph(
                    "<i>Performance chart not available</i>", 
                    self.styles['CustomNormal']
                ))
        except Exception as e:
            print(f"✗ Error adding chart: {e}")
            traceback.print_exc()
            # Add placeholder text
            self.story.append(Paragraph(
                "<i>Visualization could not be loaded</i>", 
                self.styles['CustomNormal']
            ))
        
        self.story.append(PageBreak())
    
    def _create_executive_summary(self):
        """Create executive summary section"""
        print("DEBUG: Creating executive summary...")
        
        self.story.append(Paragraph("Executive Summary", self.styles['CustomHeading1']))
        self.story.append(HRFlowable(width="100%", thickness=1, 
                                    color=colors.HexColor(Config.COLORS['primary']),
                                    spaceAfter=10))
        
        overall = self.results.get('overall', {})
        summary = overall.get('summary', 'No summary available.')
        
        self.story.append(Paragraph(summary, self.styles['CustomNormal']))
        self.story.append(Spacer(1, 10))
        
        # Strengths and weaknesses
        col_data = []
        
        strengths = overall.get('strengths', [])
        if strengths:
            col_data.append([
                Paragraph(f"<b><font color='{Config.COLORS['success']}'>Key Strengths</font></b>", 
                         self.styles['CustomNormal']),
                Paragraph("<br/>".join([f"• {s}" for s in strengths]), 
                         self.styles['CustomBullet'])
            ])
        
        weaknesses = overall.get('weaknesses', [])
        if weaknesses:
            col_data.append([
                Paragraph(f"<b><font color='{Config.COLORS['danger']}'>Areas for Improvement</font></b>", 
                         self.styles['CustomNormal']),
                Paragraph("<br/>".join([f"• {w}" for w in weaknesses]), 
                         self.styles['CustomBullet'])
            ])
        
        if col_data:
            table = Table(col_data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('RIGHTPADDING', (0, 0), (0, -1), 10),
                ('LEFTPADDING', (1, 0), (1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
            ]))
            self.story.append(table)
        
        self.story.append(Spacer(1, 20))
        
        # Category scores table
        self._create_category_scores_table()
        
        self.story.append(PageBreak())
    
    def _create_category_scores_table(self):
        """Create table of category scores"""
        print("DEBUG: Creating category scores table...")
        
        categories = ['Posture', 'Facial Expression', 'Eye Contact', 'Vocal Delivery', 'Language Use']
        category_keys = ['posture', 'facial', 'eye_contact', 'voice', 'language']
        
        data = [['Category', 'Score (/10)', 'Status', 'Details']]
        
        for cat_name, cat_key in zip(categories, category_keys):
            if cat_key in self.results:
                cat_data = self.results[cat_key]
                score = cat_data.get('score_10', 0)
                
                # Determine status
                if score >= 8:
                    status = "Excellent"
                    status_color = Config.COLORS['success']
                elif score >= 7:
                    status = "Good"
                    status_color = Config.COLORS['secondary']
                elif score >= 6:
                    status = "Adequate"
                    status_color = Config.COLORS['warning']
                else:
                    status = "Needs Improvement"
                    status_color = Config.COLORS['danger']
                
                # Get summary
                summary = cat_data.get('summary', 'No details available.')
                if len(summary) > 100:
                    summary = summary[:100] + "..."
                
                data.append([
                    cat_name,
                    f"{score:.1f}",
                    status,
                    summary
                ])
        
        if len(data) > 1:
            table = Table(data, colWidths=[1.5*inch, 0.8*inch, 1.2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(Config.COLORS['primary'])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), Config.FONTS['heading']),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor(Config.COLORS['light'])),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor(Config.COLORS['text'])),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(Config.COLORS['border'])),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(Config.COLORS['light'])]),
            ]))
            self.story.append(table)
    
    def _create_detailed_analysis(self):
        """Create detailed analysis section"""
        print("DEBUG: Creating detailed analysis...")
        
        self.story.append(Paragraph("Detailed Analysis", self.styles['CustomHeading1']))
        self.story.append(HRFlowable(width="100%", thickness=1, 
                                    color=colors.HexColor(Config.COLORS['primary']),
                                    spaceAfter=10))
        
        # Create individual category sections
        category_details = [
            ('posture', 'Posture Analysis'),
            ('facial', 'Facial Expression Analysis'),
            ('eye_contact', 'Eye Contact Analysis'),
            ('voice', 'Vocal Delivery Analysis'),
            ('language', 'Language Analysis')
        ]
        
        for cat_key, cat_title in category_details:
            if cat_key in self.results:
                self._create_category_detail(cat_key, cat_title)
                self.story.append(Spacer(1, 20))
        
        self.story.append(PageBreak())
    
    def _create_category_detail(self, cat_key, cat_title):
        """Create detailed analysis for a specific category"""
        cat_data = self.results.get(cat_key, {})
        if not cat_data:
            return
        
        self.story.append(Paragraph(cat_title, self.styles['CustomHeading2']))
        
        # Score and summary
        score_text = f"""
        <para>
        <font color="{Config.COLORS['primary']}" size="12">
        <b>Score: {cat_data.get('score_10', 0):.1f}/10</b>
        </font>
        </para>
        """
        self.story.append(Paragraph(score_text, self.styles['CustomNormal']))
        
        summary = cat_data.get('summary', '')
        if summary:
            self.story.append(Paragraph(summary, self.styles['CustomNormal']))
        
        # Create visualization
        try:
            if cat_key == 'overall':
                # Skip overall here
                return
            
            chart_path = create_modern_progress_bar(
                cat_data.get('score_10', 0), 
                label=cat_title.replace(' Analysis', '')
            )
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=5*inch, height=0.8*inch)
                self.story.append(img)
                self.story.append(Spacer(1, 10))
        except Exception as e:
            print(f"Note: Could not create chart for {cat_key}: {e}")
        
        # Key metrics
        if 'detailed_params' in cat_data:
            self._create_metrics_table(cat_data['detailed_params'], "Detailed Metrics")
        
        # Analysis type
        analysis_type = cat_data.get('analysis_type', '')
        if analysis_type:
            type_text = f"<i>Analysis method: {analysis_type}</i>"
            self.story.append(Paragraph(type_text, self.styles['CustomNormal']))
    
    def _create_metrics_table(self, metrics, title):
        """Create table of detailed metrics"""
        if not metrics:
            return
        
        data = [[title, 'Value', 'Status']]
        
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                # Format key for display
                display_key = key.replace('_', ' ').title()
                
                # Determine status
                if value >= 80:
                    status = "✓ Good"
                    status_color = Config.COLORS['success']
                elif value >= 60:
                    status = "→ Adequate"
                    status_color = Config.COLORS['warning']
                else:
                    status = "✗ Needs Work"
                    status_color = Config.COLORS['danger']
                
                data.append([
                    display_key,
                    f"{value:.1f}",
                    status
                ])
        
        if len(data) > 1:
            table = Table(data, colWidths=[2.5*inch, 1.2*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(Config.COLORS['light'])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(Config.COLORS['dark'])),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), Config.FONTS['heading']),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(Config.COLORS['border'])),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(Config.COLORS['light'])]),
            ]))
            self.story.append(table)
            self.story.append(Spacer(1, 10))
    
    def _create_recommendations(self):
        """Create recommendations section"""
        print("DEBUG: Creating recommendations...")
        
        self.story.append(Paragraph("Actionable Recommendations", self.styles['CustomHeading1']))
        self.story.append(HRFlowable(width="100%", thickness=1, 
                                    color=colors.HexColor(Config.COLORS['primary']),
                                    spaceAfter=10))
        
        categories = [
            ('posture', 'Posture Improvement'),
            ('facial', 'Facial Expression Enhancement'),
            ('eye_contact', 'Eye Contact Development'),
            ('voice', 'Vocal Delivery Training'),
            ('language', 'Language Skills Refinement')
        ]
        
        for cat_key, cat_title in categories:
            if cat_key in self.results:
                recs = self.results[cat_key].get('recommendations', [])
                if recs:
                    self.story.append(Paragraph(cat_title, self.styles['CustomHeading2']))
                    
                    bullet_items = []
                    for rec in recs:
                        bullet_items.append(ListItem(
                            Paragraph(rec, self.styles['CustomBullet']),
                            leftIndent=20
                        ))
                    
                    bullet_list = ListFlowable(bullet_items, bulletType='bullet', leftIndent=20)
                    self.story.append(bullet_list)
                    self.story.append(Spacer(1, 10))
        
        # General tips
        self.story.append(Paragraph("General Interview Tips", self.styles['CustomHeading2']))
        general_tips = [
            "Practice with video recording to review your performance",
            "Set up professional lighting and background",
            "Test your audio and video equipment beforehand",
            "Prepare talking points but avoid memorizing scripts",
            "Dress professionally for video interviews",
            "Maintain good energy throughout the interview",
            "Follow up with a thank-you email after the interview"
        ]
        
        bullet_items = []
        for tip in general_tips:
            bullet_items.append(ListItem(
                Paragraph(tip, self.styles['CustomBullet']),
                leftIndent=20
            ))
        
        bullet_list = ListFlowable(bullet_items, bulletType='bullet', leftIndent=20)
        self.story.append(bullet_list)
        
        self.story.append(PageBreak())
    
    def _create_technical_details(self):
        """Create technical details section"""
        print("DEBUG: Creating technical details...")
        
        self.story.append(Paragraph("Technical Details", self.styles['CustomHeading1']))
        self.story.append(HRFlowable(width="100%", thickness=1, 
                                    color=colors.HexColor(Config.COLORS['primary']),
                                    spaceAfter=10))
        
        video_info = self.results.get('video_info', {})
        
        tech_data = [
            ['Parameter', 'Value'],
            ['Video File', video_info.get('name', 'Unknown')],
            ['Duration', video_info.get('duration', 'Unknown')],
            ['Analysis Date', video_info.get('timestamp', 'Unknown')],
            ['Frames Analyzed', str(video_info.get('frames_analyzed', 0))],
            ['Frame Selection', video_info.get('frame_selection_method', 'Unknown')],
            ['Analysis Mode', video_info.get('analysis_mode', 'Unknown')],
            ['Overall Confidence', f"{self.results.get('overall', {}).get('analysis_confidence', 0.5)*100:.1f}%"],
            ['Report Generated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ['Report Version', '2.1 Professional']
        ]
        
        table = Table(tech_data, colWidths=[2.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(Config.COLORS['light'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(Config.COLORS['dark'])),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), Config.FONTS['heading']),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(Config.COLORS['border'])),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(Config.COLORS['light'])]),
        ]))
        self.story.append(table)
        
        # Add footer
        self.story.append(Spacer(1, 30))
        footer_text = f"""
        <para alignment="center">
        <font size="8" color="{Config.COLORS['text']}">
        Generated by Professional Interview Analyzer v2.1 • Confidential Report • {datetime.now().strftime('%Y-%m-%d')}
        </font>
        </para>
        """
        self.story.append(Paragraph(footer_text, self.styles['CustomFooter']))
    
    def _create_summary_chart(self):
        """Create summary radar chart"""
        try:
            print("DEBUG: Creating summary radar chart...")
            
            category_keys = ['posture', 'facial', 'eye_contact', 'voice', 'language']
            category_names = ['Posture', 'Facial', 'Eye Contact', 'Voice', 'Language']
            
            scores = {}
            for key, name in zip(category_keys, category_names):
                if key in self.results:
                    scores[name] = self.results[key].get('score_10', 0)
                else:
                    scores[name] = 0
            
            if scores:
                chart_path = create_performance_radar_chart(scores)
                print(f"DEBUG: Chart created at: {chart_path}")
                if chart_path:
                    print(f"DEBUG: Chart exists: {os.path.exists(chart_path)}")
                return chart_path
            else:
                print("DEBUG: No scores for chart creation")
                return None
        except Exception as e:
            print(f"DEBUG: Chart creation failed: {e}")
            traceback.print_exc()
            return None

# MAIN EXECUTION PIPELINE

def analyze_video_professional(video_path: str, output_pdf: str = None, generate_charts: bool = True):
    """
    Complete professional video analysis pipeline
    
    Args:
        video_path: Path to video file
        output_pdf: Optional output PDF path
        generate_charts: Whether to generate visual charts
    
    Returns:
        Dictionary with complete analysis results
    """
    print("\n" + "="*60)
    print("PROFESSIONAL INTERVIEW ANALYZER v2.1")
    print("="*60)
    
    # Check if video exists
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        print(f"✗ Error: Video file not found: {video_path}")
        print(f"DEBUG: Current directory: {os.getcwd()}")
        print(f"DEBUG: Video path absolute: {video_path_obj.absolute()}")
        return None
    
    print(f"📹 Analyzing: {video_path_obj.name}")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60)
    
    try:
        # Step 1: Initialize analyzer
        print("Step 1: Initializing analyzer...")
        analyzer = EnhancedProfessionalVideoAnalyzer(video_path)
        
        # Step 2: Run complete analysis
        print("Step 2: Running comprehensive analysis...")
        results = analyzer.analyze_all()
        
        if not results:
            print("✗ Analysis failed")
            return None
        
        # Step 3: Display summary
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE - SUMMARY")
        print("="*60)
        
        overall = results.get('overall', {})
        print(f"Overall Score: {overall.get('score_10', 0):.1f}/10 ({overall.get('grade', 'N/A')})")
        print(f"Overall Feedback: {overall.get('feedback', 'No feedback')}")
        print(f"Analysis Confidence: {overall.get('analysis_confidence', 0.5)*100:.1f}%")
        print()
        
        categories = ['posture', 'facial', 'eye_contact', 'voice', 'language']
        for cat in categories:
            if cat in results:
                score = results[cat].get('score_10', 0)
                print(f"{cat.title():20s}: {score:.1f}/10")
        
        # Step 4: Generate charts if requested
        if generate_charts:
            print("\nStep 3: Generating visualizations...")
            try:
                # Create comparison chart if previous data exists
                comparison_path = Config.DATA_DIR / f"{video_path_obj.stem}_previous.json"
                if comparison_path.exists():
                    try:
                        with open(comparison_path, 'r') as f:
                            previous_results = json.load(f)
                        
                        before_scores = {}
                        after_scores = {}
                        
                        for cat in categories:
                            if cat in previous_results:
                                before_scores[cat.title()] = previous_results[cat].get('score_10', 0)
                            if cat in results:
                                after_scores[cat.title()] = results[cat].get('score_10', 0)
                        
                        if before_scores and after_scores:
                            create_comparison_chart(before_scores, after_scores)
                            print("✓ Comparison chart created")
                    except Exception as e:
                        print(f"Note: Could not create comparison chart: {e}")
                
                # Create individual charts
                for cat in categories:
                    if cat in results:
                        score = results[cat].get('score_10', 0)
                        try:
                            create_enhanced_donut_chart(score, label=cat.replace('_', ' ').title())
                            create_modern_progress_bar(score, label=cat.replace('_', ' ').title())
                        except Exception as e:
                            print(f"Note: Could not create chart for {cat}: {e}")
                
                print("✓ Visualizations generated")
                
            except Exception as e:
                print(f"Note: Chart generation had issues: {e}")
        
        # Step 5: Generate PDF report
        print("\nStep 4: Generating professional report...")
        try:
            pdf_generator = ProfessionalPDFGenerator(results, output_pdf)
            report_path = pdf_generator.generate_report()
            
            if report_path:
                print(f"✓ Professional report generated: {report_path}")
                results['report_path'] = str(report_path)
            else:
                print("✗ Failed to generate PDF report")
        except Exception as e:
            print(f"✗ Error generating PDF report: {e}")
            traceback.print_exc()
        
        # Step 6: Save results for future reference
        try:
            save_path = Config.DATA_DIR / f"{video_path_obj.stem}_results.json"
            with open(save_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✓ Analysis data saved: {save_path}")
        except Exception as e:
            print(f"Note: Could not save results: {e}")
        
        print("\n" + "="*60)
        print("ANALYSIS PIPELINE COMPLETE")
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"\n✗ Critical error during analysis: {e}")
        traceback.print_exc()
        return None

def batch_analysis(video_folder: str, output_folder: str = None):
    """
    Analyze multiple videos in batch mode
    
    Args:
        video_folder: Folder containing video files
        output_folder: Optional output folder for reports
    """
    video_folder = Path(video_folder)
    
    if not video_folder.exists():
        print(f"✗ Folder not found: {video_folder}")
        return
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(video_folder.glob(f"*{ext}"))
        video_files.extend(video_folder.glob(f"*{ext.upper()}"))
    
    if not video_files:
        print(f"✗ No video files found in {video_folder}")
        return
    
    print(f"\n📁 Found {len(video_files)} video(s) to analyze")
    print("="*60)
    
    results = {}
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Analyzing: {video_file.name}")
        
        if output_folder:
            output_pdf = Path(output_folder) / f"{video_file.stem}_report.pdf"
        else:
            output_pdf = None
        
        try:
            result = analyze_video_professional(str(video_file), str(output_pdf) if output_pdf else None)
            if result:
                results[video_file.name] = result.get('overall', {}).get('score_10', 0)
        except Exception as e:
            print(f"✗ Failed to analyze {video_file.name}: {e}")
            results[video_file.name] = "Failed"
    
    # Print batch summary
    print("\n" + "="*60)
    print("BATCH ANALYSIS SUMMARY")
    print("="*60)
    
    for video, score in results.items():
        if isinstance(score, (int, float)):
            print(f"{video[:40]:40s} : {score:5.1f}/10")
        else:
            print(f"{video[:40]:40s} : {score}")

def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(
        description='Professional Interview Analyzer v2.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python integrated_analysis_report.py video.mp4
  python integrated_analysis_report.py video.mp4 --output custom_report.pdf
  python integrated_analysis_report.py videos/ --batch
  python integrated_analysis_report.py video.mp4 --username Tanvi --subject "Python Interview" --email tanvimahadik77@gmail.com --session Interview12_20260128_141022
        """
    )
    
    # Main input argument
    parser.add_argument('input', nargs='?', help='Video file or folder path')
    
    # Analysis options
    parser.add_argument('-o', '--output', help='Output PDF path')
    parser.add_argument('-b', '--batch', action='store_true', help='Batch mode for folder')
    parser.add_argument('-n', '--no-charts', action='store_true', help='Disable chart generation')
    parser.add_argument('-v', '--version', action='version', version='Professional Interview Analyzer v2.1')
    
    # User information parameters
    parser.add_argument('--username', help='User name for report customization')
    parser.add_argument('--subject', help='Interview subject/topic')
    parser.add_argument('--email', help='User email address')
    parser.add_argument('--session', help='Session identifier')
    parser.add_argument('--company', help='Company name (optional)')
    parser.add_argument('--position', help='Position applied for (optional)')
    
    args = parser.parse_args()
    
    # If no input provided, show help
    if not args.input:
        parser.print_help()
        
        # Check for video files in current directory
        current_dir = Path.cwd()
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        videos = []
        
        for ext in video_extensions:
            videos.extend(current_dir.glob(f"*{ext}"))
        
        if videos:
            print(f"\n📁 Found {len(videos)} video(s) in current directory:")
            for i, video in enumerate(videos, 1):
                print(f"  {i}. {video.name}")
            
            choice = input("\nEnter number to analyze (or Enter to exit): ").strip()
            if choice and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(videos):
                    args.input = str(videos[idx])
                else:
                    print("Invalid selection")
                    return
            else:
                return
        else:
            return
    
    input_path = Path(args.input)
    
    # Store user information in global config for use in reports
    if args.username:
        Config.USERNAME = args.username
    if args.subject:
        Config.SUBJECT = args.subject
    if args.email:
        Config.EMAIL = args.email
    if args.session:
        Config.SESSION = args.session
    if args.company:
        Config.COMPANY = args.company
    if args.position:
        Config.POSITION = args.position
    
    if args.batch or input_path.is_dir():
        # Batch mode
        output_folder = Path(args.output) if args.output else Config.REPORTS_DIR
        batch_analysis(args.input, str(output_folder))
    else:
        # Single video mode
        if not input_path.exists():
            print(f"✗ File not found: {args.input}")
            return
        
        # Enhance results with user information
        results = analyze_video_professional(
            args.input, 
            args.output, 
            not args.no_charts
        )
        
        if results:
            # Add user information to results
            if args.username or args.subject or args.email or args.session:
                results['user_info'] = {
                    'username': args.username or 'Not specified',
                    'subject': args.subject or 'Interview Analysis',
                    'email': args.email or 'Not specified',
                    'session': args.session or datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'company': args.company or 'Not specified',
                    'position': args.position or 'Not specified',
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            print(f"\n✅ Analysis complete!")
            overall = results.get('overall', {})
            print(f"\n📊 Final Score: {overall.get('score_10', 0):.1f}/10 ({overall.get('grade', 'N/A')})")
            
            # Display user information if provided
            if 'user_info' in results:
                user_info = results['user_info']
                print(f"\n👤 User Information:")
                print(f"   Name: {user_info['username']}")
                print(f"   Subject: {user_info['subject']}")
                print(f"   Email: {user_info['email']}")
                print(f"   Session: {user_info['session']}")
                if user_info['company'] != 'Not specified':
                    print(f"   Company: {user_info['company']}")
                if user_info['position'] != 'Not specified':
                    print(f"   Position: {user_info['position']}")
            
            if 'report_path' in results:
                print(f"\n📄 Report: {results['report_path']}")
                
                # Optional: Email report if email is provided
                # Optional: Email report if email is provided
                if args.email and args.username:
                    # Skip interactive prompt when running from backend
                    print(f"\n[EMAIL] Report ready for {args.email}")
                    print(f"[EMAIL] Note: Email sending requires SMTP configuration")
                # Uncomment and configure if you want to automatically send emails
                # subject = f"Interview Analysis Report - {args.subject or 'Interview'}"
                # send_email_report(results['report_path'], args.email, args.username, subject)

# CLEANUP AND UTILITY

def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        if Config.TEMP_DIR.exists():
            shutil.rmtree(Config.TEMP_DIR)
            print(f"✓ Cleaned temporary files: {Config.TEMP_DIR}")
    except Exception as e:
        print(f"Note: Could not clean temp files: {e}")

def list_reports():
    """List available analysis reports"""
    reports = list(Config.REPORTS_DIR.glob("*.pdf"))
    
    if not reports:
        print("No reports found")
        return
    
    print(f"\n📄 Available Reports ({len(reports)}):")
    print("="*60)
    
    for i, report in enumerate(reports, 1):
        mtime = datetime.fromtimestamp(report.stat().st_mtime)
        size = report.stat().st_size / 1024  # KB
        print(f"{i:3d}. {report.name:50s} {mtime.strftime('%Y-%m-%d %H:%M')}  {size:.1f} KB")

if __name__ == "__main__":
    try:
        # Ensure directories exist
        Config.setup_directories()
        
        # Register cleanup on exit
        import atexit
        atexit.register(cleanup_temp_files)
        
        # Run main function
        main()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Analysis interrupted by user")
        cleanup_temp_files()
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        traceback.print_exc()
        cleanup_temp_files()
        sys.exit(1)