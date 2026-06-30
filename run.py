# This is the file you run to start the website.
# In the terminal:  python run.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True shows helpful error pages and auto-reloads when you save.
    app.run(debug=True)
