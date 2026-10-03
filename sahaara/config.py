import os
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
EMBED_MODEL = os.getenv("SAHAARA_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
USE_EMBEDDINGS = os.getenv("SAHAARA_EMBEDDINGS", "off").lower() != "off"
EMERGENCY_NUMBERS = os.getenv("SAHAARA_EMERGENCY", "1122 / 115")
MAX_CLARIFY_ROUNDS = 2
MAX_SUPPORT_ATTEMPTS = 2
