FROM apify/actor-python-playwright:3.11

# Install ffmpeg for yt-dlp video+audio merging
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . ./

# Run the actor
CMD ["python", "main.py"]
