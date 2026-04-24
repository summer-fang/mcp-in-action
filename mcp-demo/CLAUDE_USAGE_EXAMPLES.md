# Claude + AWS OpenSearch 使用示例

## 📊 场景 1: 错误日志分析

### 用户输入：
```
我的应用最近有报错，帮我查一下最近 2 小时的 ERROR 日志，
索引是 *bts-bigaccount*，然后分析一下是什么问题。
```

### Claude 会做什么：
1. 调用 `search_aws_logs(query="ERROR", index_pattern="*bts-bigaccount*", hours_ago=2, size=20)`
2. 分析返回的日志内容
3. 识别错误模式和频率
4. 提供诊断报告

### Claude 的回复示例：
```
我已经搜索了最近 2 小时的 ERROR 日志，找到 15 条相关记录。分析如下：

📊 错误统计：
- NullPointerException: 8 次 (53%)
- SQLException: 5 次 (33%)
- TimeoutException: 2 次 (14%)

🔍 主要问题：

1. **NullPointerException** (最频繁)
   - 位置：OrderService.processPayment()
   - 原因：未检查用户对象是否为 null
   - 时间：主要发生在 14:30-15:00
   - 建议修复：
     ```java
     if (user == null) {
         throw new IllegalArgumentException("User cannot be null");
     }
     ```

2. **SQLException** (数据库连接)
   - 错误信息："Connection pool exhausted"
   - 原因：数据库连接池配置过小
   - 建议：增加连接池大小或优化查询

3. **TimeoutException** (偶发)
   - 服务：external-api-call
   - 建议：增加超时时间或实现重试机制

💡 优先修复建议：
1. 立即修复 NullPointerException（影响 50%+ 请求）
2. 调整数据库连接池配置
3. 对外部 API 调用增加降级策略
```

---

## 🔎 场景 2: 追踪特定请求

### 用户输入：
```
帮我追踪 traceId 为 "9a18bc0641e4444397e57f87007489bc" 的完整调用链，
看看这个请求为什么失败了。
```

### Claude 会做什么：
1. 调用 `search_aws_logs(query="9a18bc0641e4444397e57f87007489bc", hours_ago=10, size=50)`
2. 按时间顺序整理日志
3. 重建调用链路
4. 分析失败原因

### Claude 的回复示例：
```
我已经追踪了这个请求的完整调用链，找到 12 条相关日志。以下是调用流程：

📍 调用链路（按时间顺序）：

1. [14:23:15.123] Gateway 接收请求
   - 用户ID: user_12345
   - 端点: POST /api/orders

2. [14:23:15.234] OrderService 开始处理
   - 订单金额: $299.99
   - 调用 UserService 验证用户 ✅

3. [14:23:15.456] 调用 PaymentService
   - 支付方式: 信用卡
   - 开始调用第三方支付网关

4. [14:23:25.123] ❌ PaymentService 超时
   - 错误: "Payment gateway timeout after 10s"
   - 第三方网关未响应

5. [14:23:25.234] OrderService 开始回滚
   - 尝试取消订单
   - ❌ 回滚失败："Order status already changed"

🔴 问题根因：
- 第三方支付网关响应超时（10秒）
- 超时后的回滚逻辑失败
- 订单状态不一致

💡 建议修复：
1. 增加支付网关超时时间到 30 秒
2. 实现幂等性保证，支持多次回滚
3. 添加分布式事务管理（如 Saga 模式）
4. 对支付失败增加补偿机制

📝 参考代码：
```java
@Transactional
public Order processOrder(OrderRequest request) {
    try {
        PaymentResult result = paymentService.pay(request, 30); // 30s timeout
        if (!result.isSuccess()) {
            // 使用补偿事务
            compensationService.schedulePaymentRetry(request);
        }
        return orderRepository.save(order);
    } catch (TimeoutException e) {
        // 记录失败，等待异步补偿
        log.error("Payment timeout for order: {}", request.getOrderId());
        throw new PaymentFailedException("Payment gateway timeout", e);
    }
}
```
```

---

## 🚀 场景 3: 性能优化分析

### 用户输入：
```
最近系统响应变慢了，帮我：
1. 搜索最近 6 小时包含 "slow" 或 "timeout" 的日志
2. 分析哪些服务或接口最慢
3. 给出优化建议
```

### Claude 会做什么：
1. 调用 `search_aws_logs(query="slow OR timeout", hours_ago=6, size=50)`
2. 统计慢查询分布
3. 识别性能瓶颈
4. 提供优化方案

### Claude 的回复示例：
```
我已经分析了最近 6 小时的性能日志，找到 47 条慢查询记录。

📊 性能问题分布：

| 服务/接口 | 慢查询次数 | 平均响应时间 | 最大响应时间 |
|----------|-----------|-------------|-------------|
| /api/users/search | 23 | 3.5s | 8.2s |
| /api/orders/list | 15 | 2.1s | 5.3s |
| /api/products/filter | 9 | 4.2s | 12.1s |

🔍 详细分析：

### 1. /api/users/search (最严重)
**问题：**
- 全表扫描，没有使用索引
- 查询条件：`SELECT * FROM users WHERE name LIKE '%keyword%'`
- 数据量：500万+ 用户

**优化建议：**
```sql
-- 方案1：添加全文索引
CREATE FULLTEXT INDEX idx_user_name ON users(name);
SELECT * FROM users WHERE MATCH(name) AGAINST('keyword');

-- 方案2：使用 Elasticsearch
// 将用户数据同步到 ES，使用 ES 进行搜索
```

**预期提升：** 响应时间从 3.5s → 50ms (70x 提升)

### 2. /api/orders/list
**问题：**
- N+1 查询问题
- 每个订单单独查询用户和产品信息

**优化建议：**
```java
// 使用 JOIN 或批量查询
List<Order> orders = orderRepository.findByUserId(userId);
List<Long> userIds = orders.stream().map(Order::getUserId).collect(Collectors.toList());
Map<Long, User> userMap = userRepository.findByIdIn(userIds)
    .stream().collect(Collectors.toMap(User::getId, u -> u));

// 在内存中组装数据
orders.forEach(order -> order.setUser(userMap.get(order.getUserId())));
```

**预期提升：** 响应时间从 2.1s → 200ms (10x 提升)

### 3. /api/products/filter
**问题：**
- 复杂的多条件过滤，数据库查询效率低
- 没有使用缓存

**优化建议：**
1. 添加 Redis 缓存：
```java
@Cacheable(value = "products", key = "#filter.hashCode()")
public List<Product> filterProducts(ProductFilter filter) {
    // 查询逻辑
}
```

2. 使用预计算：
```java
// 定时任务预计算热门筛选结果
@Scheduled(fixedRate = 300000) // 5分钟
public void precomputeHotFilters() {
    List<ProductFilter> hotFilters = analyticsService.getHotFilters();
    hotFilters.forEach(filter -> {
        List<Product> results = productService.filterProducts(filter);
        redisTemplate.opsForValue().set("filter:" + filter.hashCode(), results, 5, TimeUnit.MINUTES);
    });
}
```

**预期提升：** 响应时间从 4.2s → 100ms (40x 提升)

📈 总体优化计划：

**短期（1周内）：**
- [ ] 为 users 表添加索引
- [ ] 修复 N+1 查询问题
- [ ] 添加 Redis 缓存

**中期（1个月内）：**
- [ ] 引入 Elasticsearch 做搜索
- [ ] 实现查询结果预计算
- [ ] 添加慢查询监控告警

**长期：**
- [ ] 数据库分库分表
- [ ] 引入 CDN 缓存静态资源
- [ ] 实现读写分离

💰 预期效果：
- 平均响应时间降低 80%+
- 系统吞吐量提升 5x
- 用户体验显著改善
```

---

## 🐛 场景 4: 异常趋势分析

### 用户输入：
```
帮我分析最近 24 小时内异常的趋势，
看看是否有突发问题或规律性错误。
```

### Claude 会做什么：
1. 调用 `search_aws_logs_by_time(query="ERROR OR exception", time_from="now-24h", size=50)`
2. 按时间段统计错误数量
3. 识别异常模式
4. 分析可能的原因

### Claude 的回复示例：
```
我已经分析了最近 24 小时的异常日志，以下是趋势分析：

📈 错误趋势图（每小时错误数）：

00:00 ████ 4
01:00 ███ 3
02:00 ██ 2
03:00 █ 1
...
14:00 ██████████████ 14  ⚠️ 突增
15:00 ████████████████████ 20  🔴 峰值
16:00 ██████████ 10
17:00 ██████ 6
...

🚨 关键发现：

1. **14:00-15:00 突发异常**
   - 错误数量突增 5x
   - 主要错误：DatabaseConnectionException (15次)
   - 原因分析：
     * 14:10 开始数据库连接池耗尽
     * 14:45 问题恢复
     * 可能原因：定时任务或突发流量

2. **每天 10:00 固定错误**
   - 规律：每天 10:00±5分钟
   - 错误：CacheRefreshException
   - 原因：定时缓存刷新任务失败
   - 建议：优化缓存刷新逻辑，增加重试

3. **凌晨 3:00 偶发超时**
   - 频率：一周 2-3 次
   - 错误：ExternalAPITimeout
   - 原因：第三方服务维护时间
   - 建议：增加降级策略

💡 修复优先级：

**P0 (立即修复):**
- 调查 14:00 的数据库连接池耗尽问题
- 可能需要增加连接池大小或优化连接使用

**P1 (本周修复):**
- 修复 10:00 的缓存刷新任务
- 添加失败重试和告警

**P2 (下周修复):**
- 为第三方 API 实现降级策略
- 在凌晨时段使用缓存数据

📝 监控建议：
- 设置错误率告警阈值：> 10 errors/hour
- 添加数据库连接池监控
- 定时任务执行状态监控
```

---

## 💬 其他有用的提问方式

### 日志搜索：
```
搜索包含 "OutOfMemoryError" 的日志
搜索用户 ID 为 12345 的所有日志
搜索最近 3 小时 payment 服务的日志
```

### 问题诊断：
```
为什么订单创建失败了？帮我查相关日志
用户反馈页面加载很慢，帮我定位问题
最近支付成功率下降了，帮我分析原因
```

### 代码改进：
```
根据日志分析，我的代码哪里需要改进？
这个错误应该如何处理？给出代码示例
帮我写一个异常处理的最佳实践代码
```

### 监控和告警：
```
帮我设计一个针对这类错误的监控方案
应该对哪些指标设置告警？阈值是多少？
如何预防这类问题再次发生？
```

---

## 🎯 最佳实践

1. **描述清楚问题背景**
   - ✅ "我的订单服务偶尔超时，帮我查 payment 相关的日志"
   - ❌ "查日志"

2. **指定时间范围**
   - ✅ "搜索最近 2 小时的错误日志"
   - ❌ "搜索错误日志"（默认只搜索 1 小时）

3. **提供关键词**
   - ✅ "搜索包含 traceId 或 userId 123456 的日志"
   - ❌ "搜索用户的日志"

4. **明确期望输出**
   - ✅ "分析错误原因并给出修复建议"
   - ✅ "统计各类错误的数量和占比"
   - ✅ "找出性能最慢的 5 个接口"

---

**提示：** Claude 会根据上下文智能调用工具，你只需要用自然语言描述需求即可！
