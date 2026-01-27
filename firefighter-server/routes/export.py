"""Session export endpoint."""

import csv
from io import StringIO

from flask import Blueprint, request, jsonify, current_app

from app_state import AppState

export_bp = Blueprint('export', __name__)


@export_bp.route("/sessions/<session_id>/export", methods=["GET"])
def export_session(session_id):
    """
    Export session data for annotation tool or ML training.

    Query params:
        format: "json" (default) or "csv"
        include_raw: "true" to include raw sensor data
    """
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    include_raw = request.args.get("include_raw", "false").lower() == "true"
    export_format = request.args.get("format", "json")

    store = AppState.get_vector_store()
    windows = store.get_session_data(session_id, include_raw=include_raw)

    if export_format == "csv":
        # Simple CSV export
        output = StringIO()
        if windows:
            fieldnames = [
                "id", "start_time", "end_time", "foot_count", "accel_count", "label"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(windows)

        response = current_app.response_class(
            response=output.getvalue(),
            status=200,
            mimetype="text/csv",
        )
        response.headers["Content-Disposition"] = f"attachment; filename={session_id}.csv"
        return response

    # JSON export (default)
    return jsonify({
        "session": session.to_dict(),
        "windows": windows,
        "window_count": len(windows),
    })
