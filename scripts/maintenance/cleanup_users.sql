-- ============================================================
-- 用户表数据清理脚本
-- 目标：仅保留指定用户（密码经 Python 脚本单独重置，不写入本文件）
-- 使用方法：在 MySQL 客户端中 source 此文件
-- ============================================================

-- 0. 设置变量（请自行填入，不要提交真实口令）
SET @target_username = 'yutaiyin';
SET @target_email = 'yutaiyin@shangzhou.local';
-- @target_password 已移除：密码统一由 backend/reset_password.py 重置（不落到仓库）

-- 1. 查看当前数据（执行前）
SELECT '=== 清理前数据 ===' AS info;
SELECT id, name, email, status FROM dify_accounts;
SELECT u.id, u.account_id, u.phone, u.status FROM users u;

-- 2. 获取 yutaiyin 的 account_id
SET @yutaiyin_id = (SELECT id FROM dify_accounts WHERE name = @target_username LIMIT 1);

SELECT CONCAT('yutaiyin account_id: ', @yutaiyin_id) AS info;

-- 3. 如果 yutaiyin 不存在，则创建
-- 注意：密码需要通过 Python 生成，这里先占位，后续用 Python 脚本更新
-- 如果已有 yutaiyin 账号，跳过此步

-- 4. 清理 dify_tenant_account_joins（删除非 yutaiyin 的绑定）
DELETE FROM dify_tenant_account_joins WHERE account_id != @yutaiyin_id;

-- 5. 清理 dify_accounts（删除非 yutaiyin 的账号）
DELETE FROM dify_accounts WHERE id != @yutaiyin_id;

-- 6. 清理所有角色关联
DELETE FROM user_roles;

-- 7. 清理 users 表
DELETE FROM users;

-- 8. 确保角色存在
INSERT IGNORE INTO roles (name, description) VALUES ('admin', '系统管理员');
INSERT IGNORE INTO roles (name, description) VALUES ('user', '普通用户');

-- 9. 插入 yutaiyin 的 users 记录
INSERT INTO users (account_id, phone, status, created_at, updated_at)
VALUES (@yutaiyin_id, '', 1, NOW(), NOW());

SET @yutaiyin_user_id = LAST_INSERT_ID();

-- 10. 分配 admin 角色
INSERT INTO user_roles (user_id, role_id, created_at)
SELECT @yutaiyin_user_id, id, NOW() FROM roles WHERE name = 'admin';

-- 11. 清理孤立的工作区
DELETE t FROM dify_tenants t
LEFT JOIN dify_tenant_account_joins j ON j.tenant_id = t.id
WHERE j.tenant_id IS NULL;

-- 12. 查看清理后数据
SELECT '=== 清理后数据 ===' AS info;
SELECT id, name, email, status FROM dify_accounts;
SELECT u.id, u.account_id, u.phone, u.status FROM users u;
SELECT r.name, r.description FROM roles r;
SELECT u.id AS user_id, r.name AS role_name
FROM user_roles ur
JOIN users u ON u.id = ur.user_id
JOIN roles r ON r.id = ur.role_id;

SELECT '=== 清理完成 ===' AS info;
