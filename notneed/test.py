import os
import re
import sys
from notneed.preper import Preper  
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


def convert_to_english_digits(input_path, output_path):
    # Mapping for both Persian and Arabic-Indic numerals
    numerals_mapping = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }

    try:
        with open(input_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Replace numerals with their English equivalents
        converted_content = ''.join(
            numerals_mapping.get(char, char) for char in content
        )

        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(converted_content)

        print(f"Conversion completed. Check '{output_path}' for results.")
    except FileNotFoundError:
        print(f"Error: The file '{input_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Example usage:
convert_to_english_digits('rules.txt', 'converted_rules_regex.txt')

# Check if the text file exists
txt_path = "converted_rules_regex.txt"
if not os.path.exists(txt_path):
    raise FileNotFoundError(f"{txt_path} does not exist in the current directory.")

# Extract text from the .txt file
def extract_text_from_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as file:
        return file.read()

# Read the content of the .txt file
txt_content = extract_text_from_txt(txt_path)

# Initialize the Preper class with extracted text
preprocessor = Preper(text=txt_content)

# Preprocess the text: remove noise and normalize letters
preprocessed_text = preprocessor.remove_noise()
preprocessor.text = ' '.join(preprocessed_text)  # Update text after removing noise
preprocessor.normalise_letter()  # Normalize the text

# Split the preprocessed text into sections
sections = preprocessor.text.split('\n')  # For example, split by newlines to get sections

def extract_sections_by_keywords(text):
    # Regex to match sections starting with "ماده" 
    pattern = r'(ماده \d+)(.*?)(?=(ماده \d+)|$)'  # Split until next "ماده" 
    
    # Use re.findall to capture both the "ماده" or "تبصره" and the subsequent content
    sections = re.findall(pattern, text, re.DOTALL)
    
    # Combine "ماده" or "تبصره" with their following content
    return [f'{section[0]}{section[1].strip()}' for section in sections]

sections = extract_sections_by_keywords(preprocessor.text)

# Use cache directory to avoid redownloading the model
embedder = SentenceTransformer('xmanii/maux-gte-persian', device='cpu', cache_folder="cache", trust_remote_code=True)

# Generate embeddings for each section
section_embeddings = embedder.encode(sections)

# Llama model configuration
model_name = "universitytehran/PersianMind-v1.0"
model_cache_dir = "cache"

# Check if cache directory exists
if not os.path.exists(model_cache_dir):
    os.makedirs(model_cache_dir)

tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_cache_dir)

# Load model with FP16 precision for M1 compatibility
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    cache_dir=model_cache_dir,
    torch_dtype=torch.float32,
    device_map="auto"
)

def find_relevant_section_with_subsections(question, sections, section_embeddings):
    # Generate the embedding for the question using the same model
    question_embedding = embedder.encode([question])[0]
    
    # Calculate cosine similarities between the question and each section
    similarities = cosine_similarity([question_embedding], section_embeddings)[0]
    
    # Find the index of the most relevant section (highest similarity)
    most_relevant_index = np.argmax(similarities)
    
    # Get the most relevant section (this includes subsections as well)
    relevant_section = sections[most_relevant_index]
    
    # Extract subsections related to this section (if applicable)
    # Assuming subsections are always following a "ماده" section
    if "ماده" in relevant_section:
        # Find all sections starting with "ماده" and related "تبصره" sections
        relevant_section_index = most_relevant_index
        full_section = relevant_section
        
        # Include all following subsections (تبصره) until the next "ماده"
        for i in range(relevant_section_index + 1, len(sections)):
            if sections[i].startswith("ماده"):  # New "ماده" means end of the relevant section
                break
            full_section += "\n" + sections[i]
        
        return full_section
    else:
        return relevant_section

# Read question from stdin (as passed by the Go backend)
question = sys.stdin.read().strip()

# Find the relevant section
relevant_section = find_relevant_section_with_subsections(question, sections, section_embeddings)

def remove_after_pattern(text):
    # Regular expression pattern to match the 'number-number-' and everything after it
    pattern = r'\d+-\d+-.*'
    # Replace the pattern and everything after it with an empty string
    return re.sub(pattern, '', text)

# Apply the function to the relevant_section
relevant_section = remove_after_pattern(relevant_section)

def query_llama3_farsi_v2(question, context_text):
    # طراحی Prompt پیشرفته‌تر
    prompt = f"""
    شما یک دستیار هوشمند برای پاسخ به سؤالات بر اساس قوانین دانشگاه هستید.
    پرسش: {question}

    قوانین مرتبط:
    {context_text}

    .لطفاً یک پاسخ دقیق، کامل و مبتنی بر قوانین مرتبط ارائه دهید:
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    inputs = {key: value.to(next(model.parameters()).device) for key, value in inputs.items()}
    
    output = model.generate(**inputs, temperature=0.1, top_p=0.8, max_new_tokens=1024)
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    
    return response

# Query the model
response = query_llama3_farsi_v2(question, relevant_section)

def remove_duplicate_lines(text):
    # تقسیم متن به خطوط و حذف خطوط تکراری
    lines = text.split('\n')
    unique_lines = list(dict.fromkeys(lines))  # حذف تکرار با حفظ ترتیب
    return '\n'.join(unique_lines)

response = remove_duplicate_lines(response)

# ذخیره پاسخ نهایی به فایل
with open("answer.txt", "w", encoding="utf-8") as f:
    f.write("پاسخ مبتنی بر قوانین استخراج شده از rules.txt:\n")
    f.write(response)

# Output the response (this is what will be captured by the Go backend)
sys.stdout.write(response + "\n")