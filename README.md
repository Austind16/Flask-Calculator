# CalcU

CalcU is a personal/student Flask project: a web-based scientific calculator
with keyboard input and saved calculation history.

## Features

- Basic arithmetic, percentages, powers, and parentheses
- `sin`, `cos`, `tan`, square root, logarithm, exponential, and square
- Degree-based trigonometric calculations
- Keyboard input and backspace support
- Session-based calculation history with a clear-history option
- Responsive calculator interface

## Tech Stack

- Python
- Flask
- SQLAlchemy and Flask-Migrate
- SQLite locally and PostgreSQL for deployment
- HTML, CSS, and JavaScript

## Project Structure

```text
Calc/
├── app.py
├── static/
└── templates/
migrations/
tests/
requirements.txt
Procfile
```

## Setup

1. Clone the repository:

   ```powershell
   git clone https://github.com/Austind16/Flask_Projects.git
   cd Flask_Projects
   ```

2. Create and activate a virtual environment:

   ```powershell
   py -3.14 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install the requirements:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `SECRET_KEY`. Leave `DATABASE_URL`
   empty for local SQLite.

5. Apply database migrations:

   ```powershell
   flask --app Calc.app db upgrade
   ```

6. Start Flask:

   ```powershell
   flask --app Calc.app run
   ```

7. Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

## Screenshots

![Calculator](screenshots/Screenshot_1.png)

![Calculator with history](screenshots/Screenshot_2.png)

![Calculator result](screenshots/Screenshot_3.jpg)

## Live Demo

[CalcU on Render](https://flask-projects-2e73.onrender.com)

## Testing

The project uses Python's `unittest` test suite.

```powershell
python -m unittest discover -s tests -v
```

## What I Learned

- Connecting a Flask frontend to backend calculation logic
- Handling user input with JavaScript
- Working with SQLAlchemy and database migrations
- Building a responsive web interface

## Future Improvements

- Add calculator memory functions
- Add selectable angle modes
- Improve calculation history management

## Author

Austin Dsouza
[LinkedIn](https://www.linkedin.com/in/austinn-dsouza)
