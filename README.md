# AI Lot Information Coordinator

A simple AI-powered system for managing and coordinating construction lot information.

## Features

- Ask questions about lot status, locations, appointments, and tasks
- Automatically updates knowledge base based on AI responses
- Web interface for easy interaction
- Command-line interface also available

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

3. Run the web application:
```bash
python app.py
```

4. Open your browser and go to: `http://localhost:5000`

## Usage

### Web Interface
- Enter questions in the input field
- View current lots in the sidebar
- AI responses update automatically

### Command Line
Run `python ai_test.py` for the command-line interface.

## Example Questions

- "What is the status of lot 1001 and lot 1002?"
- "Update lot 1001 status to Completed"
- "Add a new lot 2001 in Texas with status Foundation Complete"
- "What lots have appointments next week?"
