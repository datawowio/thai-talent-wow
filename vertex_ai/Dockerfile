FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY vertex_ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ ./config/
COPY skill_promotion_management/ ./skill_promotion_management/
COPY predictive_retention/ ./predictive_retention/
COPY vertex_ai/ ./vertex_ai/
COPY mock_data/ ./mock_data/
COPY output/ ./output/

# Create necessary directories
RUN mkdir -p output

# Set Python path
ENV PYTHONPATH=/app
ENV GOOGLE_CLOUD_PROJECT=th-ai-talent-wow
ENV GOOGLE_CLOUD_REGION=asia-southeast1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the secure API
CMD ["python", "vertex_ai/secure_api.py"]