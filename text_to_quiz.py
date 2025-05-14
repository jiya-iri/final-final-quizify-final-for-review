import re
import random
import nltk
from nltk.tokenize import sent_tokenize

# Ensure punkt is downloaded
nltk.download('punkt')

# Function to create fill-in-the-blank questions
def create_fill_in_the_blank_questions(text, count=5):
    sentences = sent_tokenize(text)
    questions = []

    for sentence in sentences:
        words = sentence.split()
        if len(words) > 5:
            word_candidates = [w for w in words if w.strip(".,?!").isalpha()]
            if word_candidates:
                missing_word = random.choice(word_candidates)
                question = sentence.replace(missing_word, "_____")
                questions.append({
                    "question": question.strip(),
                    "answer": missing_word.strip(".,?!")
                })
        if len(questions) >= count:
            break

    return questions

# Function to generate distractors
def generate_distractors(correct_answer, word_list):
    word_list = [w for w in word_list if w.lower() != correct_answer.lower()]
    distractors = random.sample(word_list, min(3, len(word_list)))
    return distractors

# Function to create multiple-choice questions
def create_mcq_questions(text, count=5):
    sentences = sent_tokenize(text)
    word_list = list(set(re.findall(r'\b\w+\b', text)))  # All words in the text
    mcq_questions = []

    for sentence in sentences:
        words = sentence.split()
        if len(words) > 5:
            word_candidates = [w for w in words if w.strip(".,?!").isalpha()]
            if word_candidates:
                correct_answer = random.choice(word_candidates)
                question = sentence.replace(correct_answer, "_____")
                distractors = generate_distractors(correct_answer, word_list)
                options = distractors + [correct_answer.strip(".,?!")]
                random.shuffle(options)
                mcq_questions.append({
                    "question": question.strip(),
                    "answer": correct_answer.strip(".,?!"),
                    "options": options
                })
        if len(mcq_questions) >= count:
            break

    return mcq_questions

# Function to generate the full quiz (fill-in-the-blank + MCQ)
def generate_quiz(file_path, num_fill=5, num_mcq=5, question_type="both"):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        return {"error": "File not found"}

    # Basic cleanup: remove excess whitespace and non-alphanumeric characters (except punctuation)
    content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
    content = re.sub(r'[^\w\s.,?!]', '', content)  # Remove unwanted punctuation marks

    # Determine which questions to generate based on the requested type
    quiz = {}

    if question_type == "fill_in_the_blank" or question_type == "both":
        quiz["fill_in_the_blank"] = create_fill_in_the_blank_questions(content, num_fill)

    if question_type == "mcq" or question_type == "both":
        quiz["mcq"] = create_mcq_questions(content, num_mcq)

    return quiz
