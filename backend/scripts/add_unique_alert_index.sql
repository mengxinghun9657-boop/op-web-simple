-- 添加唯一索引防止重复告警
-- 执行前先删除重复数据

-- 1. 查看重复数据
SELECT alert_type, ip, timestamp, COUNT(*) as count
FROM alert_records
GROUP BY alert_type, ip, timestamp
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- 2. 删除重复数据（保留ID最小的记录）
DELETE t1 FROM alert_records t1
INNER JOIN alert_records t2 
WHERE 
    t1.id > t2.id
    AND t1.alert_type = t2.alert_type
    AND t1.ip = t2.ip
    AND t1.timestamp = t2.timestamp;

-- 3. 添加唯一索引
CREATE UNIQUE INDEX idx_unique_alert ON alert_records(alert_type, ip, timestamp);

-- 4. 验证索引创建成功
SHOW INDEX FROM alert_records WHERE Key_name = 'idx_unique_alert';
