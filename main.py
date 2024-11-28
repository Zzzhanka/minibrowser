import webview
import psycopg
import tkinter as tk
from tkinter import messagebox, simpledialog
from multiprocessing import Process

def bmarks_add(self, url):
    print(1)
    self.cursor.execute("INSERT INTO Bookmarks (url, user_id) VALUES (%s, %s)", (url, 1))
    self.conn.commit()

def bmarks_del():
    print(2)

def bmarks():
    root = tk.Tk()
    root.geometry("300x300")
    button1=tk.Button(root, text="Add bookmarks", command=bmarks_add)
    button1.pack(pady=5)
    
    button2=tk.Button(root, text="Delete bookmarks", command=bmarks_del)
    button2.pack(pady=5)

    root.mainloop()



class Api:
    def __init__(self, **entries):
        self.__dict__.update(entries)

class Browser:
    def __init__(self, initial_url):
        self.initial_url = initial_url
        self.window = None
        self.history_back = []
        self.history_forward = []

        self.initialize_db()

    def initialize_db(self):
        """Create the history table if it doesn't exist."""
        self.conn = psycopg.connect(
            dbname='history',
            user='postgres',
            password='1234',
            host='localhost',
            port='5432'
        )
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS history (
            history_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            url text NOT NULL,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS BrowserSettings (
            setting_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            homepage_url text DEFAULT 'https://www.default.com',
            default_search_engine VARCHAR(50) DEFAULT 'Google',
            is_dark_mode_enabled BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS Bookmarks (
            bookmark_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(100) NOT NULL,
            url VARCHAR(255) NOT NULL,
            folder_name VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS Extensions (
            extension_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            extension_name VARCHAR(100) NOT NULL,
            developer_name VARCHAR(100),
            version VARCHAR(10),
            is_enabled BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );
        insert into Users (user_id, username, email, password_hash) values 
                            (1, 'Z', 'fghjkf', 'hjksg' ) on conflict do nothing;
        """)
        self.conn.commit()


    def add_to_history(self, url):
        """Add a URL to the history. Ensure no duplicates if revisiting via back/forward navigation."""
        # If navigating back to or forward to a URL, do not duplicate it.
        if self.history_back and self.history_back[-1] == url:
            return  # URL is already the current page in history
        if self.history_forward and self.history_forward[0] == url:
            return  # URL is already being visited from forward stack

        # Otherwise, add the URL and clear forward history
        self.history_back.append(url)
        self.history_forward.clear()
        self.cursor.execute("INSERT INTO history (url, user_id) VALUES (%s, %s)", (url, 1))
        self.conn.commit()

       
    def go_back(self):
        """Navigate back in history."""
        if len(self.history_back) > 1:
            # Remove the current URL from history_back stack
            current_url = self.history_back.pop()
            # Push it to the history_forward stack
            self.history_forward.append(current_url)
            # Load the previous URL from the history_back stack
            previous_url = self.history_back[-1]
            self.window.load_url(previous_url)

    def go_forward(self):
        """Navigate forward in history."""
        if self.history_forward:
            # Pop the next URL from the history_forward stack
            next_url = self.history_forward.pop()
            # Push it to the history_back stack
            self.history_back.append(next_url)
            # Load the next URL
            self.window.load_url(next_url)

    def onWindowLoad(self, window):
        """Add url to history"""
        js_script = """
        // Remove 'target' attribute from all <a> elements with a 'target' attribute
        document.querySelectorAll('a[target]').forEach(link => {
            link.removeAttribute('target');
        });

        // Add the current URL to the history using the pywebview API
        pywebview.api.addToHistory(window.location.href);

        // Listen for keydown events to navigate history
        document.addEventListener('keydown', function(event) {
            if (event.altKey && event.code === 'ArrowLeft') {
                pywebview.api.goBack(); // Navigate backward
            } else if (event.altKey && event.code === 'ArrowRight') {
                pywebview.api.goForward(); // Navigate forward
            }
        });
        """
        window.evaluate_js(js_script)

     

    def start(self):
        """Initialize and start the webview window."""
        self.window = webview.create_window(
            'Browser with History',
            self.initial_url,
            js_api=Api(
                addToHistory=self.add_to_history,
                goBack=self.go_back,
                goForward=self.go_forward
            )
        )

        self.window.events.loaded += self.onWindowLoad

        webview.start(debug=False)

    def __del__(self):
        """Close database connection on cleanup."""
        if self.conn:
            self.cursor.close()
            self.conn.close()

if __name__ == '__main__':
    initial_url = 'https://zzzhanka.github.io/site2/'
    browser = Browser(initial_url)
    p1 = Process(target=bmarks, args=(), daemon=True)  
    p1.start()
    browser.start()


