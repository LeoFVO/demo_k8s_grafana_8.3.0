# Use the official Python base image with the desired version
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN apt update && \
  apt install -y curl bash iputils-ping dnsutils vim && \
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
  chmod +x ./kubectl && \
  mv ./kubectl /usr/local/bin/kubectl

# Copy the application files to the container
COPY . .

# Expose the port on which the Flask app runs
EXPOSE 8080

# Start the Flask application
CMD ["python", "app.py"]