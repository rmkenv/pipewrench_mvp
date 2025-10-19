# PipeWrench AI - Institutional Knowledge Capture Assistant

PipeWrench AI is a FastAPI-based application designed to assist local government engineering and public works departments in capturing and formalizing institutional knowledge from retiring employees. It leverages Anthropic's Claude models to review documents, generate targeted questions, identify knowledge gaps, and draft Standard Operating Procedures (SOPs).

## Features

- **Interactive Web GUI:** A user-friendly web interface for interacting with the AI.
- **Direct Question Answering:** Ask PipeWrench AI questions directly.
- **Document Analysis:** Upload PDF, DOCX, or TXT files for advanced analysis:
    - **Generate Interview Questions:** Create targeted questions based on uploaded job descriptions, SOPs, or BMPs to facilitate knowledge transfer.
    - **Identify Knowledge Gaps:** Analyze documents to pinpoint missing information or areas requiring more detail.
    - **Create SOP Draft:** Generate a structured draft of a Standard Operating Procedure from existing documentation.
- **Anthropic Claude Integration:** Utilizes various Claude models for powerful AI capabilities.

## Getting Started

Follow these instructions to set up and run PipeWrench AI locally.

### Prerequisites

- Python 3.8+
- An Anthropic API Key (`sk-ant-...`)

### Installation

1.  **Clone the repository (or create your project directory):**
    ```bash
    git clone <your-repo-url>
    cd pipewrench-ai
    ```
    If you're not using Git, create a folder named `pipewrench-ai` and navigate into it.

2.  **Create a `static` directory:**
    ```bash
    mkdir static
    ```

3.  **Save the files:**
    -   Save the Python code (provided in the previous turn) as `main.py` in the root of your `pipewrench-ai` directory.
    -   Save the HTML code (provided in the previous turn) as `index.html` inside the `static` directory.

4.  **Create `requirements.txt`:**
    Create a file named `requirements.txt` in the root of your `pipewrench-ai` directory and add the following content:
    ```
    fastapi
    uvicorn[standard]
    anthropic
    python-multipart
    PyPDF2
    python-docx
    ```

5.  **Install dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Start the FastAPI server:**
    ```bash
    uvicorn main:app --reload
    ```
    The `--reload` flag will automatically restart the server on code changes.

2.  **Access the GUI:**
    Open your web browser and navigate to:
    ```
    http://localhost:8000/
    ```

## Usage

1.  **Enter your Anthropic API Key:** Provide your `sk-ant-...` API key in the designated field.
2.  **Select a Tab:** Choose between "Ask Questions" for direct interaction or "Analyze Document" for file-based analysis.
3.  **For "Ask Questions":** Type your question in the textarea and click "Ask PipeWrench AI".
4.  **For "Analyze Document":**
    -   Upload a PDF, DOCX, or TXT file.
    -   Select the desired "Analysis Type" (Generate Interview Questions, Identify Knowledge Gaps, or Create SOP Draft).
    -   Click "Analyze Document".
5.  **View Results:** The AI's response will appear in the "Response" or "Analysis Results" section.

## Project Structure
