FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Python packages and gcloud CLI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gnupg \
    lsb-release \
    && curl -sSL https://sdk.cloud.google.com > /tmp/gcl \
    && bash /tmp/gcl --install-dir=/usr/local --disable-prompts \
    && rm -rf /var/lib/apt/lists/* /tmp/gcl

# Add gcloud to PATH
ENV PATH="/usr/local/google-cloud-sdk/bin:${PATH}"

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