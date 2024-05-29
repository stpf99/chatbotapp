import sys
import os
import json
import urllib.parse
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit, QComboBox
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import snapshot_download

class ChatbotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.model_path = None
        self.config_path = None
        self.current_model = None
        self.tokenizer = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Chatbot')
        self.layout = QVBoxLayout()

        self.model_url_input = QLineEdit()
        self.model_url_input.setPlaceholderText("Enter model URL from Hugging Face")
        self.layout.addWidget(self.model_url_input)

        self.download_button = QPushButton('Download Model')
        self.download_button.clicked.connect(self.download_model)
        self.layout.addWidget(self.download_button)

        self.model_list = QComboBox()
        self.load_model_list()
        self.layout.addWidget(self.model_list)

        self.load_button = QPushButton('Load Model')
        self.load_button.clicked.connect(self.load_selected_model)
        self.layout.addWidget(self.load_button)

        self.text_input = QTextEdit(self)
        self.layout.addWidget(QLabel("User Input:"))
        self.layout.addWidget(self.text_input)

        self.generate_button = QPushButton('Generate Response', self)
        self.generate_button.clicked.connect(self.generate_response)
        self.layout.addWidget(self.generate_button)

        self.text_output = QTextEdit(self)
        self.text_output.setReadOnly(True)
        self.layout.addWidget(QLabel("Chatbot Response:"))
        self.layout.addWidget(self.text_output)

        self.setLayout(self.layout)
        self.show()

    def download_model(self):
        model_url = self.model_url_input.text()
        if model_url:
            try:
                model_name = urllib.parse.unquote(model_url.split("/")[-1])
                model_dir = os.path.join("models", model_name)
                snapshot_download(model_url, local_dir=model_dir)
                self.text_output.setText(f"Model downloaded successfully to {model_dir}")
                self.load_model_list()
            except Exception as e:
                self.text_output.setText(f"Error downloading model: {e}")
        else:
            self.text_output.setText("Please enter a model URL from Hugging Face.")

    def load_model_list(self):
        self.model_list.clear()
        models_dir = os.path.join(os.getcwd(), "models")
        if os.path.exists(models_dir):
            model_subdirs = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
            self.model_list.addItems(model_subdirs)

    def load_selected_model(self):
        selected_model = self.model_list.currentText()
        if selected_model:
            self.model_path = os.path.join("models", selected_model)
            self.config_path = self.model_path
            self.load_model()
            self.load_tokenizer()
        else:
            self.text_output.setText("No model selected.")

    def load_model(self):
        try:
            self.current_model = AutoModelForCausalLM.from_pretrained(self.config_path, trust_remote_code=True)
            self.text_output.setText("Model loaded successfully.")
        except Exception as e:
            self.text_output.setText(f"Error loading model: {e}")

    def load_tokenizer(self):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config_path)
            self.text_output.setText("Tokenizer loaded successfully.")
        except Exception as e:
            self.text_output.setText(f"Error loading tokenizer: {e}")

    def generate_response(self):
        if self.current_model is None or self.tokenizer is None:
            self.text_output.setText("No model or tokenizer loaded.")
            return

        user_input = self.text_input.toPlainText()
        inputs = self.tokenizer(user_input, return_tensors='pt')
        outputs = self.current_model.generate(**inputs, max_length=100, num_return_sequences=1)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        self.text_output.setText(response)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ChatbotApp()
    sys.exit(app.exec_())