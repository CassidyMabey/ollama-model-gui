import ollama
import yfinance as yf
from typing import Dict, Any, Callable
import json
import re
import os
import random
import subprocess
import base64

def is_valid_filename(filename, max_length=100):
    if not filename or len(filename) > max_length:
        return False
    if '\n' in filename or '\r' in filename:
        return False
    if filename.strip().startswith('```') or filename.strip().lower().startswith('to run'):
        return False
    if '..' in filename or filename.startswith('/'):
        return False
    if any(c in filename for c in ['<', '>', ':', '"', '|', '?', '*']):
        return False
    return True

def add_two_numbers(a: int, b: int) -> int:
    return int(a) + int(b)

def subtract_two_numbers(a: int, b: int) -> int:
    return int(a) - int(b)

def create_project(chatUUID: str, idea: str) -> str:
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    os.makedirs(project_dir, exist_ok=True)
    plan_file = os.path.join(project_dir, 'project_idea.txt')
    with open(plan_file, 'w') as f:
        f.write(idea)
    return f"Project created at {project_dir} with idea file."

def create_file(chatUUID: str, path: str = None, content: str = '', name: str = None, append: bool = False, encoded: bool = False) -> str:
    print(f"[DEBUG][create_file] chatUUID={chatUUID}, path={path}, name={name}, content_length={len(content) if content else 0}, append={append}, encoded={encoded}")
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    os.makedirs(project_dir, exist_ok=True)
    
    if path:
        path = path.replace(' ', '_').replace('project_', '').replace('project/', '')
        if path.startswith('_'):
            path = path[1:]
        if os.path.isabs(path):
            print(f"[DEBUG][create_file] Absolute path detected, using basename: {os.path.basename(path)}")
            path = os.path.basename(path)
    
    final_filename = None
    if path and is_valid_filename(path):
        final_filename = path
    elif name and is_valid_filename(name):
        final_filename = name
        if not final_filename.endswith('.py') and 'python' in (content or '').lower():
            final_filename += '.py'
    else:
        base_name = name if name else 'file'
        if not base_name.endswith('.py'):
            base_name += '.py'
        final_filename = base_name.replace(' ', '_')
    
    print(f"[DEBUG][create_file] Using filename: {final_filename}")
    
    if encoded and content:
        try:
            content = base64.b64decode(content).decode('utf-8')
        except Exception as e:
            print(f"[DEBUG][create_file] Error decoding base64 content: {e}")
            return f"Error decoding base64 content: {e}"
    if not content or content.strip() == '':
        if final_filename.endswith('.py'):
            content = '''# Python file created by Ollama
# Add your code here

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        else:
            content = '# File created by Ollama\n# Add your content here\n'
        print(f"[DEBUG][create_file] Content was empty, using default template")
    file_path = os.path.join(project_dir, final_filename)
    print(f"[DEBUG][create_file] Final file_path: {file_path}")
    
    try:
        mode = 'a' if append else 'w'
        with open(file_path, mode) as f:
            f.write(content)
        print(f"[DEBUG][create_file] File {'appended' if append else 'created'} successfully: {file_path}")
        return f"File '{final_filename}' {'appended' if append else 'created'} in project {chatUUID} at {file_path}"
    except Exception as e:
        print(f"[DEBUG][create_file] Error creating/appending file: {e}")
        return f"Error creating/appending file: {e}"

def append_file(chatUUID: str, filename: str, line: str) -> str:

    print(f"[DEBUG][append_file] chatUUID={chatUUID}, filename={filename}, line_length={len(line) if line else 0}")
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    os.makedirs(project_dir, exist_ok=True)

    if filename:
        filename = filename.replace(' ', '_').replace('project_', '').replace('project/', '')
        if filename.startswith('_'):
            filename = filename[1:]
        if os.path.isabs(filename):
            print(f"[DEBUG][append_file] Absolute path detected, using basename: {os.path.basename(filename)}")
            filename = os.path.basename(filename)
    
    if not filename or not is_valid_filename(filename):
        return f"Error: Invalid filename '{filename}'"
    
    file_path = os.path.join(project_dir, filename)
    print(f"[DEBUG][append_file] Final file_path: {file_path}")
    
    try:
        if line and not line.endswith('\n'):
            line += '\n'
        
        with open(file_path, 'a') as f:
            f.write(line)
        print(f"[DEBUG][append_file] Line appended successfully to {file_path}")
        return f"Line appended to '{filename}' in project {chatUUID}"
    except Exception as e:
        print(f"[DEBUG][append_file] Error appending to file: {e}")
        return f"Error appending to file: {e}"

def create_folder(chatUUID: str, path: str = None, name: str = None) -> str:
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    os.makedirs(project_dir, exist_ok=True)
    
    if path and path.startswith('/'):
        path = os.path.basename(path)
    
    folder_path = os.path.join(project_dir, path if path else (name if name else f'folder_{random.randint(1000,9999)}'))
    os.makedirs(folder_path, exist_ok=True)
    return f"Folder created in project {chatUUID}"

def delete_path(chatUUID: str, path: str) -> str:
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    target_path = os.path.join(project_dir, path)
    import shutil
    
    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
        return f"Folder {path} deleted in project {chatUUID}."
    elif os.path.isfile(target_path):
        os.remove(target_path)
        return f"File {path} deleted in project {chatUUID}."
    else:
        return f"Path {path} does not exist in project {chatUUID}."

def run_command(chatUUID: str, command: str, cwd: str = None) -> str:
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    try:
        result = subprocess.run(command, shell=True, cwd=cwd or project_dir, capture_output=True, text=True, timeout=10)
        print(f"[DEBUG][run_command] Ran: {command}\nstdout: {result.stdout}\nstderr: {result.stderr}")
        return f"Command output:\n{result.stdout}\n{result.stderr}"
    except Exception as e:
        print(f"[DEBUG][run_command] Error running command: {e}")
        return f"Error running command: {e}"

# Tool definitions
create_file_tool = {
    'type': 'function',
    'function': {
        'name': 'create_file',
        'description': "Create a file in the user's project folder and write content to it. You MUST always use this tool directly for file creation. Never output tool call phrases or code blocks as text. You MUST always provide a valid path (filename) for the file.",
        'parameters': {
            'type': 'object',
            'required': ['chatUUID', 'path', 'content', 'name'],
            'properties': {
                'chatUUID': {'type': 'string', 'description': 'The chat UUID, used as the project folder name.'},
                'path': {'type': 'string', 'description': 'The relative path of the file to create. This is required.'},
                'content': {'type': 'string', 'description': 'The code or text to write to the file.'},
                'name': {'type': 'string', 'description': 'The name of the file to create (must include extension).'},
            },
        },
    },
}

append_file_tool = {
    'type': 'function',
    'function': {
        'name': 'append_file',
        'description': "Append a single line to a file. Creates the file if it doesn't exist. Use this for building large files line by line to avoid content truncation issues.",
        'parameters': {
            'type': 'object',
            'required': ['chatUUID', 'filename', 'line'],
            'properties': {
                'chatUUID': {'type': 'string', 'description': 'The chat UUID, used as the project folder name.'},
                'filename': {'type': 'string', 'description': 'The name of the file to append to (must include extension).'},
                'line': {'type': 'string', 'description': 'The single line of text/code to append to the file.'},
            },
        },
    },
}

available_functions: Dict[str, Callable] = {
    'create_file': create_file,
    'append_file': append_file,
    'add_two_numbers': add_two_numbers,
    'subtract_two_numbers': subtract_two_numbers,
    'create_project': create_project,
    'create_folder': create_folder,
    'delete_path': delete_path,
    'run_command': run_command,
}

def robust_json_parse(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            content_array_pattern = r'"content"\s*:\s*\[\s*\{\s*"type"\s*:\s*"string"\s*,\s*"value"\s*:\s*"([^"]*(?:\\"[^"]*)*)"\s*\}\s*\]'
            match = re.search(content_array_pattern, json_str)
            if match:
                content_value = match.group(1)
                content_value = content_value.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
                json_str = re.sub(content_array_pattern, f'"content": "{content_value.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34)).replace(chr(10), chr(92)+chr(110))}"', json_str)
            
            def remove_duplicate_keys(json_text):
                pattern = r'"([^"]+)"\s*:\s*("(?:[^"\\]|\\.)*"|[^,}]+)'
                matches = list(re.finditer(pattern, json_text))
                

                seen_keys = {}
                for match in matches:
                    key = match.group(1)
                    if key in seen_keys:
                        start_pos, end_pos = seen_keys[key]
                        json_text = json_text[:start_pos] + json_text[end_pos:]
                        offset = end_pos - start_pos
                        for other_key, (other_start, other_end) in seen_keys.items():
                            if other_start > start_pos:
                                seen_keys[other_key] = (other_start - offset, other_end - offset)
                    
                    seen_keys[key] = (match.start(), match.end())
                
                return json_text
            
            json_str = remove_duplicate_keys(json_str)
            
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Problematic JSON: {json_str[:500]}...")
        return None

def extract_and_execute_tool_call(response_content):
    print(f"DEBUG: Processing response content: {response_content[:200]}...")
    
    data = robust_json_parse(response_content)
    
    if data and isinstance(data, dict):
        if data.get('type') == 'function' and data.get('name') in available_functions:
            function_name = data['name']
            parameters = data.get('parameters', {})
            
            print(f"DEBUG: Found function call: {function_name}")
            print(f"DEBUG: Parameters: {parameters}")
            
            if 'content' in parameters and isinstance(parameters['content'], list):
                parameters['content'] = '\n'.join([
                    x.get('value', str(x)) for x in parameters['content'] 
                    if isinstance(x, dict)
                ])
            
            if 'path' in parameters and isinstance(parameters['path'], str):
                if parameters['path'].endswith('/') and 'name' in parameters:
                    parameters['path'] = parameters['name']
            
            try:
                function = available_functions[function_name]
                result = function(**parameters)
                print(f"Function '{function_name}' executed successfully:")
                print(f"Result: {result}")
                return True
            except Exception as e:
                print(f"Error executing function '{function_name}': {e}")
                return False
    
    print("No valid function call found in response")
    return False

def build_file_line_by_line(chatUUID, filename, lines):

    print(f"[DEBUG][build_file_line_by_line] Building {filename} with {len(lines)} lines...")
    
    create_file(chatUUID, path=filename, content='', name=filename)
    
    for i, line in enumerate(lines):
        result = append_file(chatUUID, filename, line)
        if "Error" in result:
            print(f"[DEBUG][build_file_line_by_line] Error on line {i+1}: {result}")
            return False
        if i % 10 == 0: 
            print(f"[DEBUG][build_file_line_by_line] Progress: {i+1}/{len(lines)} lines")
    
    print(f"[DEBUG][build_file_line_by_line] Successfully built {filename}")
    return True

def stream_file_content(chatUUID, filename, content, chunk_size=500):

    print(f"[DEBUG][stream_file_content] DEPRECATED - Use build_file_line_by_line instead")
    lines = content.split('\n')
    return build_file_line_by_line(chatUUID, filename, lines)

if __name__ == "__main__":
    restricted_tools = [create_file_tool]
    prompt = '''You must use the create_file tool to create a file named "spaceinvaders.py" in the project with chatUUID "ccoeb981-72da-4cfa-9224-824576eac8a7".\n\nIMPORTANT: You must provide the complete Python code for a Space Invaders game using pygame in the "content" parameter. The file should contain a fully functional game with:\n- Player spaceship that moves left/right\n- Enemies that move across the screen\n- Shooting mechanics\n- Basic collision detection\n- Score system\n\nMake sure to:\n1. Set the "name" parameter to "spaceinvaders.py" \n2. Set the "path" parameter to "spaceinvaders.py"\n3. Fill the "content" parameter with the complete Python code (not empty!)\n4. Include all necessary imports (pygame, etc.)\n\nThe content parameter must not be empty - it should contain hundreds of lines of Python code for the game.'''
    print('Prompt:', prompt)
    response = ollama.chat(
        'llama3.2:1b',
        messages=[{'role': 'user', 'content': prompt}],
        tools=restricted_tools,
        stream=False,
    )
    print('Raw ollama response:', response)
    msg_content = response.message.content if hasattr(response.message, 'content') else response['message']['content']

    import re
    content_match = re.search(r'"content"\s*:\s*"(.*)"\s*,?\s*([\}\]])', msg_content, re.DOTALL)
    if content_match:
        raw_content = content_match.group(1)
        raw_content = raw_content.encode('utf-8').decode('unicode_escape')
        filename = 'spaceinvaders.py'
        chatUUID = 'ccoeb981-72da-4cfa-9224-824576eac8a7'
        encoded_content = base64.b64encode(raw_content.encode('utf-8')).decode('ascii')
        create_file(chatUUID=chatUUID, path=filename, content=encoded_content, name=filename, append=False, encoded=True)
        print(f"[DEBUG] Finished building {filename} in one go using create_file and base64 encoding (robust extraction).")
    else:
        data = robust_json_parse(msg_content)
        if data and isinstance(data, dict):
            if data.get('type') == 'function' and data.get('name') == 'create_file':
                params = data.get('parameters', {})
                filename = params.get('name') or params.get('path') or 'spaceinvaders.py'
                content = params.get('content', '')
                chatUUID = params.get('chatUUID')
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
                create_file(chatUUID=chatUUID, path=filename, content=encoded_content, name=filename, append=False, encoded=True)
                print(f"[DEBUG] Finished building {filename} in one go using create_file and base64 encoding.")
            else:
                extract_and_execute_tool_call(msg_content)
        else:
            extract_and_execute_tool_call(msg_content)