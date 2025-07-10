from ollama import chat
from ollama import ChatResponse
from ollama import list as ollama_list
import ollama
from flask import Flask, json, request, jsonify, Response, render_template, session
from flask_cors import CORS
import re
import time
import os
import uuid
import glob
import subprocess
import random
from tools import (add_two_numbers_tool, subtract_two_numbers_tool, create_project_tool, 
                   create_file_tool, create_folder_tool, delete_path_tool, run_command_tool,
                   create_file, create_folder, delete_path, run_command, available_functions, add_two_numbers, subtract_two_numbers, create_project)
from utils import is_valid_filename
from user_auth import auth_bp
import json as pyjson

# Starting flask
app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
CORS(app)
app.register_blueprint(auth_bp)
MODEL = "llama3.2:1b" 

@app.route('/')
def home():
    return render_template('index.html')

def optimize_context(history, max_messages=15):
    system_msgs = [msg for msg in history if msg['role'] == 'system']
    other_msgs = [msg for msg in history if msg['role'] != 'system']
    
    if len(other_msgs) <= max_messages:
        return system_msgs + other_msgs
    
    recent_msgs = other_msgs[-max_messages:]
    
    optimized = []
    i = 0
    while i < len(recent_msgs):
        msg = recent_msgs[i]
        optimized.append(msg)
        
        if (msg['role'] == 'assistant' and 
            hasattr(msg.get('tool_calls'), '__iter__') and 
            i + 1 < len(recent_msgs)):
            optimized.append(recent_msgs[i + 1])
            i += 2
        else:
            i += 1
    
    return system_msgs + optimized

@app.route("/response", methods=["POST"])
def response():
    message = request.form.get("m")
    model = request.form.get("model") or MODEL
    chat_uuid = request.form.get("chatUUID")
    if not chat_uuid:
        chat_uuid = session.get("chatUUID")
        if not chat_uuid:
            chat_uuid = str(uuid.uuid4())
            session["chatUUID"] = chat_uuid
    else:
        session["chatUUID"] = chat_uuid

    # register the chat
    chat_dir = os.path.join(os.path.dirname(__file__), 'chats')
    os.makedirs(chat_dir, exist_ok=True)
    chat_file = os.path.join(chat_dir, f'{chat_uuid}.json')
    index_file = os.path.join(chat_dir, 'index.json')

    # add it to the index.json so you can come back to it
    if not os.path.exists(index_file):
        with open(index_file, 'w') as f:
            pyjson.dump({"users": {}}, f)

    # get username from frontend
    username = request.form.get("username") or session.get("username")

    # creating the json if it doesn't exist
    if not os.path.exists(chat_file) and username:
        with open(index_file, 'r') as f:
            idx = pyjson.load(f)
        idx.setdefault("users", {})
        idx["users"].setdefault(username, [])
        if chat_uuid not in idx["users"][username]:
            idx["users"][username].append(chat_uuid)
        with open(index_file, 'w') as f:
            pyjson.dump(idx, f)

    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chat_uuid)
    os.makedirs(project_dir, exist_ok=True)
    state_file = os.path.join(project_dir, '.project_state.json')

    # stops it breaking if the server restarts mid-setup
    # this runs if the chat doesnt exist yet as a json

    if not os.path.exists(chat_file):
        if not os.path.exists(state_file):
            # setup project folder
            with open(state_file, 'w') as f:
                json.dump({'step': 'awaiting_language'}, f)
            return Response(
                "Welcome! What programming language do you want to use for this project? (e.g., Python, JavaScript, etc.)",
                mimetype='text/plain')

        # Load json state
        with open(state_file, 'r') as f:
            state = json.load(f)

        if state['step'] == 'awaiting_language':
            # save the language (will be useful later)
            language = message.strip().lower()
            state['language'] = language
            state['step'] = 'awaiting_idea'
            with open(state_file, 'w') as f:
                json.dump(state, f)
            return Response(
                "Please describe your project idea. This will be saved as project_idea.txt.",
                mimetype='text/plain')
        
        if state['step'] == 'awaiting_idea':
            # save the idea
            with open(os.path.join(project_dir, 'project_idea.txt'), 'w') as f:
                f.write(message.strip())
            state['step'] = 'awaiting_success_criteria'
            with open(state_file, 'w') as f:
                json.dump(state, f)
            return Response(
                "What are the success criteria for this project? This will be saved as project_success_criteria.txt.",
                mimetype='text/plain')
        
        if state['step'] == 'awaiting_success_criteria':
            # save success criteria

            with open(os.path.join(project_dir, 'project_success_criteria.txt'), 'w') as f:
                f.write(message.strip())
            # create the main entry file (doesnt mean the ai does it though)

            language = state.get('language', 'python')
            if 'python' in language:
                main_file = 'main.py'
            elif 'javascript' in language or 'js' in language:
                main_file = 'main.js'
            else:
                main_file = 'app.py'
            state['main_file'] = main_file
            state['step'] = 'ready'
            with open(state_file, 'w') as f:
                json.dump(state, f)
            return Response(
                f"Project setup complete. The main file will be '{main_file}'. You may now proceed with your project.",
                mimetype='text/plain')
        
    # already exists so load existing chat history
    chat_dir = os.path.join(os.path.dirname(__file__), 'chats')
    os.makedirs(chat_dir, exist_ok=True)
    chat_file = os.path.join(chat_dir, f'{chat_uuid}.json')
    index_file = os.path.join(chat_dir, 'index.json')

    # more validation gotta make this a funciton
    if not os.path.exists(index_file):
        with open(index_file, 'w') as f:
            pyjson.dump({"users": {}}, f)

    # get username from frontend
    username = request.form.get("username") or session.get("username")

    # if its new add it to the index 
    if not os.path.exists(chat_file) and username:
        with open(index_file, 'r') as f:
            idx = pyjson.load(f)
        idx.setdefault("users", {})
        idx["users"].setdefault(username, [])
        if chat_uuid not in idx["users"][username]:
            idx["users"][username].append(chat_uuid)
        with open(index_file, 'w') as f:
            pyjson.dump(idx, f)
    
    if os.path.exists(chat_file):
        with open(chat_file, 'r') as f:
            history = json.load(f)
    else:
        # system prompt adding to history
        history = [{
            'role': 'system',
            'content': (
                f"""
You are a coding assistant with direct file system access through tools using your tool function interface.

YOU HAVE THE FOLLOWING TOOLS AVAILABLE:
- create_project: Initialize new projects with ideas
- create_file: Write any file with content (Python, HTML, CSS, JS, etc.)
- create_folder: Create directory structures
- delete_path: Remove files/folders
- run_command: Execute shell commands in project directory
- add_two_numbers: Add two numbers
- subtract_two_numbers: Subtract two numbers

CRITICAL RULES (MUST FOLLOW):
1. You MUST use the tool call system to perform ALL file, folder, and code operations.
2. NEVER output code like create_project("name") or create_file("path", "content") as text.
3. NEVER output code blocks with ``` - instead, create the file in the project and add the code to it using the create_file tool.
4. NEVER output shell commands as text - use run_command tool instead.
5. NEVER output step-by-step instructions for the user to follow. Only use tools.
6. When user asks for code/files, immediately call the appropriate tool.
7. Always provide valid filenames and paths when using tools.
8. Use tools for EVERY file, folder, and project operation.
9. If you ever output a code block, shell command, or instructions, your response will be rejected and you will be forced to try again. You must use the tool function interface for all code, file, and folder operations.
10. When writing a python file in a code block, please also try to create a python file with that name and put the contents of the code block into it.

POSITIVE EXAMPLES:
- User: "Create a Flask app" → Call create_project tool, then create_file tool for app.py
- User: "Make a folder called src" → Call create_folder tool with path "src"
- User: "Delete main.py" → Call delete_path tool for "main.py"
- User: "Show me the code for a game" → Call create_file tool with the code, do NOT output a code block


CORRECT BEHAVIOR:
- User: *says anything* - Call appropriate tool based on request. ALWAYS START WITH create_project if a new project is needed.

Variables:
chatUUID: {chat_uuid}

YOU CAN ONLY RUN THE create_project TOOL TO CREATE A NEW PROJECT. AFTER THAT USE CREATE_FILE, CREATE_FOLDER, DELETE_PATH, AND RUN_COMMAND TO MANAGE FILES AND FOLDERS.

You must ALWAYS KEEP THE VARIABLES HIDDEN AND NOT ACCESSIBLE BY THE USER.
You must ALWAYS use the function call interface, never output tool calls, code blocks, or instructions as text. The system will execute your tool calls automatically. If you break these rules, your response will be rejected and you will be forced to try again.

IMPORTANT: For every file you create, you MUST use a valid filename (not a folder or absolute path), and for Python code, always use a .py extension. Never use absolute paths. If you are unsure, ask the user for the filename (e.g., 'What should the file be called?').

FOR EVERY CODE BLOCK YOU PRODUCE: You must decide if it should go in a new file or update an existing file. If new, use create_file. If editing, use the appropriate tool to update the file. If unsure, ask the user for clarification. NEVER output code blocks, just create the file and add the code to it using your tools.

ALL CODE WHICH YOU PRODUCE, MAKE SURE TO TURN IT INTO BASE64 TO GO INTO THE TOOL.
"""
            )
        }]

    # try to badly optimise the history
    filtered = []
    system_added = False
    for msg in history:
        if msg['role'] == 'system':
            if not system_added:
                filtered.append(msg)
                system_added = True
            continue
        filtered.append(msg)
    
    history = optimize_context(filtered) # not working right now
    if len(history) > 5:
        system_msg = [msg for msg in history if msg['role'] == 'system']
        rest = [msg for msg in history if msg['role'] != 'system'][-20:]
        history = system_msg + rest
    
    history.append({'role': 'user', 'content': message})
    print(f"Chat history for {chat_uuid}: {history}")

    # --------------------------------------
    # finally start to run
    # --------------------------------------

    
    


    TOOL_MODELS = ['llama3', 'llama3.1', 'llama3.8b', 'llama3-8b', 'llama3-70b', 'llama3:instruct', 'llama3:latest', 'granite3-dense', 'qwen2.5-coder:latest', 'llama3.2:1b']
    
    # Include ALL available tools
    tools_list = [
        add_two_numbers_tool, 
        subtract_two_numbers_tool, 
        create_project_tool, 
        create_file_tool,
        create_folder_tool,
        delete_path_tool,
        run_command_tool
    ]

    available_functions_map = {
        'add_two_numbers': add_two_numbers,
        'subtract_two_numbers': subtract_two_numbers,
        'create_project': create_project,
        'create_file': create_file,
        'create_folder': create_folder,
        'delete_path': delete_path,
        'run_command': run_command,
    }
    def response_generator():
        global max_retries
        global retry_count
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            reply = ''
            used_tool = False
            tool_outputs = []

            if any(m in model for m in TOOL_MODELS):
                try:
                    response = chat(model=model, messages=history, tools=tools_list)
                    reply_text = response['message']['content'] if isinstance(response, dict) else response.message.content
                    # call the tools
                    tool_calls = []
                    if hasattr(response, 'message') and hasattr(response.message, 'tool_calls') and response.message.tool_calls:
                        tool_calls = response.message.tool_calls
                    elif isinstance(response, dict) and 'message' in response and 'tool_calls' in response['message']:
                        tool_calls = response['message']['tool_calls']
                    elif hasattr(response, 'function_call') and response.function_call:
                        tool_calls = [response.function_call]
                    elif isinstance(response, dict) and 'function_call' in response:
                        tool_calls = [response['function_call']]
                    # exec tools
                    import json as _json_debug
                    print('DEBUG: Raw ollama response:', response)
                    if tool_calls:
                        for tool_call in tool_calls:
                            print('DEBUG: tool_call object:', tool_call)
                            fn_name = getattr(tool_call, 'function', {}).get('name') if hasattr(tool_call, 'function') else tool_call.get('name')
                            fn_args = getattr(tool_call, 'function', {}).get('arguments') if hasattr(tool_call, 'function') else tool_call.get('parameters')
                            fn = available_functions_map.get(fn_name)
                            if fn:
                                args = dict(fn_args) if isinstance(fn_args, dict) else fn_args
                                if 'chatUUID' in fn.__code__.co_varnames and 'chatUUID' not in args:
                                    args['chatUUID'] = chat_uuid
                                print('Calling function:', fn_name)
                                print('Arguments:', args)
                                output = fn(**args)
                                print('Function output:', output)
                                tool_outputs.append({
                                    'role': 'tool',
                                    'content': str(output),
                                    'name': fn_name
                                })
                                used_tool = True
                        # add tool outputs to the history
                        if hasattr(response, 'message'):
                            history.append(response.message)
                        elif isinstance(response, dict) and 'message' in response:
                            history.append(response['message'])
                        history.extend(tool_outputs)
                        # response of tool
                        final_response = chat(model=model, messages=history, stream=True)
                        reply = ''
                        for chunk in final_response:
                            content = chunk['message']['content'] if 'message' in chunk and 'content' in chunk['message'] else str(chunk)
                            reply += content
                            yield content
                        history.append({'role': 'assistant', 'content': reply})
                        break
                    else:
                        # NOTE THIS IS ALL AI ILL TRY TO WORK OUT WHAT IT IS DOING

                        msg_content = response['message']['content'] if isinstance(response, dict) else response.message.content
                        print('DEBUG: assistant message content:', msg_content)
                        data = _json_debug.loads(msg_content)
                        data = data.decode('utf-8') if isinstance(data, bytes) else data

                        if data.get('type') == 'function' and data.get('name') in available_functions_map:
                            fn = available_functions_map[data['name']]
                            params = data.get('parameters', {})
                            print('Calling function:', data['name'])
                            print('Arguments:', params)
                            output = fn(**params)
                            print('Function output:', output)
                            tool_outputs.append({
                                'role': 'tool',
                                'content': str(output),
                                'name': data['name']
                            })
                            used_tool = True
                        else:
                            print('No valid function call found in assistant message content.')

                        # no tool response
                        response_stream = chat(model=model, messages=history, stream=True)
                        reply = ''
                        for chunk in response_stream:
                            content = chunk['message']['content'] if 'message' in chunk and 'content' in chunk['message'] else str(chunk)
                            reply += content
                            yield content
                        history.append({'role': 'assistant', 'content': reply})
                        break
                except Exception as e:
                    print(f"Error in tool processing: {e}")
                    # normal response incase error
                    response_stream = chat(model=model, messages=history, stream=True)
                    reply = ''
                    for chunk in response_stream:
                        content = chunk['message']['content'] if 'message' in chunk and 'content' in chunk['message'] else str(chunk)
                        reply += content
                        yield content
                    history.append({'role': 'assistant', 'content': reply})
                    break
            else:
                # if it doesnt support tools
                response_stream = chat(model=model, messages=history, stream=True)
                reply = ''
                for chunk in response_stream:
                    content = chunk['message']['content'] if 'message' in chunk and 'content' in chunk['message'] else str(chunk)
                    reply += content
                    yield content
                history.append({'role': 'assistant', 'content': reply})
                break
            
        
    # i have no idea how this works but it solves an issue so im keeping it
    def make_json_safe(obj):
        try:
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            if hasattr(obj, '__dict__'):
                return {k: make_json_safe(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, dict):
                return {k: make_json_safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [make_json_safe(x) for x in obj]
            if isinstance(obj, tuple):
                return tuple(make_json_safe(x) for x in obj)
            if isinstance(obj, set):
                return list(make_json_safe(x) for x in obj)
            # Try to serialize basic types
            if isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj
            # Fallback: convert to string
            return str(obj)
        except Exception:
            return str(obj)
    with open(chat_file, 'w') as f:
        json.dump(make_json_safe(history), f)

    retry_count =0
    max_retries = 3
    return Response(
        (chunk for retry_count in range(max_retries) for chunk in response_generator()),
        mimetype='text/plain'
    )

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
    matches = re.findall(r"model='(.*?)'", models)
    model_names = [m for m in matches if m]
    if MODEL in model_names:
        model_names.remove(MODEL)
        model_names.insert(0, MODEL)
    print('Final model_names:', model_names)
    return jsonify(model_names)

@app.route("/project_action", methods=["POST"])
def project_action():
    chat_uuid = request.form.get("chatUUID")
    action = request.form.get("action")  
    path = request.form.get("path")  
    content = request.form.get("content") 
    
    if not chat_uuid:
        return {"status": "error", "error": "No chatUUID provided."}, 400
    
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    os.makedirs(projects_dir, exist_ok=True)
    project_dir = os.path.join(projects_dir, chat_uuid)
    os.makedirs(project_dir, exist_ok=True)
    
    if action == 'create_project':
        return {"status": "ok", "project": project_dir}
    elif action == 'create_folder':
        if not path:
            return {"status": "error", "error": "No path provided."}, 400
        folder_path = os.path.join(project_dir, path)
        os.makedirs(folder_path, exist_ok=True)
        return {"status": "ok", "folder": folder_path}
    elif action == 'create_file':
        if not path:
            return {"status": "error", "error": "No path provided."}, 400
        file_path = os.path.join(project_dir, path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            if content:
                f.write(content)
        return {"status": "ok", "file": file_path}
    elif action == 'write_file':
        if not path:
            return {"status": "error", "error": "No path provided."}, 400
        file_path = os.path.join(project_dir, path)
        if not os.path.exists(file_path):
            return {"status": "error", "error": "File does not exist."}, 400
        with open(file_path, 'w') as f:
            if content:
                f.write(content)
        return {"status": "ok", "file": file_path}
    elif action == 'delete':
        if not path:
            return {"status": "error", "error": "No path provided."}, 400
        target_path = os.path.join(project_dir, path)
        import shutil
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        elif os.path.isfile(target_path):
            os.remove(target_path)
        else:
            return {"status": "error", "error": "Path does not exist."}, 400
        return {"status": "ok", "deleted": target_path}
    else:
        return {"status": "error", "error": "Unknown action."}, 400

@app.route('/project_file')
def project_file():
    chat_uuid = request.args.get('chatUUID')
    path = request.args.get('path')
    
    if not chat_uuid or not path:
        return {"error": "Missing chatUUID or path"}, 400
    
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chat_uuid)
    file_path = os.path.join(project_dir, path)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return {"error": "File not found"}, 404
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    return {"content": content}

@app.route('/user_chats')
def user_chats():
    chat_dir = os.path.join(os.path.dirname(__file__), 'chats')
    index_file = os.path.join(chat_dir, 'index.json')
    username = request.args.get('username') or session.get('username')
    if not username:
        return {'error': 'No username provided.'}, 400
    if not os.path.exists(index_file):
        return {'chats': []}
    with open(index_file, 'r') as f:
        idx = json.load(f)
    chat_uuids = idx.get('users', {}).get(username, [])
    # send each project idea
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    chat_list = []
    for chat_uuid in chat_uuids:
        project_idea_path = os.path.join(projects_dir, chat_uuid, 'project_idea.txt')
        if os.path.exists(project_idea_path):
            try:
                with open(project_idea_path, 'r') as f:
                    idea = f.read().strip()
                display = idea if idea else chat_uuid
            except Exception:\
                display = chat_uuid
        else:
            display = chat_uuid
        chat_list.append({'chatUUID': chat_uuid, 'display': display})
    return {'chats': chat_list}

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    data = request.get_json()
    username = data.get('username')
    chat_uuid = data.get('chatUUID')
    if not username or not chat_uuid:
        return {'error': 'Missing username or chatUUID'}, 400
    chat_dir = os.path.join(os.path.dirname(__file__), 'chats')
    index_file = os.path.join(chat_dir, 'index.json')
    if not os.path.exists(index_file):
        return {'error': 'No index file'}, 404
    with open(index_file, 'r') as f:
        idx = pyjson.load(f)
    user_chats = idx.get('users', {}).get(username, [])
    if chat_uuid in user_chats:
        user_chats.remove(chat_uuid)
        idx['users'][username] = user_chats
        with open(index_file, 'w') as f:
            pyjson.dump(idx, f)
    # del the chat file
    chat_file = os.path.join(chat_dir, f'{chat_uuid}.json')
    if os.path.exists(chat_file):
        os.remove(chat_file)
    return {'success': True}

@app.route('/create_chat')
def create_chat():
    username = request.args.get('username')
    if not username:
        return {'error': 'No username provided'}, 400
    chat_uuid = str(uuid.uuid4())
    chat_dir = os.path.join(os.path.dirname(__file__), 'chats')
    os.makedirs(chat_dir, exist_ok=True)
    chat_file = os.path.join(chat_dir, f'{chat_uuid}.json')
    with open(chat_file, 'w') as f:
        json.dump([], f)
    index_file = os.path.join(chat_dir, 'index.json')
    if not os.path.exists(index_file):
        with open(index_file, 'w') as f:
            pyjson.dump({"users": {}}, f)
    with open(index_file, 'r') as f:
        idx = pyjson.load(f)
    idx.setdefault("users", {})
    idx["users"].setdefault(username, [])
    if chat_uuid not in idx["users"][username]:
        idx["users"][username].append(chat_uuid)
    with open(index_file, 'w') as f:
        pyjson.dump(idx, f)
    session['chatUUID'] = chat_uuid
    return {'chatUUID': chat_uuid, 'message': 'Chat created successfully'}

if __name__ == '__main__':
    app.run()



app.run()