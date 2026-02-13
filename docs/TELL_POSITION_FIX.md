# 修复文件读取位置追踪错误

## 错误信息

```
OSError: telling position disabled by next() call
```

## 问题原因

在迭代文件时，Python 不允许调用 `f.tell()` 来获取文件位置。当使用 `for line in f:` 迭代器时，文件句柄处于一种特殊状态，此时调用 `tell()` 会抛出错误。

### 错误的代码

```python
with open(file, 'r') as f:
    for line in f:
        # 处理行...
        self._last_position = f.tell()  # ❌ 错误！
```

## 解决方案

通过计算行的字节长度来手动更新位置，而不是调用 `f.tell()`。

### 正确的代码

```python
with open(file, 'r', encoding='utf-8') as f:
    for line in f:
        # 更新读取位置（通过行长度）
        self._last_position += len(line.encode('utf-8'))
        # 处理行...
```

## 原理

### 文件编码和字节长度

- 文件是以字节形式存储的，不是字符形式
- `len(line)` 返回的是字符数，不是字节数
- 不同编码下，一个字符可能占用多个字节
- UTF-8 编码中：
  - ASCII 字符（0-127）：1字节
  - 中文字符：3字节
  - Emoji：4字节

### 计算位置

```python
# 字符数（不正确）
len(line)  # ❌

# 字节数（正确）
len(line.encode('utf-8'))  # ✅
```

## 完整实现

```python
def parse_new_events(self) -> tuple[List[BuyEvent], List[RefreshEvent]]:
    """解析新的日志事件"""
    if not os.path.exists(self.game_log_path):
        logger.warning(f"游戏日志文件不存在: {self.game_log_path}")
        return [], []

    try:
        with open(self.game_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 检查文件是否被重置
            current_size = os.path.getsize(self.game_log_path)
            if current_size < self._last_size:
                logger.info("日志文件已被重置，从头开始读取")
                self._last_position = 0
                self._inventory_manager.reset_backpack_initialized()
            self._last_size = current_size

            # 首次启动，跳到文件末尾
            if not self._initialized:
                logger.info("首次启动，跳到日志文件末尾，只监控新日志")
                self._last_position = current_size
                self._initialized = True
                return [], []

            # 跳转到上次读取位置
            f.seek(self._last_position)

            buy_events = []
            refresh_events = []
            
            for line in f:
                # ✅ 更新读取位置（通过行长度）
                self._last_position += len(line.encode('utf-8'))
                
                parsed = self._parse_log_line(line)
                if not parsed:
                    continue

                # 处理日志行
                try:
                    self._process_log_line(parsed, buy_events, refresh_events)
                except Exception as e:
                    logger.error(f"处理日志行时发生错误: {e}", exc_info=True)

            # 文件结束时，如果有未完成的事件，强制结束
            if self._current_event:
                logger.warning(f"文件结束，强制关闭未完成事件: {self._current_event.event_type}")
                self._finalize_event(buy_events, refresh_events)

            return buy_events, refresh_events

    except Exception as e:
        logger.error(f"解析日志失败: {e}", exc_info=True)
        return [], []
```

## 为什么不能使用 tell()？

### Python 文件迭代器的工作原理

当使用 `for line in f:` 时：
1. Python 会创建一个文件迭代器
2. 迭代器内部维护读取位置
3. 迭代过程中调用 `tell()` 可能导致：
   - 迭代器状态不一致
   - 返回错误的位置
   - 抛出 `OSError`

### 官方文档说明

根据 Python 官方文档：

> "Using tell() with the text mode file object is not recommended because it may not be accurate due to the buffering used by the operating system or Python's own buffering."

在文本模式下使用 `tell()` 是不推荐的，因为由于操作系统或 Python 的缓冲，它可能不准确。

## 其他注意事项

### 1. 文件编码

必须使用正确的文件编码：

```python
with open(file, 'r', encoding='utf-8', errors='ignore') as f:
    # ...
```

- `encoding='utf-8'`: 使用 UTF-8 编码
- `errors='ignore'`: 忽略编码错误（防止因特殊字符导致程序崩溃）

### 2. 换行符

不同操作系统使用不同的换行符：
- Windows: `\r\n` (CRLF) - 2 字节
- Linux/Mac: `\n` (LF) - 1 字节
- 旧 Mac: `\r` (CR) - 1 字节

使用 `len(line.encode('utf-8'))` 会自动处理这些差异。

### 3. 文件重置检测

检测文件是否被清空或重置：

```python
current_size = os.path.getsize(self.game_log_path)
if current_size < self._last_size:
    # 文件被重置，从头开始读取
    self._last_position = 0
```

## 测试

验证修复是否正确工作：

```bash
python main.py
```

预期结果：
- ✅ 不再出现 `telling position disabled by next() call` 错误
- ✅ 日志能够正常解析
- ✅ 文件位置正确追踪
- ✅ 不会重复解析同一行

## 总结

### 修复前

```python
for line in f:
    parsed = self._parse_log_line(line)
    if not parsed:
        self._last_position = f.tell()  # ❌ 错误
        continue
    # ...
self._last_position = f.tell()  # ❌ 错误
```

### 修复后

```python
for line in f:
    self._last_position += len(line.encode('utf-8'))  # ✅ 正确
    parsed = self._parse_log_line(line)
    if not parsed:
        continue
    # ...
# 不需要在循环结束前更新位置
```

### 关键点

1. ❌ 不要在文件迭代器中调用 `f.tell()`
2. ✅ 使用 `len(line.encode('utf-8'))` 计算字节数
3. ✅ 每次处理一行后更新位置
4. ✅ 正确处理文件编码
5. ✅ 检测文件重置
