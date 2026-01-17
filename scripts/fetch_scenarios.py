import os
import urllib.request
import urllib.parse
import sys

SCENARIOS_DIR = os.path.join('public', 'assets', 'scenarios')

# List of Wikimedia Commons filenames that depict traffic scenarios
SCENARIO_FILES = [
    "Varmdovagen_2008b.jpg",
    "Stocksund-Mörby_-_KMB_-_16001000419624.jpg",
    "Ulriksdal-Kista_-_KMB_-_16001000414984.jpg",
    "Vällingby_-_KMB_-_16001000411504.jpg",
    "Västberga_-_KMB_-_16001000288664.jpg",
    "Västberga_-_KMB_-_16001000288844.jpg",
    "Road_(7000914999).jpg",
    "Landsvag_i_norra_Sverige,_Johannes_Jansson.jpg",
    "Type-section_Swedish_2+1_highway.png",
    "Västra_industriområdet_Kiruna_September_2019_01.jpg",
    "Norrtälje_Estunavägen.tif", # Might convert or skip if large, let's try
    "E4_Huskvarna_2010.jpg", # Guessing
    "Rondell_Skövde.jpg", # Guessing
    "Vägverkets_övningskörningsskylt.jpg" # Classic
]

# Better robust list with validated names from the fetch output
VALIDATED_FILES = [
    "Varmdovagen_2008b.jpg",
    "Stocksund-Mörby_-_KMB_-_16001000419624.jpg", 
    "Ulriksdal-Kista_-_KMB_-_16001000414984.jpg",
    "Vällingby_-_KMB_-_16001000411504.jpg",
    "Västberga_-_KMB_-_16001000288664.jpg",
    "Road_(7000914999).jpg",
    "Landsvag_i_norra_Sverige,_Johannes_Jansson.jpg",
    "Type-section_Swedish_2+1_highway.png",
    "Västra_industriområdet_Kiruna_September_2019_01.jpg",
    "Raksträcka_mellan_Svartnäs_och_Svärdsjö.jpg",
    "Norrvra_Sweden_201005.JPG",
    "Enköping-_(15914370131).jpg",
    "Lödöse-IMAG0211.jpg",
    "Skräddartorpsvägen_i_Mälby.jpg"
]


def download_file(filename):
    if not os.path.exists(SCENARIOS_DIR):
        os.makedirs(SCENARIOS_DIR)
        
    filepath = os.path.join(SCENARIOS_DIR, filename)
    if os.path.exists(filepath):
        print(f"Exists: {filename}")
        return

    # Use Special:FilePath
    encoded_name = urllib.parse.quote(filename)
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded_name}"
    
    # Request width=1024 to get a decent JPG/PNG mostly
    if not filename.lower().endswith('.svg'):
        url += "?width=1024"

    print(f"Downloading {filename}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Iller6dev/1.0 (https://github.com/example/iller6)'}
        )
        with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print("Success.")
    except Exception as e:
        print(f"Failed: {e}")

def main():
    print(f"Fetching {len(VALIDATED_FILES)} scenario images...")
    for f in VALIDATED_FILES:
        download_file(f)

if __name__ == '__main__':
    main()
