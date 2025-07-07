from ollama import chat
from ollama import ChatResponse
from ollama import list as ollama_list
import ollama
from flask import Flask, json, request, jsonify, Response
from flask_cors import CORS
import re
import time
app = Flask(__name__)
CORS(app)
MODEL = "smollm:latest"
@app.route('/')
def home():
  return ""

@app.route("/response", methods=["POST"])
def response():
    message = request.form.get("m")
    model = request.form.get("model") or MODEL
    def generate():
        try:
            for chunk in chat(model=model, messages=[{'role': 'user', 'content': message}], stream=True):
                content = chunk['message']['content'] if 'message' in chunk and 'content' in chunk['message'] else str(chunk)
                yield content
        except TypeError:
            response: ChatResponse = chat(model=model, messages=[{'role': 'user', 'content': message}])
            yield response['message']['content']
    return Response(generate(), mimetype='text/plain')

@app.route("/downloadmodel", methods=["POST"])
def downloadmodel():
    ollamaModel = request.form.get("model")
    print(ollamaModel)
    if not ollamaModel:
        return {"status_code": 400, "text": "No model name provided."}
    try:
        ollama.pull(ollamaModel)
        return {"status_code": 200, "done": True, "text": f"Successfully downloaded {ollamaModel}"}
    except Exception as e:
        return {"status_code": 400, "error": str(e), "text": f"Failed to download {ollamaModel}"}
    
@app.route("/deletemodel")
def deletemodel():
  ollamaModel = request.form.get("model")
  try:
    ollama.delete(ollamaModel)
    return {"status_code": 200, "text": f"Successfully deleted {ollamaModel}"}
  except Exception as e:
    return {"status_code": 400, "text": f"Failed to delete {ollamaModel}", "error": str(e)}

@app.route("/listmodels")
def listmodels():
    models = str(ollama_list())
    print('Received models:', models)
    matches = re.findall(r"model='(.*?)'", models)
    model_names = [m for m in matches if m]
    if MODEL in model_names:
        model_names.remove(MODEL)
        model_names.insert(0, MODEL)
    print('Final model_names:', model_names)
    return jsonify(model_names)


app.run()