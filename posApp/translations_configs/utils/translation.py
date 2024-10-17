import json
import os

def load_translation(language_code):
    file_path = os.path.join(f'posApp/translations_configs/translations/{language_code}.json')
    default_file_path = os.path.join(f'posApp/translations_configs/translations/en.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        return translations
    except FileNotFoundError:
        # print(f'anga: {file_path}')
        with open(default_file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        return translations
