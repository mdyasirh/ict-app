# MathHumanizer - AI Text Humanization Tool

## Overview
MathHumanizer is an advanced AI text humanization system designed to rewrite AI-generated content to be statistically indistinguishable from human writing. It uses mathematical metrics (perplexity and burstiness) to evade AI detection systems like Turnitin.

## ⚡ Quick Start

```bash
cd /workspace/mathhumanizer
python start_server.py
```

Then open your browser to: **http://127.0.0.1:8001**

## Features

### Core Capabilities
- **Perplexity Optimization**: Increases word unpredictability using DistilGPT-2 analysis
- **Burstiness Enhancement**: Varies sentence lengths to mimic human writing patterns
- **Forbidden Word Detection**: Identifies and replaces AI-typical vocabulary
- **Iterative Refinement**: Multi-pass feedback loop for optimal results
- **PDF Support**: Upload and process PDF documents
- **Training Mode**: Calibrate with your own AI/human text samples

### Technical Components
1. **Text Analyzer** (DistilGPT-2): Computes perplexity, burstiness, and forbidden word counts
2. **Pre-Processor**: Rule-based injections for burstiness and perplexity enhancement
3. **LLM Rewriter**: Llama 3 integration via Ollama API
4. **Feedback Controller**: Iterative refinement based on metric targets

## Installation

### Prerequisites
- Python 3.10+
- Ollama installed and running locally with `llama3` model
- Internet connection for initial model download (~400MB for DistilGPT-2)

### Setup Steps

1. **Navigate to the project directory:**
   ```bash
   cd /workspace/mathhumanizer
   ```

2. **Install dependencies:**
   ```bash
   python -m pip install fastapi uvicorn ollama torch transformers nltk sentence-transformers PyPDF2 python-multipart numpy
   ```

3. **Download NLTK data:**
   ```bash
   python -c "import nltk; nltk.download('punkt'); nltk.download('wordnet'); nltk.download('omw-1.4')"
   ```

4. **Ensure Ollama is running with Llama 3:**
   ```bash
   # Install Ollama if not already installed (https://ollama.ai)
   # Then pull the model:
   ollama pull llama3
   ```

## Usage

### Starting the Backend Server

```bash
cd /workspace/mathhumanizer
python start_server.py
```

Or directly:
```bash
python humanizer_api.py
```

The server will start on `http://127.0.0.1:8001`

### Accessing the Frontend

Open your web browser and navigate to:
```
http://127.0.0.1:8001
```

### Workflow

#### Step 1: Training (Optional but Recommended)
1. Upload or paste AI-generated text (100% AI score)
2. Upload or paste human-written text (0% AI score)
3. Click "Analyze & Train Model"
4. Review calibration results showing statistical differences
5. Proceed to humanization

#### Step 2: Humanization
1. Paste your AI-generated text in the input panel
2. Optionally click "Analyze First" to see current metrics
3. Click "Humanize Text"
4. View iteration results and final output
5. Copy the humanized text

## API Endpoints

### POST `/api/train`
Upload training samples for calibration.

**Parameters:**
- `ai_text` (form): AI-generated text sample
- `human_text` (form): Human-written text sample
- `ai_file` (file): PDF/TXT file with AI text
- `human_file` (file): PDF/TXT file with human text

### POST `/api/humanize`
Main humanization endpoint.

**Request Body:**
```json
{
    "text": "Your AI-generated text here..."
}
```

**Response:**
```json
{
    "original": {
        "perplexity": 85.2,
        "cv": 0.25,
        "forbidden_count": 12
    },
    "iterations": [...],
    "final_text": "Humanized output...",
    "success": true,
    "final_metrics": {
        "perplexity": 145.6,
        "cv": 0.52,
        "forbidden_count": 0
    }
}
```

### POST `/api/analyze`
Analyze text without rewriting.

### GET `/api/stats`
Get current training data statistics.

### GET `/api/health`
Health check endpoint.

## Mathematical Targets

The system aims for these metrics to achieve human-like text:

| Metric | AI Text | Human Text | Target |
|--------|---------|------------|--------|
| Perplexity | 60-90 | 120-180 | >120 |
| Burstiness (CV) | 0.2-0.35 | 0.45-0.75 | >0.45 |
| Forbidden Words | High | Low/None | 0 |

## Configuration

### Adjustable Parameters in `humanizer_api.py`:

```python
# AI word blacklist
AI_BLACKLIST = {...}

# Humanization settings
max_iters = 3          # Maximum refinement iterations
target_perplexity = 120  # Target perplexity threshold
target_cv = 0.45       # Target burstiness threshold

# LLM settings
model = "llama3"       # Ollama model name
temperature = 0.95     # Generation temperature
```

## Troubleshooting

### Common Issues

1. **"Backend may not be running"**
   - Ensure you've started the server with `python start_server.py`
   - Check that port 8001 is not in use

2. **"LLM service unavailable"**
   - Verify Ollama is installed and running
   - Pull the llama3 model: `ollama pull llama3`
   - Check Ollama service status

3. **Slow processing / Model download issues**
   - First run downloads the DistilGPT-2 model (~350MB)
   - Ensure sufficient disk space
   - The system has a fallback mode using word statistics if model can't load

4. **Poor humanization quality**
   - Provide training samples for better calibration
   - Increase `target_perplexity` and `target_cv` values
   - Try multiple iterations manually

5. **Memory errors**
   - Reduce max sequence length in `calculate_perplexity()`
   - Process shorter text segments

## Security Notes

- All processing happens locally - no data sent to external services
- Training data is stored in-memory only (resets on restart)
- Run on localhost only for security

## License

This tool is provided for educational purposes. Users are responsible for ensuring compliance with their institution's academic integrity policies.

## Credits

Built with:
- FastAPI (Backend framework)
- Hugging Face Transformers (DistilGPT-2)
- Ollama (Local LLM inference)
- NLTK (Natural language processing)
- PyPDF2 (PDF extraction)
