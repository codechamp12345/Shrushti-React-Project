# facial_expression_analysis.py
import cv2
import numpy as np
import os
import sys
import json
from datetime import datetime
from collections import defaultdict, Counter
import math
import warnings
warnings.filterwarnings('ignore')

import sys
import os

# Fix for Windows Unicode
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Try to import dlib for better face detection
try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False
    print("⚠️ dlib not available, using OpenCV face detection")

class FacialExpressionAnalyzer:
    def __init__(self):
        """Initialize facial expression analyzer"""
        self.emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
        
        # Load face detector
        self.face_detector = self.load_face_detector()
        
        # Load emotion recognition model
        self.emotion_model = self.load_emotion_model()
        
        # Facial action unit mappings (simplified)
        self.au_mappings = {
            'happy': ['AU12', 'AU6'],      # Smile and cheek raise
            'sad': ['AU4', 'AU15'],        # Brow lower and lip corner depress
            'angry': ['AU4', 'AU7', 'AU23'],  # Brow lower, lid tight, lip tighten
            'surprise': ['AU1', 'AU2', 'AU5', 'AU26'],  # Brow raise, eye widen, jaw drop
            'fear': ['AU1', 'AU2', 'AU4', 'AU5', 'AU20', 'AU26'],  # Fear complex
            'disgust': ['AU9', 'AU10', 'AU17'],  # Nose wrinkle, upper lip raise
            'neutral': []  # No significant AUs
        }
        
        # Expression thresholds
        self.thresholds = {
            'engagement_min': 0.3,      # Minimum expression intensity for engagement
            'neutral_max': 0.7,         # Maximum neutral for engagement
            'smile_optimal': 0.4,       # Optimal smile intensity
            'variety_min': 3,           # Minimum different expressions
            'consistency_threshold': 0.5  # Consistency threshold
        }
        
        # Expression importance weights
        self.weights = {
            'engagement': 0.30,
            'positivity': 0.25,
            'expressiveness': 0.20,
            'consistency': 0.15,
            'variety': 0.10
        }
        
        print("✅ Facial Expression Analyzer initialized")
    
    def load_face_detector(self):
        """Load face detector (dlib if available, else OpenCV)"""
        if DLIB_AVAILABLE:
            try:
                # Try to load dlib's HOG face detector
                detector = dlib.get_frontal_face_detector()
                print("✅ dlib face detector loaded")
                return ('dlib', detector)
            except Exception as e:
                print(f"⚠️ dlib failed: {e}, falling back to OpenCV")
        
        # Fallback to OpenCV
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if not os.path.exists(cascade_path):
                # Try alternative path
                cascade_path = "haarcascade_frontalface_default.xml"
                if not os.path.exists(cascade_path):
                    raise FileNotFoundError("Haar cascade file not found")
            
            detector = cv2.CascadeClassifier(cascade_path)
            print("✅ OpenCV face detector loaded")
            return ('opencv', detector)
        except Exception as e:
            print(f"❌ Failed to load face detector: {e}")
            return None
    
    def load_emotion_model(self):
        """Load emotion recognition model"""
        # Try multiple model paths
        model_paths = [
            "emotion-ferplus-8.onnx",
            "emotion_ferplus.onnx",
            "models/emotion-ferplus-8.onnx",
            os.path.join(os.path.dirname(__file__), "emotion-ferplus-8.onnx")
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if model_path:
            try:
                net = cv2.dnn.readNetFromONNX(model_path)
                print(f"✅ Emotion model loaded from {model_path}")
                return net
            except Exception as e:
                print(f"❌ Failed to load ONNX model: {e}")
        
        print("⚠️ Using rule-based expression analysis")
        return None
    
    def detect_faces(self, frame):
        """Detect faces in frame using available detector"""
        if not self.face_detector:
            return []
        
        detector_type, detector = self.face_detector
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if detector_type == 'dlib':
            # dlib detection
            faces = detector(gray, 1)  # 1 means upsample once
            face_rects = []
            for face in faces:
                x, y = face.left(), face.top()
                w, h = face.right() - x, face.bottom() - y
                face_rects.append((x, y, w, h))
            return face_rects
        else:
            # OpenCV detection
            faces = detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            return [(x, y, w, h) for (x, y, w, h) in faces]
    
    def preprocess_face(self, face_img):
        """Preprocess face image for emotion recognition"""
        # Resize to model input size
        target_size = (64, 64)
        resized = cv2.resize(face_img, target_size)
        
        # Convert to grayscale
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # Normalize
        normalized = gray.astype(np.float32) / 255.0
        
        # Standardize (zero mean, unit variance)
        mean = np.mean(normalized)
        std = np.std(normalized)
        standardized = (normalized - mean) / (std + 1e-6)
        
        return standardized
    
    def predict_emotion(self, face_img):
        """Predict emotion from face image"""
        if self.emotion_model is None:
            # Rule-based fallback
            return self.rule_based_emotion(face_img)
        
        try:
            # Preprocess face
            processed = self.preprocess_face(face_img)
            
            # Prepare blob for DNN
            blob = cv2.dnn.blobFromImage(processed.reshape(64, 64, 1), 
                                         scalefactor=1.0, 
                                         size=(64, 64))
            
            # Set input and forward pass
            self.emotion_model.setInput(blob)
            predictions = self.emotion_model.forward()[0]
            
            # Convert to dictionary
            emotion_dict = dict(zip(self.emotion_labels, predictions.flatten()))
            
            # Add confidence and dominant emotion
            dominant = max(emotion_dict.items(), key=lambda x: x[1])
            emotion_dict['dominant'] = dominant[0]
            emotion_dict['confidence'] = float(dominant[1])
            
            return emotion_dict
            
        except Exception as e:
            print(f"❌ Emotion prediction failed: {e}")
            return self.rule_based_emotion(face_img)
    
    def rule_based_emotion(self, face_img):
        """Rule-based emotion estimation when model is not available"""
        # Simple brightness-based estimation (placeholder)
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray) / 255.0
        
        # Mock emotions based on simple rules
        base_emotions = {
            'angry': 0.1,
            'disgust': 0.1,
            'fear': 0.1,
            'happy': min(0.3, brightness * 0.5),
            'sad': max(0.1, (1 - brightness) * 0.3),
            'surprise': 0.1,
            'neutral': max(0.3, 1 - brightness * 0.5)
        }
        
        # Normalize
        total = sum(base_emotions.values())
        normalized = {k: v/total for k, v in base_emotions.items()}
        
        dominant = max(normalized.items(), key=lambda x: x[1])
        normalized['dominant'] = dominant[0]
        normalized['confidence'] = float(dominant[1])
        
        return normalized
    
    def calculate_expression_metrics(self, emotion_dict):
        """Calculate expression metrics from emotion predictions"""
        metrics = {}
        
        # Engagement (1 - neutral probability)
        metrics['engagement'] = 1.0 - emotion_dict.get('neutral', 0.0)
        
        # Positivity (happy + surprise - angry - sad - fear - disgust)
        positive = emotion_dict.get('happy', 0.0) + emotion_dict.get('surprise', 0.0) * 0.5
        negative = (emotion_dict.get('angry', 0.0) + 
                   emotion_dict.get('sad', 0.0) + 
                   emotion_dict.get('fear', 0.0) + 
                   emotion_dict.get('disgust', 0.0))
        metrics['positivity'] = max(0.0, positive - negative)
        
        # Expressiveness (variance from neutral)
        non_neutral = {k: v for k, v in emotion_dict.items() if k != 'neutral' and k in self.emotion_labels}
        if non_neutral:
            metrics['expressiveness'] = max(non_neutral.values())
        else:
            metrics['expressiveness'] = 0.0
        
        # Smile intensity (specific for interviews)
        metrics['smile_intensity'] = emotion_dict.get('happy', 0.0)
        
        # Seriousness (for professional context)
        serious_emotions = ['neutral', 'sad', 'angry', 'disgust']
        metrics['seriousness'] = sum(emotion_dict.get(e, 0.0) for e in serious_emotions)
        
        return metrics
    
    def analyze_video_expressions(self, video_path, sample_rate=10):
        """Analyze facial expressions from video"""
        print(f"🎭 Starting facial expression analysis: {video_path}")
        
        if not os.path.exists(video_path):
            return self.get_default_result(f"Video not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return self.get_default_result(f"Cannot open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"   📊 Video: {total_frames} frames, {fps:.1f} FPS, {duration:.1f}s")
        
        # Storage for analysis results
        all_emotions = []
        all_metrics = []
        dominant_emotions = []
        frame_results = []
        
        frame_count = 0
        analyzed_count = 0
        face_detected_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Sample frames for performance
            if frame_count % sample_rate == 0:
                # Detect faces
                faces = self.detect_faces(frame)
                
                if faces:
                    face_detected_frames += 1
                    # Use the largest face (assuming main subject)
                    x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
                    face_img = frame[y:y+h, x:x+w]
                    
                    if face_img.size > 0:
                        # Predict emotion
                        emotion_dict = self.predict_emotion(face_img)
                        all_emotions.append(emotion_dict)
                        
                        # Calculate metrics
                        metrics = self.calculate_expression_metrics(emotion_dict)
                        all_metrics.append(metrics)
                        
                        # Track dominant emotion
                        dominant = emotion_dict.get('dominant', 'neutral')
                        dominant_emotions.append(dominant)
                        
                        # Store frame result
                        frame_results.append({
                            'frame': frame_count,
                            'emotion': emotion_dict,
                            'metrics': metrics,
                            'face_rect': (x, y, w, h)
                        })
                        
                        analyzed_count += 1
            
            frame_count += 1
            
            # Progress indicator
            if frame_count % 1000 == 0:
                print(f"   📈 Processed {frame_count}/{total_frames} frames...")
        
        cap.release()
        
        if analyzed_count == 0:
            return self.get_default_result("No faces detected in video")
        
        print(f"✅ Analyzed {analyzed_count} frames with face detection")
        
        # Calculate overall statistics
        results = self.calculate_overall_statistics(
            all_emotions, 
            all_metrics, 
            dominant_emotions,
            analyzed_count,
            duration
        )
        
        return results
    
    def calculate_overall_statistics(self, all_emotions, all_metrics, dominant_emotions, analyzed_count, duration):
        """Calculate overall statistics from frame analysis"""
        
        # Emotion frequency
        emotion_counter = Counter(dominant_emotions)
        emotion_frequencies = {emotion: count/analyzed_count for emotion, count in emotion_counter.items()}
        
        # Average emotion probabilities
        avg_emotions = {}
        for emotion in self.emotion_labels:
            avg_prob = np.mean([e.get(emotion, 0.0) for e in all_emotions])
            avg_emotions[emotion] = float(avg_prob)
        
        # Average metrics
        avg_metrics = {}
        for metric_name in all_metrics[0].keys():
            avg_value = np.mean([m[metric_name] for m in all_metrics])
            avg_metrics[metric_name] = float(avg_value)
        
        # Engagement rate (frames with engagement > threshold)
        engagement_threshold = self.thresholds['engagement_min']
        engaged_frames = sum(1 for m in all_metrics if m['engagement'] > engagement_threshold)
        engagement_rate = engaged_frames / analyzed_count
        
        # Expression variety
        unique_expressions = len(set(dominant_emotions))
        expression_variety = min(1.0, unique_expressions / len(self.emotion_labels))
        
        # Consistency (how stable are expressions)
        if len(dominant_emotions) > 1:
            changes = sum(1 for i in range(1, len(dominant_emotions)) 
                         if dominant_emotions[i] != dominant_emotions[i-1])
            consistency = 1.0 - (changes / (len(dominant_emotions) - 1))
        else:
            consistency = 1.0
        
        # Calculate scores
        scores = self.calculate_scores(avg_metrics, engagement_rate, expression_variety, consistency)
        
        # Generate verdict
        verdict, verdict_detail = self.generate_verdict(scores['overall'])
        
        # Generate recommendations
        recommendations = self.generate_recommendations(avg_emotions, avg_metrics, scores)
        
        # Compile results
        results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'overall_assessment': {
                'score_100': scores['overall'],
                'score_10': round(scores['overall'] / 10, 1),
                'verdict': verdict,
                'verdict_detail': verdict_detail,
                'dominant_emotion': emotion_counter.most_common(1)[0][0] if emotion_counter else 'neutral',
                'engagement_rate': round(engagement_rate * 100, 1),
                'expression_variety': round(expression_variety * 100, 1),
                'consistency_score': round(consistency * 100, 1)
            },
            'emotion_distribution': {
                'average_probabilities': {k: round(v, 3) for k, v in avg_emotions.items()},
                'frequency_distribution': {k: round(v, 3) for k, v in emotion_frequencies.items()},
                'most_common_expression': emotion_counter.most_common(3) if emotion_counter else []
            },
            'expression_metrics': {
                'engagement': round(avg_metrics.get('engagement', 0) * 100, 1),
                'positivity': round(avg_metrics.get('positivity', 0) * 100, 1),
                'expressiveness': round(avg_metrics.get('expressiveness', 0) * 100, 1),
                'smile_intensity': round(avg_metrics.get('smile_intensity', 0) * 100, 1),
                'seriousness': round(avg_metrics.get('seriousness', 0) * 100, 1)
            },
            'detailed_scores': scores,
            'statistical_summary': {
                'analyzed_frames': analyzed_count,
                'face_detected_frames': len(all_emotions),
                'engagement_threshold': engagement_threshold,
                'neutral_dominance': round(emotion_frequencies.get('neutral', 0) * 100, 1)
            },
            'recommendations': recommendations,
            'model_info': {
                'face_detector': self.face_detector[0] if self.face_detector else 'none',
                'emotion_model': 'ONNX' if self.emotion_model else 'rule-based',
                'analysis_version': '2.0'
            }
        }
        
        return results
    
    def calculate_scores(self, avg_metrics, engagement_rate, variety, consistency):
        """Calculate detailed scores for different aspects"""
        
        # Engagement Score (0-100)
        engagement_score = min(100, engagement_rate * 120)
        
        # Positivity Score (0-100)
        positivity = avg_metrics.get('positivity', 0)
        positivity_score = min(100, positivity * 200)
        
        # Expressiveness Score (0-100)
        expressiveness = avg_metrics.get('expressiveness', 0)
        expressiveness_score = min(100, expressiveness * 150)
        
        # Consistency Score (0-100)
        consistency_score = consistency * 100
        
        # Variety Score (0-100)
        variety_score = variety * 100
        
        # Overall Score (weighted)
        overall_score = (
            engagement_score * self.weights['engagement'] +
            positivity_score * self.weights['positivity'] +
            expressiveness_score * self.weights['expressiveness'] +
            consistency_score * self.weights['consistency'] +
            variety_score * self.weights['variety']
        )
        
        return {
            'engagement': round(engagement_score, 1),
            'positivity': round(positivity_score, 1),
            'expressiveness': round(expressiveness_score, 1),
            'consistency': round(consistency_score, 1),
            'variety': round(variety_score, 1),
            'overall': round(overall_score, 1)
        }
    
    def generate_verdict(self, overall_score):
        """Generate verdict based on overall score"""
        if overall_score >= 90:
            return "Exceptional", "Highly expressive, engaging, and professional"
        elif overall_score >= 80:
            return "Excellent", "Very good expressiveness and engagement"
        elif overall_score >= 70:
            return "Good", "Appropriate expressions with good engagement"
        elif overall_score >= 60:
            return "Acceptable", "Basic expressiveness, room for improvement"
        elif overall_score >= 50:
            return "Needs Improvement", "Limited expression variety"
        else:
            return "Poor", "Minimal facial expression engagement"
    
    def generate_recommendations(self, avg_emotions, avg_metrics, scores):
        """Generate personalized recommendations"""
        recommendations = []
        
        # Check for over-neutral expression
        if avg_emotions.get('neutral', 0) > 0.7:
            recommendations.append("Increase facial expressiveness - try to show more emotion")
        
        # Check for low engagement
        if scores['engagement'] < 60:
            recommendations.append("Work on engaging facial expressions - focus on the conversation")
        
        # Check for low positivity
        if scores['positivity'] < 60:
            recommendations.append("Incorporate more positive expressions - smile naturally when appropriate")
        
        # Check for low smile intensity
        if avg_metrics.get('smile_intensity', 0) < 0.3:
            recommendations.append("Use genuine smiles to create positive impression")
        
        # Check for too much seriousness
        if avg_metrics.get('seriousness', 0) > 0.7:
            recommendations.append("Balance seriousness with appropriate positive expressions")
        
        # Check for expression variety
        if scores['variety'] < 50:
            recommendations.append("Vary facial expressions more - avoid monotone face")
        
        # Check for over-expressiveness (for professional context)
        if avg_metrics.get('expressiveness', 0) > 0.8:
            recommendations.append("Maintain professional composure - slightly reduce exaggerated expressions")
        
        # Add general positive reinforcement if good
        if scores['overall'] >= 80:
            recommendations.insert(0, "Excellent facial expression control - maintain this balance")
        elif scores['overall'] >= 70:
            recommendations.insert(0, "Good expression management - continue practicing")
        
        # Ensure we have recommendations
        if not recommendations:
            recommendations = [
                "Maintain natural expressions during conversation",
                "Practice expressing confidence through facial cues"
            ]
        
        return recommendations[:5]  # Top 5 recommendations
    
    def get_default_result(self, error_message=""):
        """Return default result when analysis fails"""
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'overall_assessment': {
                'score_100': 0,
                'score_10': 0,
                'verdict': 'Analysis Failed',
                'verdict_detail': error_message or 'Could not analyze facial expressions',
                'dominant_emotion': 'neutral',
                'engagement_rate': 0,
                'expression_variety': 0,
                'consistency_score': 0
            },
            'emotion_distribution': {
                'average_probabilities': {e: 0 for e in self.emotion_labels},
                'frequency_distribution': {},
                'most_common_expression': []
            },
            'expression_metrics': {
                'engagement': 0,
                'positivity': 0,
                'expressiveness': 0,
                'smile_intensity': 0,
                'seriousness': 0
            },
            'detailed_scores': {
                'engagement': 0,
                'positivity': 0,
                'expressiveness': 0,
                'consistency': 0,
                'variety': 0,
                'overall': 0
            },
            'statistical_summary': {
                'analyzed_frames': 0,
                'face_detected_frames': 0,
                'engagement_threshold': self.thresholds['engagement_min'],
                'neutral_dominance': 0
            },
            'recommendations': [
                "Ensure face is clearly visible in video",
                "Check lighting conditions for better detection",
                "Maintain consistent distance from camera"
            ],
            'model_info': {
                'face_detector': 'none',
                'emotion_model': 'none',
                'analysis_version': '2.0'
            }
        }
    
    def visualize_analysis(self, frame, emotion_dict, metrics, face_rect):
        """Visualize analysis on frame (for debugging/display)"""
        x, y, w, h = face_rect
        
        # Draw face rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Display dominant emotion
        dominant = emotion_dict.get('dominant', 'neutral')
        confidence = emotion_dict.get('confidence', 0)
        
        emotion_text = f"{dominant}: {confidence:.2f}"
        cv2.putText(frame, emotion_text, (x, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display metrics
        y_offset = y + h + 20
        for i, (metric_name, value) in enumerate(metrics.items()):
            metric_text = f"{metric_name}: {value:.2f}"
            cv2.putText(frame, metric_text, (x, y_offset + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame


# Main function for backward compatibility
def analyze_facial_expressions_no_tf(video_path, sample_rate=10):
    """
    Main function to analyze facial expressions from video.
    Returns comprehensive facial expression analysis report.
    """
    analyzer = FacialExpressionAnalyzer()
    return analyzer.analyze_video_expressions(video_path, sample_rate)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        sample_rate = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        print("=" * 60)
        print("FACIAL EXPRESSION ANALYSIS")
        print("=" * 60)
        
        result = analyze_facial_expressions_no_tf(video_path, sample_rate)
        
        # Pretty print summary
        print("\n" + "=" * 60)
        print("📊 ANALYSIS SUMMARY:")
        print("=" * 60)
        print(f"✅ Verdict: {result['overall_assessment']['verdict']}")
        print(f"📈 Overall Score: {result['overall_assessment']['score_10']}/10")
        print(f"🎭 Dominant Emotion: {result['overall_assessment']['dominant_emotion']}")
        print(f"😊 Engagement Rate: {result['overall_assessment']['engagement_rate']}%")
        print(f"🔄 Expression Variety: {result['overall_assessment']['expression_variety']}%")
        print("=" * 60)
        
        # Print detailed results as JSON
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({
            "error": "No video path provided",
            "usage": "python facial_expression_analysis.py <video_file_path> [sample_rate]"
        }, indent=2))