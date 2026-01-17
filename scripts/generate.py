import os
import sys
import yaml
import json
import uuid
import collections
import random
import urllib.request
import urllib.parse
import base64
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# -------------------------------------------------------------------------
# SETUP
# -------------------------------------------------------------------------
client = OpenAI() 

DATA_DIR = 'data'
ASSETS_DIR = os.path.join('public', 'assets')

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

# Medical exam system prompt (default)
SYSTEM_PROMPT_MEDICAL = """
Du är en expertlärare som skapar högkvalitativa, avancerade flashcards-frågor.
Ditt mål är att generera svåra, precisa och pedagogiska flervalsfrågor PÅ SVENSKA.

Språk: Svenska.
Ton: Professionell, akademisk med.

INNEHÅLLSKRAV:
1. Feedback MÅSTE vara koncis (1 mening). Börja INTE med "Rätt" eller "Fel", det visas automatiskt.
2. Explanation MÅSTE vara syntes-orienterad (2-3 meningar).
3. Svårighetsgrad: Läkarexamen / Specialistnivå.
"""

# Körkortsteori system prompt
SYSTEM_PROMPT_KORKORTSTEORI = """
Du är en erfaren körskoleinstruktör som skapar pedagogiska och varierande frågor för svenska körkortsteoriprov.
Ditt mål är att generera realistiska, relevanta och lärorika flervalsfrågor PÅ SVENSKA.

Språk: Svenska.
Ton: Tydlig, pedagogisk och praktisk.

INNEHÅLLSKRAV:
1. Frågor ska vara relevanta för B-körkort (personbil) i Sverige.
2. Feedback MÅSTE vara koncis (1 mening). Börja INTE med "Rätt" eller "Fel", det visas automatiskt.
3. Explanation MÅSTE vara pedagogisk och praktisk (2-3 meningar).
4. Frågor om vägmärken ska ha image-fältet ifyllt korrekt.
5. VIKTIGT: Om frågan handlar om vad ett vägmärke betyder, FÅR DU INTE nämna märkets namn i frågetexten!
   - FEL: "Vad betyder skylten 'Förbud mot infart' (bilden)?"
   - RÄTT: "Vad innebär detta vägmärke?" eller "Vägmärket i bilden markerar..."
6. Svårighetsgrad: Svenska körkortsteoriprov (både grundläggande och fördjupade frågor).
7. Inkludera praktiska situationer som förare möter i verkligheten.
8. SVARSALTERNATIV: De felaktiga alternativen (distraktorerna) ska vara trovärdiga och semi-relaterade till ämnet.
   - Undvik uppenbart felaktiga påståenden (som 'Snöröjning pågår' för en motorvägsskylt).
   - Alternativen ska vara sådana som en orutinerad förare rimligen skulle kunna blanda ihop med det rätta svaret.
"""

def get_system_prompt(subject: str) -> str:
    """Returns appropriate system prompt based on subject."""
    if subject == 'korkortsteori':
        return SYSTEM_PROMPT_KORKORTSTEORI
    else:
        return SYSTEM_PROMPT_MEDICAL

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

def get_road_sign_context(subject: str) -> str:
    """Returns context about Swedish road signs if subject is körkortsteori."""
    if subject != 'korkortsteori':
        return ""
    
    return """
VÄGMÄRKEN KONTEXT (för frågor med bilder):
När du skapar frågor om vägmärken, ange bildfilnamnet enligt mönstret: "vagmarke_[beskrivning].jpg"
t.ex. "vagmarke_stopplikt.jpg", "vagmarke_farthinder.jpg", "vagmarke_overgangsstalle.jpg"

Vanliga svenska vägmärken inkluderar:
- Varning: Varningsmärken (triangel med röd kant): Korsning, kurva, djur, barn, vägarbete, etc.
- Förbuds: Runda röda märken: Förbud mot infart, omkörning förbjuden, stopplikt, m.m.
- Påbuds: Blå runda märken: Gångbana, cykelbana, påbjuden körriktning
- Upplysnings: Blå fyrkantiga/rektangulära: Motorväg, mötesplats, parkering
- Vägvisnings: Gröna/vita skyltar med platsinformation

När du skapar en fråga om ett specifikt vägmärke:
1. Beskriv märket tydligt i image-fältet (t.ex. "vagmarke_stopplikt.jpg")
2. Frågan ska testa förståelse för märkets betydelse och tillämpning
3. Svarsalternativen ska vara rimliga men bara ett korrekt
"""

# -------------------------------------------------------------------------
# ROAD SIGN AUTOMATION
# -------------------------------------------------------------------------
def download_image(url, filename):
    """Downloads image/svg from URL and saves to public/assets/."""
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
        
    filepath = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(filepath):
        print(f"  [Skip] Image already exists: {filename}")
        return True
        
    print(f"  [Download] Fetching from: {url}")
    try:
        # Wikimedia Special:FilePath with width param redirects to a scaled PNG
        # Even for SVGs, asking for ?width=600 typically gives a PNG thumb
        if 'wikimedia' in url and filename.lower().endswith('.png') and 'Special:FilePath' in url:
             if '?' not in url:
                 url += "?width=600"
        
        # User-Agent is required by Wikipedia
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Iller6dev/1.0 (https://github.com/example/iller6)'}
        )
        with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        
        print(f"  [Success] Saved to {filepath}")
        return True
    except Exception as e:
        print(f"  [Error] Failed to download {url}: {e}")
        return False

def get_existing_sign_filenames(subject='korkortsteori'):
    """Finds all image filenames already used in question files."""
    used_images = set()
    subject_path = os.path.join(DATA_DIR, subject)
    if not os.path.exists(subject_path):
        return used_images
    
    for fname in os.listdir(subject_path):
        if fname.endswith('.yaml') or fname.endswith('.yml'):
            questions = load_existing(os.path.join(subject_path, fname))
            for q in questions:
                if q.get('image'):
                    used_images.add(q['image'])
    return used_images

def run_roadsign_generator(count=5):
    """
    1. Loads roadsigns_db.json
    2. Filters out signs that are already used in existing questions
    3. Downloads images for N random signs
    4. Generates questions for those signs
    """
    db_path = os.path.join(DATA_DIR, 'korkortsteori', 'roadsigns_db.json')
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found. Please create it first.")
        return

    with open(db_path, 'r', encoding='utf-8') as f:
        road_signs = json.load(f)
    
    if not road_signs:
        print("No signs in DB.")
        return

    # Filter out already used signs
    used_filenames = get_existing_sign_filenames('korkortsteori')
    available_signs = [s for s in road_signs if s['filename'] not in used_filenames]
    
    print(f"\nDB Size: {len(road_signs)}")
    print(f"Already used unique images: {len(used_filenames)}")
    print(f"Available for new questions: {len(available_signs)}")
    
    if not available_signs:
        print("All signs in DB have been used! Add more signs to DB or delete old questions.")
        return

    # Select random signs from AVAILABLE ones
    selected_signs = []
    if count >= len(available_signs):
         selected_signs = available_signs
    else:
         selected_signs = random.sample(available_signs, count)
    
    print(f"\nProcessing {len(selected_signs)} new road signs...")
    
    signs_context = []
    
    for sign in selected_signs:
        # Resolve URL
        # If 'url' key exists, use it. If 'wiki_file' exists, construct Special:FilePath URL
        # Note: We want PNGs for the app usually. If filename ends in .svg, we might stick with svg if vite handles it.
        # But earlier I set filenames to .svg in the DB.
        
        target_filename = sign.get('filename')
        wiki_file = sign.get('wiki_file')
        direct_url = sign.get('url')
        
        # Determine download URL
        download_url = direct_url
        if not download_url and wiki_file:
            # Special:FilePath redirects to actual file
            # For automation, this is easiest.
            encoded_wiki = urllib.parse.quote(wiki_file)
            download_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded_wiki}"
            
        if download_image(download_url, target_filename):
            signs_context.append({
                "name": sign['name'],
                "category": sign.get('category', 'Unknown'),
                "image_file": target_filename
            })
            
    if not signs_context:
        print("No images available to generate questions for.")
        return

    # Generate questions
    print(f"\nGenererar {len(signs_context)} frågor via OpenAI...")
    
    system_prompt = get_system_prompt('korkortsteori')
    
    # Construct a specific prompt
    signs_desc = "\n".join([f"- {s['name']} (Fil: {s['image_file']}, Kategori: {s['category']})" for s in signs_context])
    
    user_prompt = f"""
    Ämne: Körkortsteori (Vägmärken från Databas)
    
    BILDER ÄR NEDLADDADE OCH KLARA.
    
    Jag har laddat ner följande vägmärken:
    {signs_desc}
    
    UPPGIFT:
    Generera EN fråga för VARJE vägmärke i listan ovan.
    Totalt: {len(signs_context)} frågor.
    
    KRAV:
    1. Använd exakt filnamnet som anges för varje skylt i 'image'-fältet.
    2. Frågan ska handla specifikt om den skylten.
    3. VIKTIGT: AVSLÖJA INTE svaret i frågan! Skriv inte: "Vad betyder 'Stoppskylt'?". Skriv: "Vad innebär detta märke?".
    4. 'tags' ska inkludera 'Vägmärken' och kategorin (t.ex. '{signs_context[0]['category']}').
    5. Ge pedagogisk feedback.
    """
    
    try:
        completion = client.chat.completions.create(
            model="gpt-5-mini", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "question_batch",
                    "schema": build_question_batch_schema(),
                    "strict": True
                }
            }
        )
        
        raw_json = completion.choices[0].message.content
        batch = QuestionBatch.model_validate_json(raw_json)
        
        # Save to specific file
        output_file = os.path.join(DATA_DIR, 'korkortsteori', 'vagmarken_auto.yaml')
        existing_data = load_existing(output_file)
        
        new_data = [q.model_dump() for q in batch.questions]
        
        # Ensure unique IDs
        for q in new_data:
             q['id'] = f"kor-auto-{uuid.uuid4().hex[:6]}"

        all_data = existing_data + new_data
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(all_data, f, sort_keys=False, allow_unicode=True)
            
        print(f"\nSUCCÉ! Genererade {len(new_data)} frågor och sparade till {output_file}")
        
    except Exception as e:
        print(f"Error during auto-generation: {e}")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def run_scenario_generator(count=5):
    """
    1. Scans public/assets/scenarios
    2. Filters out used images
    3. Sends image to GPT-4o Vision to generate scenario question
    """
    scenarios_dir = os.path.join(ASSETS_DIR, 'scenarios')
    if not os.path.exists(scenarios_dir):
        print(f"Error: {scenarios_dir} not found. Run fetch_scenarios.py first.")
        return

    output_file = os.path.join(DATA_DIR, 'korkortsteori', 'scenarios.yaml')
    
    # Check used images
    used_images = set()
    if os.path.exists(output_file):
        existing_data = load_existing(output_file)
        if existing_data:
             for q in existing_data:
                 if q.get('image'):
                     # stored as "scenarios/filename.jpg" usually
                     used_images.add(os.path.basename(q['image']))
    else:
        existing_data = []

    # Find available images
    all_files = [f for f in os.listdir(scenarios_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    available = [f for f in all_files if f not in used_images]
    
    print(f"\nFound {len(all_files)} images, {len(available)} available.")
    
    if not available:
        print("No new scenario images to process.")
        return
        
    # Select images
    if count > len(available):
        to_process = available
    else:
        to_process = random.sample(available, count)
        
    print(f"Processing {len(to_process)} images...")
    
    new_questions = []
    
    for img_file in to_process:
        print(f"  > Analyzing {img_file}...")
        img_path = os.path.join(scenarios_dir, img_file)
        base64_image = encode_image(img_path)
        
        system_prompt = get_system_prompt('korkortsteori')
        # Tweak prompt for Vision
        system_prompt += "\n\nOBS: Du kommer få en bild på en trafiksituation. Din uppgift är att skapa en teorifråga baserad på vad föraren ser (man ser inte alltid motorhuven/ratten, men utgå från kamerans perspektiv). Identifiera risker, regler eller vägmärken i bilden."

        try:
            # Using gpt-4o for reliable Vision support
            completion = client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": "Analysera trafiksituationen i denna bild. Skapa EN utmanande körkortsfråga (flerval) baserad på bilden. Vad bör föraren tänka på? Vilka regler gäller? Var specifik kopplat till bildens innehåll."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                 response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "question_batch",
                        "schema": build_question_batch_schema(),
                        "strict": True
                    }
                }
            )
            
            raw_json = completion.choices[0].message.content
            batch = QuestionBatch.model_validate_json(raw_json)
            
            # Post-process: Add image path and ensure ID unique
            for q in batch.questions:
                q.image = f"scenarios/{img_file}" # Relative to assets/
                q.id = f"kor-scene-{uuid.uuid4().hex[:6]}"
                new_questions.append(q.model_dump())
                
        except Exception as e:
            print(f"    Failed to generate for {img_file}: {e}")

    # Save
    if new_questions:
        all_data = existing_data + new_questions
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(all_data, f, sort_keys=False, allow_unicode=True)
        print(f"\nSaved {len(new_questions)} new scenario questions to {output_file}")


def main():
    print("--- Iller6 Content Factory (Structured v2026) ---")
    
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

    # BRANCH FOR KÖRKORTSTEORI
    if subject == 'korkortsteori':
        print("\n--- Körkortsteori Mode ---")
        print("1. Standard (Topic-based text/manual images)")
        print("2. AUTO Road Signs (Download images + Generate questions)")
        print("3. AUTO Traffic Scenarios (Analyze local scenario images)")
        try:
            mode = input("Select Mode (1/2/3): ").strip()
        except:
            mode = "1"
            
        if mode == "2":
            try:
                cnt = int(input("How many road sign questions? (Default 5): ").strip())
            except:
                cnt = 5
            run_roadsign_generator(cnt)
            return

        if mode == "3":
            try:
                cnt = int(input("How many scenario questions? (Default 5): ").strip())
            except:
                cnt = 5
            run_scenario_generator(cnt)
            return

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
    # For körkortsteori, default to using images (road signs)
    default_images = 'y' if subject == 'korkortsteori' else 'n'
    use_images_input = input(f"Generate Image-based questions? ({'Y/n' if default_images == 'y' else 'y/N'}): ").lower().strip()
    if use_images_input == '':
        use_images = (default_images == 'y')
    else:
        use_images = use_images_input == 'y'
    
    try:
        c_in = input("How many questions to generate? (Default 5): ").strip()
        count_req = int(c_in) if c_in else 5
    except ValueError:
        print("Invalid number, defaulting to 5.")
        count_req = 5
    
    if use_images:
        if subject == 'korkortsteori':
            print("  NOTE: Road sign images will be referenced. Ensure image files exist in public/assets/")
        else:
            print("  NOTE: You must manually add images to public/assets/ matching the generated IDs.")

    # 5. Call LLM
    print(f"\nContacting OpenAI (gpt-5-mini) via Structured Outputs...")
    
    # Get appropriate system prompt and context
    system_prompt = get_system_prompt(subject)
    road_sign_context = get_road_sign_context(subject)
    
    # Create ID prefix based on subject (use first 3 characters)
    # Subject-specific prefix mapping for better readability
    id_prefix_map = {
        'korkortsteori': 'kor',
        'medical_exam': 'med',
    }
    id_prefix = id_prefix_map.get(subject, subject[:3].lower())
    
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
    
    {road_sign_context}

    UPPGIFT:
    Generera {count_req} nya frågor.
    - FYLL LUCKOR i ämnet: skapa frågor som kompletterar det som saknas.
    - Återanvänd gärna existerande taggar när det passar; introducera nya endast om nödvändigt.
    - Generera unika IDn med format ex: "{id_prefix}-gen-{uuid.uuid4().hex[:4]}-..."
    """
    
    try:
        # Standard Structured Outputs (Non-Beta)
        completion = client.chat.completions.create(
            model="gpt-5-mini", 
            messages=[
                {"role": "system", "content": system_prompt},
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
