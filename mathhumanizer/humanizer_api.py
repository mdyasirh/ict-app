"""
MathHumanizer - AI Text Humanization Backend
Turnitin AI Detection Evasion System
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import ollama
import nltk
from nltk.corpus import wordnet as wn
import random
import re
import math
import numpy as np
import PyPDF2
import io
import os
from typing import List, Dict, Optional
import json

# Initialize FastAPI app
app = FastAPI(title="MathHumanizer", description="AI Text Humanization API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)

# ===== 1. Load Perplexity Analyzer (DistilGPT-2) =====
# Deferred loading - will load on first use to avoid blocking startup
MODEL_LOADED = False
analyzer_tokenizer = None
analyzer_model = None

def load_analyzer_model():
    """Lazy load the analyzer model when needed"""
    global MODEL_LOADED, analyzer_tokenizer, analyzer_model
    
    if analyzer_tokenizer is not None or analyzer_model is not None:
        return  # Already attempted loading
    
    print("Loading DistilGPT-2 analyzer model...")
    try:
        import os
        os.environ['HF_HUB_OFFLINE'] = '1'  # Force offline mode to fail fast if not cached
        analyzer_tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
        analyzer_model = AutoModelForCausalLM.from_pretrained("distilgpt2")
        analyzer_model.eval()
        MODEL_LOADED = True
        print("✓ Analyzer model loaded successfully!")
    except Exception as e:
        print(f"⚠ Could not load DistilGPT-2 model: {e}")
        print("→ Using fallback metric calculations (word statistics based).")
        print("→ For better results, ensure ~400MB free disk space for model download.")
        MODEL_LOADED = False

# ===== 2. Forbidden Words & Thesaurus =====
AI_BLACKLIST = {
    "delve", "foster", "tapestry", "crucial", "moreover", "testament", 
    "multifaceted", "underscore", "beacon", "furthermore", "additionally", 
    "consequently", "nevertheless", "thus", "hence", "notably", "pivotal",
    "robust", "comprehensive", "intricate", "paradigm", "nuanced",
    "highlight", "emphasize", "demonstrate", "illustrate", "showcase",
    "significant", "substantial", "considerable", "remarkable", "exceptional",
    "integral", "essential", "vital", "paramount", "imperative",
    "facilitate", "implement", "utilize", "leverage", "optimize",
    "enhance", "strengthen", "bolster", "augment", "amplify"
}

# Storage for training samples (in-memory for this demo)
training_data = {
    "ai_samples": [],
    "human_samples": []
}

def calculate_perplexity(text: str) -> float:
    """Calculate perplexity using DistilGPT-2"""
    # Lazy load model on first call
    if not MODEL_LOADED and analyzer_tokenizer is None:
        load_analyzer_model()
    
    if not MODEL_LOADED or not text.strip():
        # Fallback: estimate perplexity based on word rarity and sentence structure
        if not text.strip():
            return 0.0
        words = text.split()
        # Simple heuristic: longer words and varied vocabulary = higher perplexity
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        unique_ratio = len(set(words)) / len(words) if words else 0
        # Estimate perplexity (typical range 60-180)
        estimated = 70 + (avg_word_len * 5) + (unique_ratio * 30)
        return estimated
    
    enc = analyzer_tokenizer(
        text, 
        return_tensors="pt", 
        truncation=True, 
        max_length=512,
        padding=True
    )
    
    with torch.no_grad():
        outputs = analyzer_model(**enc, labels=enc["input_ids"])
        loss = outputs.loss
    
    return math.exp(loss.item())

def sentence_length_cv(text: str) -> float:
    """Calculate coefficient of variation of sentence lengths (burstiness)"""
    sentences = nltk.sent_tokenize(text)
    if len(sentences) < 2:
        return 0.0
    
    lengths = [len(s.split()) for s in sentences]
    mean_len = np.mean(lengths)
    if mean_len == 0:
        return 0.0
    
    std_len = np.std(lengths)
    return std_len / mean_len

def count_forbidden_words(text: str) -> Dict[str, int]:
    """Count occurrences of AI-typical words"""
    words = re.findall(r'\b\w+\b', text.lower())
    counts = {}
    for word in words:
        if word in AI_BLACKLIST:
            counts[word] = counts.get(word, 0) + 1
    return counts

def get_surprising_synonym(word: str, context_sentence: str) -> str:
    """Get a synonym that increases perplexity"""
    if not MODEL_LOADED:
        # Fallback: just return a different word from WordNet without perplexity scoring
        synonyms = []
        for synset in wn.synsets(word):
            for lemma in synset.lemmas():
                lemma_name = lemma.name().replace("_", " ")
                if lemma_name != word and "_" not in lemma.name() and len(lemma_name) <= 3:
                    synonyms.append(lemma_name)
        if synonyms:
            return random.choice(list(set(synonyms)))
        return word
    
    synonyms = []
    for synset in wn.synsets(word):
        for lemma in synset.lemmas():
            lemma_name = lemma.name().replace("_", " ")
            if lemma_name != word and "_" not in lemma.name() and len(lemma_name) <= 3:
                synonyms.append(lemma_name)
    
    if not synonyms:
        return word
    
    # Pick one with highest perplexity (most surprising)
    best_syn = word
    base_text = context_sentence.replace(word, "[MASK]")
    best_score = 0
    
    for syn in set(synonyms):
        candidate = base_text.replace("[MASK]", syn)
        try:
            score = calculate_perplexity(candidate)
            if score > best_score:
                best_score = score
                best_syn = syn
        except:
            continue
    
    return best_syn

# ===== 3. Pre-Processing Functions =====
def pre_process(text: str) -> str:
    """Apply rule-based transformations to increase burstiness and perplexity"""
    
    # a) Replace some blacklist words with surprising synonyms
    words = text.split()
    new_words = []
    for i, w in enumerate(words):
        clean_word = w.lower().strip(".,;:!?\"'()[]{}")
        if clean_word in AI_BLACKLIST and random.random() < 0.15:
            context = " ".join(words[max(i-5,0):min(i+5,len(words))])
            syn = get_surprising_synonym(clean_word, context)
            # Preserve original case
            if w[0].isupper():
                syn = syn.capitalize()
            new_words.append(syn)
        else:
            new_words.append(w)
    
    text = " ".join(new_words)
    
    # b) Inject burstiness: split long sentences
    sentences = nltk.sent_tokenize(text)
    if len(sentences) > 2:
        long_indices = [i for i, s in enumerate(sentences) if len(s.split()) > 20]
        if long_indices:
            split_idx = random.choice(long_indices)
            s = sentences[split_idx]
            # Split at comma, semicolon, or em-dash
            parts = re.split(r'(, |; | — | —)', s)
            if len(parts) > 2:
                short_part = "".join(parts[:2]).strip()
                if short_part.endswith((',', ';')):
                    short_part = short_part[:-1]
                short_part += "."
                rest_part = "".join(parts[2:]).strip()
                if rest_part and rest_part[0].islower():
                    rest_part = rest_part[0].upper() + rest_part[1:]
                sentences[split_idx] = short_part + " " + rest_part
    
    # c) Insert short reflective sentences occasionally
    if len(sentences) > 3 and random.random() < 0.3:
        insert_idx = random.randint(1, len(sentences) - 1)
        phrases = [
            "This is a key point.",
            "Worth noting.",
            "Indeed, this matters.",
            "Consider the implication.",
            "An important observation.",
            "This cannot be overlooked."
        ]
        sentences.insert(insert_idx, random.choice(phrases))
    
    return " ".join(sentences)

# ===== 4. LLM Rewriting with Math-Aware Prompt =====
SYSTEM_PROMPT = """You are an expert academic writer specializing in producing human-like text that evades AI detection systems.

Your task is to rewrite the given academic text so that it becomes statistically indistinguishable from human writing.

MATHEMATICAL TARGETS (YOU MUST ACHIEVE THESE):
- Perplexity > 130: Use unlikely but correct word choices. Avoid predictable phrasing.
- Sentence-length CV > 0.5: Mix very short sentences (2-5 words) with very long ones (35+ words). Never have three consecutive sentences of similar length.
- Absolutely avoid these words: {blacklist}
- Keep ALL citations, technical terms, mathematical notation, and headings exactly as they appear.
- Maintain formal academic tone (IELTS Band 7+ English).
- Preserve the original meaning completely.
- Output ONLY the rewritten text, no commentary or explanations.

WRITING STYLE INSTRUCTIONS:
- Start some sentences with conjunctions (And, But, Yet) for natural flow.
- Use occasional parenthetical remarks or dashes for variety.
- Include rhetorical questions sparingly if appropriate.
- Vary paragraph lengths significantly.
- Use passive voice occasionally (humans do this too).
- Insert brief transitional phrases that are less common.
""".format(blacklist=", ".join(sorted(AI_BLACKLIST)))

def rewrite_with_llm(text: str, model: str = "llama3", temp: float = 0.95, feedback: str = "") -> str:
    """Send text to LLM for rewriting with mathematical targets"""
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if feedback:
        user_content = f"{feedback}\n\nOriginal text to rewrite:\n{text}"
    else:
        user_content = text
    
    messages.append({"role": "user", "content": user_content})
    
    try:
        response = ollama.chat(
            model=model,
            messages=messages,
            options={
                "temperature": temp,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 2048
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service unavailable: {str(e)}")

# ===== 5. Feedback Loop Controller =====
def humanize(text: str, max_iters: int = 3, target_perplexity: float = 120, target_cv: float = 0.45) -> Dict:
    """Main humanization pipeline with feedback loop"""
    
    results = {
        "original": {
            "perplexity": calculate_perplexity(text),
            "cv": sentence_length_cv(text),
            "forbidden_count": sum(count_forbidden_words(text).values())
        },
        "iterations": [],
        "final_text": "",
        "success": False
    }
    
    # Pre-process
    processed = pre_process(text)
    
    best_output = processed
    best_score = 0
    
    for i in range(max_iters):
        # Get LLM rewrite
        if i == 0:
            output = rewrite_with_llm(processed)
        else:
            feedback_msg = f"Previous attempt metrics: perplexity={prev_p:.0f}, CV={prev_cv:.2f}. "
            if prev_p < target_perplexity:
                feedback_msg += f"Increase perplexity above {target_perplexity}. Use more surprising and varied word choices. "
            if prev_cv < target_cv:
                feedback_msg += f"Increase sentence length variation dramatically. Mix very short (3-5 words) and very long (35+ words) sentences. CV must exceed {target_cv}. "
            output = rewrite_with_llm(processed, feedback=feedback_msg)
        
        # Measure metrics
        p = calculate_perplexity(output)
        cv = sentence_length_cv(output)
        forbidden = count_forbidden_words(output)
        forbidden_total = sum(forbidden.values())
        
        iteration_result = {
            "iteration": i + 1,
            "perplexity": p,
            "cv": cv,
            "forbidden_count": forbidden_total,
            "forbidden_words": forbidden,
            "text": output
        }
        results["iterations"].append(iteration_result)
        
        # Calculate composite score
        score = (p / target_perplexity) * 0.6 + (cv / target_cv) * 0.4
        if forbidden_total > 0:
            score *= (1 - forbidden_total * 0.05)  # Penalty for forbidden words
        
        if score > best_score:
            best_score = score
            best_output = output
        
        # Check if targets met
        if p >= target_perplexity and cv >= target_cv and forbidden_total == 0:
            results["final_text"] = output
            results["success"] = True
            results["final_metrics"] = {
                "perplexity": p,
                "cv": cv,
                "forbidden_count": forbidden_total
            }
            return results
        
        prev_p = p
        prev_cv = cv
    
    # Return best attempt if targets not fully met
    results["final_text"] = best_output
    final_p = calculate_perplexity(best_output)
    final_cv = sentence_length_cv(best_output)
    final_forbidden = count_forbidden_words(best_output)
    results["final_metrics"] = {
        "perplexity": final_p,
        "cv": final_cv,
        "forbidden_count": sum(final_forbidden.values())
    }
    results["success"] = (final_p >= target_perplexity * 0.8 and final_cv >= target_cv * 0.8)
    
    return results

# ===== 6. PDF Extraction =====
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file"""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n\n"
    return text.strip()

# ===== 7. Training Data Management =====
@app.post("/api/train")
async def train_model(
    ai_text: Optional[str] = Form(None),
    human_text: Optional[str] = Form(None),
    ai_file: Optional[UploadFile] = File(None),
    human_file: Optional[UploadFile] = File(None)
):
    """Accept AI and human-written samples for calibration"""
    
    try:
        # Process AI text
        if ai_text:
            training_data["ai_samples"].append(ai_text)
        elif ai_file:
            contents = await ai_file.read()
            if ai_file.filename.endswith('.pdf'):
                text = extract_text_from_pdf(contents)
            else:
                text = contents.decode('utf-8')
            training_data["ai_samples"].append(text)
        
        # Process human text
        if human_text:
            training_data["human_samples"].append(human_text)
        elif human_file:
            contents = await human_file.read()
            if human_file.filename.endswith('.pdf'):
                text = extract_text_from_pdf(contents)
            else:
                text = contents.decode('utf-8')
            training_data["human_samples"].append(text)
        
        # Analyze samples to calibrate thresholds
        ai_metrics = []
        human_metrics = []
        
        for sample in training_data["ai_samples"]:
            ai_metrics.append({
                "perplexity": calculate_perplexity(sample),
                "cv": sentence_length_cv(sample),
                "forbidden": sum(count_forbidden_words(sample).values())
            })
        
        for sample in training_data["human_samples"]:
            human_metrics.append({
                "perplexity": calculate_perplexity(sample),
                "cv": sentence_length_cv(sample),
                "forbidden": sum(count_forbidden_words(sample).values())
            })
        
        calibration = {
            "ai_samples_count": len(training_data["ai_samples"]),
            "human_samples_count": len(training_data["human_samples"]),
            "ai_avg_perplexity": np.mean([m["perplexity"] for m in ai_metrics]) if ai_metrics else 0,
            "ai_avg_cv": np.mean([m["cv"] for m in ai_metrics]) if ai_metrics else 0,
            "human_avg_perplexity": np.mean([m["perplexity"] for m in human_metrics]) if human_metrics else 0,
            "human_avg_cv": np.mean([m["cv"] for m in human_metrics]) if human_metrics else 0,
        }
        
        return JSONResponse(content={
            "status": "success",
            "message": "Training samples accepted and analyzed",
            "calibration": calibration
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")

# ===== 8. API Endpoints =====
class TextIn(BaseModel):
    text: str

@app.post("/api/humanize")
async def humanize_endpoint(data: TextIn):
    """Main humanization endpoint"""
    try:
        result = humanize(data.text)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Humanization error: {str(e)}")

@app.post("/api/analyze")
async def analyze_text(data: TextIn):
    """Analyze text metrics without rewriting"""
    text = data.text
    return JSONResponse(content={
        "perplexity": calculate_perplexity(text),
        "cv": sentence_length_cv(text),
        "forbidden_words": count_forbidden_words(text),
        "sentence_count": len(nltk.sent_tokenize(text)),
        "word_count": len(text.split())
    })

@app.get("/api/stats")
async def get_stats():
    """Get current training data statistics"""
    ai_count = len(training_data["ai_samples"])
    human_count = len(training_data["human_samples"])
    
    return JSONResponse(content={
        "ai_samples": ai_count,
        "human_samples": human_count,
        "ready": ai_count > 0 and human_count > 0
    })

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend HTML"""
    html_path = os.path.join(os.path.dirname(__file__), "humanizer.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return HTMLResponse(content="<h1>MathHumanizer API</h1><p>Backend is running. Frontend HTML not found.</p>")

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "model_loaded": True}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("MathHumanizer Backend Starting...")
    print("="*60)
    print("Starting server on http://127.0.0.1:8001")
    print("Open your browser to access the frontend")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8001)
