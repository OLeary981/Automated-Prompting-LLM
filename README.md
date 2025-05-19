# Automated Prompting LLM

## Overview

A Flask application for managing and automating prompts to Large Language Models (LLMs), with a focus on reading stories and answering questions.

## Table of Contents

* [Demo](#demo)
* [Features](#features)
* [Installation](#installation)
* [Database Setup](#database-setup)
* [Initial Setup](#initial-setup)
* [Usage](#usage-guide)
* [Project Structure](#project-structure)
* [Acknowledgements](#acknowledgements)

## Demo

If you have a live demo, GIF, or video, link or embed it here.

## Features

* 📝 Create and manage stories and templates
* 🎛️ Build and customise prompts for LLMs
* 🤖 Integrate with LLM providers (Groq focus) to send prompt batches
* ⚙️ Manage model configurations with custom parameters
* 📊 Track and analyse LLM responses
* 🗂️ Organise content with categories and tags

## Installation

```bash
# Clone the repository
$ git clone https://github.com/OLeary981/Automated-Prompting-LLM.git
$ cd Automated-Prompting-LLM

#Create and activate a virtual Environment:
$ python -m venv.venv

On Windows
.venv\Scripts\activate

On macOS/Linux
source .venv/bin/activate

# Install dependencies
$ pip install -r requirements.txt

# Create a .env file and copy .env.example
$ cp .env.example .env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URI=sqlite:///app.db
GROQ_API_KEY=your-groq-api-key

```
## Database Setup

This application uses SQLAlchemy with Flask-Migrate to manage the database schema. The database is automatically created when you first run the application, but you need to apply migrations to create the tables.

### Initial Setup

After installing dependencies and setting up your `.env` file:

1. Initialize the database (first-time setup only):
   ```bash
   flask db upgrade
   ```
2. This will create all necessary tables based on the latest migration version.

## Running the Application

```bash
# Start the development server
$ flask run
The application will be available at `http://127.0.0.1:5000`.

```

## Usage Guide

### Managing Models

1. Navigate to "Manage LLM Models" on the homepage
2. Click "Add New Model" to add a model configuration
3. For Groq models, select from the dropdown to auto-fill details
4. Configure model parameters as needed

### Creating Stories

1. Go to "Work with Stories" on the homepage
2. Click "Add Story" to create a new story
3. Assign categories and tags to organize your content
4. Stories can also be created from templates

### Building Prompts

1. Select "Build and Send a Prompt to an LLM" from the homepage
2. Choose one or more stories as the base content
3. Select a question to focus the prompt
4. Choose a model to generate the response
5. Select parameters and add an optional run description
6. View and save the generated response(s)

### Managing Templates

Use templates to create standardized story structures:

1. Navigate to "Build Stories from Template" 
2. Create new templates with placeholders
3. Generate stories by filling in template values
4. Values will be supplied from the database but can also be added manually.

## Database Migrations

This project uses Flask-Migrate (Alembic) for database migrations. 

To apply migrations after pulling updates:
flask db upgrade

## Project Structure

- `/app` - Main application code
  - `/blueprints` - Route definitions organised by feature
  - `/models` - SQLAlchemy database models
  - `/services` - Business logic and external service integration
  - `/templates` - Jinja2 HTML templates
  - `/static` - CSS, JavaScript, and other static files
  - `/utils` - Utility functions and helpers
- `/migrations` - Database migration scripts
- `/tests` - Test cases and fixtures


## Technologies


* **Backend:** Python 3.11.9, Flask 3, SQLAlchemy
* **Frontend:** HTML / Jinja2, Bootstrap 4
* **Testing:** Pytest, Coverage




## Contact

Anne O'Leary — 126710105+OLeary981@users.noreply.github.com

Project Link: [Automated-Prompting-LLM](https://github.com/OLeary981/Automated-Prompting-LLM)


## Acknowledgements

* [Dr Austen Rainer QUB](https://pure.qub.ac.uk/en/persons/austen-rainer)
* [Awesome README Templates](https://github.com/matiassingers/awesome-readme)
* [Shields.io Badges](https://shields.io/)
* [Flaticon - 404](https://www.flaticon.com/free-icons/error-404)
* [Flaticon - development](https://www.flaticon.com/free-animated-icons/development)
