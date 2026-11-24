"""One error boundary for the JSON APIs: a ServiceError becomes its status, anything else a logged 500."""

import functools
import logging

from flask import jsonify

from core.errors import ServiceError

logger = logging.getLogger(__name__)


def guarded(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except ServiceError as exc:
            return jsonify({"success": False, "error": exc.message}), exc.status
        except Exception:
            logger.exception("[API] unhandled error in %s", view.__name__)
            return jsonify({"success": False, "error": "Something went wrong."}), 500

    return wrapper
