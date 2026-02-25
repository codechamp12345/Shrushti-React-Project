# eye_behavior_analysis.py (updated version of your code)
import cv2
import numpy as np
import mediapipe as mp
import math
import os
from datetime import datetime
import json

import sys
import os

# Fix for Windows Unicode
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
# --- MediaPipe setup ---
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Eye & iris landmarks for gaze
LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
LEFT_IRIS_C  = 468
RIGHT_IRIS_C = 473

# Blink detection indices
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

# Constants
CLOSED_EYES_FRAME = 3
center_thresh = 0.03  # for gaze
FPS_DEFAULT = 30.0
CALIBRATION_FRAMES = 30

def analyze_eye_behavior(video_path):
    """
    Main analysis function for eye behavior
    Returns comprehensive results including gaze, blinks, focus, and stability
    """
    if not os.path.exists(video_path):
        return {"error": f"File not found: {video_path}"}
    
    # Extract filename for reporting
    filename = os.path.basename(video_path)
    
    # --- Video read ---
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS_DEFAULT
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = frame_count/fps
    minutes = max(1e-6, duration_sec/60)
    
    # --- Buffers ---
    direction_counts = {"left":0,"right":0,"center":0,"up":0,"down":0}
    gx_list, gy_list = [], []
    focus_frames = 0
    valid_frames = 0
    frames_with_face = 0
    
    # Blink detection variables
    CEF_COUNTER = 0
    TOTAL_BLINKS = 0
    
    # Store blink timestamps
    blink_timestamps = []
    
    # Calibration
    calib_gy_values = []
    gy_offset = 0.0
    
    # --- Main loop ---
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: 
            break
        
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)
        frame_idx += 1
        
        if not res.multi_face_landmarks:
            continue
        
        lms = res.multi_face_landmarks[0].landmark
        valid_frames += 1
        frames_with_face += 1
        
        # --- Gaze ---
        left_pts = np.stack(get_landmarks(lms, LEFT_EYE_IDX, w, h))
        right_pts = np.stack(get_landmarks(lms, RIGHT_EYE_IDX, w, h))
        left_iris = np.array([lms[LEFT_IRIS_C].x*w, lms[LEFT_IRIS_C].y*h])
        right_iris = np.array([lms[RIGHT_IRIS_C].x*w, lms[RIGHT_IRIS_C].y*h])
        gx_l, gy_l = normalize_gaze(left_pts, left_iris)
        gx_r, gy_r = normalize_gaze(right_pts, right_iris)
        gx, gy = (gx_l+gx_r)/2, (gy_l+gy_r)/2
        
        # --- Auto calibration in first few frames ---
        if frame_idx <= CALIBRATION_FRAMES:
            calib_gy_values.append(gy)
            if frame_idx == CALIBRATION_FRAMES:
                gy_offset = np.mean(calib_gy_values)
        gy -= gy_offset
        
        gx_list.append(gx)
        gy_list.append(gy)
        
        # Focus detection (both eyes open & center gaze)
        ratio = blinkRatio(lms, RIGHT_EYE, LEFT_EYE,w,h) 
        eyes_open = ratio <= 4.1
        
        if eyes_open and abs(gx)<=center_thresh and abs(gy)<=center_thresh:
            focus_frames += 1
        
        # Blink detection
        if ratio > 4.1:
            CEF_COUNTER += 1
        else:
            if CEF_COUNTER >= CLOSED_EYES_FRAME:
                TOTAL_BLINKS += 1
                blink_timestamps.append(frame_idx/fps)  # Store timestamp in seconds
            CEF_COUNTER = 0
        
        # Gaze direction
        if eyes_open:
            if gx < -center_thresh:
                direction = "left"
            elif gx > center_thresh:
                direction = "right"
            else:
                direction = "center"
        
            # Vertical adjustments
            if direction == "center":
                if gy < -center_thresh:
                    direction = "up"
                elif gy > center_thresh:
                    direction = "down"
        
            direction_counts[direction] += 1
    
    cap.release()
    
    # --- Calculate Metrics ---
    total_eye_frames = sum(direction_counts.values()) or 1
    gaze_percent = {k: round(v/total_eye_frames*100, 2) for k,v in direction_counts.items()}
    
    # Calculate blink rate
    blink_rate = round(TOTAL_BLINKS/minutes, 2) if minutes > 0 else 0
    
    # Focus percentage
    focus_percent = round(focus_frames/(valid_frames or 1)*100, 2)
    
    # Stability calculation
    if gx_list and gy_list:
        all_movements = gx_list + gy_list
        movement_std = np.std(all_movements)
        stability = round(100 * (1 - min(movement_std, 1.0)), 2)
    else:
        stability = 0
    
    # Blink score
    if 15 <= blink_rate <= 20:
        blink_score = 20
    elif 20 < blink_rate <= 30 or 10 <= blink_rate < 15:
        blink_score = 15
    else:
        blink_score = max(0, 10 - abs(blink_rate-20)/2)
    
    # Eye contact score (weighted)
    forward_gaze = gaze_percent.get('center', 0)
    eye_contact_score = round(
        0.3 * min(forward_gaze/100 * 10, 10) +  # Gaze forward component
        0.3 * min(focus_percent/100 * 10, 10) +  # Focus component
        0.2 * blink_score/20 * 10 +  # Blink component
        0.2 * stability/100 * 10,  # Stability component
        1
    )
    
    # Confidence level based on eye contact
    confidence_level = "High" if eye_contact_score >= 8.0 else "Medium" if eye_contact_score >= 6.0 else "Low"
    
    # Calculate blink intervals
    blink_intervals = []
    if len(blink_timestamps) > 1:
        for i in range(1, len(blink_timestamps)):
            interval = blink_timestamps[i] - blink_timestamps[i-1]
            blink_intervals.append(round(interval, 2))
    
    avg_blink_interval = round(np.mean(blink_intervals), 2) if blink_intervals else 0
    
    return {
        'filename': filename,
        'duration_sec': round(duration_sec, 2),
        'valid_frames': valid_frames,
        'frames_with_face': frames_with_face,
        
        # Scores
        'total_score': eye_contact_score,
        'eye_contact_score': eye_contact_score,
        'blink_score': blink_score,
        'stability': stability,
        
        # Metrics
        'blink_rate': blink_rate,
        'total_blinks': TOTAL_BLINKS,
        'avg_blink_interval': avg_blink_interval,
        'focus_percent': focus_percent,
        'gaze_distribution': gaze_percent,
        'confidence_level': confidence_level,
        
        # Raw data for aggregation
        'forward_gaze_percent': gaze_percent.get('center', 0),
        'blink_intervals': blink_intervals,
        
        # Timestamps
        'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# --- Helper functions (unchanged from your original) ---
def euclideanDistance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def blinkRatio(lms, right_indices, left_indices, w, h):
    def xy(idx):
        return np.array([lms[idx].x*w, lms[idx].y*h])
    
    # Right eye
    rh_right = xy(right_indices[0])
    rh_left = xy(right_indices[8])
    rv_top = xy(right_indices[12])
    rv_bottom = xy(right_indices[4])
    reRatio = euclideanDistance(rh_right, rh_left) / (euclideanDistance(rv_top, rv_bottom)+1e-6)
    
    # Left eye
    lh_right = xy(left_indices[0])
    lh_left = xy(left_indices[8])
    lv_top = xy(left_indices[12])
    lv_bottom = xy(left_indices[4])
    leRatio = euclideanDistance(lh_right, lh_left) / (euclideanDistance(lv_top, lv_bottom)+1e-6)
    
    return (reRatio + leRatio)/2

def get_landmarks(lms, idx_list, w, h):
    return [np.array([lms[i].x*w, lms[i].y*h], dtype=np.float32) for i in idx_list]

def normalize_gaze(eye_pts, iris_xy):
    xs, ys = eye_pts[:,0], eye_pts[:,1]
    x_c, y_c = (xs.min()+xs.max())/2.0, (ys.min()+ys.max())/2.0
    w, h = xs.max()-xs.min()+1e-6, ys.max()-ys.min()+1e-6
    gx = (iris_xy[0]-x_c)/w
    gy = (iris_xy[1]-y_c)/h
    return gx, gy