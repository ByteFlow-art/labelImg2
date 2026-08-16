import sys
import os

# 将当前项目根目录添加到 python 搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import labelImg

if __name__ == "__main__":
    sys.exit(labelImg.main())

