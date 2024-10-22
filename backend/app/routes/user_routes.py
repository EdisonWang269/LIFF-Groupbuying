from flask import Blueprint, request, jsonify

from flask_jwt_extended import create_access_token, get_jwt
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required

from ..database import execute_query

user_bp = Blueprint('user', __name__)

def check_role(store_id, userid):
    queries = [
        ("SELECT * FROM Group_buying_merchant WHERE store_id = %s AND merchant_userid = %s;", "merchant"),
        ("SELECT * FROM Customer WHERE store_id = %s AND userid = %s;", "customer")
    ]
    for query, role in queries:
        info = execute_query(query, (store_id, userid))
        if info:
            return {"role": role, "info": info}
    return None

# 登入授權 (POST)
# 驗證身份並創建 JWT token
@user_bp.route("/api/auth/login", methods=["POST"])
def login_check():
    data = request.json
    store_id = data.get('store_id')
    userid = data.get('userid')

    if not store_id or not userid:
        return jsonify({"error": "store_id and userid are required"}), 400

    role_info = check_role(store_id, userid)
    if role_info:
        identity = {"store_id": store_id, "userid": userid}
        additional_claims = {"role": role_info["role"]}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify({"access_token": access_token}), 200

    query = "INSERT INTO Customer (userid, store_id) VALUES(%s, %s);"
    result = execute_query(query, (userid, store_id))
    if result:
        identity = {"store_id": store_id, "userid": userid}
        additional_claims = {"role": "customer"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, message="Successfully enrolled"), 201
        
    return jsonify({"error": "Enroll failed due to database error"}), 500

# 更改用戶名字和電話 (PUT)
# 更新特定用戶的信息
@user_bp.route("/api/users/<string:userid>", methods=["PUT"])
@jwt_required()
def update_user_info(userid):
    data = request.json
    phone = data.get('phone')
    user_name = data.get('user_name')

    if not phone or not user_name:
        return jsonify({"error": "Phone and user_name are required"}), 400
    
    identity = get_jwt_identity()
    store_id = identity.get('store_id')
    current_userid = identity.get('userid')

    if userid != current_userid:
        return jsonify({"error": "You can only update your own information"}), 403

    claims = get_jwt()
    role = claims['role']
    
    if role == "merchant":
        return jsonify({"error": "Merchants cannot update their information through this endpoint"}), 403

    query = "UPDATE Customer SET user_name = %s, phone = %s WHERE userid = %s AND store_id = %s"
    result = execute_query(query, (user_name, phone, userid, store_id))
    if result:
        return jsonify({"message": "User info updated successfully"}), 200
    
    return jsonify({"error": "Failed to update user info"}), 500

# 修改用戶黑名單狀態 (PUT)
# 修改用戶的黑名單狀態，operation 可以是 0, 1, -1
@user_bp.route("/api/users/<string:userid>/blacklist", methods=["PUT"])
@jwt_required()
def update_user_blacklist(userid):
    data = request.json
    operation = data.get('operation')

    try:
        operation = int(operation)
        if operation not in [0, 1, -1]:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid operation, must be 0, 1, or -1"}), 400
    
    identity = get_jwt_identity()
    store_id = identity.get('store_id')

    claims = get_jwt()
    role = claims['role']
    if role != 'merchant':
        return jsonify({"error": "Insufficient permissions"}), 403

    role_info = check_role(store_id, userid)
    if not role_info:
        return jsonify({"error": "User not found"}), 404
    
    if role_info["role"] == "merchant":
        return jsonify({"error": "Merchants don't have a blacklist status"}), 400
    
    current_blacklist = role_info["info"][4]
    new_blacklist = max(0, current_blacklist + operation if operation != 0 else 0)

    query = "UPDATE Customer SET blacklist = %s WHERE userid = %s AND store_id = %s"
    result = execute_query(query, (new_blacklist, userid, store_id))
    if result:
        return jsonify({"message": "User blacklist status updated successfully", "new_blacklist": new_blacklist}), 200
    
    return jsonify({"error": "Failed to update user blacklist status"}), 500