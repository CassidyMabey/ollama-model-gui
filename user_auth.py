# PYTHON MONGODB USER AUTHENTICATION EXAMPLE
import os
import hashlib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import Blueprint, request, session, jsonify

uri = "nuh uh"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['ollama-ai']
users = db['users']

auth_bp = Blueprint('auth', __name__)

# Helper to hash passwords

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required.'}), 400
    if users.find_one({'username': username}):
        return jsonify({'error': 'Username already exists.'}), 409
    hashed = hash_password(password)
    users.insert_one({'username': username, 'password': hashed})
    return jsonify({'success': True})

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required.'}), 400
    user = users.find_one({'username': username})
    if not user or user['password'] != hash_password(password):
        return jsonify({'error': 'Invalid credentials.'}), 401
    session['username'] = username
    return jsonify({'success': True, 'username': username})

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'success': True})
