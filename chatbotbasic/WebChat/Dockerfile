FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Set environment variable for OpenAI key 
# ENV OPENAI_API_KEY=<your-key-here>

# Default command to run the app
CMD ["python", "app.py"]
