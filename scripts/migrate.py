import os
import yaml
import json
import uuid
import concurrent.futures
import time
from openai import OpenAI

# -------------------------------------------------------------------------
# CONSTANTS & SETUP
# -------------------------------------------------------------------------
SOURCE_FILE = 'data/medical_exam/incorrectly_formatted_questions/questions.yaml'
MIGRATION_LOG = 'data/medical_exam/migration_log.json'
DEST_DIR = 'data/medical_exam'

# Categories Map: Input Key (normalized) -> Output Filename
# We map the categories user requested.
CATEGORY_FILES = {
    'neurologi': 'neurologi.yaml',
    'internmedicin': 'internmedicin.yaml',
    'allmanmedicin': 'allmanmedicin.yaml',
    'psykiatri': 'psykiatri.yaml',
    'ortopedi': 'ortopedi.yaml',
    'kirurgi': 'kirurgi.yaml',
    'akutmedicin': 'akutmedicin.yaml',
    'diabetologi': 'diabetologi.yaml',
    'endokrinologi': 'endokrinologi.yaml',
    'gastroenterologi': 'gastroenterologi.yaml',
    'hepatologi': 'hepatologi.yaml',
    'hematologi': 'hematologi.yaml',
    'kardiologi': 'kardiologi.yaml',
    'lungmedicin': 'lungmedicin.yaml',
    'njurmedicin': 'njurmedicin.yaml',
    'klinisk farmakologi': 'klinisk_farmakologi.yaml',
    'oron-nasa-hals': 'oron_nasa_hals.yaml',
    'oron-nasa-hals-sjukdomar': 'oron_nasa_hals.yaml' # Alias
}

client = OpenAI() # Assumes ENV var is set

# -------------------------------------------------------------------------
# PROMPT
# -------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are an expert Swedish medical tutor refining exam questions.
Your task is to take a raw, potentially incomplete medical question and reformat it into a structured, high-quality YAML object.

Formatting Rules:
1. OUTPUT: Valid JSON only (so I can parse it easily).
2. Language: Swedish throughout.
3. Tags: Generate 1-3 concise medical tags (e.g. "Arytmi", "Diagnostik").
4. Feedback: VERY CONCISE (max 1-2 sentences). Explain WHY the option is wrong/right. Do NOT start with "Rätt" or "Fel".
5. Explanation: Concise summary (2-3 sentences max) of the concept.
6. Category: Choose the SINGLE best fit from this list:
   [Neurologi, Internmedicin, Allmänmedicin, Psykiatri, Ortopedi, Kirurgi, Akutmedicin, Diabetologi, Endokrinologi, Gastroenterologi, Hepatologi, Hematologi, Kardiologi, Lungmedicin, Njurmedicin, Klinisk Farmakologi, Öron-Näsa-Hals]

JSON Structure (Return this object):
{
  "category": "Kardiologi", 
  "data": {
    "type": "multiple_choice",
    "tags": ["Tag1", "Tag2"],
    "question": "Updated question text...",
    "image": null,
    "options": [
      { "text": "Option A", "correct": false, "feedback": "Concise reason..." },
      { "text": "Option B", "correct": true, "feedback": "Concise reason..." }
    ],
    "explanation": "General Explanation..."
  }
}
"""

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------

def load_log():
    if os.path.exists(MIGRATION_LOG):
        with open(MIGRATION_LOG, 'r') as f:
            return set(json.load(f))
    return set()

def save_log(processed_ids):
    with open(MIGRATION_LOG, 'w') as f:
        json.dump(list(processed_ids), f)

def append_to_yaml(filename, data_object):
    """Thread-safe append roughly (we use a file lock in practice, but here we process linearly after generation or use simple appends)"""
    # Simply appending YAML document separator might be safer if files are large, 
    # but here we load-append-dump to keep valid structure.
    # To be safe with threads, we can write separate temp files or lock.
    # For this script, we will gather results and write in main thread to avoid corruption.
    pass 

# -------------------------------------------------------------------------
# WORKER
# -------------------------------------------------------------------------

def process_question(raw_q):
    """
    Takes a raw question dict from source yaml.
    Returns (category_filename, cleaned_data_object) or None.
    """
    try:
        # Prompt construction
        user_prompt = f"""
        Original Data:
        Category Hint: {raw_q.get('category', 'Unknown')}
        Question: {raw_q.get('question')}
        Options: {raw_q.get('options')}
        Correct Index: {raw_q.get('correct_option_index')}
        More Info: {raw_q.get('more_information')}
        
        Refine and Format.
        """
        
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" },
            verbosity="low",
            reasoning_effort="medium"
        )
        
        result = json.loads(response.choices[0].message.content)
        
        category_name = result['category'].lower().replace('ö', 'o').replace('ä', 'a').replace('å', 'a').replace(' ', '_')
        
        # Map to filename 
        # Heuristic matching
        target_file = None
        for key, fname in CATEGORY_FILES.items():
            if key in category_name:
                target_file = fname
                break
        
        if not target_file:
            # Fallback to internmedicin or generic if unknown
            target_file = 'internmedicin.yaml' 

        # Add ID
        data = result['data']
        data['id'] = f"med-{category_name[:3]}-{uuid.uuid4().hex[:6]}"
        
        return (target_file, data)

    except Exception as e:
        print(f"Error processing {raw_q.get('number', '?')}: {e}")
        return None

# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------

def main():
    print("Loading source data...")
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        source_data = yaml.safe_load(f)
    
    print(f"Found {len(source_data)} questions.")
    
    processed_ids = load_log()
    print(f"Already processed: {len(processed_ids)}")
    
    # Filter out already processed
    to_process = [q for q in source_data if str(q.get('number')) not in processed_ids]
    print(f"Remaining to process: {len(to_process)}")
    
    # Batch processing
    BATCH_SIZE = 10 # Process in small batches to save frequently
    
    # We'll use a ThreadPoolExecutor
    # BUT we need to be careful not to spam the API too hard if rate limits exists.
    # 5 workers seems safe.
    
    current_batch_results = {} # { filename: [questions] }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # We submit all, but iterate results as they come
        # Actually better to submit in chunks
        
        for i in range(0, len(to_process), BATCH_SIZE):
            batch = to_process[i : i+BATCH_SIZE]
            futures = {executor.submit(process_question, q): q for q in batch}
            
            print(f"Processing batch {i} - {i+BATCH_SIZE}...")
            
            for future in concurrent.futures.as_completed(futures):
                raw_q = futures[future]
                res = future.result()
                
                if res:
                    fname, data = res
                    if fname not in current_batch_results:
                        current_batch_results[fname] = []
                    current_batch_results[fname].append(data)
                    
                    # Mark as processed
                    processed_ids.add(str(raw_q.get('number')))
            
            # SAVE BATCH
            print("  Saving batch...")
            for fname, new_questions in current_batch_results.items():
                fpath = os.path.join(DEST_DIR, fname)
                
                # Load existing to append
                if os.path.exists(fpath):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        existing = yaml.safe_load(f) or []
                else:
                    existing = []
                
                existing.extend(new_questions)
                
                with open(fpath, 'w', encoding='utf-8') as f:
                    yaml.dump(existing, f, sort_keys=False, allow_unicode=True)
            
            # Clear batch buffer
            current_batch_results = {}
            # Update Log
            save_log(processed_ids)
            
            # Nicety
            time.sleep(1)

    print("Migration complete!")

if __name__ == '__main__':
    main()
