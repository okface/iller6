import os
import sys
import yaml
import json
import uuid
import collections
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# -------------------------------------------------------------------------
# SETUP
# -------------------------------------------------------------------------
client = OpenAI() 

DATA_DIR = 'data'

# -------------------------------------------------------------------------
# PYDANTIC MODELS (Structured Output 2025/2026 Standard)
# -------------------------------------------------------------------------

# Note:
# - The Pydantic models validate the model output we receive (Python-side safety).
# - OpenAI Structured Outputs requires an explicit JSON Schema (response_format json_schema).
#   We keep a separate schema builder to guarantee strict requirements like
#   additionalProperties=false across all nested objects.

# Helper for OpenAI Strict Mode (requires additionalProperties: false)
class StrictBaseModel(BaseModel):
    model_config = {"extra": "forbid"}

class Option(StrictBaseModel):
    text: str = Field(..., description="Svarsalternativets text")
    correct: bool = Field(..., description="True om detta är rätt svar, annars False")
    feedback: str = Field(..., description="Mycket koncis feedback (1 mening) om varför detta är rätt eller fel. Börja INTE med 'Rätt' eller 'Fel'.")

class Question(StrictBaseModel):
    id: str = Field(..., description="Ett unikt ID, t.ex 'med-gen-ab12'")
    type: str = Field("multiple_choice", description="Alltid 'multiple_choice'")
    tags: List[str] = Field(..., description="1-3 korta taggar på svenska (t.ex 'Anatomi') OBS: Taggar ska inte ge bort svaret.")
    question: str = Field(..., description="Själva frågetexten")
    image: Optional[str] = Field(None, description="Filename i assets eller null")
    options: List[Option]
    explanation: str = Field(..., description="Övergripande koncis förklaring (2-3 meningar)")

class QuestionBatch(StrictBaseModel):
    questions: List[Question]


def build_question_batch_schema():
    # OpenAI Structured Outputs "strict" requires JSON Schema where:
    # - every object has `type: object`
    # - `required` exists and includes every key in `properties`
    # - `additionalProperties: false`
    # Optional fields must still be required, but can allow `null`.
    option_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "text": {"type": "string", "description": "Svarsalternativets text"},
            "correct": {"type": "boolean", "description": "True om detta är rätt svar, annars False"},
            "feedback": {
                "type": "string",
                "description": "Mycket koncis feedback (1 mening) om varför detta är rätt eller fel, i relation till frågan och övriga alternativ. Börja INTE med 'Rätt' eller 'Fel'.",
            },
        },
        "required": ["text", "correct", "feedback"],
    }

    question_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "description": "Ett unikt ID, t.ex 'med-gen-ab12'"},
            "type": {"type": "string", "enum": ["multiple_choice"], "description": "Alltid 'multiple_choice'"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
                "description": "1-3 korta taggar på svenska (t.ex 'Anatomi') OBS: Taggar ska inte ge bort svaret.",
            },
            "question": {"type": "string", "description": "Själva frågetexten"},
            "image": {
                "type": ["string", "null"],
                "description": "Filename i assets eller null",
            },
            "options": {
                "type": "array",
                "items": option_schema,
                "minItems": 4,
                "maxItems": 6,
            },
            "explanation": {
                "type": "string",
                "description": "Övergripande koncis förklaring (2-3 meningar)",
            },
        },
        "required": ["id", "type", "tags", "question", "image", "options", "explanation"],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "questions": {
                "type": "array",
                "items": question_schema,
                "minItems": 1,
            }
        },
        "required": ["questions"],
    }

# -------------------------------------------------------------------------
# PROMPTS
# -------------------------------------------------------------------------

SYSTEM_PROMPT = """
Du är en expertlärare som skapar högkvalitativa, avancerade flashcards-frågor.
Ditt mål är att generera svåra, precisa och pedagogiska flervalsfrågor PÅ SVENSKA.

Språk: Svenska.
Ton: Professionell, akademisk med.

INNEHÅLLSKRAV:
1. Feedback MÅSTE vara koncis (1 mening). Börja INTE med "Rätt" eller "Fel", det visas automatiskt.
2. Explanation MÅSTE vara syntes-orienterad (2-3 meningar).
3. Svårighetsgrad: Läkarexamen / Specialistnivå.
"""

# -------------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------------

def get_subjects():
    """Returns a list of folders in data/ excluding hidden/utility folders."""
    return [d for d in os.listdir(DATA_DIR) 
            if os.path.isdir(os.path.join(DATA_DIR, d)) 
            and not d.startswith('.') 
            and d != 'incorrectly_formatted_questions']

def get_topics(subject):
    """Returns list of .yaml filenames in data/subject/"""
    path = os.path.join(DATA_DIR, subject)
    if not os.path.exists(path): return []
    return [f for f in os.listdir(path) if f.endswith('.yaml')]

def load_existing(filepath):
    """Loads existing YAML."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return yaml.safe_load(f) or []
        except:
            return []

def analyze_existing_content(questions):
    """Summary of existing Tags for the prompt."""
    tag_counts = collections.Counter()
    
    for q in questions:
        tags = q.get('tags', [])
        if isinstance(tags, list):
            for t in tags:
                tag_counts[t] += 1
                
    summary = {tag: count for tag, count in tag_counts.most_common(50)}
    return summary, len(questions)


def analyze_tag_usage_across_subject(subject: str):
    """Counts tag usage across all topics within a subject folder."""
    tag_counts = collections.Counter()
    total_questions = 0

    subject_path = os.path.join(DATA_DIR, subject)
    if not os.path.isdir(subject_path):
        return {}, 0

    for fname in os.listdir(subject_path):
        if not (fname.endswith('.yaml') or fname.endswith('.yml')):
            continue
        full_path = os.path.join(subject_path, fname)
        questions = load_existing(full_path)
        if not isinstance(questions, list):
            continue

        for q in questions:
            if not isinstance(q, dict):
                continue
            tags = q.get('tags', [])
            if isinstance(tags, list):
                for t in tags:
                    tag_counts[t] += 1
            total_questions += 1

    summary = {tag: count for tag, count in tag_counts.most_common(100)}
    return summary, total_questions

def main():
    print("--- Iller5 Content Factory (Structured v2026) ---")
    
    # 1. Select Subject
    subjects = get_subjects()
    if not subjects:
        print("No subjects found in data/.")
        sys.exit(1)
        
    print("\nSubjects:")
    for i, s in enumerate(subjects):
        print(f"{i+1}. {s}")
        
    try:
        s_idx = int(input("\nSelect Subject (Number): ")) - 1
        subject = subjects[s_idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        sys.exit(1)
    
    # 2. Select Topic
    topics = get_topics(subject)
    print(f"\nTopics in {subject}:")
    for i, t in enumerate(topics):
        print(f"{i+1}. {t}")
    print(f"{len(topics)+1}. [New Topic]")
    
    try:
        t_idx = int(input("\nSelect Topic (Number): ")) - 1
    except (ValueError, IndexError):
        print("Invalid selection.")
        sys.exit(1)
    
    if t_idx == len(topics):
        new_name = input("Enter new topic name (e.g. 'fysiologi'): ").strip()
        if not new_name.endswith('.yaml'):
            new_name += '.yaml'
        filename = new_name
    else:
        filename = topics[t_idx]
        
    filepath = os.path.join(DATA_DIR, subject, filename)
    
    # 3. Analyze Context
    existing = load_existing(filepath)
    tag_summary, total_count = analyze_existing_content(existing)
    subject_tag_summary, subject_total_count = analyze_tag_usage_across_subject(subject)
    
    print(f"  Loaded {total_count} existing questions.")
    
    # 4. Config
    use_images = input("Generate Image-based questions? (y/N): ").lower().strip() == 'y'
    
    try:
        c_in = input("How many questions to generate? (Default 5): ").strip()
        count_req = int(c_in) if c_in else 5
    except ValueError:
        print("Invalid number, defaulting to 5.")
        count_req = 5
    
    if use_images:
        print("  NOTE: You must manually add images to public/assets/ matching the generated IDs.")

    # 5. Call LLM
    print(f"\nContacting OpenAI (gpt-5-mini) via Structured Outputs...")
    
    user_prompt = f"""
    Ämne: {subject}
    Topic: {filename.replace('.yaml', '')}
    Bilder: {'JA' if use_images else 'NEJ'}

    NULÄGE / KONTEXT:
    - I denna topic-fil finns {total_count} frågor.
    - I hela ämnesmappen ({subject}) finns {subject_total_count} frågor.

    TAGGAR (använd detta för att förstå vad som redan täcks och vad som saknas):
    - Tagg-frekvens (denna topic): {json.dumps(tag_summary, ensure_ascii=False)}
    - Tagg-frekvens (hela ämnet): {json.dumps(subject_tag_summary, ensure_ascii=False)}

    UPPGIFT:
    Generera {count_req} nya frågor.
    - FYLL LUCKOR i ämnet: skapa frågor som kompletterar det som saknas.
    - Återanvänd gärna existerande taggar när det passar; introducera nya endast om nödvändigt.
    - Generera unika IDn med format ex: "med-gen-{uuid.uuid4().hex[:4]}-..."
    """
    
    try:
        # Standard Structured Outputs (Non-Beta)
        completion = client.chat.completions.create(
            model="gpt-5-mini", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "question_batch",
                    "schema": build_question_batch_schema(),
                    "strict": True
                }
            },
            verbosity="low",
            reasoning_effort="medium"
        )
        
        # Manually parse the strict JSON response
        raw_json = completion.choices[0].message.content
        batch = QuestionBatch.model_validate_json(raw_json)
        
        if not batch or not batch.questions:
            print("Error: No questions generated.")
            return

        print(f"\nGenerated {len(batch.questions)} questions successfully.")
        
        # Convert Pydantic models back to dicts for YAML saving
        new_data = [q.model_dump() for q in batch.questions]

        # Ensure IDs are truly unique if LLM failed (double check)
        for q in new_data:
            if 'med-gen' not in q['id']:
                 q['id'] = f"med-gen-{uuid.uuid4().hex[:6]}"

        # Append to file
        all_data = existing + new_data
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(all_data, f, sort_keys=False, allow_unicode=True)
            
        print(f"Saved to {filepath}")
        
    except Exception as e:
        print(f"Error during generation: {e}")
        # Fallback debug
        if hasattr(e, 'body'):
             print(e.body)

if __name__ == '__main__':
    main()
