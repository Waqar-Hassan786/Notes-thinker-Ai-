# GoodWill AI Notes Maker

![WhatsApp Image 2025-12-05 at 09 05 10_bd8fea6e](https://github.com/user-attachments/assets/7d53b7a4-b270-4be1-b9fa-4a91e74b4cae)
![WhatsApp Image 2025-12-05 at 08 57 43_607abcab](https://github.com/user-attachments/assets/06b6a9c9-586f-459f-a6fc-efc814229d37)


**Transform question images into beautifully formatted, bilingual (English & Urdu) PDF notes instantly. Powered by GPT-4o-mini and advanced PDF generation.**

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-311/)
[![Framework](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![AI Model](https://img.shields.io/badge/AI_Model-GPT--4o--mini-purple.svg)](https://openai.com/gpt-4o/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Overview

The **GoodWill AI Notes Maker** is a sophisticated web application designed to automate the tedious process of creating study notes. Students and educators can simply upload images of questions from textbooks or exam papers, and the AI will:

1.  **Detect and extract** every question from the images.
2.  **Generate concise, exam-focused answers** in both English and Urdu.
3.  **Compile the results** into a professional, ready-to-print PDF document, complete with proper right-to-left (RTL) formatting for Urdu text.

This project solves a real-world problem for students, saving them hours of manual work and helping them prepare for exams more efficiently.

## ✨ Key Features

*   **AI-Powered Question & Answer Generation**: Utilizes **OpenAI's GPT-4o-mini** to intelligently parse questions from images and generate accurate answers.
*   **Bilingual Support**: Provides answers in both **English and Urdu**, catering to a wider audience.
*   **Advanced PDF Creation**: Generates high-quality, beautifully styled PDFs using `ReportLab`, featuring:
    *   **Custom Watermarks & Branding** ("GoodWill Educational Content").
    *   **Proper Right-to-Left (RTL) Rendering**: A custom `RTLParagraph` class ensures flawless display and wrapping of the Urdu language.
    *   **Professional Typography** with custom fonts and structured layouts.
*   **Modern Web Interface**:
    *   A clean, intuitive UI built with Flask and modern HTML/CSS.
    *   **Drag-and-drop** functionality for easy image uploads.
    *   Real-time progress modals and success notifications.
*   **Chapter Management**:
    *   Organize notes by chapter.
    *   View, re-generate, download, or delete previously created notes.
*   **Containerized & Deployable**: Comes with a `Dockerfile` and is configured for easy deployment on platforms like Render using Gunicorn.

---

## 🛠️ Tech Stack & Core Libraries

| Category              | Technology / Library                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- |
| **Backend**           | ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python) ![Flask](https://img.shields.io/badge/-Flask-000000?logo=flask) ![Gunicorn](https://img.shields.io/badge/-Gunicorn-499848?logo=gunicorn) |
| **AI Integration**    | ![OpenAI](https://img.shields.io/badge/-OpenAI-412991?logo=openai)                       |
| **PDF Generation**    | `ReportLab`                                                                             |
| **RTL Text Support**  | `arabic-reshaper`, `python-bidi`                                                        |
| **Image Processing**  | `Pillow`, `OpenCV`                                                                      |
| **Frontend**          | ![HTML5](https://img.shields.io/badge/-HTML5-E34F26?logo=html5) ![CSS3](https://img.shields.io/badge/-CSS3-1572B6?logo=css3) ![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?logo=javascript) |
| **Containerization**  | ![Docker](https://img.shields.io/badge/-Docker-2496ED?logo=docker)                       |

---

## 🚀 Running the Project Locally

To get the application running on your local machine, follow these steps.

### 1. Prerequisites

*   **Python 3.11** or later.
*   **ImageMagick** (required by some `ReportLab` features).
*   **OpenAI API Key**: Create a `.env` file in the root directory and add your key:
    ```
    OPENAI_API_KEY='your-secret-api-key'
    ```

### 2. Clone the Repository

```bash
git clone https://github.com/Waqar-Hassan786/your-repo-name.git
cd your-repo-name
```

### 3. Set Up a Virtual Environment & Install Dependencies

```bash
# Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install all required packages
pip install -r requirements.txt
```

### 4. Run the Application

```bash
# Start the Flask development server
flask run
```

The application will be accessible at `http://127.0.0.1:5000`.

### 5. Running with Docker (Alternative)

You can also build and run the project using Docker, which handles all dependencies internally.

```bash
# Build the Docker image
docker build -t notes-maker .

# Run the Docker container (make sure to pass the API key)
docker run -p 5000:5000 --env-file .env notes-maker
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Waqar-Hassan786/your-repo-name/issues).

1.  **Fork** the repository.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a **Pull Request**.

## 📄 License

This project is distributed under the MIT License. See `LICENSE` for more information.

---

*This project was created by Waqar Hassan as part of the GoodWill educational content initiative.*
