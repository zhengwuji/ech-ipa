# GitHub自动推送模块
import subprocess
import os
import sys
from version import get_version, increment_version

def git_push_force():
    """强制推送到GitHub"""
    try:
        # 检查是否在git仓库中
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        if result.returncode != 0:
            print("错误: 当前目录不是git仓库")
            return False
        
        # 获取当前版本
        current_version = get_version()
        
        # 递增版本
        new_version = increment_version()
        
        # 添加所有更改
        subprocess.run(['git', 'add', '.'], check=True)
        
        # 提交（使用非交互模式）
        commit_message = f"Auto commit - Version {new_version}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        # 强制推送到GitHub
        subprocess.run(['git', 'push', '--force', 'origin', 'main'], check=True)
        
        print(f"成功推送到GitHub，版本: {current_version} -> {new_version}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Git操作失败: {e}")
        return False
    except Exception as e:
        print(f"推送失败: {e}")
        return False

if __name__ == '__main__':
    git_push_force()

