import threading
import random
import time
import tkinter as tk
from queue import Queue, Empty
import heapq
import math

# ----------------------------
# إعدادات الخريطة والروبوتات
# ----------------------------
ROWS = 12
COLS = 16
CELL_SIZE = 40
NUM_ROBOTS = 5
MAX_ROBOTS = 12

# الشبكة وحالة الخلايا (0 = فارغ, >0 = robot id)
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
# (لا نستخدم قفل خلية فردي هنا لأن الحركة تمر عبر MovementManager)
robot_colors = ["red","blue","green","orange","purple","cyan","magenta","yellow","pink","brown","gray","lime"]

# ----------------------------
# واجهة المستخدم وآلية التحديث من الخيوط
# ----------------------------
root = tk.Tk()
root.title("Ultimate Smart Robot Simulation — Final")

# نجعل الـ canvas أصغر من الشبكة لتفعيل ال-scroll (مربع عرضي)
CANVAS_VIEW_W = min(800, COLS * CELL_SIZE)
CANVAS_VIEW_H = min(600, ROWS * CELL_SIZE)

canvas_frame = tk.Frame(root)
canvas_frame.grid(row=0, column=0, columnspan=6)

h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
canvas = tk.Canvas(canvas_frame, width=CANVAS_VIEW_W, height=CANVAS_VIEW_H,
                   xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
h_scroll.config(command=canvas.xview)
v_scroll.config(command=canvas.yview)
h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

# set scrollregion to full grid
canvas.config(scrollregion=(0,0,COLS*CELL_SIZE, ROWS*CELL_SIZE))

# طابور لتحديث واجهة المستخدم من الخيوط بأمان
ui_queue = Queue()

def schedule_update_cell(x, y, robot_id):
    ui_queue.put(("cell", x, y, robot_id))

def schedule_update_stats():
    ui_queue.put(("stats",))

def schedule_draw_path(rid, path):
    ui_queue.put(("path", rid, list(path)))

def schedule_clear_path(rid):
    ui_queue.put(("clear_path", rid))

def schedule_follow(rid):
    ui_queue.put(("follow", rid))

def process_ui_queue():
    try:
        while True:
            item = ui_queue.get_nowait()
            kind = item[0]
            if kind == "cell":
                _, x, y, robot_id = item
                _do_update_cell(x, y, robot_id)
            elif kind == "stats":
                _do_update_stats()
            elif kind == "path":
                _, rid, path = item
                _do_draw_path(rid, path)
            elif kind == "clear_path":
                _, rid = item
                _do_clear_path(rid)
            elif kind == "follow":
                _, rid = item
                _do_follow_center(rid)
    except Empty:
        pass
    root.after(40, process_ui_queue)

# ----------------------------
# رسم الشبكة (مخزن للأشكال)
# ----------------------------
rects = [[None for _ in range(COLS)] for _ in range(ROWS)]
texts = [[None for _ in range(COLS)] for _ in range(ROWS)]
for i in range(ROWS):
    for j in range(COLS):
        rects[i][j] = canvas.create_rectangle(
            j*CELL_SIZE, i*CELL_SIZE, (j+1)*CELL_SIZE, (i+1)*CELL_SIZE,
            fill="white", outline="black"
        )

# مسارات مرسومة لكل روبوت (IDs of canvas items)
path_items = {}  # rid -> [item,...]
follow_rect = None

def _do_update_cell(x, y, robot_id):
    global texts
    if robot_id == 0:
        canvas.itemconfig(rects[x][y], fill="white")
        if texts[x][y]:
            canvas.delete(texts[x][y])
            texts[x][y] = None
    else:
        color = robot_colors[(robot_id-1) % len(robot_colors)]
        canvas.itemconfig(rects[x][y], fill=color)
        if texts[x][y]:
            canvas.delete(texts[x][y])
        texts[x][y] = canvas.create_text(
            y*CELL_SIZE + CELL_SIZE//2,
            x*CELL_SIZE + CELL_SIZE//2,
            text=str(robot_id),
            fill="white",
            font=("Arial", 12, "bold")
        )
