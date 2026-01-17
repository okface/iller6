import os
import yaml
import json
import glob
from datetime import datetime, timezone

# Constants
DATA_DIR = 'data'
OUTPUT_FILE = 'public/content.json'

def bundle():
    print(f"Scanning {DATA_DIR} for .yaml files...")
    
    subjects = {} # Structure: { "Folder": ["File1", "File2"] }
    all_questions = []
    
    # Walk through data directory
    # We look for data/{Folder}/{File}.yaml
    for root, dirs, files in os.walk(DATA_DIR):
        # SKIP hidden folders or specific ignore folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'incorrectly_formatted_questions']
        
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                full_path = os.path.join(root, file)
                
                # Get Subject (Folder name) and Topic (Filename without ext)
                rel_path = os.path.relpath(full_path, DATA_DIR)
                parts = rel_path.split(os.sep)
                
                # We expect data/Subject/Topic.yaml so parts should be [Subject, Topic.yaml]
                if len(parts) >= 2:
                    subject = parts[0]
                    topic = os.path.splitext(parts[-1])[0]
                    
                    # Store in subjects map
                    if subject not in subjects:
                        subjects[subject] = []
                    subjects[subject].append(topic)
                    
                    # Parse YAML
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            
                        if data and isinstance(data, list):
                            print(f"  Loaded {len(data)} questions from {subject}/{topic}")
                            # Append metadata to each question for tracking source
                            for q in data:
                                q['source'] = f"{subject}/{topic}"
                                all_questions.append(q)
                        else:
                            print(f"  Warning: {full_path} is empty or not a list.")
                            
                    except Exception as e:
                        print(f"  Error reading {full_path}: {e}")

    # Output structure
    output = {
        "subjects": subjects,
        "questions": all_questions,
        "meta": {
            "total_questions": len(all_questions),
            "generated_at": datetime.now(timezone.utc).isoformat() # ISO 8601 UTC
        }
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
        
    print(f"Bundle complete! wrote to {OUTPUT_FILE}")
    print(f"Total Subjects: {len(subjects)}")
    print(f"Total Questions: {len(all_questions)}")

if __name__ == '__main__':
    bundle()
