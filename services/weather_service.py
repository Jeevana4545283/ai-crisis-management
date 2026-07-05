import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def _advanced_disaster_prediction(self, temp, humidity, wind, description, month, hour):
        risk_score = 0
        alerts = []

        if temp >= 45:
            risk_score += 3
            alerts.append("🔥 Extreme Heatwave Risk")
        elif temp >= 38:
            risk_score += 2
            alerts.append("🔥 High Heat Risk")

        if humidity >= 90:
            risk_score += 3
            alerts.append("🌊 Severe Flood Risk")
        elif humidity >= 75:
            risk_score += 2
            alerts.append("🌧 Heavy Rain Possibility")

        if wind >= 20:
            risk_score += 3
            alerts.append("🌪 Cyclone / Storm Risk")
        elif wind >= 12:
            risk_score += 2
            alerts.append("💨 Strong Winds Warning")

        desc = description.lower() if description else ""

        if "thunderstorm" in desc:
            risk_score += 3
            alerts.append("⚡ Thunderstorm Danger")

        if "rain" in desc:
            risk_score += 2
            alerts.append("🌧 Active Rainfall")

        if "clear" in desc and temp > 40:
            risk_score += 2
            alerts.append("🔥 Dry Heat Fire Risk")

        if "fog" in desc:
            alerts.append("🌫 Low Visibility Alert")

        if month in [6,7,8,9] and humidity > 80:
            risk_score += 2
            alerts.append("🌊 Monsoon Flood Risk")

        if month in [3,4,5] and temp > 40:
            risk_score += 2
            alerts.append("🔥 Summer Heatwave")

        if month in [10,11] and wind > 15:
            risk_score += 2
            alerts.append("🌪 Cyclone Season Alert")

        if 12 <= hour <= 16 and temp > 40:
            alerts.append("☀️ Peak Heat Hours Danger")

        if 0 <= hour <= 5 and humidity > 90:
            alerts.append("🌫 Night Fog / Moisture Risk")

        if risk_score >= 8:
            final = "🚨 EXTREME DISASTER RISK"
        elif risk_score >= 5:
            final = "⚠️ HIGH DISASTER RISK"
        elif risk_score >= 3:
            final = "🟡 MODERATE RISK"
        else:
            final = "🟢 LOW RISK"

        return final, alerts

    def get_weather_and_risk(self, city):
        if not self.api_key:
            logger.error("OpenWeatherMap API key is missing.")
            return {"error": "Weather service is not configured."}, 500

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
            response = requests.get(url)
            res = response.json()

            if response.status_code != 200:
                logger.warning(f"Weather API error for city {city}: {res.get('message')}")
                return {"error": res.get("message", "City not found")}, response.status_code

            temp = res["main"]["temp"]
            humidity = res["main"]["humidity"]
            wind = res["wind"]["speed"]
            description = res["weather"][0]["description"]

            now = datetime.now()
            
            final_risk, alerts = self._advanced_disaster_prediction(
                temp, humidity, wind, description, now.month, now.hour
            )

            return {
                "city": res["name"],
                "temp": temp,
                "humidity": humidity,
                "wind": wind,
                "description": description,
                "risk": final_risk,
                "alerts": alerts
            }, 200

        except Exception as e:
            logger.error(f"Exception in weather service: {e}")
            return {"error": "Failed to fetch weather data"}, 500
