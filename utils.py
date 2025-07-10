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
