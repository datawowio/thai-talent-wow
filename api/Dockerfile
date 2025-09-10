FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Python packages and gcloud CLI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gnupg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update && apt-get install -y google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML API and dependencies
COPY api/retention_api.py ./
COPY api/database.py ./
COPY config/ ./config/
COPY predictive_retention/ ./predictive_retention/
COPY mock_data/ ./mock_data/

# Create output directory
RUN mkdir -p output

# Set environment variables
ENV API_SECRET_KEY=${API_SECRET_KEY:-th-ai-talent-wow-secret-2024}

# Expose port
EXPOSE 8080

# Run the ML retention API
CMD ["python", "retention_api.py"]