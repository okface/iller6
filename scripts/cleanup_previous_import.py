import os
import yaml
import json

DATA_DIR = 'data/medical_exam'
IMPORT_LOG = 'data/medical_exam/new_questions_import_log.json'

def main():
    print("--- Cleaning up previous 'imp-' questions ---")
    
    # 1. Clean YAML files
    files_cleaned = 0
    questions_removed = 0
    
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith('.yaml'):
            continue
            
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
            except:
                print(f"Skipping broken file: {filename}")
                continue
                
        if not isinstance(data, list):
            continue
            
        # Filter out questions starting with 'imp-'
        original_count = len(data)
        new_data = [q for q in data if not str(q.get('id', '')).startswith('imp-')]
        
        removed = original_count - len(new_data)
        
        if removed > 0:
            questions_removed += removed
            files_cleaned += 1
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(new_data, f, sort_keys=False, allow_unicode=True)
            print(f"cleaned {filename}: removed {removed} questions.")

    print(f"\nTotal questions removed: {questions_removed} from {files_cleaned} files.")

    # 2. Reset Log
    if os.path.exists(IMPORT_LOG):
        print("\nResetting import log...")
        with open(IMPORT_LOG, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("Log cleared.")
    else:
        print("\nLog file not found, nothing to reset.")

    print("\nCleanup complete. You can now re-run the import script.")

if __name__ == "__main__":
    main()
