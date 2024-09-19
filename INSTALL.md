# Installation Guide

This guide provides step-by-step instructions to set up the project after cloning the repository.

## Step 1: Install Miniconda

Download and install Miniconda using the following commands:

```bash
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh > Miniconda3.sh
chmod +x Miniconda3.sh
./Miniconda3.sh
```

## Step 2: Create a Conda Environment

Create a new Conda environment with Python 3.12 and activate it:

```bash
conda create -y -n nlp python=3.12
conda activate nlp
```

## Step 3: Clone the Repository

Clone the repository using the specified branch:

```bash
git clone https://github.com/genomehubs/goat-nlp
cd goat-nlp
```

## Step 4: Install Python Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

## Step 5: Install Ollama

Install Ollama using the provided script:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Step 6: Run Ollama

Run the Ollama application:

```bash
ollama run lama3.1:8b-instruct-q4_0
```

## Step 7: Start the Flask Application

Set the necessary environment variables and start the Flask application:

```bash
export OLLAMA_HOST_URL=http://127.0.0.1:11434
export RETRY_COUNT=5
export GOAT_BASE_URL=https://goat.genomehubs.org/api/v2
export ATTRIBUTE_API_TTL=172800
python -m flask run
```

## Step 8: Start the frontend

**Change directory:**

```
cd ui
```

**Create a `.env` file:**

```
NEXT_PUBLIC_OLLAMA_URL="http://127.0.0.1:11434"
NEXT_GOAT_NLP_BACKEND="http://localhost:5000"
```

**Install dependencies:**

```
npm install
```

**Start the development server:**

```
npm run dev
```
The UI will be available at `http://localhost:3000/`

# Testing guide

Install dev dependencies

```
pip install -r requirements-dev.txt
```

Run `pytest`

```
export OLLAMA_HOST_URL=http://127.0.0.1:11434
export RETRY_COUNT=5
export GOAT_BASE_URL=https://goat.genomehubs.org/api/v2
export ATTRIBUTE_API_TTL=172800

pytest -W ignore::DeprecationWarning -k test_intent_module
```
