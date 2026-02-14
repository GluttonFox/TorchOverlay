# TorchOverlay 架构优化方案

## 📊 现状分析

### 1. 代码冗余问题

#### 1.1 价格服务冗余（严重）
**问题**：
- `price_update_service.py` (225行) - 同步版本
- `async_price_update_service.py` (460行) - 异步版本
- 代码重复率 > 80%
- API调用逻辑、时间管理、日志记录完全重复

**影响**：
- 维护成本高：修改一处需要同步修改另一处
- 代码膨胀：两个服务共685行，可优化至300行
- 内存浪费：同时加载两个服务增加内存占用

**优化方案**：
- 合并为统一的 `PriceUpdateService`
- 内部使用 `asyncio` 或线程池实现异步
- 对外提供同步和异步两种接口
- 代码量减少 ~55%

#### 1.2 截图服务冗余（中等）
**问题**：
- `capture_service.py` (247行) - 基础截图
- `capture_memory_optimization_service.py` (342行) - 优化包装
- 后者是对前者的装饰器模式，但实现冗余

**影响**：
- 不必要的抽象层
- 装饰器模式增加调用开销

**优化方案**：
- 将优化功能作为可选参数集成到 `CaptureService`
- 使用策略模式而非装饰器模式
- 代码量减少 ~30%

#### 1.3 兑换相关服务（轻微）
**问题**：
- `exchange_log_service.py` - 兑换日志
- `refresh_log_service.py` - 刷新日志
- `exchange_monitor_service.py` - 兑换监控
- 职责有重叠

**优化方案**：
- 合并为 `ExchangeLogManager`
- 统一日志存储和查询接口

### 2. 架构设计问题

#### 2.1 接口定义不规范
**问题**：
- `services/interfaces/` 定义的是数据类，非真正的接口
- 缺少抽象基类（ABC）
- 依赖注入容器未被使用

**优化方案**：
- 使用 `abc.ABC` 定义真正的接口
- 或者移除interfaces目录，使用协议（Protocol）
- 在 factories.py 中使用 DI 容器

#### 2.2 服务职责不够清晰
**问题**：
- `game_log_parser_service.py` (1269行) - 职责过多
- `exchange_verification_service.py` (513行) - 混合了验证和UI更新

**优化方案**：
- 遵循单一职责原则
- 拆分过大的服务类
- 分离业务逻辑和UI逻辑

### 3. 内存溢出风险

#### 3.1 图像对象未释放
**位置**：
- `capture_service.py` - Image.open() 后未显式close
- `exchange_verification_service.py` - 可能有缓存图像

**影响**：
- 长时间运行导致内存累积
- PIL Image 对象占用大内存（每张截图 ~5-10MB）

**优化方案**：
- 使用 `with` 语句或显式 `img.close()`
- 在 `finally` 块中释放资源
- 定期触发 `gc.collect()`

#### 3.2 缓存无大小限制
**位置**：
- `game_log_parser_service.py:107` - `_update_records_cache` 无过期
- `window_cache_service.py:50` - `_window_cache` 无大小限制
- `ocr_cache_service.py` - OCR结果缓存

**优化方案**：
- 使用 LRU Cache 替代普通字典
- 设置最大缓存大小和TTL
- 定期清理过期缓存

#### 3.3 列表累积未清理
**位置**：
- `exchange_verification_service.py` - 兑换记录列表持续增长
- `game_log_parser_service.py` - 事件列表

**优化方案**：
- 设置最大记录数量
- 超出时自动清理最旧的记录
- 使用循环队列或环形缓冲区

### 4. 性能问题

#### 4.1 重复的文件I/O
**位置**：
- 价格更新服务重复读取 `item.json`
- 配置文件重复读取

**优化方案**：
- 使用内存缓存 + 文件监听（已有热更新）
- 减少文件读取频率

#### 4.2 线程和锁使用不当
**位置**：
- 多个服务创建独立线程
- 缺少统一的线程池管理

**优化方案**：
- 使用 `concurrent.futures.ThreadPoolExecutor`
- 统一线程管理和资源清理

## 🎯 优化实施计划

### Phase 1: 合并冗余服务（优先级：高）

#### 1.1 合并价格服务
**文件操作**：
1. 创建新的 `services/price_update_service_v2.py`
2. 实现统一的价格服务
3. 更新 `factories.py` 使用新服务
4. 删除旧的 `async_price_update_service.py`

**预期收益**：
- 代码量减少 ~400行
- 内存节省 ~5-10MB
- 维护性提升

#### 1.2 重构截图服务
**文件操作**：
1. 在 `capture_service.py` 中集成优化功能
2. 删除 `capture_memory_optimization_service.py`
3. 更新依赖引用

**预期收益**：
- 代码量减少 ~150行
- 调用开销降低 ~10%

### Phase 2: 内存管理优化（优先级：高）

#### 2.1 修复图像资源泄漏
**文件操作**：
1. 审查所有 `Image.open()` 调用
2. 添加显式资源释放
3. 在关键路径添加 `gc.collect()`

**目标文件**：
- `services/capture_service.py`
- `services/exchange_verification_service.py`
- `services/ocr_cache_service.py`

#### 2.2 添加缓存大小限制
**文件操作**：
1. 使用 `functools.lru_cache` 或 `cachetools`
2. 为所有缓存设置TTL和maxsize
3. 实现定期清理机制

**目标文件**：
- `services/game_log_parser_service.py`
- `services/window_cache_service.py`
- `services/ocr_cache_service.py`

### Phase 3: 架构优化（优先级：中）

#### 3.1 重构大服务
**文件操作**：
1. 拆分 `game_log_parser_service.py`：
   - `game_log_parser.py` - 核心解析逻辑
   - `inventory_tracker.py` - 背包状态追踪
   - `event_matcher.py` - 事件匹配逻辑

2. 拆分 `exchange_verification_service.py`：
   - `exchange_matcher.py` - 兑换匹配逻辑
   - `exchange_storage.py` - 兑换记录存储
   - `exchange_validator.py` - 兑换验证逻辑

#### 3.2 规范接口定义
**文件操作**：
1. 重新设计 `services/interfaces/` 结构
2. 使用 `abc.ABC` 定义抽象接口
3. 或移除interfaces目录

### Phase 4: 性能优化（优先级：中）

#### 4.1 统一线程池管理
**文件操作**：
1. 创建 `core/thread_pool_manager.py`
2. 所有异步任务使用统一线程池
3. 实现优雅关闭机制

#### 4.2 优化文件I/O
**文件操作**：
1. 实现配置文件内存缓存
2. 减少重复的文件读取
3. 使用更高效的序列化（msgpack）

## 📈 预期收益

### 代码质量
- 代码量减少 ~15-20%
- 重复率从 ~30% 降低到 <5%
- 圈复杂度降低

### 内存使用
- 内存峰值降低 ~30-40%
- 内存泄漏风险消除
- 长时间运行稳定性提升

### 性能提升
- API响应时间减少 ~15%
- 截图速度提升 ~10%
- 日志解析速度提升 ~20%

### 可维护性
- 服务职责清晰
- 依赖关系简化
- 扩展性增强

## 🚀 实施优先级

### 立即执行（高优先级）
1. 合并价格服务
2. 修复图像资源泄漏
3. 添加缓存大小限制

### 近期执行（中优先级）
4. 重构截图服务
5. 统一线程池管理
6. 优化文件I/O

### 后续优化（低优先级）
7. 重构大服务
8. 规范接口定义
9. 添加性能监控

## 📝 注意事项

1. **向后兼容**：保持API兼容，分步迁移
2. **测试覆盖**：每个阶段完成后进行充分测试
3. **性能基准**：建立性能基准，对比优化效果
4. **回滚计划**：每个优化阶段都有回滚方案
5. **文档更新**：同步更新代码文档和架构文档

## 🔍 监控指标

优化后需要监控的关键指标：
- 内存使用峰值
- 内存泄漏趋势
- CPU使用率
- API响应时间
- 截图成功率
- 日志解析成功率
