import webview
import psycopg
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from multiprocessing import Process
from queue import Queue

class BookmarksManager:
    def __init__(self, db_config):
        self.db_config = db_config
        self.queue = Queue()
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def worker(self):
        """Worker thread to handle database operations."""
        # conn = psycopg.connect(**self.db_config)
        cursor = conn.cursor()
        while True:
            task = self.queue.get()
            if task is None:
                break
            action, data, callback = task
            try:
                if action == "add":
                    cursor.execute(
                        "INSERT INTO Bookmarks (url, user_id, title) VALUES (%s, %s, %s)",
                        (data['url'], data['user_id'], data.get('title', 'Untitled'))
                    )
                    conn.commit()
                elif action == "delete":
                    cursor.execute("DELETE FROM Bookmarks WHERE bookmark_id = %s", (data['bookmark_id'],))
                    conn.commit()
                elif action == "fetch":
                    cursor.execute("SELECT bookmark_id, title, url FROM Bookmarks WHERE user_id = %s", (data['user_id'],))
                    bookmarks = cursor.fetchall()
                    if callback:
                        callback(bookmarks)
            except Exception as e:
                print(f"Error in {action}: {e}")
            finally:
                self.queue.task_done()
        cursor.close()
        conn.close()

    def add_bookmark(self, url, user_id, title=None, callback=None):
        self.queue.put(("add", {"url": url, "user_id": user_id, "title": title}, callback))

    def delete_bookmark(self, bookmark_id, callback=None):
        self.queue.put(("delete", {"bookmark_id": bookmark_id}, callback))

    def fetch_bookmarks(self, user_id, callback):
        self.queue.put(("fetch", {"user_id": user_id}, callback))

    def stop(self):
        self.queue.put(None)


def bmarks(db_config):
    user_id = 1  # For demonstration; replace with actual user logic
    manager = BookmarksManager(db_config)

    def add_bookmark():
        url = simpledialog.askstring("Add Bookmark", "Enter the URL:")
        title = simpledialog.askstring("Add Bookmark", "Enter the title (optional):")
        if url:
            manager.add_bookmark(url, user_id, title)
            refresh_bookmarks()

    def delete_bookmark(bookmark_id):
        if messagebox.askyesno("Delete Bookmark", "Are you sure you want to delete this bookmark?"):
            manager.delete_bookmark(bookmark_id)
            refresh_bookmarks()

    def refresh_bookmarks():
        def update_list(bookmarks):
            listbox.delete(0, tk.END)
            for bookmark in bookmarks:
                listbox.insert(tk.END, f"{bookmark[1]} ({bookmark[2]})")
                listbox.bookmark_ids[listbox.size() - 1] = bookmark[0]  # Map index to bookmark ID

        listbox.bookmark_ids = {}
        manager.fetch_bookmarks(user_id, update_list)

    root = tk.Tk()
    root.title("Bookmarks Manager")
    root.geometry("400x400")

    button_add = tk.Button(root, text="Add Bookmark", command=add_bookmark)
    button_add.pack(pady=5)

    listbox = tk.Listbox(root)
    listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def on_delete():
        selected = listbox.curselection()
        if selected:
            bookmark_id = listbox.bookmark_ids[selected[0]]
            delete_bookmark(bookmark_id)

    button_delete = tk.Button(root, text="Delete Selected Bookmark", command=on_delete)
    button_delete.pack(pady=5)

    refresh_bookmarks()
    root.protocol("WM_DELETE_WINDOW", lambda: (manager.stop(), root.destroy()))
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
        self.db_config = {
            'dbname': 'history',
            'user': 'postgres',
            'password': 'pasword',
            'host': 'localhost',
            'port': '5432'
        }

        self.initialize_db()

    def initialize_db(self):
        """Create the history table if it doesn't exist."""
        self.conn = psycopg.connect(**self.db_config)
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


    def move_to_url(self, url):
        print(url)
        self.window.load_url(url)
        
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
        p1 = Process(target=bmarks, args=(self.db_config,), daemon=True)
        p1.start()
        webview.start(debug=False)

    def __del__(self):
        """Close database connection on cleanup."""
        if self.conn:
            self.cursor.close()
            self.conn.close()

if __name__ == '__main__':
    initial_url = 'https://zzzhanka.github.io/site2/'
    browser = Browser(initial_url)
    browser.start()

