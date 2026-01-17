import os
import csv
import yaml
import json
import uuid
import concurrent.futures
import threading
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from collections import defaultdict

# -------------------------------------------------------------------------
# CONSTANTS & SETUP
# -------------------------------------------------------------------------
CSV_FILE = 'New_questions.csv'
IMPORT_LOG = 'data/medical_exam/new_questions_import_log.json'
DEST_DIR = 'data/medical_exam'

# Categories Map: Input Key (normalized) -> Output Filename
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
    'oron-nasa-hals-sjukdomar': 'oron_nasa_hals.yaml'
}

client = OpenAI()

# -------------------------------------------------------------------------
# PYDANTIC MODELS (Reused for OpenAI Structured Outputs)
# -------------------------------------------------------------------------
class StrictBaseModel(BaseModel):
    model_config = {"extra": "forbid"}

class Option(StrictBaseModel):
    text: str = Field(..., description="The text of the option")
    correct: bool = Field(..., description="True if this is the correct answer, else False")
    feedback: str = Field(..., description="Concise feedback (1 sentence) in Swedish on why this is right or wrong. Do NOT start with 'Rätt' or 'Fel'.")

class QuestionData(StrictBaseModel):
    # ID is generated in Python, not by LLM to ensure collision safety for this import
    type: str = Field("multiple_choice", description="Always 'multiple_choice'")
    tags: List[str] = Field(..., description="1-3 short medical tags in Swedish (e.g. 'Anatomi'). Do not reveal answer.")
    question: str = Field(..., description="Refined question text in Swedish")
    image: Optional[str] = Field(None, description="Always null for this import unless specified")
    options: List[Option]
    explanation: str = Field(..., description="Overall concise explanation (2-3 sentences) in Swedish.")

class ClassifiedQuestion(StrictBaseModel):
    category: str = Field(..., description="The medical category this question belongs to (e.g. 'Kardiologi', 'Neurologi')")
    data: QuestionData

# -------------------------------------------------------------------------
# PROMPT
# -------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are an expert Swedish medical tutor refactoring exam questions.
I will provide a raw question and a list of options. The raw data likely lacks the correct answer indication.
Your task is to:
1. Identify the correct answer based on medical knowledge.
2. Refine the question text if needed (fix typos, make concise).
3. Generate concise feedback for EACH option (why it is right/wrong). Do NOT start feedback with "Rätt" or "Fel".
4. Generate 1-3 tags.
5. Provide a short general explanation.
6. Classify the question into one of the following categories:
   [Neurologi, Internmedicin, Allmänmedicin, Psykiatri, Ortopedi, Kirurgi, Akutmedicin, Diabetologi, Endokrinologi, Gastroenterologi, Hepatologi, Hematologi, Kardiologi, Lungmedicin, Njurmedicin, Klinisk Farmakologi, Öron-Näsa-Hals]

Output must be valid JSON matching the schema.
Language: Swedish.
"""

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------
file_locks = defaultdict(threading.Lock)
log_lock = threading.Lock()

def load_log():
    if os.path.exists(IMPORT_LOG):
        try:
            with open(IMPORT_LOG, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def append_to_log(processed_id):
    with log_lock:
        current = load_log()
        current.add(processed_id)
        with open(IMPORT_LOG, 'w', encoding='utf-8') as f:
            json.dump(list(current), f)

def get_dest_file(category):
    normalized = category.lower().replace('ö', 'o').replace('ä', 'a').replace('å', 'a').replace(' ', '_').replace('-', '_') # Simple normalization attempts
    # Check exact map first
    if category.lower() in CATEGORY_FILES:
        return CATEGORY_FILES[category.lower()]
    
    # Try fuzzy match or default
    for key, val in CATEGORY_FILES.items():
        if key in normalized:
            return val
    
    return "blandat.yaml" # Fallback

def safe_append_yaml(filename, question_obj):
    full_path = os.path.join(DEST_DIR, filename)
    
    # We use a lock per filename to avoid race conditions when writing
    with file_locks[filename]:
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # We read existing to check format or just append? 
        # Appending in YAML is safe if we start a new list item.
        # But standard python yaml dump might not be easy to just 'append' to a list file without reading it all or using stream.
        # Given files aren't huge, reading and writing is safer for valid syntax.
        
        existing_data = []
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                try:
                    existing_data = yaml.safe_load(f) or []
                except yaml.YAMLError:
                    existing_data = []
        
        if not isinstance(existing_data, list):
            existing_data = []
            
        existing_data.append(question_obj)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            yaml.dump(existing_data, f, allow_unicode=True, sort_keys=False)

def build_schema():
    # Helper for OpenAI Strict Mode schema
    option_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "text": {"type": "string", "description": "The text of the option"},
            "correct": {"type": "boolean", "description": "True if this is the correct answer, else False"},
            "feedback": {
                "type": "string",
                "description": "Concise feedback (1 sentence) in Swedish on why this is right or wrong. Do NOT start with 'Rätt' or 'Fel'."
            }
        },
        "required": ["text", "correct", "feedback"]
    }

    question_data_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {"type": "string", "enum": ["multiple_choice"]},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
                "description": "1-3 short medical tags in Swedish"
            },
            "question": {"type": "string", "description": "Refined question text in Swedish"},
            "image": {
                "type": ["string", "null"],
                "description": "Always null for this import unless specified"
            },
            "options": {
                "type": "array",
                "items": option_schema,
                "minItems": 2,
                "maxItems": 6
            },
            "explanation": {"type": "string", "description": "Overall concise explanation (2-3 sentences) in Swedish."}
        },
        "required": ["type", "tags", "question", "image", "options", "explanation"]
    }

    classified_question_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "Neurologi", "Internmedicin", "Allmänmedicin", "Psykiatri", "Ortopedi", 
                    "Kirurgi", "Akutmedicin", "Diabetologi", "Endokrinologi", "Gastroenterologi", 
                    "Hepatologi", "Hematologi", "Kardiologi", "Lungmedicin", "Njurmedicin", 
                    "Klinisk Farmakologi", "Öron-Näsa-Hals"
                ]
            },
            "data": question_data_schema
        },
        "required": ["category", "data"]
    }

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ClassifiedQuestion",
            "schema": classified_question_schema,
            "strict": True
        }
    }

# -------------------------------------------------------------------------
# WORKER
# -------------------------------------------------------------------------
def process_data(row, original_csv_id):
    question_text = row['Question']
    raw_options = row['Options'] # List of strings
    
    # Prepare user message
    user_content = f"Question: {question_text}\nOptions:\n"
    for i, opt in enumerate(raw_options):
        user_content += f"{i+1}. {opt}\n"

    try:
        print(f"   Contacting OpenAI (gpt-5-mini) for ID {original_csv_id}...")
        completion = client.chat.completions.create(
            model="gpt-5-mini", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format=build_schema(),
            verbosity="low",
            reasoning_effort="medium"
        )
        
        result = json.loads(completion.choices[0].message.content)
        category = result['category']
        q_data = result['data']
        
        # Inject ID
        # We prefix with imp- to indicate import and use UUID
        q_data['id'] = f"imp-{uuid.uuid4().hex[:8]}"
        
        # Determine destination
        dest_file = get_dest_file(category)
        
        # Save
        safe_append_yaml(dest_file, q_data)
        
        # Log success
        append_to_log(original_csv_id)
        
        print(f"✅ Imported CSV ID {original_csv_id} -> {dest_file} (New ID: {q_data['id']})")
        return True

    except Exception as e:
        print(f"❌ Failed CSV ID {original_csv_id}: {str(e)}")
        return False

# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
def main():
    if not os.path.exists(CSV_FILE):
        print(f"File {CSV_FILE} not found.")
        return

    processed = load_log()
    
    rows_to_process = []
    
    print("Reading CSV...")
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f: # sig handles BOM if present (Excel)
        reader = csv.reader(f, delimiter=';')
        header = next(reader, None)
        
        if not header:
            print("Empty CSV.")
            return

        for row in reader:
            if not row: continue
            
            # Row structure: ID; Question; Opt1; Opt2; ...
            if len(row) < 3: 
                continue 
                
            csv_id = row[0]
            question = row[1]
            options = [o for o in row[2:] if o.strip()]
            
            # Check skip conditions
            if csv_id in processed:
                continue
            
            if "[SE BILD" in question or "SE BILD" in question:
                print(f"Skipping ID {csv_id} (Image required)")
                append_to_log(csv_id) # Mark as processed so we don't retry forever
                continue
                
            rows_to_process.append({
                'id': csv_id,
                'Question': question,
                'Options': options
            })

    print(f"Found {len(rows_to_process)} questions to process.")
    
    # Process in parallel
    WORKERS = 25 # Increased for speed with gpt-5-mini
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(process_data, r, r['id']): r['id'] for r in rows_to_process}
        
        for future in concurrent.futures.as_completed(futures):
            # We just wait for completion, logging handles output
            pass

    print("Done!")

if __name__ == "__main__":
    main()
