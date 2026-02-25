# body_posture_analysis.py
import cv2
import mediapipe as mp
import numpy as np
import math
import json
from datetime import datetime
from scipy import stats
import warnings
warnings.filterwarnings('ignore')
import sys
import os

# Fix for Windows Unicode
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
class BodyPostureAnalyzer:
    def __init__(self):
        # Initialize MediaPipe solutions
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize pose detector
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,  # 2 is most accurate
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Posture thresholds (in degrees or pixels)
        self.thresholds = {
            'head_pitch': {'good': 0, 'acceptable': 10, 'poor': 20},
            'head_yaw': {'good': 5, 'acceptable': 15, 'poor': 30},
            'head_roll': {'good': 2, 'acceptable': 5, 'poor': 10},
            'spine_inclination': {'good': 2, 'acceptable': 8, 'poor': 15},
            'shoulder_tilt': {'good': 2, 'acceptable': 5, 'poor': 10},
            'hip_alignment': {'good': 2, 'acceptable': 5, 'poor': 10},
            'lean_forward': {'good': 0, 'acceptable': 3, 'poor': 8},
            'confidence_level': 0.7
        }
        
        # Ideal angles for perfect posture
        self.ideal_angles = {
            'head_pitch': 0,      # Looking straight ahead
            'head_yaw': 0,        # Facing forward
            'head_roll': 0,       # No tilt
            'spine_inclination': 0, # Vertical spine
            'shoulder_tilt': 0,   # Level shoulders
            'hip_alignment': 0    # Level hips
        }
    
    def calculate_angle(self, a, b, c):
        """Calculate angle between three points with b as vertex"""
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))
        
        return angle
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def get_landmark_coordinates(self, landmarks, landmark_idx, image_width, image_height):
        """Extract normalized landmark coordinates"""
        if landmarks and landmark_idx < len(landmarks.landmark):
            landmark = landmarks.landmark[landmark_idx]
            return [landmark.x * image_width, landmark.y * image_height]
        return None
    
    def analyze_frame_posture(self, frame, frame_count, total_frames):
        """Analyze posture for a single frame"""
        image_height, image_width = frame.shape[:2]
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        
        if not results.pose_landmarks:
            return None
        
        # Extract key landmarks
        landmarks = {
            'nose': self.get_landmark_coordinates(results.pose_landmarks, 
                                                  self.mp_pose.PoseLandmark.NOSE, 
                                                  image_width, image_height),
            'left_eye': self.get_landmark_coordinates(results.pose_landmarks, 
                                                     self.mp_pose.PoseLandmark.LEFT_EYE, 
                                                     image_width, image_height),
            'right_eye': self.get_landmark_coordinates(results.pose_landmarks, 
                                                      self.mp_pose.PoseLandmark.RIGHT_EYE, 
                                                      image_width, image_height),
            'left_ear': self.get_landmark_coordinates(results.pose_landmarks, 
                                                     self.mp_pose.PoseLandmark.LEFT_EAR, 
                                                     image_width, image_height),
            'right_ear': self.get_landmark_coordinates(results.pose_landmarks, 
                                                      self.mp_pose.PoseLandmark.RIGHT_EAR, 
                                                      image_width, image_height),
            'left_shoulder': self.get_landmark_coordinates(results.pose_landmarks, 
                                                          self.mp_pose.PoseLandmark.LEFT_SHOULDER, 
                                                          image_width, image_height),
            'right_shoulder': self.get_landmark_coordinates(results.pose_landmarks, 
                                                           self.mp_pose.PoseLandmark.RIGHT_SHOULDER, 
                                                           image_width, image_height),
            'left_elbow': self.get_landmark_coordinates(results.pose_landmarks, 
                                                       self.mp_pose.PoseLandmark.LEFT_ELBOW, 
                                                       image_width, image_height),
            'right_elbow': self.get_landmark_coordinates(results.pose_landmarks, 
                                                        self.mp_pose.PoseLandmark.RIGHT_ELBOW, 
                                                        image_width, image_height),
            'left_wrist': self.get_landmark_coordinates(results.pose_landmarks, 
                                                       self.mp_pose.PoseLandmark.LEFT_WRIST, 
                                                       image_width, image_height),
            'right_wrist': self.get_landmark_coordinates(results.pose_landmarks, 
                                                        self.mp_pose.PoseLandmark.RIGHT_WRIST, 
                                                        image_width, image_height),
            'left_hip': self.get_landmark_coordinates(results.pose_landmarks, 
                                                     self.mp_pose.PoseLandmark.LEFT_HIP, 
                                                     image_width, image_height),
            'right_hip': self.get_landmark_coordinates(results.pose_landmarks, 
                                                      self.mp_pose.PoseLandmark.RIGHT_HIP, 
                                                      image_width, image_height),
            'left_knee': self.get_landmark_coordinates(results.pose_landmarks, 
                                                      self.mp_pose.PoseLandmark.LEFT_KNEE, 
                                                      image_width, image_height),
            'right_knee': self.get_landmark_coordinates(results.pose_landmarks, 
                                                       self.mp_pose.PoseLandmark.RIGHT_KNEE, 
                                                       image_width, image_height),
            'left_ankle': self.get_landmark_coordinates(results.pose_landmarks, 
                                                       self.mp_pose.PoseLandmark.LEFT_ANKLE, 
                                                       image_width, image_height),
            'right_ankle': self.get_landmark_coordinates(results.pose_landmarks, 
                                                        self.mp_pose.PoseLandmark.RIGHT_ANKLE, 
                                                        image_width, image_height)
        }
        
        # Check if all required landmarks are available
        required_landmarks = ['nose', 'left_eye', 'right_eye', 'left_shoulder', 
                             'right_shoulder', 'left_hip', 'right_hip']
        for landmark in required_landmarks:
            if landmarks[landmark] is None:
                return None
        
        # Calculate posture metrics
        metrics = {}
        
        # 1. Head Pitch (vertical tilt)
        eye_center = [(landmarks['left_eye'][0] + landmarks['right_eye'][0]) / 2,
                     (landmarks['left_eye'][1] + landmarks['right_eye'][1]) / 2]
        metrics['head_pitch'] = math.degrees(
            math.atan2(landmarks['nose'][1] - eye_center[1],
                      landmarks['nose'][0] - eye_center[0])
        )
        
        # 2. Head Yaw (horizontal turn)
        metrics['head_yaw'] = math.degrees(
            math.atan2(landmarks['left_eye'][0] - landmarks['right_eye'][0],
                      landmarks['left_eye'][1] - landmarks['right_eye'][1])
        )
        
        # 3. Head Roll (side tilt)
        metrics['head_roll'] = math.degrees(
            math.atan2(landmarks['left_eye'][1] - landmarks['right_eye'][1],
                      landmarks['left_eye'][0] - landmarks['right_eye'][0])
        )
        
        # 4. Spine Inclination
        mid_shoulder = [(landmarks['left_shoulder'][0] + landmarks['right_shoulder'][0]) / 2,
                       (landmarks['left_shoulder'][1] + landmarks['right_shoulder'][1]) / 2]
        mid_hip = [(landmarks['left_hip'][0] + landmarks['right_hip'][0]) / 2,
                  (landmarks['left_hip'][1] + landmarks['right_hip'][1]) / 2]
        
        spine_vector = np.array(mid_shoulder) - np.array(mid_hip)
        vertical_vector = np.array([0, -1])
        
        spine_angle = math.degrees(
            math.acos(np.dot(spine_vector, vertical_vector) / 
                     (np.linalg.norm(spine_vector) * np.linalg.norm(vertical_vector) + 1e-6))
        )
        metrics['spine_inclination'] = spine_angle if spine_angle <= 90 else 180 - spine_angle
        
        # 5. Shoulder Tilt
        metrics['shoulder_tilt'] = abs(landmarks['left_shoulder'][1] - landmarks['right_shoulder'][1]) * 100
        
        # 6. Hip Alignment
        metrics['hip_alignment'] = abs(landmarks['left_hip'][1] - landmarks['right_hip'][1]) * 100
        
        # 7. Forward Lean (distance from camera)
        # Using shoulder width as reference for depth estimation
        shoulder_width = self.calculate_distance(landmarks['left_shoulder'], landmarks['right_shoulder'])
        hip_width = self.calculate_distance(landmarks['left_hip'], landmarks['right_hip'])
        metrics['forward_lean'] = abs(shoulder_width - hip_width) / shoulder_width * 100
        
        # 8. Arm positions (symmetry)
        if landmarks['left_elbow'] and landmarks['right_elbow']:
            left_elbow_angle = self.calculate_angle(landmarks['left_shoulder'],
                                                   landmarks['left_elbow'],
                                                   landmarks['left_wrist'])
            right_elbow_angle = self.calculate_angle(landmarks['right_shoulder'],
                                                    landmarks['right_elbow'],
                                                    landmarks['right_wrist'])
            metrics['arm_symmetry'] = abs(left_elbow_angle - right_elbow_angle)
        else:
            metrics['arm_symmetry'] = 0
        
        # 9. Sitting/Standing posture
        if landmarks['left_knee'] and landmarks['right_knee']:
            knee_angle_left = self.calculate_angle(landmarks['left_hip'],
                                                  landmarks['left_knee'],
                                                  landmarks['left_ankle'])
            knee_angle_right = self.calculate_angle(landmarks['right_hip'],
                                                   landmarks['right_knee'],
                                                   landmarks['right_ankle'])
            avg_knee_angle = (knee_angle_left + knee_angle_right) / 2
            metrics['posture_type'] = 'sitting' if avg_knee_angle < 135 else 'standing'
        else:
            metrics['posture_type'] = 'unknown'
        
        # Add frame information
        metrics['frame_count'] = frame_count
        metrics['frame_progress'] = frame_count / total_frames
        
        return metrics
    
    def categorize_metric(self, metric_name, value):
        """Categorize a metric as Good, Acceptable, or Poor"""
        thresholds = self.thresholds.get(metric_name, {})
        
        if abs(value) <= thresholds.get('good', 0):
            return 'Excellent'
        elif abs(value) <= thresholds.get('acceptable', 10):
            return 'Acceptable'
        elif abs(value) <= thresholds.get('poor', 20):
            return 'Needs Improvement'
        else:
            return 'Poor'
    
    def calculate_score(self, metric_name, value):
        """Calculate score for a metric (0-100)"""
        thresholds = self.thresholds.get(metric_name, {})
        ideal = self.ideal_angles.get(metric_name, 0)
        
        deviation = abs(value - ideal)
        poor_threshold = thresholds.get('poor', 20)
        
        if deviation <= thresholds.get('good', 0):
            return 100
        elif deviation <= thresholds.get('acceptable', 10):
            return 80
        elif deviation <= poor_threshold:
            return 60 - ((deviation - thresholds.get('acceptable', 10)) / 
                        (poor_threshold - thresholds.get('acceptable', 10))) * 20
        else:
            return max(0, 40 - ((deviation - poor_threshold) / poor_threshold) * 40)
    
    def analyze_video_posture(self, video_path, sample_rate=5):
        """
        Analyze posture from video file
        sample_rate: Analyze every nth frame (for performance)
        """
        print(f"Starting posture analysis for: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error opening video file: {video_path}")
            return self.get_default_result()
        
        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        duration = total_frames / fps
        
        print(f"Video info: {total_frames} frames, {fps:.1f} FPS, {duration:.1f} seconds")
        
        # Initialize metrics storage
        all_metrics = []
        frame_metrics_dict = {}
        
        frame_count = 0
        analyzed_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Sample frames for performance
            if frame_count % sample_rate == 0:
                metrics = self.analyze_frame_posture(frame, frame_count, total_frames)
                if metrics:
                    all_metrics.append(metrics)
                    frame_metrics_dict[frame_count] = metrics
                    analyzed_frames += 1
            
            frame_count += 1
            
            # Progress indicator
            if frame_count % 100 == 0:
                print(f"Processed {frame_count}/{total_frames} frames...")
        
        cap.release()
        
        if not all_metrics:
            print("No frames with pose detected")
            return self.get_default_result()
        
        print(f"Analyzed {analyzed_frames} frames with pose detection")
        
        # Calculate overall statistics
        metrics_summary = {}
        for metric in all_metrics[0].keys():
            if metric not in ['frame_count', 'frame_progress', 'posture_type']:
                values = [m[metric] for m in all_metrics]
                metrics_summary[metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'median': np.median(values)
                }
        
        # Calculate individual scores and categories
        posture_scores = {}
        posture_categories = {}
        
        for metric_name, stats in metrics_summary.items():
            mean_value = stats['mean']
            posture_scores[metric_name] = self.calculate_score(metric_name, mean_value)
            posture_categories[metric_name] = self.categorize_metric(metric_name, mean_value)
        
        # Calculate overall posture score
        weights = {
            'head_pitch': 0.15,
            'head_yaw': 0.15,
            'head_roll': 0.10,
            'spine_inclination': 0.25,
            'shoulder_tilt': 0.15,
            'hip_alignment': 0.10,
            'forward_lean': 0.05,
            'arm_symmetry': 0.05
        }
        
        overall_score = 0
        for metric, weight in weights.items():
            if metric in posture_scores:
                overall_score += posture_scores[metric] * weight
        
        overall_score = round(overall_score, 1)
        
        # Determine posture consistency
        consistency_scores = []
        for metric_name in posture_scores.keys():
            values = [m[metric_name] for m in all_metrics]
            consistency = 100 - (np.std(values) / (np.mean(values) + 1e-6) * 100)
            consistency_scores.append(max(0, min(100, consistency)))
        
        posture_consistency = np.mean(consistency_scores) if consistency_scores else 0
        
        # Determine most common posture type
        posture_types = [m.get('posture_type', 'unknown') for m in all_metrics]
        if posture_types:
            main_posture_type = max(set(posture_types), key=posture_types.count)
        else:
            main_posture_type = 'unknown'
        
        # Count issues
        issues = []
        poor_count = 0
        for metric_name, category in posture_categories.items():
            if category in ['Needs Improvement', 'Poor']:
                poor_count += 1
                issues.append(f"{metric_name.replace('_', ' ').title()}: {category}")
        
        # Generate verdict
        if overall_score >= 90:
            verdict = "Excellent Posture"
            verdict_detail = "Professional and confident posture throughout"
        elif overall_score >= 80:
            verdict = "Good Posture"
            verdict_detail = "Strong posture with minor improvements possible"
        elif overall_score >= 70:
            verdict = "Acceptable Posture"
            verdict_detail = "Basic posture maintained, some areas need attention"
        elif overall_score >= 60:
            verdict = "Needs Improvement"
            verdict_detail = "Several posture issues detected"
        else:
            verdict = "Poor Posture"
            verdict_detail = "Significant posture problems requiring attention"
        
        # Generate recommendations
        recommendations = self.generate_recommendations(posture_categories, posture_scores)
        
        # Compile comprehensive result
        result = {
            'analysis_timestamp': datetime.now().isoformat(),
            'video_info': {
                'path': video_path,
                'total_frames': total_frames,
                'analyzed_frames': analyzed_frames,
                'fps': fps,
                'duration_seconds': duration,
                'sample_rate': sample_rate
            },
            'overall_assessment': {
                'score_100': overall_score,
                'score_10': round(overall_score / 10, 1),
                'verdict': verdict,
                'verdict_detail': verdict_detail,
                'consistency_score': round(posture_consistency, 1),
                'posture_type': main_posture_type,
                'issue_count': poor_count,
                'total_metrics': len(posture_categories)
            },
            'detailed_metrics': {},
            'issues_detected': issues[:10],  # Top 10 issues
            'recommendations': recommendations,
            'statistical_summary': metrics_summary
        }
        
        # Add detailed metrics
        for metric_name in posture_scores.keys():
            result['detailed_metrics'][metric_name] = {
                'score_100': round(posture_scores[metric_name], 1),
                'score_10': round(posture_scores[metric_name] / 10, 1),
                'category': posture_categories[metric_name],
                'average_value': round(metrics_summary[metric_name]['mean'], 2),
                'std_deviation': round(metrics_summary[metric_name]['std'], 2),
                'ideal_value': self.ideal_angles.get(metric_name, 0),
                'thresholds': self.thresholds.get(metric_name, {})
            }
        
        print(f"Posture analysis completed. Overall score: {overall_score}/100")
        return result
    
    def generate_recommendations(self, categories, scores):
        """Generate personalized recommendations based on posture analysis"""
        recommendations = []
        
        # Head position recommendations
        if categories.get('head_pitch') in ['Needs Improvement', 'Poor']:
            if scores.get('head_pitch', 0) > 0:
                recommendations.append("Keep your head level - you're looking down too much")
            else:
                recommendations.append("Lower your chin slightly - you're looking up too much")
        
        if categories.get('head_yaw') in ['Needs Improvement', 'Poor']:
            recommendations.append("Face the camera directly - avoid turning your head to the side")
        
        if categories.get('head_roll') in ['Needs Improvement', 'Poor']:
            recommendations.append("Keep your head straight - avoid tilting to one side")
        
        # Spine recommendations
        if categories.get('spine_inclination') in ['Needs Improvement', 'Poor']:
            if scores.get('spine_inclination', 0) > 5:
                recommendations.append("Sit/stand up straighter - avoid slouching forward")
            else:
                recommendations.append("Relax your back slightly - avoid being too rigid")
        
        # Shoulder recommendations
        if categories.get('shoulder_tilt') in ['Needs Improvement', 'Poor']:
            recommendations.append("Relax and level your shoulders - one appears higher than the other")
        
        # Hip recommendations
        if categories.get('hip_alignment') in ['Needs Improvement', 'Poor']:
            recommendations.append("Distribute weight evenly - hips should be level")
        
        # Forward lean recommendations
        if categories.get('forward_lean') in ['Needs Improvement', 'Poor']:
            recommendations.append("Maintain comfortable distance from camera - avoid leaning too far forward or back")
        
        # General recommendations if issues are present
        if len([c for c in categories.values() if c in ['Needs Improvement', 'Poor']]) >= 3:
            recommendations.append("Consider adjusting your chair height and screen position")
            recommendations.append("Take regular breaks to stretch and reset your posture")
        
        # Add positive reinforcement if good
        excellent_count = len([c for c in categories.values() if c == 'Excellent'])
        if excellent_count >= 5:
            recommendations.insert(0, "Excellent overall posture - maintain these good habits!")
        
        # Ensure we have at least some recommendations
        if not recommendations:
            recommendations = [
                "Maintain your current posture - it's working well for you",
                "Continue regular posture checks to maintain good habits"
            ]
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def get_default_result(self):
        """Return default result when analysis fails"""
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'overall_assessment': {
                'score_100': 0,
                'score_10': 0,
                'verdict': 'Analysis Failed',
                'verdict_detail': 'Could not analyze posture from video',
                'consistency_score': 0,
                'posture_type': 'unknown',
                'issue_count': 0,
                'total_metrics': 0
            },
            'detailed_metrics': {},
            'issues_detected': ['Unable to detect pose in video'],
            'recommendations': ['Ensure good lighting and clear view of upper body',
                              'Position camera at eye level'],
            'video_info': {},
            'statistical_summary': {}
        }
    
    def visualize_posture(self, frame, landmarks, metrics=None):
        """Visualize posture analysis on frame (for debugging/display)"""
        if landmarks:
            # Draw pose landmarks
            self.mp_drawing.draw_landmarks(
                frame,
                landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
        
        if metrics:
            # Add text overlay with posture metrics
            y_offset = 30
            cv2.putText(frame, "Posture Analysis", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            for i, (metric, value) in enumerate(metrics.items()):
                if metric not in ['frame_count', 'frame_progress', 'posture_type']:
                    y_offset += 25
                    cv2.putText(frame, f"{metric}: {value:.1f}", (10, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame


# Main function for backward compatibility
def get_body_posture_report(video_path, sample_rate=5):
    """
    Main function to analyze body posture from video.
    Returns comprehensive posture analysis report.
    """
    analyzer = BodyPostureAnalyzer()
    return analyzer.analyze_video_posture(video_path, sample_rate)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        sample_rate = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        result = get_body_posture_report(video_path, sample_rate)
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({
            "error": "No video path provided",
            "usage": "python body_posture_analysis.py <video_file_path> [sample_rate]"
        }, indent=2))