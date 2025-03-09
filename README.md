# NLP Chatbot

A sophisticated chatbot powered by Natural Language Processing (NLP) and a PostgreSQL backend, designed to handle user queries in Persian. This project integrates advanced NLP techniques, including text embedding and cosine similarity, with a robust backend system for job queueing and status tracking.

## Key Features

- **Persian Language Support**: The chatbot is optimized for Persian text, with preprocessing and embedding models tailored for Persian language understanding.
- **NLP Pipeline**: Utilizes Sentence Transformers for text embeddings and a fine-tuned LLaMA model for generating context-aware responses.
- **Job Queueing System**: A PostgreSQL-backed job management system allows users to submit queries, track job statuses, and receive real-time updates via Server-Sent Events (SSE).
- **Interactive Frontend**: A clean and responsive web interface built with HTML, CSS, and JavaScript, enabling users to interact with the chatbot seamlessly.
- **Contextual Responses**: The chatbot extracts relevant context from a predefined set of rules and generates accurate, context-aware answers.

## Technologies Used

- **Backend**: Go (Golang) with PostgreSQL for job management and status tracking.
- **NLP**: Python with Sentence Transformers, LLaMA model, and cosine similarity for text processing.
- **Frontend**: HTML, CSS, and JavaScript for a user-friendly interface.
- **Real-Time Updates**: Server-Sent Events (SSE) for streaming job status updates to the frontend.

## How It Works

1. Users submit their questions via the web interface.
2. The backend enqueues the job and processes it using the NLP pipeline.
3. The chatbot extracts relevant context from a rules database and generates a response.
4. Users receive real-time updates on their job status and the final response.

## Use Cases

- **Customer Support**: Automate responses to frequently asked questions in Persian.
- **Educational Tools**: Provide students with instant answers to questions based on predefined rules.
- **Legal or Regulatory Assistance**: Offer context-aware responses based on legal or regulatory documents.

## Getting Started

1. Clone the repository.
2. Set up the PostgreSQL database and configure the connection string.
3. Install the required Python dependencies for the NLP pipeline.
4. Run the Go backend server and launch the frontend.
5. Start interacting with the chatbot!
