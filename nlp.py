import os
import re
import sys
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Initialize Sentence Transformer (Persian Embeddings)
embedder = SentenceTransformer('xmanii/maux-gte-persian', device='cpu', cache_folder="cache", trust_remote_code=True)

# Initialize LLaMA Model Configuration
model_name = "universitytehran/PersianMind-v1.0"
model_cache_dir = "cache"

if not os.path.exists(model_cache_dir):
    os.makedirs(model_cache_dir)

# Load Tokenizer and Model
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_cache_dir)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    cache_dir=model_cache_dir,
    torch_dtype=torch.float32,
    device_map="auto"
)

def preprocess_text(text):
    """
    Applies cleaning steps such as removing noise and normalizing numbers.
    """
    numerals_mapping = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    text = ''.join(numerals_mapping.get(c, c) for c in text)
    text = re.sub(r'\d+-\d+-.*', '', text)
    return text

def batch_encode_sections(embedder, sections, batch_size=16):  # Increase batch size
    """
    Encodes sections in larger batches to process more data at once.
    """
    embeddings = []
    for i in range(0, len(sections), batch_size):
        batch = sections[i:i + batch_size]
        embeddings.extend(embedder.encode(batch))
    return np.array(embeddings)

def extract_relevant_context(question, text, section_embeddings, section_files, file_first_lines, context_window=10, top_n=2):  # Increase context_window and top_n
    """
    Finds the most relevant sections using cosine similarity and returns the entire context,
    including all the relevant sections and their original order.
    """
    question_embedding = embedder.encode([question])[0]
    similarities = cosine_similarity([question_embedding], section_embeddings)[0]

    # Get the indices of the top_n most relevant sections
    relevant_indices = np.argsort(similarities)[-top_n:][::-1]  # Sort and pick the top_n

    # Collect all relevant sections, including the first line of each file
    relevant_sections = []
    for index in relevant_indices:
        start_index = max(index - context_window // 2, 0)
        end_index = min(index + context_window // 2 + 1, len(text.splitlines()))

        relevant_lines = text.splitlines()[start_index:end_index]
        file_name = section_files[index]
        first_line = file_first_lines[file_name]

        # Add the first line from the file and the relevant lines from the section
        relevant_sections.append(f"منبع : {first_line}\n" + "\n".join(relevant_lines))

    # Sort the sections by their original order to maintain logical flow
    relevant_sections.sort(key=lambda x: section_files.index(file_name))

    # Combine all relevant sections into one full context
    ordered_relevant_context = "\n\n".join(relevant_sections)

    return ordered_relevant_context

def generate_response(question, context):
    """
    Generates a response using the LLaMA model with a larger token length.
    """
    # Check if the context is too long for the model (max token length is 2048)
    max_token_length = 2048  # Increase max token length

    context_tokens = tokenizer(context, return_tensors="pt")["input_ids"]
    if len(context_tokens[0]) > max_token_length:
        context = tokenizer.decode(context_tokens[0][:max_token_length])

    # Prepare the prompt with the complete context
    prompt = f"""

    پرسش: {question}

    قوانین مرتبط:
    {context}

    لطفاً یک پاسخ دقیق، کامل و مبتنی بر قوانین مرتبط ارائه دهید:
    """

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_token_length)
    inputs = {key: value.to(next(model.parameters()).device) for key, value in inputs.items()}

    output = model.generate(**inputs, temperature=0.1, max_new_tokens=1024)
    return tokenizer.decode(output[0], skip_special_tokens=True)

# Main Execution
if __name__ == "__main__":
    try:
        question = sys.stdin.read().strip()

        # Load and preprocess the text from multiple files in "rules" directory
        rules_dir = "rules"
        raw_text = ""
        section_files = []  # List to store the corresponding file names
        file_first_lines = {}  # Dictionary to store the first line of each file

        for file_name in os.listdir(rules_dir):
            if file_name.endswith(".txt"):
                with open(os.path.join(rules_dir, file_name), "r", encoding="utf-8") as f:
                    file_text = f.read()
                    raw_text += file_text + "\n"
                    section_files.extend([file_name] * len(file_text.splitlines()))  # Match each line to the file
                    file_first_lines[file_name] = file_text.splitlines()[0]  # Save the first line of the file

        preprocessed_text = preprocess_text(raw_text)
        sections = preprocessed_text.splitlines()
        section_embeddings = batch_encode_sections(embedder, sections)

        # Find the most relevant context and generate a response
        relevant_context = extract_relevant_context(question, preprocessed_text, section_embeddings, section_files, file_first_lines)

        # Generate the final response based on the full relevant context
        response = generate_response(question, relevant_context)

        # Save response to a file
        with open("answer.txt", "w", encoding="utf-8") as f:
            f.write(response)

        sys.stdout.write(response + "\n")

    except Exception as e:
        sys.stderr.write(f"An error occurred: {str(e)}\n")
