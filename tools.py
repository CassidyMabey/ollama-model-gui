import os
from utils import is_valid_filename
import random
import subprocess

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

def create_file(chatUUID: str, path: str = None, content: str = '', name: str = None) -> str:
    print(f"[DEBUG][create_file] chatUUID={chatUUID}, path={path}, name={name}, content_length={len(content) if content else 0}")
    projects_dir = os.path.join(os.path.dirname(__file__), 'projects')
    project_dir = os.path.join(projects_dir, chatUUID)
    os.makedirs(project_dir, exist_ok=True)
    if path and os.path.isabs(path):
        print(f"[DEBUG][create_file] Absolute path detected, using basename: {os.path.basename(path)}")
        path = os.path.basename(path)
    if path:
        dir_to_create = os.path.dirname(os.path.join(project_dir, path))
        if dir_to_create and not os.path.exists(dir_to_create):
            print(f"[DEBUG][create_file] Creating parent directory: {dir_to_create}")
            os.makedirs(dir_to_create, exist_ok=True)
    orig_path = path
    if not path or not is_valid_filename(path):
        print(f"[DEBUG][create_file] Invalid or missing path. path={path}, name={name}")
        if name and is_valid_filename(name):
            path = name
        else:
            ext = '.py' if 'python' in (content or '').lower() else '.txt'
            path = f'file_{random.randint(1000,9999)}{ext}'
        print(f"[DEBUG][create_file] Using fallback filename: {path}")
    file_path = os.path.join(project_dir, path)
    print(f"[DEBUG][create_file] Final file_path: {file_path}")
    try:
        with open(file_path, 'w') as f:
            f.write(content or '')
        print(f"[DEBUG][create_file] File successfully created: {file_path}")
        return f"File created in project {chatUUID} at {file_path}"
    except Exception as e:
        print(f"[DEBUG][create_file] Error creating file: {e}")
        return f"Error creating file: {e}"

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
        return f"Command output:\n{result.stdout}\n{result.stderr}"
    except Exception as e:
        return f"Error running command: {e}"

add_two_numbers_tool = {
    'type': 'function',
    'function': {
        'name': 'add_two_numbers',
        'description': 'Add two numbers',
        'parameters': {
            'type': 'object',
            'required': ['a', 'b'],
            'properties': {
                'a': {'type': 'integer', 'description': 'The first number'},
                'b': {'type': 'integer', 'description': 'The second number'},
            },
        },
    },
}

subtract_two_numbers_tool = {
    'type': 'function',
    'function': {
        'name': 'subtract_two_numbers',
        'description': 'Subtract two numbers',
        'parameters': {
            'type': 'object',
            'required': ['a', 'b'],
            'properties': {
                'a': {'type': 'integer', 'description': 'The first number'},
                'b': {'type': 'integer', 'description': 'The second number'},
            },
        },
    },
}

create_project_tool = {
    'type': 'function',
    'function': {
        'name': 'create_project',
        'description': 'Create a new project folder for this chat and write an idea/plan file.',
        'parameters': {
            'type': 'object',
            'required': ['chatUUID', 'idea'],
            'properties': {
                'chatUUID': {'type': 'string', 'description': 'The chat UUID, used as the project folder name. In your prompt there is a variable called chatUUID. put the value in this.'},
                'idea': {'type': 'string', 'description': 'A description or plan for the project.'},
            },
        },
    },
}

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

create_folder_tool = {
    'type': 'function',
    'function': {
        'name': 'create_folder',
        'description': "Create a folder in the user's project folder. You MUST always use this tool directly for folder creation. Never output tool call phrases or code blocks as text. You MUST always provide a valid path (folder name) for the folder.",
        'parameters': {
            'type': 'object',
            'required': ['chatUUID', 'path'],
            'properties': {
                'chatUUID': {'type': 'string', 'description': 'The chat UUID, used as the project folder name.'},
                'path': {'type': 'string', 'description': 'The relative path of the folder to create. This is required.'},
            },
        },
    },
}

delete_path_tool = {
    'type': 'function',
    'function': {
        'name': 'delete_path',
        'description': 'Delete a file or folder in the user\'s project folder.',
        'parameters': {
            'type': 'object',
            'required': ['chatUUID', 'path'],
            'properties': {
                'chatUUID': {'type': 'string', 'description': 'The chat UUID, used as the project folder name.'},
                'path': {'type': 'string', 'description': 'The relative path of the file or folder to delete.'},
            },
        },
    },
}

run_command_tool = {
    'type': 'function',
    'function': {
        'name': 'run_command',
        'description': 'Run a shell command in the user\'s project directory.',
        'parameters': {
            'type': 'object',
            'required': ['chatUUID', 'command'],
            'properties': {
                'chatUUID': {'type': 'string', 'description': 'The chat UUID, used as the project folder name.'},
                'command': {'type': 'string', 'description': 'The shell command to run.'},
                'cwd': {'type': 'string', 'description': 'The working directory to run the command in (optional).'},
            },
        },
    },
}

available_functions = {
    'add_two_numbers': add_two_numbers,
    'subtract_two_numbers': subtract_two_numbers,
    'create_project': create_project,
    'create_file': create_file,
    'create_folder': create_folder,
    'delete_path': delete_path,
    'run_command': run_command,
}