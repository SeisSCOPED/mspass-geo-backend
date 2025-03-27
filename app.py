import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
mongo_uri = f"mongodb://mspasspod:{MONGO_PASSWORD}@mspasspod.pods.tacc.tapis.io:443/?ssl=true"
dbclient = MongoClient(mongo_uri)
db = dbclient.get_database('scoped2024')
collection = db['source']

def get_coordinates_in_range(lon_range, lat_range, collection):
    min_lon, max_lon = lon_range
    min_lat, max_lat = lat_range

    results = collection.find({
        'lon': {'$gte': min_lon, '$lte': max_lon},
        'lat': {'$gte': min_lat, '$lte': max_lat}
    })

    return [(doc['lon'], doc['lat']) for doc in results]

@app.route('/api/coordinates/', methods=['POST'])
def get_coordinates():
    try:
        data = request.get_json()
        lon_range = tuple(data['lon_range'])
        lat_range = tuple(data['lat_range'])

        coords = get_coordinates_in_range(lon_range, lat_range, collection)

        response = jsonify({'coordinates': coords})
        return response

    except Exception as e:
        response = jsonify({'error': str(e)})
        return response, 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
