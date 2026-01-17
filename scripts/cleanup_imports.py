import os
import yaml
import glob

DATA_DIR = 'data/medical_exam'

def main():
    print("Starting cleanup of imported questions (ID starting with 'imp-')...")
    
    yaml_files = glob.glob(os.path.join(DATA_DIR, '*.yaml'))
    
    total_removed = 0
    
    for fpath in yaml_files:
        if 'incorrectly_formatted_questions' in fpath:
            continue
            
        with open(fpath, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
            except Exception as e:
                print(f"Error reading {fpath}: {e}")
                continue
        
        if not data or not isinstance(data, list):
            continue
            
        original_count = len(data)
        # Filter out questions with ID starting with 'imp-'
        clean_data = [q for q in data if not (isinstance(q, dict) and q.get('id', '').startswith('imp-'))]
        
        removed_count = original_count - len(clean_data)
        
        if removed_count > 0:
            with open(fpath, 'w', encoding='utf-8') as f:
                yaml.dump(clean_data, f, allow_unicode=True, sort_keys=False)
            print(f"Removed {removed_count} questions from {os.path.basename(fpath)}")
            total_removed += total_removed + removed_count
    
    # Remove the log file
    log_file = os.path.join(DATA_DIR, 'new_questions_import_log.json')
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"Removed log file: {log_file}")
        
    print(f"Cleanup complete. Total removed: {total_removed}")

if __name__ == "__main__":
    main()
