# Helper script to populate roadsigns_db.json from Wikipedia markdown source (hardcoded here for now based on context)
import json
import os
import re

DATA_DIR = os.path.join('data', 'korkortsteori')
DB_FILE = os.path.join(DATA_DIR, 'roadsigns_db.json')

# This is a condensed version of the content found in the context
# I am manually extracting the relevant lines to ensure high quality
# Input format from context: [Name](url/File:Name.svg)
raw_signs = [
    ("Varning för farlig kurva", "Sweden_road_sign_A1-1.svg", "Varning"),
    ("Varning för flera farliga kurvor", "Sweden_road_sign_A2-1.svg", "Varning"),
    ("Varning för nedförslutning", "Sweden_road_sign_A3.svg", "Varning"),
    ("Varning för stigning", "Sweden_road_sign_A4.svg", "Varning"),
    ("Varning för avsmalnande väg", "Sweden_road_sign_A5-1.svg", "Varning"),
    ("Varning för bro", "Sweden_road_sign_A6.svg", "Varning"),
    ("Varning för kaj", "Sweden_road_sign_A7.svg", "Varning"),
    ("Varning för ojämn väg", "Sweden_road_sign_A8.svg", "Varning"),
    ("Varning för farthinder", "Sweden_road_sign_A9-1.svg", "Varning"),
    ("Varning för stenskott", "Sweden_road_sign_A11.svg", "Varning"),
    ("Varning för stenras", "Sweden_road_sign_A12-1.svg", "Varning"),
    ("Varning för övergångsställe", "Sweden_road_sign_A13.svg", "Varning"),
    ("Varning för gående", "Sweden_road_sign_A14.svg", "Varning"),
    ("Varning för barn", "Sweden_road_sign_A15.svg", "Varning"),
    ("Varning för cyklande och mopedförare", "Sweden_road_sign_A16.svg", "Varning"),
    ("Varning för skidåkare", "Sweden_road_sign_A17.svg", "Varning"),
    ("Varning för ridande", "Sweden_road_sign_A18.svg", "Varning"),
    ("Varning för älg", "Sweden_road_sign_A19-1.svg", "Varning"),
    ("Varning för hjortdjur", "Sweden_road_sign_A19-2.svg", "Varning"),
    ("Varning för nötkreatur", "Sweden_road_sign_A19-3.svg", "Varning"),
    ("Varning för häst", "Sweden_road_sign_A19-4.svg", "Varning"),
    ("Varning för ren", "Sweden_road_sign_A19-5.svg", "Varning"),
    ("Varning för får", "Sweden_road_sign_A19-6.svg", "Varning"),
    ("Varning för vildsvin", "Sweden_road_sign_A19-7.svg", "Varning"),
    ("Varning för vägarbete", "Sweden_road_sign_A20.svg", "Varning"),
    ("Varning för flerfärgssignal", "Sweden_road_sign_A22.svg", "Varning"),
    ("Varning för lågt flygande flygplan", "Sweden_road_sign_A23-1.svg", "Varning"),
    ("Varning för sidvind", "Sweden_road_sign_A24-1.svg", "Varning"),
    ("Varning för mötande trafik", "Sweden_road_sign_A25.svg", "Varning"),
    ("Varning för tunnel", "Sweden_road_sign_A26.svg", "Varning"),
    ("Varning för svag vägkant", "Sweden_road_sign_A27.svg", "Varning"),
    ("Varning för vägkorsning", "Sweden_road_sign_A28.svg", "Varning"),
    ("Varning för cirkulationsplats", "Sweden_road_sign_A30.svg", "Varning"),
    ("Varning för långsamtgående fordon", "Sweden_road_sign_A31.svg", "Varning"),
    ("Varning för kö", "Sweden_road_sign_A34.svg", "Varning"),
    ("Varning för järnvägskorsning med bommar", "Sweden_road_sign_A35.svg", "Varning"),
    ("Varning för järnvägskorsning utan bommar", "Sweden_road_sign_A36.svg", "Varning"),
    ("Väjningsplikt", "Sweden_road_sign_B1.svg", "Väjningsplikt"),
    ("Stopplikt", "Sweden_road_sign_B2.svg", "Väjningsplikt"),
    ("Övergångsställe", "Sweden_road_sign_B3-1.svg", "Väjningsplikt"),
    ("Huvudled", "Sweden_road_sign_B4.svg", "Väjningsplikt"),
    ("Huvudled upphör", "Sweden_road_sign_B5.svg", "Väjningsplikt"),
    ("Väjningsplikt mot mötande trafik", "Sweden_road_sign_B6.svg", "Väjningsplikt"),
    ("Mötande trafik har väjningsplikt", "Sweden_road_sign_B7.svg", "Väjningsplikt"),
    ("Cykelöverfart", "Sweden_road_sign_B8.svg", "Väjningsplikt"),
    ("Förbud mot infart med fordon", "Sweden_road_sign_C1.svg", "Förbud"),
    ("Förbud mot trafik med fordon", "Sweden_road_sign_C2.svg", "Förbud"),
    ("Förbud mot trafik med motorcykel", "Sweden_road_sign_C5.svg", "Förbud"),
    ("Förbud mot trafik med tung lastbil", "Sweden_road_sign_C7.svg", "Förbud"),
    ("Förbud mot omkörning", "Sweden_road_sign_C27.svg", "Förbud"),
    ("Förbud mot omkörning med tung lastbil", "Sweden_road_sign_C29.svg", "Förbud"),
    ("Hastighetsbegränsning 30", "Sweden_road_sign_C31-30.svg", "Förbud"),
    ("Hastighetsbegränsning 40", "Sweden_road_sign_C31-40.svg", "Förbud"),
    ("Hastighetsbegränsning 50", "Sweden_road_sign_C31-50.svg", "Förbud"),
    ("Hastighetsbegränsning 60", "Sweden_road_sign_C31-60.svg", "Förbud"),
    ("Hastighetsbegränsning 70", "Sweden_road_sign_C31-70.svg", "Förbud"),
    ("Hastighetsbegränsning 80", "Sweden_road_sign_C31-80.svg", "Förbud"),
    ("Hastighetsbegränsning 90", "Sweden_road_sign_C31-90.svg", "Förbud"),
    ("Hastighetsbegränsning 100", "Sweden_road_sign_C31-100.svg", "Förbud"),
    ("Hastighetsbegränsning 110", "Sweden_road_sign_C31-110.svg", "Förbud"),
    ("Hastighetsbegränsning 120", "Sweden_road_sign_C31-120.svg", "Förbud"),
    ("Förbud mot att parkera", "Sweden_road_sign_C35.svg", "Förbud"),
    ("Datumparkering", "Sweden_road_sign_C38.svg", "Förbud"),
    ("Förbud mot att stanna och parkera", "Sweden_road_sign_C39.svg", "Förbud"),
    ("Vändplats", "Sweden_road_sign_C42-1.svg", "Förbud"),
    ("Påbjuden körriktning höger", "Sweden_road_sign_D1-2.svg", "Påbud"),
    ("Påbjuden körbana", "Sweden_road_sign_D2-1.svg", "Påbud"),
    ("Cirkulationsplats", "Sweden_road_sign_D3.svg", "Påbud"),
    ("Påbjuden gångbana", "Sweden_road_sign_D4.svg", "Påbud"),
    ("Påbjuden cykelbana", "Sweden_road_sign_D5.svg", "Påbud"),
    ("Påbjuden gång- och cykelbana", "Sweden_road_sign_D6.svg", "Påbud"),
    ("Motorväg", "Sweden_road_sign_E1.svg", "Anvisning"),
    ("Motorväg upphör", "Sweden_road_sign_E2.svg", "Anvisning"),
    ("Motortrafikled", "Sweden_road_sign_E3.svg", "Anvisning"),
    ("Motortrafikled upphör", "Sweden_road_sign_E4.svg", "Anvisning"),
    ("Tätort", "Sweden_road_sign_E5.svg", "Anvisning"),
    ("Tätort upphör", "Sweden_road_sign_E6.svg", "Anvisning"),
    ("Gågata", "Sweden_road_sign_E7.svg", "Anvisning"),
    ("Gågata upphör", "Sweden_road_sign_E8.svg", "Anvisning"),
    ("Gångfartsområde", "Sweden_road_sign_E9.svg", "Anvisning"),
    ("Gångfartsområde upphör", "Sweden_road_sign_E10.svg", "Anvisning"),
    ("Rekommenderad lägre hastighet", "Sweden_road_sign_E11-3.svg", "Anvisning"),
    ("Sammanvävning", "Sweden_road_sign_E15.svg", "Anvisning"),
    ("Enkelriktad trafik", "Sweden_road_sign_E16-1.svg", "Anvisning"),
    ("Återvändsgata", "Sweden_road_sign_E17-1.svg", "Anvisning"),
    ("Mötesplats", "Sweden_road_sign_E18.svg", "Anvisning"),
    ("Parkering", "Sweden_road_sign_E19.svg", "Anvisning"),
    ("Busshållplats", "Sweden_road_sign_E22.svg", "Anvisning"),
    ("Kameraövervakning", "Sweden_road_sign_E24.svg", "Anvisning"),
    ("Tunnel", "Sweden_road_sign_E26.svg", "Anvisning"),
    ("Nödutgång", "Sweden_road_sign_E28-1.svg", "Anvisning"),
]

# Create standard naming convention map
# We want clean filenames like: vagmarke_varning_farlig_kurva.svg
def make_filename(category, name):
    clean_name = name.lower()
    clean_name = clean_name.replace('å', 'a').replace('ä', 'a').replace('ö', 'o')
    clean_name = re.sub(r'[^a-z0-9]+', '_', clean_name)
    clean_name = clean_name.strip('_')
    
    # Prefix
    if 'vagmarke' not in clean_name:
        prefix = 'vagmarke_'
        # Add category if specific
        if category.lower() in ['varning', 'forbud', 'pabud', 'anvisning']:
            prefix += category.lower().replace('å','a').replace('ä','a').replace('ö','o') + '_'
        
        # Avoid double prefix if name already contains category
        if clean_name.startswith(category.lower().replace('å','a').replace('ä','a').replace('ö','o')):
             clean_name = clean_name  # It already effectively has prefix
        else:
             clean_name = prefix + clean_name
            
    return f"{clean_name}.svg"

new_db = []
for name, wiki_file, category in raw_signs:
    fname = make_filename(category, name)
    
    entry = {
        "name": name,
        "category": category,
        "filename": fname,
        "wiki_file": wiki_file
    }
    new_db.append(entry)

# Ensure directory
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Write DB
with open(DB_FILE, 'w', encoding='utf-8') as f:
    json.dump(new_db, f, indent=2, ensure_ascii=False)

print(f"Created DB with {len(new_db)} signs at {DB_FILE}")
