import re
from difflib import get_close_matches

# ----------------------------
# CENTRALIZED SENDER DATABASE
# ----------------------------
SENDER_ALIASES = {
    # Project Manager
    "reign pajanustan": "Reign Pajanustan", "reign": "Reign Pajanustan", "pajanustan": "Reign Pajanustan",
    "shekinah tejada": "Shekinah Tejada", "shekinah": "Shekinah Tejada", "tejada": "Shekinah Tejada",
    "angela taylan": "Angela Taylan", "angela": "Angela Taylan", "taylan": "Angela Taylan",
    
    # System Administration and Maintenance (SysAD)
    "lester ragel": "Lester Ragel", "lester": "Lester Ragel", "ragel": "Lester Ragel",
    "lebron satumba": "Lebron Satumba", "lebron": "Lebron Satumba", "satumba": "Lebron Satumba",
    "dani dasco": "Dani Dasco", "dani": "Dani Dasco", "dasco": "Dani Dasco",
    
    # Artificial Intelligence
    "leonardo yoro": "Leonardo Yoro", "uno yoro": "Leonardo Yoro", "uno": "Leonardo Yoro", "leo": "Leonardo Yoro",
    "naithan balondo": "Naithan Balondo", "naithan": "Naithan Balondo", "naitnan baionda": "Naithan Balondo",
    "bharon candelaria": "Bharon Candelaria", "bharon": "Bharon Candelaria",
    "alberto catapang": "Alberto Catapang", "abet": "Alberto Catapang", "alberto": "Alberto Catapang",
    "dominic almazan": "Dominic Almazan", "dom": "Dominic Almazan", "doms": "Dominic Almazan", "dominic": "Dominic Almazan",

    # Web Development
    "ryan dorona": "Ryan Dorona", "ryan": "Ryan Dorona", "dorona": "Ryan Dorona",
    "luis laguardia": "Luis Laguardia", "luis": "Luis Laguardia", "laguardia": "Luis Laguardia",
    "john kevin": "John Kevin", "kevin": "John Kevin",
    "joshua cazeñas": "Joshua Cazeñas", "joshua": "Joshua Cazeñas", "cazenas": "Joshua Cazeñas",
    "enzo hernandez": "Enzo Hernandez", "enzo": "Enzo Hernandez",
    "yna pajanustan": "Yna Pajanustan", "yna": "Yna Pajanustan",
    "Cezzann Gabrielle Amido,": "Cezzann Gabrielle Amido", "cezzann": "Cezzann Gabrielle Amido", "amido": "Cezzann Gabrielle Amido",

    # Computer Engineering
    "jayson cada": "Jayson Cada", "jayson": "Jayson Cada", "cada": "Jayson Cada",
    "jennoh medina": "Jennoh Medina", "jennoh": "Jennoh Medina", "medina": "Jennoh Medina",
    "joman andy lopena": "Joman Andy Lopena", "joman": "Joman Andy Lopena", "lopena": "Joman Andy Lopena",

    # Accounting
    "riza mae balanquit": "Riza Mae S. Balanquit", "balanquit": "Riza Mae S. Balanquit",
    "easha": "Easha",
    "rachelle frondozo": "Rachelle Frondozo", "frondozo": "Rachelle Frondozo",
    "kim ong": "Kim Ong", "kim": "Kim Ong",
    "louis anne padilla": "Louis Anne L. Padilla", "padilla": "Louis Anne L. Padilla",
    "denise jayne parman": "Denise Jayne M. Parman", "parman": "Denise Jayne M. Parman",
    "rocie": "Rocie",
    "john benedict turla": "John Benedict C. Turla", "turla": "John Benedict C. Turla", "benedict": "John Benedict C. Turla",
    "valerie mhae ymson": "Valerie Mhae P. Ymson", "ymson": "Valerie Mhae P. Ymson", "valerie": "Valerie Mhae P. Ymson",

    # Miscellaneous / Legacy
    "jpa": "JPA","comfac-ems": "Comfac-EMS",
    "michael magsino": "Michael Magsino", "magsino": "Michael Magsino",
    "jonathan": "Jonathan", 
    "joan hechanova": "Joan Hechanova", "joan": "Joan Hechanova"
}

# ----------------------------
# OFFICIAL ORGANIZATION
# ----------------------------
OFFICIAL_ORGANIZATION = {
    "Project Manager": ["Reign Pajanustan", "Shekinah Tejada", "Angela Taylan"],
    "System Administration and Maintenance": ["Lester Ragel", "Lebron Satumba", "Dani Dasco"],
    "Artificial Intelligence": ["Leonardo Yoro", "Naithan Balondo", "Bharon Candelaria", "Alberto Catapang", "Dominic Almazan"],
    "Web Development": ["Ryan Dorona", "Luis Laguardia", "John Kevin", "Joshua Cazeñas", "Enzo Hernandez", "Yna Pajanustan", "Cezzann Gabrielle Amido"],
    "Computer Engineering": ["Jayson Cada", "Jennoh Medina", "Joman Andy Lopena"],
    "Accounting": [
        "Riza Mae S. Balanquit", "Easha", "Rachelle Frondozo", "Kim Ong", 
        "Louis Anne L. Padilla", "Denise Jayne M. Parman", "Rocie", 
        "John Benedict C. Turla", "Valerie Mhae P. Ymson"
    ],
    "Miscellaneous": ["JPA", "Michael Magsino", "Jonathan", "Joan Hechanova", "Comfac-EMS"]
}

# ----------------------------
# CORE CLEANING FUNCTIONS
# ----------------------------
def resolve_sender(text):
    if not text: return None
    # Pre-process common OCR errors (AI -> AL, 0 -> O)
    clean = text.lower().strip().replace('ai', 'al').replace('0', 'o')
    
    # Direct Alias Check
    for alias, official in SENDER_ALIASES.items():
        if alias in clean: return official
        
    # Fuzzy Match fallback
    matches = get_close_matches(clean, SENDER_ALIASES.keys(), n=1, cutoff=0.7)
    return SENDER_ALIASES[matches[0]] if matches else None

def is_timestamp(text):
    if not text: return False
    processed = text.upper().replace('O', '0').replace('I', '1').replace('.', ':')
    return bool(re.search(r'\d{1,2}:\d{2}\s?(AM|PM|M)', processed))

def clean_message_text(text):
    if not text: return ""
    # Remove Date Headers
    text = re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\w+\s+\d{1,2},?\s+\d{4}', '', text, flags=re.IGNORECASE)
    # Remove "Deleted" System Messages
    text = re.sub(r'This message was deleted\.?', '', text, flags=re.IGNORECASE)
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "today", "yesterday"]
    if text.lower().strip() in days: return ""
    text = text.replace("Photo message", "")
    return text.strip()

def is_noise(text):
    noise_triggers = [
        "activate windows", "go to settings", "type a message", 
        "rakuten viber", "gif", "pinned on", "this message was deleted",
        "click on the highlighted text to set a reminder", 
        "right click message to translate"
    ]
    return any(trigger in text.lower() for trigger in noise_triggers)

def detect_dynamic_header(lines):
    pinned_keywords = ["pinned on", "pinned message"]
    for line in lines:
        text = line[1][0].lower()
        if any(k in text for k in pinned_keywords):
            return line[0][2][1] + 5 
    return 0