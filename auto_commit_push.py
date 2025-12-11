# 自动提交和推送脚本
import subprocess
import sys
from version import increment_version
import os

def auto_commit_and_push():
    """自动提交并推送到GitHub（强制推送）"""
    try:
        # 检查git是否初始化
        if not os.path.exists('.git'):
            print("初始化git仓库...")
            subprocess.run(['git', 'init'], check=True)
            subprocess.run(['git', 'branch', '-M', 'main'], check=True)
        
        # 递增版本号
        old_version = None
        if os.path.exists('version.json'):
            import json
            with open('version.json', 'r', encoding='utf-8') as f:
                old_version = json.load(f).get('version')
        
        new_version = increment_version()
        print(f"版本更新: {old_version} -> {new_version}")
        
        # 添加远程仓库（如果不存在）
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                # 添加远程仓库
                subprocess.run(['git', 'remote', 'add', 'origin', 
                              'https://github.com/zhengwuji/jianche1.git'], check=True)
                print("已添加远程仓库: https://github.com/zhengwuji/jianche1.git")
        except:
            pass
        
        # 添加所有文件
        subprocess.run(['git', 'add', '.'], check=True)
        
        # 提交（使用非交互模式，自动允许）
        commit_message = f"Auto commit - Version {new_version}"
        try:
            subprocess.run(['git', 'commit', '-m', commit_message], 
                         check=True, capture_output=True)
            print(f"已提交: {commit_message}")
        except subprocess.CalledProcessError as e:
            # 如果没有变化，会失败，这是正常的
            if "nothing to commit" in e.stdout.decode() if e.stdout else "":
                print("没有需要提交的更改")
                return
            else:
                raise
        
        # 强制推送到GitHub
        print("正在推送到GitHub...")
        result = subprocess.run(['git', 'push', '--force', 'origin', 'main'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ 成功推送到GitHub！版本: {new_version}")
        else:
            # 如果是第一次推送，可能需要设置上游分支
            if "no upstream branch" in result.stderr:
                subprocess.run(['git', 'push', '--set-upstream', 'origin', 'main', '--force'], 
                             check=True)
                print(f"✓ 成功推送到GitHub（首次推送）！版本: {new_version}")
            else:
                print(f"推送失败: {result.stderr}")
                return False
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Git操作失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
        return False
    except Exception as e:
        print(f"操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = auto_commit_and_push()
    sys.exit(0 if success else 1)

