# from flaskext.mysql import MySQL
import mysql.connector

import configparser

# config_path = '/home/wangpython/Gogroupbuy/backend/config.ini'
config_path = 'backend/config.ini'

config = configparser.ConfigParser()
config.read(config_path)

DB_CONFIG = {
  'user': config['db']['username'],
  'password': config['db']['password'],
  'host': config['db']['host'],
  'database': config['db']['database'],
}

def get_database_connection():
    return mysql.connector.connect(**DB_CONFIG)

def execute_query(query, params=None, fetchall=False):
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)

        if query.strip().upper().startswith('SELECT'):
            if fetchall:
                return cursor.fetchall()
            else:
                return cursor.fetchone()
            
        else:
            conn.commit()
            return True

    except Exception as e:
        print(str(e))
        conn.rollback()
        return None
    
    finally:
        cursor.close()
        conn.close()