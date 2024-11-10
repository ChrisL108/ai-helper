# src/gui/ui_handler.py

import tkinter as tk
from tkinter import ttk
import random

class AssistantUI:
    def __init__(self, window_title="Jarviz"):
        self.r = tk.Tk()
        self.r.title(window_title)
        self.r.geometry("450x550")
        self.r.configure(bg='#1e1e1e')  # Dark background
        self.stop_callback = None
        self.exit_callback = None
        # States and their colors
        self.states = {
            'idle': '#2c3e50',       # Dark blue-gray
            'listening': '#2ecc71',  # Green
            'processing': '#e74c3c', # Red
            'speaking': '#3498db'    # Blue
        }
        
        self.current_state = 'idle'
        self.is_running = True
        
        self._setup_ui()
        # self._animate_pulse()
        self._animate_lightning()  # Start the lightning animation
        
    def _setup_ui(self):
        """Set up the UI elements"""
        # Canvas for the animations
        self.canvas = tk.Canvas(
            self.r, 
            width=300, 
            height=300, 
            background='#1e1e1e'
        )
        self.canvas.pack(pady=20)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            self.r,
            textvariable=self.status_var,
            font=('Arial', 14),
            background='#1e1e1e',
            foreground='white'
        )
        self.status_label.pack(pady=10)
        
        # Transcript display
        self.transcript = tk.Text(
            self.r,
            height=5,
            width=40,
            font=('Arial', 10),
            bg='#2d2d2d',
            fg='white',
            wrap=tk.WORD
        )
        self.transcript.pack(pady=10, padx=20)
        
        # Frame for buttons
        button_frame = tk.Frame(self.r, bg='#1e1e1e')
        button_frame.pack(pady=(0, 10))

        # Stop button
        self.stop_button_canvas = tk.Canvas(
            button_frame,
            width=50,
            height=50,
            bg='#1e1e1e',
            highlightthickness=0
        )
        self.stop_button_canvas.pack(side=tk.LEFT, padx=(0, 10))

        # Draw circular red button
        self.stop_button_canvas.create_oval(
            5, 5, 45, 45,
            fill='red',
            outline='red'
        )

        # Draw square in the middle
        self.stop_button_canvas.create_rectangle(
            20, 20, 30, 30,
            fill='white',
            outline='white'
        )

        # Bind click event to the canvas
        self.stop_button_canvas.bind("<Button-1>", lambda event: self.on_stop_button_pressed())

        # Exit button
        self.exit_button = ttk.Button(
            button_frame,
            text="Exit",
            command=self.on_exit_button_pressed
        )
        self.exit_button.pack(side=tk.LEFT)

        # Configure style for dark theme
        style = ttk.Style()
        style.configure(
            'Custom.TLabel',
            background='#1e1e1e',
            foreground='white'
        )

    # def _animate_pulse(self):
    #     """Animate the pulsing circle using Tkinter's after method"""
    #     if self.is_running:
    #         try:
    #             # Update animation frame
    #             self.animation_frame += 0.1
    #             
    #             # Calculate pulse size using sine wave
    #             self.pulse_size = math.sin(self.animation_frame) * 0.2 + 0.8  # 0.6 to 1.0
    #             
    #             # Get current state color
    #             color = self.states[self.current_state]
    #             
    #             # Clear previous circle
    #             self.canvas.delete("pulse")
    #             
    #             # Draw new circle
    #             center_x = 150
    #             center_y = 150
    #             radius = 50 * self.pulse_size
    #             
    #             # Draw main circle
    #             self.canvas.create_oval(
    #                 center_x - radius,
    #                 center_y - radius,
    #                 center_x + radius,
    #                 center_y + radius,
    #                 fill=color,
    #                 tags="pulse"
    #             )
    #             
    #             # Schedule the next animation frame
    #             self.r.after(50, self._animate_pulse)  # 50ms = 20 fps
    #             
    #         except tk.TclError:
    #             print("Tkinter error in _animate_pulse")
    #             # Window was closed
    #             self.is_running = False

    def _animate_lightning(self):
        """Animate a vertical line with a lightning effect"""
        if self.is_running:
            try:
                # Clear previous line
                self.canvas.delete("lightning")
                
                # Draw "lightning" line
                x = 150  # Center of the canvas
                y_start = 0
                y_end = 300
                segments = 20  # Number of segments in the line
                segment_length = (y_end - y_start) / segments
                
                points = [(x, y_start)]
                
                # Determine offset range based on current state
                if self.current_state in ['listening']:
                    offset_range = (-2, 2)  # Smaller movement
                else:
                    offset_range = (-30, 30)  # Larger movement
                
                for i in range(1, segments):
                    # Randomly offset the x position to create a jagged effect
                    offset = random.randint(*offset_range)
                    points.append((x + offset, y_start + i * segment_length))
                
                points.append((x, y_end))
                
                # Draw the line segments
                for i in range(len(points) - 1):
                    self.canvas.create_line(
                        points[i][0], points[i][1],
                        points[i+1][0], points[i+1][1],
                        fill="cyan", width=2, tags="lightning"
                    )
                
                # Schedule the next frame
                self.r.after(100, self._animate_lightning)  # 100ms delay for animation
                
            except tk.TclError:
                print("Tkinter error in _animate_lightning")
                # Window was closed
                self.is_running = False

    def set_state(self, state):
        """Set the current state and update UI"""
        if state in self.states:
            self.current_state = state
            # print(f"State changed to: {self.current_state}")  # Debugging print
            status_texts = {
                'idle': 'Ready',
                'listening': 'Listening...',
                'processing': 'Processing...',
                'speaking': 'Speaking...'
            }
            self.status_var.set(status_texts[state])
            
    def update_transcript(self, text, is_user=True):
        """Update the transcript display"""
        self.transcript.insert(tk.END, f"{'You' if is_user else 'Jarvis'}: {text}\n")
        self.transcript.see(tk.END)  # Scroll to bottom
        
    def clear_transcript(self):
        """Clear the transcript display"""
        self.transcript.delete(1.0, tk.END)
        
    def on_stop_button_pressed(self):
        """Handle the stop button press."""
        if self.stop_callback:
            self.stop_callback()
        
    def on_exit_button_pressed(self):
        """Handle the exit button press."""
        if self.exit_callback:
            self.exit_callback()
        self.cleanup()

    def run(self):
        """Start the UI"""
        self.r.mainloop()
        
    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        try:
            self.r.quit()
        except:
            pass