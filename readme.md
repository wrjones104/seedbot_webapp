# SeedBot Web App

A Django-based web application that serves as a companion to the SeedBot Discord bot. It provides a user-friendly interface for viewing, creating, and managing presets for the Final Fantasy VI: Worlds Collide randomizer.

**Live Site:** [https://seedbot.net](https://seedbot.net)

## Key Features

* **Preset Browser:** View all public presets in a modern, responsive card layout with search and filtering capabilities.
* **Discord Authentication:** Secure user login via Discord OAuth2, managed by `django-allauth`.
* **Preset Management:** Authenticated users can create, read, update, and delete their own presets through a clean web interface.
* **Personal Dashboard:** A "My Presets" page shows a user all the presets they have created.
* **Dynamic Flag Processing:** The application processes "arguments" from presets to dynamically modify game flags on the fly, ensuring consistency with the Discord bot's logic.
* **Live Flag Validation:** Preset flags are validated against the external randomizer API upon submission to ensure they are valid, with a user-friendly loading indicator.

## Technology Stack

* **Backend:** Python, Django, Gunicorn
* **Frontend:** Pico.css, Select2.js, jQuery
* **Database:** SQLite (configured for a multi-database setup)
* **Authentication:** `django-allauth`

## Local Development Setup

To run this project on your local machine, follow these steps.

**1. Clone the Repository:**
```bash
git clone [https://github.com/wrjones104/seedbot_webapp.git](https://github.com/wrjones104/seedbot_webapp.git)
cd seedbot_webapp
2. Create Environment and Install Dependencies:

Bash

# Create and activate a Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use `\.venv\Scripts\activate`

# Install required packages
pip install -r requirements.txt
```

**3. Set Up Databases:**
This project uses two SQLite databases:

* db.sqlite3: Handles Django's internal data (users, sessions, redirects).
* seeDBot.sqlite: Handles the main application data (presets, users with admin flags).

Place your existing seeDBot.sqlite file in the appropriate directory as referenced by your settings.py file (../seedbot2000/db/seeDBot.sqlite).

Then, run migrations to create the tables for the Django database:

Bash

```
python manage.py migrate
```

**4. Configure Environment Variables:**
The application requires a .env file to store secret keys. This file should be placed in your seedbot2000 directory. Create a file named .env and add the following variables:

```
SECRET_KEY='your-django-secret-key'
new_api_key='your-ff6wc-api-key'
# Add any other required secrets
```

**5. Create a Superuser:**
This will create an administrator account for the Django admin panel.

```
python manage.py createsuperuser
```

**6. Run the Development Server:**

```
python manage.py runserver
```

The application should now be running on http://127.0.0.1:8000.

## Production Deployment
The live version of this application is deployed on a GCP VM (Debian/Linux). It uses Apache as a reverse proxy to a Gunicorn application server, which is managed as a background service by systemd.