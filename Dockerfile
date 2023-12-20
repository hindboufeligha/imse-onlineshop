# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /M2

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
#RUN pip install --no-cache-dir -r requirements.txt

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt


# Copy the content of the local src directory to the working directory
COPY . /M2

# Expose port 5000 for the Flask app to run on
EXPOSE 5000

# Define environment variable
#ENV NAME World

# Command to run the application
CMD ["python", "./main.py"]
