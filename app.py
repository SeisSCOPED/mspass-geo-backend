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
earthquake_collection = db['source']
station_collection = db['source'] # TODO

def shift_longitude_preserve_decimal(lon, shift):
    """
    Shift longitude by an integer (e.g., ±360), preserving the original decimal precision.
    Example: lon = 170.3456, shift = -360 -> returns -189.6544
    """
    int_part = int(lon)
    dec_part = lon - int_part
    shifted = int_part + shift + dec_part
    # Preserve decimal digits from original
    lon_str = str(lon)
    if '.' in lon_str:
        decimal_places = len(lon_str.split('.')[1])
    else:
        decimal_places = 0
    return round(shifted, decimal_places)

def normalize_longitude(lon):
    """Normalize longitude to [-180, 180], preserving exact decimal format."""
    if lon == 180 or lon == -180:
        return lon

    int_part = int(lon)
    dec_part = lon - int_part
    result = ((int_part + 180) % 360) - 180 + dec_part

    # Preserve decimal places
    lon_str = str(lon)
    if '.' in lon_str:
        decimal_places = len(lon_str.split('.')[1])
    else:
        decimal_places = 0

    return round(result, decimal_places)

def wrap_longitude_query(min_lon, max_lon, lat_range, collection):
    min_lat, max_lat = lat_range

    norm_min = normalize_longitude(min_lon)
    norm_max = normalize_longitude(max_lon)

    if norm_min <= norm_max:
        cursor = collection.find({
            'lon': {'$gte': norm_min, '$lte': norm_max},
            'lat': {'$gte': min_lat, '$lte': max_lat}
        })
    else:
        # Wrapping across the -180/180 boundary
        cursor1 = collection.find({
            'lon': {'$gte': norm_min},
            'lat': {'$gte': min_lat, '$lte': max_lat}
        })
        cursor2 = collection.find({
            'lon': {'$lte': norm_max},
            'lat': {'$gte': min_lat, '$lte': max_lat}
        })
        cursor = list(cursor1) + list(cursor2)

    return list(cursor)

def wrap_lon_to_query_range(lon_in_db, query_min, query_max):
    """Wrap longitude into the user-specified query range, preserving decimal precision."""
    result = lon_in_db
    while result < query_min:
        result = shift_longitude_preserve_decimal(result, 360)
    while result > query_max:
        result = shift_longitude_preserve_decimal(result, -360)
    return result

def get_coordinates(collection):
    try:
        data = request.get_json()
        lon_range = tuple(data['lon_range'])  # Possibly out of [-180, 180]
        lat_range = tuple(data['lat_range'])

        docs = wrap_longitude_query(lon_range[0], lon_range[1], lat_range, collection)

        original_coords = []
        normalized_coords = []
        all_coords = []

        for doc in docs:
            lon_db = doc['lon']
            lat_db = doc['lat']

            # Original coordinates: project into user's longitude range
            lon_original = wrap_lon_to_query_range(lon_db, lon_range[0], lon_range[1])
            original_coords.append((lon_original, lat_db))

            # Normalized coordinates: wrap to [-180, 180]
            normalized_coords.append((normalize_longitude(lon_db), lat_db))

            # All copies: lon - 360, lon, lon + 360
            all_coords.extend([
                (shift_longitude_preserve_decimal(lon_db, -360), lat_db),
                (lon_db, lat_db),  # already in DB precision
                (shift_longitude_preserve_decimal(lon_db, 360), lat_db)
            ])

        response = jsonify({
            'coordinates': original_coords,
            'normalized_coordinates': normalized_coords,
            'all_coordinates': all_coords
        })
        return response

    except Exception as e:
        response = jsonify({'error': str(e)})
        return response, 400

@app.route('/api/earthquakes/', methods=['POST'])
def get_earthquake_coordinates():
    return get_coordinates(earthquake_collection)

@app.route('/api/stations/', methods=['POST'])
def get_station_coordinates():
    return get_coordinates(station_collection)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
