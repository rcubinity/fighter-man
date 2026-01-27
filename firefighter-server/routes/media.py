"""Video upload and streaming endpoints."""

import os
import logging

from flask import Blueprint, request, jsonify, send_file, Response

from app_state import AppState

logger = logging.getLogger(__name__)

media_bp = Blueprint('media', __name__)

# Base directory for resolving relative paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_video_storage_path():
    """Get video storage path, resolving relative paths to BASE_DIR."""
    path = os.getenv('VIDEO_STORAGE_PATH', './data/videos')
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return path


@media_bp.route("/sessions/<session_id>/upload-video", methods=["POST"])
def upload_session_video(session_id):
    """
    Upload video file for a session.

    Expects multipart/form-data with 'video' file.
    Stores video file on disk and updates session record.
    """
    # Check if video file is in request
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # Validate session exists
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Get video storage path
    video_storage_path = get_video_storage_path()

    # Create videos directory if it doesn't exist
    os.makedirs(video_storage_path, exist_ok=True)

    # Save with session_id as filename
    filename = f"{session_id}.webm"
    file_path = os.path.join(video_storage_path, filename)

    try:
        video_file.save(file_path)
        file_size = os.path.getsize(file_path)

        # Update session record with video metadata
        repo.update(
            session_id,
            video_file_path=filename,
            video_size_bytes=file_size
        )

        logger.info(
            f"[Video] Uploaded for session {session_id}: {filename} ({file_size} bytes)"
        )

        return jsonify({
            'success': True,
            'video_file_path': filename,
            'size_bytes': file_size
        }), 200

    except Exception as e:
        logger.error(f"[Video] Upload failed for session {session_id}: {str(e)}")
        return jsonify({'error': f'Failed to save video: {str(e)}'}), 500


@media_bp.route("/sessions/<session_id>/video", methods=["GET"])
def get_session_video(session_id):
    """
    Stream video file for a session.

    Supports HTTP Range requests for seeking.
    Returns video/webm with appropriate headers.
    """
    # Get session and check if video exists
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if not session.video_file_path:
        return jsonify({'error': 'No video file for this session'}), 404

    # Get video storage path
    video_storage_path = get_video_storage_path()
    file_path = os.path.join(video_storage_path, session.video_file_path)

    # Check if file exists on disk
    if not os.path.exists(file_path):
        logger.error(f"[Video] File not found on disk: {file_path}")
        return jsonify({'error': 'Video file not found on disk'}), 404

    # Get file size
    file_size = os.path.getsize(file_path)

    # Handle Range requests for video seeking
    range_header = request.headers.get('Range', None)

    if range_header:
        # Parse range header (format: "bytes=start-end")
        try:
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1

            # Ensure valid range
            start = max(0, start)
            end = min(end, file_size - 1)

            # Read chunk
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)

            # Return partial content (206)
            response = Response(data, 206, mimetype='video/webm')
            response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            response.headers.add('Accept-Ranges', 'bytes')
            response.headers.add('Content-Length', len(data))
            return response

        except Exception as e:
            logger.error(f"[Video] Range request failed: {str(e)}")
            # Fall through to full file response on error

    # Return full file (no range request or range parsing failed)
    return send_file(
        file_path,
        mimetype='video/webm',
        as_attachment=False,
        download_name=f"session_{session_id}.webm"
    )
