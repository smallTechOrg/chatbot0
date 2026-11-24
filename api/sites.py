"""A tenant's websites and their prompts: /api/domains (list, add) and /api/domains/<key>/prompts (read, save)."""

from flask import Blueprint, jsonify, request

from api.guard import guarded
from auth.session import current_user, login_required
from tenancy import sites

sites_bp = Blueprint("sites", __name__, url_prefix="/api/domains")


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@sites_bp.get("")
@guarded
@login_required
def list_sites():
    return jsonify({"domains": sites.list_sites(current_user())})


@sites_bp.post("")
@guarded
@login_required
def add_site():
    domain = sites.add_site(current_user(), _body().get("website"))
    return jsonify({"success": True, "domain": {"key": domain["key"], "address": domain["address"]}}), 201


@sites_bp.get("/<key>/prompts")
@guarded
@login_required
def get_prompts(key: str):
    return jsonify({"prompts": sites.get_prompts(current_user(), key)})


@sites_bp.put("/<key>/prompts")
@guarded
@login_required
def put_prompts(key: str):
    sites.set_prompts(current_user(), key, _body())
    return jsonify({"success": True})


@sites_bp.get("/<key>/prompt-chain")
@guarded
@login_required
def get_prompt_chain(key: str):
    return jsonify(sites.prompt_chain(current_user(), key))
