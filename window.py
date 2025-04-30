import tkinter as tk
from tkinter import ttk

def open_window(title):
    # Create a new top-level window
    new_win = tk.Toplevel(root)
    new_win.title(title)
    new_win.geometry("300x200")  # You can adjust default size
    label = ttk.Label(new_win, text=f"This is the {title} window.")
    label.pack(padx=20, pady=20)

# Main window
root = tk.Tk()
root.title("Main Window")
root.geometry("400x200")

# Button frame
frame = ttk.Frame(root, padding=20)
frame.pack(expand=True)

# Create buttons and bind them to open new windows
buttons = {
    "Home": lambda: open_window("Home"),
    "New": lambda: open_window("New"),
    "Add": lambda: open_window("Add"),
    "Delete": lambda: open_window("Delete"),
}

for i, (text, cmd) in enumerate(buttons.items()):
    btn = ttk.Button(frame, text=text, command=cmd)
    btn.grid(row=0, column=i, padx=10, pady=10)

# Start the main loop
root.mainloop()
