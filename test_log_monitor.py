#!/usr/bin/env python3
"""监控日志文件变化"""
import os
import time

# 日志文件路径（从您的调试信息中获取）
log_path = r"D:\TapTap\PC Games\172664\UE_game\Torchlight\Saved\Logs\UE_game.log"

print(f"监控日志文件: {log_path}")
print("=" * 60)

if not os.path.exists(log_path):
    print(f"日志文件不存在!")
else:
    last_size = os.path.getsize(log_path)
    print(f"日志文件当前大小: {last_size} 字节")
    print(f"请重新登录游戏，观察日志文件变化...")
    print("=" * 60)

    try:
        for i in range(30):  # 监控30秒
            time.sleep(1)
            current_size = os.path.getsize(log_path)
            if current_size != last_size:
                print(f"[{i+1}s] 日志文件大小变化: {last_size} -> {current_size} (增加 {current_size - last_size} 字节)")
                last_size = current_size

                # 读取新增的内容
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_size - (current_size - last_size))
                    new_lines = f.readlines()
                    print(f"新增 {len(new_lines)} 行:")
                    for line in new_lines[-5:]:  # 只显示最后5行
                        if 'LoadUILogicProgress' in line:
                            print(f"  >>> {line.strip()}")
                        elif len(new_lines) <= 5:
                            print(f"      {line.strip()}")
            else:
                print(f"[{i+1}s] 日志文件大小未变化: {last_size}")

        print("=" * 60)
        print("监控结束")
    except KeyboardInterrupt:
        print("\n监控被用户中断")
