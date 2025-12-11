# 驱动诊断工具
import os
import sys
import shutil
from pathlib import Path

def diagnose_driver_issues():
    """诊断驱动问题"""
    print("=" * 60)
    print("浏览器驱动诊断工具")
    print("=" * 60)
    print()
    
    # 检查驱动缓存目录
    cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
    print(f"1. 检查驱动缓存目录: {cache_path}")
    
    if os.path.exists(cache_path):
        print(f"   ✓ 缓存目录存在")
        
        # 查找驱动文件
        driver_files = []
        for root, dirs, files in os.walk(cache_path):
            for file in files:
                if 'chromedriver' in file.lower() or 'msedgedriver' in file.lower():
                    driver_files.append(os.path.join(root, file))
        
        if driver_files:
            print(f"   找到 {len(driver_files)} 个驱动文件:")
            for driver_file in driver_files:
                file_size = os.path.getsize(driver_file)
                print(f"   - {driver_file}")
                print(f"     大小: {file_size:,} 字节 ({file_size / 1024:.2f} KB)")
                
                # 检查文件是否有效
                if file_size < 100 * 1024:
                    print(f"     ✗ 文件太小，可能损坏")
                else:
                    print(f"     ✓ 文件大小正常")
                
                # 检查是否是有效的PE文件
                try:
                    with open(driver_file, 'rb') as f:
                        header = f.read(2)
                        if header == b'MZ':
                            print(f"     ✓ 有效的Windows可执行文件")
                        else:
                            print(f"     ✗ 无效的可执行文件格式")
                except:
                    print(f"     ✗ 无法读取文件")
        else:
            print(f"   - 未找到驱动文件")
    else:
        print(f"   - 缓存目录不存在（首次使用）")
    
    print()
    
    # 检查浏览器安装
    print("2. 检查浏览器安装:")
    from browser_detector import detect_browsers
    browsers = detect_browsers()
    
    if browsers:
        print(f"   找到 {len(browsers)} 个浏览器:")
        for name, path in browsers.items():
            print(f"   - {name}: {path}")
            if os.path.exists(path):
                print(f"     ✓ 文件存在")
            else:
                print(f"     ✗ 文件不存在")
    else:
        print(f"   ✗ 未找到已安装的浏览器")
    
    print()
    
    # 提供解决方案
    print("=" * 60)
    print("建议的解决方案:")
    print("=" * 60)
    print()
    print("如果驱动文件损坏或无效，请执行以下操作：")
    print()
    print(f"1. 删除驱动缓存目录:")
    print(f"   {cache_path}")
    print()
    print("2. 或者运行 '清理驱动缓存.bat'")
    print()
    print("3. 重新启动程序，程序会自动重新下载驱动")
    print()
    print("4. 如果问题持续，请检查：")
    print("   - 网络连接是否正常")
    print("   - 防病毒软件是否阻止了下载")
    print("   - 是否有足够的磁盘空间")
    print()
    
    # 询问是否清理缓存
    response = input("是否现在清理驱动缓存？(y/n): ").strip().lower()
    if response == 'y':
        try:
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path, ignore_errors=True)
                print(f"✓ 已清理缓存目录: {cache_path}")
            else:
                print("缓存目录不存在，无需清理")
        except Exception as e:
            print(f"✗ 清理失败: {e}")
    
    print()
    print("诊断完成！")

if __name__ == '__main__':
    try:
        diagnose_driver_issues()
    except Exception as e:
        print(f"诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")

