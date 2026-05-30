# Minimal image for the PoC. In production, the base image and the build
# pipeline would come from the platform team's Backstage template.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "streamlit>=1.34" \
    "langgraph>=0.2.30" \
    "langchain-openai>=0.2.0" \
    "langchain-core>=0.3.0" \
    "pandas>=2.2" \
    "python-dotenv>=1.0"

# Copy app code and data.
COPY src ./src
COPY data ./data

EXPOSE 8501

# Streamlit needs to bind to 0.0.0.0 to be reachable from outside the container.
CMD ["streamlit", "run", "src/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
