# MsPASS GEO Backend

This repository contains a Flask-based API service for interacting with MongoDB earthquake and station data, as well as generating and uploading Jupyter notebooks for station analysis.

## Features

- Query earthquake and station coordinates from MongoDB
- Normalize and wrap longitude ranges across the -180/180 boundary
- Generate prebuilt Jupyter notebooks for station data analysis
- Upload notebooks to a Jupyter server via its REST API
- Dockerized for easy deployment

## Requirements

- Python 3.10+
- MongoDB database with `source` and `site` collections for earthquake events and stations respectively.
- A Jupyter Notebook server (for notebook upload feature) e.g. MsPASS
- The following Python packages:
  - flask
  - flask-cors
  - pymongo
  - requests

## Environment Variables

The following environment variables should be set:

- **MONGO_PASSWORD**: Password for connecting to MongoDB.
- **DEFAULT_NOTEBOOK_SERVER_URL** (optional): Default Jupyter server URL, used if not provided in requests.
- **DEFAULT_NOTEBOOK_TOKEN** (optional): Default Jupyter API token, used if not provided in requests.

## Endpoints

### POST /api/earthquakes/

Queries earthquake coordinates within specified longitude and latitude ranges.  
**Request body:** JSON with `lon_range` and `lat_range`.

**Response:**  
A JSON object containing:
- `coordinates`: original coordinates mapped into the user's longitude range
- `normalized_coordinates`: coordinates normalized into [-180, 180] range
- `all_coordinates`: coordinates with longitude shifted by -360, 0, +360

Each coordinate object includes:
- `lon`: longitude (float)
- `lat`: latitude (float)
- `magnitude`: earthquake magnitude (if available)

### POST /api/stations/

Queries station coordinates within specified longitude and latitude ranges.  
**Request body:** JSON with `lon_range` and `lat_range`.

**Response:**  
A JSON object containing:
- `coordinates`: original coordinates mapped into the user's longitude range
- `normalized_coordinates`: coordinates normalized into [-180, 180] range
- `all_coordinates`: coordinates with longitude shifted by -360, 0, +360

Each coordinate object includes:
- `lon`: longitude (float)
- `lat`: latitude (float)
- `id`: station identifier (built from `id` or `net.sta.loc` fields)

### POST /api/generate-station-notebook/

Generates a Jupyter notebook for a given station and uploads it to a Jupyter server.  
**Request body:** JSON with `station_id`, optionally `notebook_server_url` and `notebook_token`.

**Response:**  
The notebook content sent to the Jupyter server includes:
- Code cells for installing `pymongo`, connecting to MongoDB, setting credentials
- Example MongoDB queries for counting and retrieving picks associated with the station
- A preformatted `.ipynb` notebook structure compatible with Jupyter

## Running the App

To run locally:

1. Set the required environment variables.
2. Install dependencies using `pip install -r requirements.txt`.
3. Start the Flask app with python app.py.

Alternatively, build and run the Docker container:

1. Pull the Docker image using `docker pull --platform=linux/amd64 ghcr.io/seisscoped/mspass-geo-backend:latest`.
2. Run the container with `docker run --platform=linux/amd64 -p 5050:5050 --env MONGO_PASSWORD=yourPassword --env DEFAULT_NOTEBOOK_SERVER_URL=yourServerURL --env DEFAULT_NOTEBOOK_TOKEN=yourToken ghcr.io/seisscoped/mspass-geo-backend:latest`.

The app will be available at http://localhost:5050.

**Notes:**

The `--platform=linux/amd64` ensures compatibility if you are on an ARM-based system (like Apple M1/M2); Docker will emulate amd64 if needed.

On native amd64 systems (like most Intel/AMD machines), you can omit the `--platform` flag, but it’s safe to leave it in for consistency across environments.

## Notes

- The notebook generation uploads using Jupyter’s REST API, so the server must be accessible and token-authenticated.
- Avoid setting DEFAULT_NOTEBOOK_SERVER_URL to localhost or 127.0.0.1 when using Docker. Inside a Docker container, localhost refers only to the container itself — not the host machine and not other containers.

## License

This project is licensed under the MIT License.
