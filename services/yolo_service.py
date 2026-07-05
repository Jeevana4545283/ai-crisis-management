import os
import cv2
import logging
import yt_dlp
import time

logger = logging.getLogger(__name__)

# Make ultralytics import optional for safety
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics YOLO is not installed. YOLO features will not work.")

class YoloService:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        self.load_model()
        
    def load_model(self):
        if not YOLO_AVAILABLE:
            logger.error("Cannot load model: ultralytics is not installed.")
            return False
            
        if not os.path.exists(self.model_path):
            logger.warning(f"YOLO model not found at {self.model_path}. Video streaming will be disabled.")
            return False
            
        try:
            logger.info(f"Loading YOLO model from {self.model_path}...")
            self.model = YOLO(self.model_path)
            self.is_loaded = True
            logger.info("YOLO model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.is_loaded = False
            return False

    def generate_frames(self, source_url, is_youtube=False):
        if not self.is_loaded or self.model is None:
            logger.error("Cannot stream: YOLO model is missing.")
            yield b""
            return
            
        stream_url = source_url
        if is_youtube:
            try:
                # Get direct video stream URL
                ydl_opts = {'format': 'best', 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(source_url, download=False)
                    stream_url = info['url']
            except Exception as e:
                logger.error(f"Failed to extract YouTube URL: {e}")
                yield b""
                return

        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            logger.error(f"Cannot open video source: {source_url}")
            yield b""
            return
            
        logger.info(f"Started YOLO stream for source: {source_url}")
        
        target_fps = 15  # Limit FPS to avoid CPU overload
        frame_time = 1.0 / target_fps
        
        while True:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                logger.info("Stream ended or failed to read frame.")
                break
                
            # Resize frame for faster inference and lower bandwidth
            h, w = frame.shape[:2]
            scale = 640 / max(h, w)
            frame_resized = cv2.resize(frame, (int(w*scale), int(h*scale)))
            
            # Run inference
            try:
                results = self.model.predict(frame_resized, conf=0.3, verbose=False)
                annotated = results[0].plot()
                
                # Encode as JPEG
                ret, buffer = cv2.imencode('.jpg', annotated)
                if not ret:
                    continue
                    
                frame_bytes = buffer.tobytes()
                
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                       
            except Exception as e:
                logger.error(f"Inference error during stream: {e}")
                break
                
            # Sleep if we processed the frame faster than the target FPS
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
                
        cap.release()
        logger.info(f"Stopped YOLO stream for source: {source_url}")
