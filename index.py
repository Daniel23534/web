from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient, errors
from bson import json_util
import os
from flask_socketio import SocketIO, emit
import json


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')

# Conexión a MongoDB Atlas
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client['ControlTemperatura']
temperaturas = db['temperaturas']

# Variable para almacenar la temperatura actual
temperatura_actual = None

@app.route('/temperatura_actual', methods=['POST'])
def recibir_temperatura():
    global temperatura_actual
    temperatura_actual = request.json.get('temperatura')
    socketio.emit('actualizar_temperatura', {'temperatura': temperatura_actual})
    return jsonify({"mensaje": "Temperatura actualizada"}), 200

@app.route('/obtener_temperatura_actual', methods=['GET'])
def enviar_temperatura():
    global temperatura_actual
    if temperatura_actual is not None:
        return jsonify({"temperatura": temperatura_actual}), 200
    else:
        return jsonify({"error": "Temperatura no disponible"}), 404

@app.route('/temperatura_objetivo', methods=['GET'])
def get_temperatura_objetivo():
    try:
        temperatura = temperaturas.find_one({"tipo": "objetivo"})
        if temperatura:
            temperatura = json.loads(json.dumps(temperatura, default=json_util.default))
            return jsonify(temperatura), 200
        else:
            return jsonify({"error": "Documento no encontrado"}), 404
    except errors.ServerSelectionTimeoutError as e:
        return jsonify({"error": "No se puede conectar a la base de datos", "details": str(e)}), 500

@app.route('/temperatura_objetivo', methods=['POST'])
def update_temperatura_objetivo():
    try:
        data = request.get_json()
        temperatura_objetivo = data.get('temperatura')
        if temperatura_objetivo is None or not isinstance(temperatura_objetivo, (int, float)):
            raise ValueError("Entrada de temperatura inválida")
        resultado = temperaturas.update_one({"tipo": "objetivo"}, {"$set": {"temperatura": temperatura_objetivo}}, upsert=True)
        if resultado.acknowledged:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Actualización fallida"}), 500
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

@app.route('/alerta_gas', methods=['POST'])
def alerta_gas():
    data = request.get_json()
    nivel_gas = data['nivel']
    socketio.emit('alerta_gas', {'nivel': nivel_gas})
    return jsonify({"mensaje": "Alerta de gas enviada"}), 200

@socketio.on('alerta_distancia')
def manejar_alerta_distancia(data):
    emit('notificacion_distancia', {'distancia': data['distancia']})

@app.route('/alerta_distancia', methods=['POST'])
def alerta_distancia():
    data = request.get_json()
    distancia = data['distancia']
    if distancia < 10:
        socketio.emit('alerta_proximidad', {'distancia': distancia})
    return jsonify({"mensaje": "Alerta de distancia procesada"}), 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
