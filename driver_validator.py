# 驱动验证模块
import os
import struct
import subprocess

def is_valid_exe(file_path):
    """验证文件是否是有效的Windows可执行文件"""
    try:
        if not os.path.exists(file_path):
            return False
        
        # 检查文件大小（驱动应该至少100KB）
        file_size = os.path.getsize(file_path)
        if file_size < 100 * 1024:
            return False
        
        # 检查PE文件头（Windows可执行文件）
        with open(file_path, 'rb') as f:
            # 读取DOS头
            dos_header = f.read(64)
            if len(dos_header) < 64:
                return False
            
            # 检查MZ签名
            if dos_header[0:2] != b'MZ':
                return False
            
            # 读取PE头偏移
            pe_offset = struct.unpack('<I', dos_header[60:64])[0]
            if pe_offset == 0 or pe_offset >= file_size:
                return False
            
            # 读取PE头
            f.seek(pe_offset)
            pe_header = f.read(4)
            if len(pe_header) < 4:
                return False
            
            # 检查PE签名
            if pe_header != b'PE\x00\x00':
                return False
            
            # 读取机器类型
            machine = struct.unpack('<H', f.read(2))[0]
            # 0x014c = i386 (32位), 0x8664 = x86-64 (64位)
            if machine not in [0x014c, 0x8664]:
                return False
            
            return True
    except:
        return False

def test_driver(driver_path):
    """测试驱动是否可以运行"""
    try:
        # 尝试运行驱动并立即退出
        result = subprocess.run(
            [driver_path, '--version'],
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.returncode == 0 or len(result.stdout) > 0 or len(result.stderr) > 0
    except:
        try:
            # 如果--version失败，尝试直接运行（应该会显示帮助信息）
            result = subprocess.run(
                [driver_path],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            # 即使返回错误码，如果有输出说明文件是可执行的
            return len(result.stdout) > 0 or len(result.stderr) > 0
        except:
            return False

