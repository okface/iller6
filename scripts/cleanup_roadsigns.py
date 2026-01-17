# Helper script to clean up road sign questions that give away the answer
import yaml
import re
import os

def clean_questions(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data:
        return

    count = 0
    removed_count = 0
    cleaned_data = []

    for q in data:
        # 1. Remove questions with broken images (null image) if they seem to be visual questions
        # Heuristic: if question says "this sign" or "in result" but image is null
        text = q.get('question', '').lower()
        img = q.get('image')
        
        if (not img) and ('skylt' in text or 'märke' in text or 'bild' in text):
             print(f"Removing question (missing image): {q['id']}")
             removed_count += 1
             continue

        # 2. Fix "giving away the answer"
        # Regex to find: "Vad betyder skylten 'X' (filename)?" -> "Vad betyder skylten?"
        # Pattern 1: Vad betyder skylten '...' (vagmarke_...)?
        # Pattern 2: Vad innebär skylten '...'?
        
        old_q = q['question']
        
        # Remove filename in parens
        new_q = re.sub(r'\s*\([^\)]+\)\?', '?', old_q) # Remove (filename)? at end
        new_q = re.sub(r'\s*\([^\)]+\)', '', new_q)    # Remove (filename) anywhere
        
        # Remove quoted name
        # Ex: "Vad betyder skylten 'Förbud mot infart'?" -> "Vad betyder denna skylt?"
        if "'" in new_q or '"' in new_q:
            # Try to replace specific phrase patterns
            new_q = re.sub(r"skylten\s+['\"].+?['\"]", "denna skylt", new_q, flags=re.IGNORECASE)
            new_q = re.sub(r"märket\s+['\"].+?['\"]", "detta märke", new_q, flags=re.IGNORECASE)
        
        if new_q != old_q:
            print(f"Fixed: {old_q} -> {new_q}")
            q['question'] = new_q
            count += 1
        
        cleaned_data.append(q)

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(cleaned_data, f, sort_keys=False, allow_unicode=True)

    print(f"Cleaned {count} questions. Removed {removed_count} broken questions.")

# Run on the relevant files
clean_questions('data/korkortsteori/vagmarken_auto.yaml')
clean_questions('data/korkortsteori/trafik_och_vagmarken.yaml')
