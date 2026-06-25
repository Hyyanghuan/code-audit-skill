"""违规代码测试 fixture - 应触发审计失败"""

import os

# 硬编码密码（自定义规则）
password = "super_secret_123"

def run_user_code(code: str):
    # eval 禁用（自定义规则 + bandit）
    return eval(code)

def connect_db():
    # SQL 拼接（自定义规则）
    user_id = "1"
    query = "SELECT * FROM users WHERE id=" + user_id
    return query

if __name__ == "__main__":
    run_user_code("1+1")
