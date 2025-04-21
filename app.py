import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import requests
import json
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
mongo_uri = f"mongodb://mspasspod:{MONGO_PASSWORD}@mspasspod.pods.tacc.tapis.io:443/?ssl=true"
dbclient = MongoClient(mongo_uri)
# db = dbclient.get_database('scoped2024')
db = dbclient.get_database('mspass')
earthquake_collection = db['source']
station_collection = db['site']

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

def get_coordinates(collection, collection_name):
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

            # Optionally include magnitude if it's an earthquake collection
            extra_fields = {}
            if collection_name == 'earthquakes' and 'magnitude' in doc:
                extra_fields['magnitude'] = doc['magnitude']

            # Original coordinates: project into user's longitude range
            lon_original = wrap_lon_to_query_range(lon_db, lon_range[0], lon_range[1])
            original_coords.append({'lon': lon_original, 'lat': lat_db, **extra_fields})

            # Normalized coordinates: wrap to [-180, 180]
            normalized_coords.append({'lon': normalize_longitude(lon_db), 'lat': lat_db, **extra_fields})

            # All copies: lon - 360, lon, lon + 360
            all_coords.extend([
                {'lon': shift_longitude_preserve_decimal(lon_db, -360), 'lat': lat_db, **extra_fields},
                {'lon': lon_db, 'lat': lat_db, **extra_fields}, # already in DB precision
                {'lon': shift_longitude_preserve_decimal(lon_db, 360), 'lat': lat_db, **extra_fields}
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

def generate_station_notebook_json(station_id):
    cells = [
        # Cell 1: Install pymongo
        "!pip install pymongo",

        # Cell 2: Imports
        "from pymongo import MongoClient",

        # Cell 3: Username & Password
        "\n".join([
            '# TODO: Replace with your actual username & password',
            'USERNAME = "username"',
            'PASSWORD = "password"'
        ]),

        # Cell 4: URI
        "\n".join([
            '# TODO: Replace with your actual MongoDB URI',
            'uri = f"mongodb://{USERNAME}:{PASSWORD}@localhost:27017/"'
        ]),

        # Cell 5: Connect to database
        "\n".join([
            'dbclient = MongoClient(uri)',
            'db = dbclient.get_database("earthscope")'
        ]),

        # Cell 6: Set station ID
        f'station_id = "{station_id}"',

        # Cell 7: Count documents & find one
        "\n".join([
            'total = db.picks.count_documents({"tid": station_id})',
            'first = db.picks.find_one({"tid": station_id})',
            'print("Total picks:", total)',
            'if first:',
            '    print("First pick (via find_one):", first)',
            'else:',
            '    print("No picks found.")'
        ]),

        # Cell 8: List all picks and access first element (may be slow if large)
        "\n".join([
            '# CAUTION: This loads all picks into memory. Use with caution on large datasets.',
            'picks = list(db.picks.find({"tid": station_id}))',
            'print("Total picks:", len(picks))',
            'if picks:',
            '    print("First pick (via list):", picks[0])',
            'else:',
            '    print("No picks found.")'
        ])
    ]

    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "metadata": {},
                "source": cell.strip().splitlines(keepends=True),
                "outputs": [],
                "execution_count": None
            }
            for cell in cells
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.x"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    return notebook

@app.route('/api/earthquakes/', methods=['POST'])
def get_earthquake_coordinates():
    return get_coordinates(earthquake_collection, 'earthquakes')

@app.route('/api/stations/', methods=['POST'])
def get_station_coordinates():
    return get_coordinates(station_collection, 'stations')

@app.route('/api/generate-station-notebook/', methods=['POST'])
def generate_and_send_station_notebook():
    data = request.get_json()
    station_id = data.get('station_id')
    notebook_server_url = data.get('notebook_server_url')

    if not station_id or not notebook_server_url:
        return jsonify({'error': 'Missing station_id or notebook_server_url'}), 400

    notebook_data = generate_station_notebook_json(station_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    notebook_name = f"/pods-jupyter/scoped/file{timestamp}.ipynb"

    try:
        # Upload notebook via Jupyter's REST API (PUT method for Contents API)
        response = requests.put(
            f"{notebook_server_url}/api/contents/{notebook_name}",
            headers = {
                "Content-Type": "application/json"
            },
            data = json.dumps({
                "type": "notebook",
                "format": "json",
                "content": notebook_data
            })
        )

        if response.status_code in [200, 201]:
            response = jsonify({
                'message': f'Notebook {notebook_name} uploaded successfully.',
                'filename': notebook_name
            })
            return response
        else:
            response = jsonify({
                'error': 'Failed to upload notebook',
                'status_code': response.status_code,
                'details': response.text
            })
            return response, 500

    except Exception as e:
        response = jsonify({'error': str(e)})
        return response, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
