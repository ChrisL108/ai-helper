import tkinter as tk
from tkinter import ttk
import sqlite3
import json
from datetime import datetime

class DBViewer(tk.Tk):
    def __init__(self, db_path):
        super().__init__()
        
        self.db_path = db_path
        self.title(f"SQLite Viewer - {db_path}")
        self.geometry("800x600")
        
        # Create main container
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add refresh button
        self.refresh_btn = ttk.Button(
            self.main_frame, 
            text="Refresh Data",
            command=self.refresh_data
        )
        self.refresh_btn.pack(pady=(0, 10))
        
        # Create treeview
        self.tree = ttk.Treeview(self.main_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            self.main_frame, 
            orient="vertical", 
            command=self.tree.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Add detail view
        self.detail_text = tk.Text(self.main_frame, height=10)
        self.detail_text.pack(fill=tk.X, pady=(10, 0))
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.show_details)
        
        self.refresh_data()
        
        # Auto-refresh every 5 seconds
        self.auto_refresh()
    
    def auto_refresh(self):
        self.refresh_data()
        self.after(5000, self.auto_refresh)  # Schedule next refresh
    
    def refresh_data(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get column names
        cursor.execute("PRAGMA table_info(memories)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Configure columns in treeview
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)  # Adjust width as needed
        
        # Get data
        cursor.execute("SELECT * FROM memories ORDER BY id DESC")
        rows = cursor.fetchall()
        
        # Insert data
        for row in rows:
            values = []
            for col in columns:
                val = row[col]
                # Format certain columns for better display
                if col == 'embedding':
                    val = f"<binary {len(val)} bytes>"
                elif col == 'metadata':
                    try:
                        val = json.loads(val)
                        val = f"<metadata: {len(val)} keys>"
                    except:
                        val = "<invalid metadata>"
                values.append(val)
            
            self.tree.insert("", "end", values=values)
        
        conn.close()
    
    def show_details(self, event):
        # Clear previous details
        self.detail_text.delete(1.0, tk.END)
        
        # Get selected item
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get all values
        values = self.tree.item(selection[0])['values']
        
        # Connect to database to get raw data
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM memories WHERE id=?", (values[0],))
        row = cursor.fetchone()
        
        if row:
            # Format and display details
            details = []
            for key in row.keys():
                value = row[key]
                if key == 'metadata':
                    try:
                        value = json.dumps(json.loads(value), indent=2)
                    except:
                        value = str(value)
                elif key == 'embedding':
                    value = f"<binary data, {len(value)} bytes>"
                
                details.append(f"{key}:\n{value}\n")
            
            self.detail_text.insert(1.0, "\n".join(details))
        
        conn.close()

if __name__ == "__main__":
    viewer = DBViewer("semantic_memory.db")
    viewer.mainloop()