FROM python:3.11-slim

# Install Azure Functions Core Tools dependencies and Chrome for Selenium
RUN apt-get update && apt-get install -y \
    curl unzip libicu-dev gnupg \
    wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Chrome/Chromium for Selenium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Azure Functions Core Tools)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install Azure Functions Core Tools
RUN npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Set environment variables
ENV AzureWebJobsScriptRoot=/app \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python \
    AzureWebJobsStorage=""

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy function app code
COPY . .

EXPOSE 80
ENTRYPOINT ["func", "start", "--host", "0.0.0.0", "--port", "80", "--python"]
