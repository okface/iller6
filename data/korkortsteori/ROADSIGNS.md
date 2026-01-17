"""
Swedish Road Sign Resources and Image Naming Guide

This document describes how to handle Swedish road signs (vägmärken) for körkortsteori questions.

IMAGE NAMING CONVENTION:
All road sign images should be named using the pattern: vagmarke_[description].jpg/png
stored in: public/assets/

COMMON SWEDISH ROAD SIGNS:

1. VARNINGSSKYLTAR (Warning Signs - Yellow triangle with red border):
   - vagmarke_korsning.png - Korsning (Intersection)
   - vagmarke_farlig_kurva_hoger.png - Farlig kurva höger (Dangerous curve right)
   - vagmarke_farlig_kurva_vanster.png - Farlig kurva vänster (Dangerous curve left)
   - vagmarke_barn.png - Varning för barn (Warning for children)
   - vagmarke_djur.png - Varning för djur (Warning for animals)
   - vagmarke_vagarbete.png - Vägarbete (Road work)
   - vagmarke_farthinder.png - Farthinder (Speed bump)
   - vagmarke_overgangsstalle.png - Övergångsställe (Pedestrian crossing)
   - vagmarke_cyklist.png - Varning för cyklister (Warning for cyclists)

2. FÖRBUDSSKYLTAR (Prohibition Signs - Red circle):
   - vagmarke_stopplikt.png - Stopplikt (Stop sign)
   - vagmarke_forbud_infart.png - Förbud mot infart (No entry)
   - vagmarke_forbjuden_omkoring.png - Omkörning förbjuden (No overtaking)
   - vagmarke_forbjuden_parkering.png - Parkering förbjuden (No parking)
   - vagmarke_forbjuden_stannande.png - Stannande förbjudet (No stopping)
   - vagmarke_hogsta_tillaten_hastighet.png - Högsta tillåtna hastighet (Speed limit)
   - vagmarke_infart_forbjuden.png - Infart förbjuden (Entry prohibited)

3. PÅBUDSSKYLTAR (Mandatory Signs - Blue circle):
   - vagmarke_gangbana.png - Gångbana (Pedestrian path)
   - vagmarke_cykelbana.png - Cykelbana (Cycle path)
   - vagmarke_gang_och_cykelbana.png - Gång- och cykelbana (Shared path)
   - vagmarke_korriktning.png - Påbjuden körriktning (Mandatory direction)

4. UPPLYSNINGSSKYLTAR (Information Signs - Blue rectangle):
   - vagmarke_motorvag.png - Motorväg (Motorway)
   - vagmarke_motorvag_upphör.png - Motorväg upphör (Motorway ends)
   - vagmarke_motestrafik.png - Mötestrafik (Two-way traffic)
   - vagmarke_parkering.png - Parkering (Parking)
   - vagmarke_gangpassage.png - Gångpassage (Pedestrian crossing)

5. VÄGVISNINGSSKYLTAR (Direction Signs - Green/White):
   - vagmarke_riktning.png - Vägvisning (Direction sign)

IMAGE SOURCES:
1. Transportstyrelsen: https://www.transportstyrelsen.se/sv/vagtrafik/Vagmarken/
   - Official Swedish Transport Agency with all road signs
   
2. Wikipedia Commons: Swedish road signs
   - Many Swedish road signs are available under Creative Commons
   
3. Generate simple SVG representations for common signs
   - For production, consider using or creating SVG versions

GENERATION WORKFLOW:
1. When generating questions, the LLM will reference images by filename
2. After generation, manually download/create the referenced images
3. Place images in public/assets/ directory
4. Re-run bundle.py to update content

Example question with road sign:
```yaml
- id: "kor-gen-a1b2"
  type: "multiple_choice"
  tags: ["Vägmärken", "Varning"]
  question: "Vad betyder denna skylt?"
  image: "vagmarke_barn.png"
  options:
    - text: "Varning för lekande barn"
      correct: true
      feedback: "Varnar förare om att barn kan befinna sig på eller nära vägen."
    - text: "Varning för skola"
      correct: false
      feedback: "Detta är inte en skolskylt, utan en generell varning för barn."
  explanation: "Gul triangel med två springande barn visar att förare ska vara extra uppmärksam på barn som kan springa ut på vägen."
```

IMPLEMENTATION NOTES:
- Images can be null for text-only questions
- Road sign questions should always have an image
- The generate.py script prompts for image generation based on subject
- For körkortsteori, image generation defaults to YES
"""
