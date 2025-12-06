import threading
import random
import time
import tkinter as tk
from queue import Queue, Empty

# ----------------------------
# Grid & Robot Configuration
# ----------------------------
ROWS = 12
COLS = 16
CELL_SIZE = 40
INITIAL_ROBOTS = 5
MAX_MOVES = 20

# Grid: 0 = empty, >0 = robot id
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]

# Robot colors
robot_colors = [
    "red","blue","green","orange","purple",
    "cyan","magenta","yellow","pink","brown",
    "gray","lime"
]

# ----------------------------
# Tkinter Setup & UI Queue
# ----------------------------
root = tk.Tk()
root.title("Robot Synchronization Simulation — Final Version")

CANVAS_VIEW_W = min(800, COLS * CELL_SIZE)
CANVAS_VIEW_H = min(600, ROWS * CELL_SIZE)

canvas_frame = tk.Frame(root)
canvas_frame.grid(row=0, column=0, columnspan=6)

h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)

canvas = tk.Canvas(
    canvas_frame,
    width=CANVAS_VIEW_W,
    height=CANVAS_VIEW_H,
    xscrollcommand=h_scroll.set,
    yscrollcommand=v_scroll.set
)

h_scroll.config(command=canvas.xview)
v_scroll.config(command=canvas.yview)
h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

canvas.config(scrollregion=(0,0, COLS * CELL_SIZE, ROWS * CELL_SIZE))

ui_queue = Queue()

def schedule_update_cell(x, y, robot_id):
    ui_queue.put(("cell", x, y, robot_id))

def schedule_update_stats():
    ui_queue.put(("stats",))

def process_ui_queue():
    try:
        while True:
            item = ui_queue.get_nowait()
            kind = item[0]

            if kind == "cell":
                _, x, y, rid = item
                _update_cell_display(x, y, rid)

            elif kind == "stats":
                _update_stats_text()
    except Empty:
        pass

    root.after(40, process_ui_queue)

# ----------------------------
# Draw Grid Cells
# ----------------------------
rects = [[None for _ in range(COLS)] for _ in range(ROWS)]
texts = [[None for _ in range(COLS)] for _ in range(ROWS)]

for i in range(ROWS):
    for j in range(COLS):
        rects[i][j] = canvas.create_rectangle(
            j * CELL_SIZE, i * CELL_SIZE,
            (j + 1) * CELL_SIZE, (i + 1) * CELL_SIZE,
            fill="white", outline="black"
        )

def _update_cell_display(x, y, rid):
    """Update a cell color and label."""
    if rid == 0:
        canvas.itemconfig(rects[x][y], fill="white")
        if texts[x][y]:
            canvas.delete(texts[x][y])
            texts[x][y] = None
    else:
        color = robot_colors[(rid - 1) % len(robot_colors)]
        canvas.itemconfig(rects[x][y], fill=color)

        if texts[x][y]:
            canvas.delete(texts[x][y])

        texts[x][y] = canvas.create_text(
            y * CELL_SIZE + CELL_SIZE // 2,
            x * CELL_SIZE + CELL_SIZE // 2,
            text=str(rid), fill="white",
            font=("Arial", 12, "bold")
        )

# ----------------------------
# Robot Class
# ----------------------------
class Robot(threading.Thread):
    """A robot that moves randomly on the grid."""

    def __init__(self, rid, start_x, start_y):
        super().__init__(daemon=True)
        self.rid = rid
        self.x = start_x
        self.y = start_y
        self.max_moves = random.randint(10, MAX_MOVES)
        self.moves_done = 0
        self.running = True

    def run(self):
        while self.running and self.moves_done < self.max_moves:
            time.sleep(random.uniform(0.3, 0.8))

            dx, dy = random.choice(
                [(-1,0),(1,0),(0,-1),(0,1),
                 (-1,-1),(-1,1),(1,-1),(1,1)]
            )

            nx = self.x + dx
            ny = self.y + dy

            # Check boundaries
            if not (0 <= nx < ROWS and 0 <= ny < COLS):
                continue

            # Attempt move atomically
            with movement_lock:
                if grid[nx][ny] == 0:  # empty
                    # Clear old cell
                    grid[self.x][self.y] = 0
schedule_update_cell(self.x, self.y, 0)

                    # Move robot
                    self.x, self.y = nx, ny
                    grid[nx][ny] = self.rid

                    schedule_update_cell(nx, ny, self.rid)
                    schedule_update_stats()

            self.moves_done += 1

        # Robot finishes and disappears
        with movement_lock:
            if grid[self.x][self.y] == self.rid:
                grid[self.x][self.y] = 0
                schedule_update_cell(self.x, self.y, 0)

# ----------------------------
# Movement Lock
# ----------------------------
movement_lock = threading.Lock()

# ----------------------------
# Stats Panel
# ----------------------------
stats_label = tk.Label(root, text="Robots Running: 0", font=("Arial", 14))
stats_label.grid(row=1, column=0, pady=10)

def _update_stats_text():
    active = sum(1 for r in robots if r.is_alive())
    stats_label.config(text=f"Robots Running: {active}")

# ----------------------------
# Control Buttons
# ----------------------------
def start_simulation():
    """Start the simulation with random robot positions."""
    global robots
    robots = []

    # Clear grid
    for i in range(ROWS):
        for j in range(COLS):
            grid[i][j] = 0
            schedule_update_cell(i, j, 0)

    # Place robots
    used = set()

    for rid in range(1, INITIAL_ROBOTS + 1):
        while True:
            x = random.randint(0, ROWS - 1)
            y = random.randint(0, COLS - 1)

            if (x, y) not in used:
                used.add((x,y))
                grid[x][y] = rid
                schedule_update_cell(x, y, rid)

                r = Robot(rid, x, y)
                robots.append(r)
                r.start()
                break

    schedule_update_stats()

def reset_simulation():
    """Stop all robots and clear grid."""
    for r in robots:
        r.running = False

    for i in range(ROWS):
        for j in range(COLS):
            grid[i][j] = 0
            schedule_update_cell(i, j, 0)

    schedule_update_stats()

start_btn = tk.Button(root, text="Start", width=20, command=start_simulation)
start_btn.grid(row=2, column=0, pady=5)

reset_btn = tk.Button(root, text="Reset", width=20, command=reset_simulation)
reset_btn.grid(row=3, column=0, pady=5)

# ----------------------------
# Run UI Processor & Mainloop
# ----------------------------
robots = []
process_ui_queue()
root.mainloop()
