FROM apify/actor-python-playwright:3.11

# Copy requirements
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium for TikTok-Api
RUN playwright install chromium

# Copy source code
COPY . ./

# Run the actor
CMD ["python", "main.py"]
