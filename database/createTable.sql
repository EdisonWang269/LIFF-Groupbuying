CREATE DATABASE Groupbuy;
USE Groupbuy;

CREATE TABLE Group_buying_merchant(
	merchant_userid VARCHAR(255) NOT NULL,
	store_name VARCHAR(255),
	store_id VARCHAR(255),
	address VARCHAR(255),
	business_hours VARCHAR(255),
	CONSTRAINT Group_buying_merchant_PK  PRIMARY KEY(store_id),
	UNIQUE(store_id)
);

CREATE TABLE Customer(
	userid VARCHAR(255) NOT NULL,
 	store_id VARCHAR(255) NOT NULL,
	user_name VARCHAR(255),
	phone VARCHAR(10) DEFAULT NULL,
	blacklist TINYINT DEFAULT 0,
	CONSTRAINT Customer_PK PRIMARY KEY(userid, store_id)
);

CREATE TABLE Product(
	product_id BIGINT NOT NULL AUTO_INCREMENT,
	store_id VARCHAR(255) NOT NULL,
	price DOUBLE,
	unit VARCHAR(255),
	cost DOUBLE,
	product_describe VARCHAR(255),
	supplier_name VARCHAR(255),
	product_name VARCHAR(255),
	product_picture VARCHAR(255),
	purchase_quantity INT,
	launch_date DATETIME,
	statement_date DATETIME,
	arrival_date DATETIME,
	due_days TINYINT,
	CONSTRAINT Product_PK PRIMARY KEY(product_id),
	UNIQUE(product_id)
);

CREATE TABLE `Order`(
	order_id BIGINT  NOT NULL AUTO_INCREMENT PRIMARY KEY,
	userid VARCHAR(255) NOT NULL,
	product_id BIGINT  NOT NULL ,
	quantity INT,
	receive_status Boolean DEFAULT FALSE,
	CONSTRAINT Order_FK1 FOREIGN KEY(userid) REFERENCES Customer(userid),
	CONSTRAINT Order_FK2 FOREIGN KEY(product_id) REFERENCES Product(product_id)
);
