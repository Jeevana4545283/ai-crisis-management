import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

# We make tf import optional in case tensorflow is not fully installed or we want to avoid crashes
try:
    import tensorflow as tf
    from tensorflow.keras.preprocessing import image
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow is not available. ML predictions will not work.")

class DisasterMLService:
    def __init__(self, model_path="disaster_model_best.h5"):
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        
        # Default mapping - ideally this should be saved alongside the model during training (e.g. as a JSON file)
        self.class_map = {
            0: "Cyclone / Storm",
            1: "Earthquake",
            2: "Fire / Heatwave",
            3: "Flood"
        }
        
        self.img_size = (224, 224)
        
    def load_model(self):
        if not TF_AVAILABLE:
            logger.error("Cannot load model: TensorFlow is not installed.")
            return False
            
        if not os.path.exists(self.model_path):
            logger.warning(f"Disaster ML model not found at {self.model_path}. Predictions will be disabled.")
            return False
            
        try:
            logger.info(f"Loading disaster model from {self.model_path}...")
            self.model = tf.keras.models.load_model(self.model_path)
            self.is_loaded = True
            logger.info("Disaster ML model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load disaster ML model: {e}")
            self.is_loaded = False
            return False
            
    def predict(self, img_path):
        if not self.is_loaded or self.model is None:
            return {"error": "Model is not loaded or missing."}, 503
            
        try:
            img = image.load_img(img_path, target_size=self.img_size)
            img_array = image.img_to_array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            # Predict
            preds = self.model.predict(img_array)
            idx = np.argmax(preds)
            confidence = float(preds[0][idx])
            
            # If the index is out of bounds for our hardcoded map, just return the raw index
            predicted_class = self.class_map.get(idx, f"Class_{idx}")
            
            logger.info(f"Prediction successful: {predicted_class} ({confidence:.2f}) for {img_path}")
            
            return {
                "prediction": predicted_class,
                "confidence": confidence,
                "class_index": int(idx)
            }, 200
            
        except Exception as e:
            logger.error(f"Prediction error for {img_path}: {e}")
            return {"error": f"Failed to process image: {str(e)}"}, 400
