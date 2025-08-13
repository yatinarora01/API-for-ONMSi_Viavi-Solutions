from flask import Flask, jsonify

import requests

from flask_cors import CORS


app = Flask(__name__)
CORS(app)
@app.route('/combined', methods=['GET'])
def get_combined_data():
    weather = requests.get("https://api.open-meteo.com/v1/forecast?latitude=28.61&longitude=77.23&current_weather=true").json()
    github = requests.get("https://api.github.com/users/octocat").json()
    yatingithub = requests.get("https://api.github.com/users/yatinarora01").json()
    air_quality = requests.get("https://api.waqi.info/feed/delhi/?token=demo").json()

    combined = {
        "weather": weather["current_weather"],
        "github": {
            "username": github["login"],
            "followers": github["followers"],
            "repos": github["public_repos"]
        },
        "yatingithub": {
            "username": yatingithub["login"],
            "followers": yatingithub["followers"],
            "repos": yatingithub["public_repos"]
        },
        "air_quality": {
            "aqi": air_quality["data"]["aqi"],
            "location": air_quality["data"]["city"]["name"],
            "dominant_pollutant": air_quality["data"]["dominentpol"]
        }
    }

    return jsonify(combined)


if __name__ == '__main__':
    app.run(debug = True)

    
