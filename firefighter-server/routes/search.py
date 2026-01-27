"""Similarity search endpoint."""

from flask import Blueprint, request, jsonify

from app_state import AppState

search_bp = Blueprint('search', __name__)


@search_bp.route("/query/similar", methods=["POST"])
def query_similar():
    """
    Find similar sensor patterns.

    Request body: {
        "window_id": "id of reference window",
        "session_id": "optional filter by session",
        "label": "optional filter by label",
        "limit": 10
    }
    """
    data = request.get_json() or {}
    window_id = data.get("window_id")
    session_filter = data.get("session_id")
    label_filter = data.get("label")
    limit = data.get("limit", 10)

    if not window_id:
        return jsonify({"error": "window_id is required"}), 400

    store = AppState.get_vector_store()

    # Get the reference window's vector
    try:
        points = store.client.retrieve(
            collection_name=store.config.collection,
            ids=[window_id],
            with_vectors=True,
        )
        if not points:
            return jsonify({"error": "Window not found"}), 404

        reference_vector = points[0].vector
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Search for similar
    results = store.query_similar(
        vector=reference_vector,
        limit=limit + 1,  # +1 because result may include the reference
        session_id=session_filter,
        label=label_filter,
    )

    # Remove the reference window from results
    results = [r for r in results if r["id"] != window_id][:limit]

    return jsonify({
        "reference_id": window_id,
        "similar_windows": results,
    })
