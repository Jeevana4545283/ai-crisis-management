import os
import logging
from dotenv import load_dotenv

from flask import Flask, Response, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

from config import DEMO_OFFICERS, AREAS_DATA
from services.ml_service import DisasterMLService
from services.yolo_service import YoloService
from services.weather_service import WeatherService
from services.notification_service import NotificationService

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
secret_key = os.environ.get("FLASK_SECRET_KEY")
if not secret_key:
    raise RuntimeError("CRITICAL ERROR: FLASK_SECRET_KEY is missing from environment variables.")
app.secret_key = secret_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Services globally
ml_service = DisasterMLService(model_path=os.path.join(BASE_DIR, "disaster_model_best.h5"))
ml_service.load_model()

yolo_service = YoloService(model_path=os.path.join(BASE_DIR, "yolov8n.pt"))

weather_service = WeatherService(api_key=os.environ.get("OPENWEATHER_API_KEY"))

notification_service = NotificationService(
    api_key=os.environ.get("VONAGE_API_KEY"),
    api_secret=os.environ.get("VONAGE_API_SECRET")
)

def login_required():
    return "officer_id" in session

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        officer_id = request.form.get("officer_id")
        password = request.form.get("password")

        # SECURITY NOTE: This application currently uses mock credentials defined in config.py
        # For production, this MUST be replaced with a secure database lookup and password hashing (e.g., bcrypt).
        for demo_id, _, city, demo_pass in DEMO_OFFICERS:
            if officer_id == demo_id and password == demo_pass:
                session["officer_id"] = officer_id
                area = city.lower().replace(" ", "-")
                logger.info(f"Officer {officer_id} logged in successfully.")
                return redirect(url_for("dashboard", area=area))

        logger.warning(f"Failed login attempt for officer_id: {officer_id}")
        return render_template("index.html", error="Invalid credentials")
    return render_template("index.html")

@app.route("/dashboard/<area>")
def dashboard(area):
    if not login_required():
        return redirect(url_for("index"))

    area_key = area.lower().replace(" ", "-")
    data = AREAS_DATA.get(area_key)

    if not data:
        logger.warning(f"Dashboard requested for unknown area: {area}")
        return redirect(url_for("dashboard", area="vijayawada"))

    return render_template(
        "dashboard.html",
        dynamic_data=data,
        current_area=area_key,
        officer_id=session["officer_id"],
    )

@app.route('/profile')
def view_profile():
    return render_template('profile.html')

@app.route("/run_yolo", methods=["POST"])
def run_yolo():
    data = request.get_json()
    yt_link = data.get("youtube_link")
    if yt_link:
        logger.info(f"YOLO stream requested for: {yt_link}")
        stream_url = url_for('video_feed', youtube_url=yt_link)
        return jsonify({"status": "started", "stream_url": stream_url})
    return jsonify({"status": "failed", "message": "No YouTube link provided"}), 400

@app.route("/api/video_feed")
def video_feed():
    youtube_url = request.args.get('youtube_url')
    if not youtube_url:
        return jsonify({"error": "No source provided"}), 400
        
    if not yolo_service.is_loaded:
        return jsonify({"error": "YOLO model not loaded"}), 503
        
    return Response(yolo_service.generate_frames(youtube_url, is_youtube=True),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/get_weather", methods=["POST"])
def get_weather():
    data = request.get_json()
    city = data.get("city")
    if not city:
        return jsonify({"error": "City not provided"}), 400
        
    result, status = weather_service.get_weather_and_risk(city)
    return jsonify(result), status

@app.route("/send_sms", methods=["POST"])
def send_sms():
    data = request.get_json()
    city = data.get("city")
    team = data.get("team")
    
    if not city or not team:
        return jsonify({"error": "Missing city or team parameters"}), 400
        
    result, status = notification_service.send_crisis_alert(city, team)
    return jsonify(result), status

@app.route("/api/predict_disaster", methods=["POST"])
def api_predict_disaster():
    if "image" not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
        
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No image selected for uploading"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        uploads_dir = os.path.join(BASE_DIR, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        filepath = os.path.join(uploads_dir, filename)
        try:
            file.save(filepath)
            result, status_code = ml_service.predict(filepath)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return jsonify(result), status_code
                
        except Exception as e:
            logger.error(f"Failed during disaster prediction API: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": "Internal Server Error"}), 500

@app.route("/<area>/road_inspections")
def road_inspections(area):
    if not login_required(): return redirect(url_for("index"))
    return render_template("road_inspections.html", current_area=area)

@app.route("/<area>/work-orders")
def work_orders(area):
    if not login_required(): return redirect(url_for("index"))
    return render_template("work_orders.html", current_area=area)

@app.route("/<area>/contractors")
def contractors(area):
    if not login_required(): return redirect(url_for("index"))
    return render_template("contractors.html", current_area=area)

@app.route("/<area>/budget")
def budget(area):
    if not login_required(): return redirect(url_for("index"))
    return render_template("budget.html", current_area=area)

@app.route('/crisis_inspection')
def crisis_inspection():
    return render_template("crisis_inspection.html")

@app.route("/<area>/complaints")
def complaints(area):
    if not login_required(): return redirect(url_for("index"))
    return render_template("complaints.html", current_area=area)

@app.route("/<area>/reports")
def reports(area):
    if not login_required(): return redirect(url_for("index"))
    return render_template("reports.html", current_area=area)

@app.route('/assign')
def assign():
    return render_template("assign.html")

@app.route('/map')
def map():
    return render_template("map.html")

@app.route("/logout")
def logout():
    session.clear()
    logger.info("User logged out.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)