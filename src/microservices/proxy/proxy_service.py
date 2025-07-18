import os
import random
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 8000))
MONOLITH_URL = os.environ.get("MONOLITH_URL", "http://localhost:8080")
MOVIES_SERVICE_URL = os.environ.get("MOVIES_SERVICE_URL", "http://localhost:8081")
EVENTS_SERVICE_URL = os.environ.get("EVENTS_SERVICE_URL", "http://localhost:8082")
GRADUAL_MIGRATION = os.environ.get("GRADUAL_MIGRATION", "true").lower() == "true"
MOVIES_MIGRATION_PERCENT = int(os.environ.get("MOVIES_MIGRATION_PERCENT", 50))


def route_request(url, method, data=None, headers=None, params=None):
    """Routes the request to the specified URL."""
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            return jsonify({"error": "Method not supported"}), 405

        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error routing request: {e}")
        return jsonify({"error": str(e)}), 500


def should_route_to_movies():
    """Determines if a request should be routed to the movies service."""
    if not GRADUAL_MIGRATION:
        return False

    return random.randint(0, 100) < MOVIES_MIGRATION_PERCENT


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return "OK", 200


@app.route("/api/users", methods=["GET", "POST"])
def users():
    """Routes user-related requests to the monolith."""
    monolith_url = f"{MONOLITH_URL}/api/users"
    method = request.method
    data = request.get_json() if method == "POST" else None
    headers = {"Content-Type": "application/json"} if method == "POST" else None
    params = request.args if method == "GET" else None
    return route_request(monolith_url, method, data, headers, params)


@app.route("/api/movies", methods=["GET", "POST"])
def movies():
    """Routes movie-related requests based on feature flag."""
    method = request.method
    data = request.get_json() if method == "POST" else None
    headers = {"Content-Type": "application/json"} if method == "POST" else None
    params = request.args if method == "GET" else None
    if should_route_to_movies():
        movies_service_url = f"{MOVIES_SERVICE_URL}/api/movies"
        print("Routing to Movies Service")
        return route_request(movies_service_url, method, data, headers, params)
    else:
        monolith_url = f"{MONOLITH_URL}/api/movies"
        print("Routing to Monolith")
        return route_request(monolith_url, method, data, headers, params)


@app.route("/api/events/<event_type>", methods=["POST"])
def events(event_type):
    """Routes event-related requests to the events service."""
    events_service_url = f"{EVENTS_SERVICE_URL}/api/events/{event_type}"
    method = request.method
    data = request.get_json()
    headers = {"Content-Type": "application/json"}
    return route_request(events_service_url, method, data, headers)


@app.route("/api/payments", methods=["GET", "POST"])
def payments():
    """Routes payment-related requests to the monolith."""
    monolith_url = f"{MONOLITH_URL}/api/payments"
    method = request.method
    data = request.get_json() if method == "POST" else None
    headers = {"Content-Type": "application/json"} if method == "POST" else None
    params = request.args if method == "GET" else None
    return route_request(monolith_url, method, data, headers, params)


@app.route("/api/subscriptions", methods=["GET", "POST"])
def subscriptions():
    """Routes subscription-related requests to the monolith."""
    monolith_url = f"{MONOLITH_URL}/api/subscriptions"
    method = request.method
    data = request.get_json() if method == "POST" else None
    headers = {"Content-Type": "application/json"} if method == "POST" else None
    params = request.args if method == "GET" else None
    return route_request(monolith_url, method, data, headers, params)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
