from pathlib import Path
import json

def load_questions(limit=50):
    """
    Load questions from the pre-extracted auto_question.json dataset.
    This replaces the vector database chunk preview approach with real questions.
    """
    json_path = Path(__file__).parent / "auto_question.json"
    if not json_path.exists():
        raise FileNotFoundError(f"File dataset tidak ditemukan: {json_path}")
        
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    # Return questions up to the limit
    return questions[:limit]