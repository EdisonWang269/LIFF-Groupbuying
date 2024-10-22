from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..database import execute_query

from datetime import datetime

import configparser

import cloudinary
import cloudinary.uploader
import cloudinary.api

config_path = 'backend/config.ini'
config = configparser.ConfigParser()
config.read(config_path)

cloudinary.config(
    cloud_name = config['cloudinary']['cloud_name'], 
    api_key = config['cloudinary']['api_key'], 
    api_secret = config['cloudinary']['api_secret'],
    secure = True
)

product_bp = Blueprint("product", __name__)

# 獲取商家的所有商品列表
@product_bp.route("/api/products", methods=["GET"])
@jwt_required()
def get_all_products_by_storeid():
    try:
        identity = get_jwt_identity()
        store_id = identity.get("store_id")

        query = """
            SELECT 
                product_id,
                statement_date,
                price,
                unit,
                product_name,
                product_picture,
                product_describe
            FROM 
                Product
            WHERE
                store_id = %s
            ORDER BY 
                product_id DESC;
        """
        
        products = execute_query(query, (store_id,), True)

        if not products:
            return jsonify({"message": "No products found"}), 404

        data = []
        for product in products:
            data.append({
                "product_id": product[0],
                "statement_date": product[1].strftime("%Y-%m-%d") if product[1] else None,
                "price": float(product[2]),
                "unit": product[3],
                "product_name": product[4],
                "product_picture": product[5]
            })

        response = {
            "message": "Successfully retrieved product list",
            "length": len(data),
            "data": data,
        }
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 新增一項商品
@product_bp.route("/api/products", methods=["POST"])
@jwt_required()
def create_product():
    try:
        # 獲取用戶身份和角色
        identity = get_jwt_identity()
        store_id = identity.get("store_id")
        claims = get_jwt()
        role = claims["role"]

        # 檢查用戶角色
        if role != "merchant":
            return jsonify({"message": "Only merchant can create product"}), 403

        # 檢查所有必要欄位是否存在
        required_fields = ["price", "unit", "product_name", "product_describe", "supplier_name", "launch_date", "statement_date", "cost"]
        for field in required_fields:
            if field not in request.form:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # 獲取並驗證所有欄位
        price = request.form.get("price")
        unit = request.form.get("unit")
        product_name = request.form.get("product_name")
        product_describe = request.form.get("product_describe")
        supplier_name = request.form.get("supplier_name")
        launch_date = request.form.get("launch_date")
        statement_date = request.form.get("statement_date")
        cost = request.form.get("cost")

        # 驗證數值欄位
        try:
            price = float(price)
            cost = float(cost)
            if price < 0 or cost < 0:
                return jsonify({"error": "Price and cost must be non-negative"}), 400
        except ValueError:
            return jsonify({"error": "Invalid price or cost format"}), 400

        # 驗證日期欄位
        try:
            launch_date = datetime.strptime(launch_date, "%Y-%m-%d")
            statement_date = datetime.strptime(statement_date, "%Y-%m-%d")
            if launch_date > statement_date:
                return jsonify({"error": "Launch date cannot be later than statement date"}), 400
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # 檢查產品名稱是否已存在
        query_check = "SELECT * FROM Product WHERE store_id = %s AND product_name = %s;"
        existing_product = execute_query(query_check, (store_id, product_name), True)
        if existing_product:
            return jsonify({"error": "Product with this name already exists"}), 400

        # 檢查並處理圖片上傳
        if 'product_picture' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['product_picture']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # 檢查文件類型
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        if not file.filename.lower().split('.')[-1] in allowed_extensions:
            return jsonify({"error": "Invalid file type"}), 400

        # 上傳圖片到 Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(file)
            image_url = upload_result.get('url')
        except Exception as e:
            return jsonify({"error": f"Failed to upload image: {str(e)}"}), 500

        # 插入數據庫
        query = """
        INSERT INTO Product (store_id, price, unit, product_describe, supplier_name, product_name, product_picture, launch_date, statement_date, cost)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        result = execute_query(
            query,
            (store_id, price, unit, product_describe, supplier_name, product_name, image_url, launch_date, statement_date, cost),
        )

        if result:
            return jsonify({"message": "Product created successfully", "image_url": image_url}), 201
        else:
            return jsonify({"error": "Failed to create product"}), 500

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# 結單時管理者進貨，更新團購商品：purchase_quantity
@product_bp.route("/api/products/<int:product_id>/quantity", methods=["PUT"])
@jwt_required()
def update_purchase_quantity(product_id):
    try:
        # 驗證輸入數據
        if not request.is_json:
            return jsonify({"error": "Missing JSON in request"}), 400
        
        data = request.json
        purchase_quantity = data.get("purchase_quantity")
        
        if purchase_quantity is None:
            return jsonify({"error": "Missing purchase_quantity in request"}), 400
        
        if not isinstance(purchase_quantity, int) or purchase_quantity < 0:
            return jsonify({"error": "Invalid purchase_quantity. Must be a non-negative integer"}), 400

        # 驗證用戶身份和權限
        claims = get_jwt()
        role = claims.get("role")
        identity = get_jwt_identity()
        store_id = identity.get("store_id")

        if role != "merchant":
            return jsonify({"error": "權限不足"}), 403

        # 檢查產品是否屬於該商家
        check_query = "SELECT store_id FROM Product WHERE product_id = %s"
        result = execute_query(check_query, (product_id,), False) 

        if result is None:
            return jsonify({"error": "Product not found"}), 404

        if result[0] != store_id:
            return jsonify({"error": "You don't have permission to update this product"}), 403

        # 更新產品數量
        update_query =  """
                            UPDATE Product
                            SET purchase_quantity = %s
                            WHERE product_id = %s AND store_id = %s
                        """
        result = execute_query(update_query, (purchase_quantity, product_id, store_id))

        if result:
            return jsonify({"message": "Product purchase_quantity updated successfully"}), 200
        else:
            return jsonify({"error": "Failed to update product purchase_quantity"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 到貨時(更新團購商品：到貨日期arrival_date/領取截止日due_days)
@product_bp.route("/api/products/<int:product_id>/arrival", methods=["PUT"])
@jwt_required()
def update_arrival_date(product_id):
    # 驗證輸入數據
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.json
    arrival_date = data.get("arrival_date")
    due_days = data.get("due_days")
    
    if not arrival_date or due_days is None:
        return jsonify({"error": "Missing arrival_date or due_days in request"}), 400
    
    # 驗證日期格式
    try:
        arrival_date = datetime.strptime(arrival_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid arrival_date format. Use YYYY-MM-DD"}), 400
    
    # 驗證 due_days
    try:
        due_days = int(due_days)
        if due_days < 0 or due_days > 255:  # TINYINT 範圍檢查
            return jsonify({"error": "Invalid due_days. Must be between 0 and 255"}), 400
    except ValueError:
        return jsonify({"error": "Invalid due_days. Must be an integer"}), 400

    # 驗證用戶身份和權限
    claims = get_jwt()
    role = claims.get("role")
    identity = get_jwt_identity()
    store_id = identity.get("store_id")

    if role != "merchant":
        return jsonify({"error": "權限不足"}), 403

    # 檢查產品是否屬於該商家
    check_query = "SELECT store_id FROM Product WHERE product_id = %s"
    product = execute_query(check_query, (product_id,), False)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product[0] != store_id:
        return jsonify({"error": "You don't have permission to update this product"}), 403

    # 更新產品信息
    update_query =  """
                        UPDATE Product
                        SET arrival_date = %s, due_days = %s
                        WHERE product_id = %s AND store_id = %s
                    """
    try:
        result = execute_query(update_query, (arrival_date, due_days, product_id, store_id))

        if result:
            return jsonify({
                "message": "Product arrival information updated successfully",
                "arrival_date": arrival_date.strftime("%Y-%m-%d"),
                "due_days": due_days
            }), 200
        else:
            return jsonify({"error": "Failed to update product arrival information"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 更改結單日期（傳product_id，新結單時間，更新statement_date)
@product_bp.route("/api/products/<int:product_id>/statementdate", methods=["PUT"])
@jwt_required()
def update_statement_date(product_id):
    # 驗證用戶身份和權限
    claims = get_jwt()
    role = claims.get("role")
    identity = get_jwt_identity()
    store_id = identity.get("store_id")

    if role != "merchant":
        return jsonify({"error": "權限不足"}), 403

    # 驗證輸入數據
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.json
    new_statement_date = data.get("new_statement_date")

    if not new_statement_date:
        return jsonify({"error": "Missing new_statement_date in request"}), 400

    # 驗證日期格式
    try:
        new_statement_date = datetime.strptime(new_statement_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid new_statement_date format. Use YYYY-MM-DD"}), 400

    # 檢查產品是否存在且屬於該商家
    check_query = "SELECT store_id FROM Product WHERE product_id = %s"
    product = execute_query(check_query, (product_id,), False)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product[0] != store_id:
        return jsonify({"error": "You don't have permission to update this product"}), 403

    # 更新產品信息
    update_query =  """
                        UPDATE Product
                        SET statement_date = %s
                        WHERE product_id = %s AND store_id = %s
                    """
    try:
        result = execute_query(update_query, (new_statement_date, product_id, store_id))

        if result:
            return jsonify({
                "message": "Statement date updated successfully",
                "product_id": product_id,
                "new_statement_date": new_statement_date.strftime("%Y-%m-%d")
            }), 200
        else:
            return jsonify({"error": "Failed to update statement date. No changes made."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500