"""测试窗口是否正常显示"""
import tkinter as tk
from tkinter import messagebox

root = tk.Tk()
root.title("测试窗口")
root.geometry("300x200")

label = tk.Label(root, text="如果你能看到这个窗口，说明 tkinter 工作正常", font=("Arial", 12))
label.pack(pady=20)

def test_messagebox():
    result = messagebox.askokcancel(
        "测试对话框",
        "这是一个测试对话框。\n\n点击【确定】继续，点击【取消】退出。"
    )
    if result:
        print("用户点击了确定")
    else:
        print("用户点击了取消")
        root.destroy()

button = tk.Button(root, text="测试对话框", command=test_messagebox)
button.pack(pady=10)

root.mainloop()
