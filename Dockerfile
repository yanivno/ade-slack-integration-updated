# Use the official Azure Functions Python 3.11 base image
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set the working directory
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Copy requirements and install dependencies
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

# Copy function code
COPY . /home/site/wwwroot/expirationRunNow
COPY host.json /home/site/wwwroot/

# Set working directory to function app root
WORKDIR /home/site/wwwroot
