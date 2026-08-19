# -*- coding: utf-8 -*-
"""
Windows 资源管理器实时文件夹排序动态同步模块
1. 毫秒级探测 Windows Explorer 当前打开该文件夹窗口的真实实时排序列与正倒序（SortColumns）
2. 支持：按名称（自然增序/降序）、按修改日期（最新在上/最旧在上）、按大小（递增/递减）、按类型等全部 Windows 系统排序规则
3. 当用户在资源管理器中点击切换排序后，即时感知并自动触发图片列表无缝重排
"""

import os
import sys
import subprocess
import tempfile
import functools
import re
import time

# Windows 原生 StrCmpLogicalW 自然比较函数
WIN_STRCMP = None
if sys.platform == 'win32':
    try:
        import ctypes
        _shlwapi = ctypes.windll.shlwapi
        _StrCmpLogicalW = _shlwapi.StrCmpLogicalW
        _StrCmpLogicalW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        _StrCmpLogicalW.restype = ctypes.c_int

        def win_cmp(a, b):
            return _StrCmpLogicalW(str(a), str(b))

        WIN_STRCMP = functools.cmp_to_key(win_cmp)
    except Exception:
        WIN_STRCMP = None

def natural_sort_key(path_str):
    """跨平台自然排序键 (数值递增、字母不区分大小写)"""
    filename = os.path.basename(path_str)
    parts = [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]
    return (os.path.dirname(path_str).lower(), parts)

JS_SORT_QUERY_SCRIPT = r'''
try {
    var stream = new ActiveXObject('ADODB.Stream');
    stream.Type = 2; // adTypeText
    stream.Charset = 'utf-8';
    stream.Open();
    stream.LoadFromFile(WScript.Arguments(0));
    var target = stream.ReadText().replace(/^\s+|\s+$/g, '').toLowerCase().replace(/\\+$/, '');
    stream.Close();

    var shell = new ActiveXObject('Shell.Application');
    var wins = shell.Windows();
    var found_sort = '';

    for (var i = 0; i < wins.Count; i++) {
        try {
            var w = wins.Item(i);
            if (w && w.Document && w.Document.Folder) {
                var p = '';
                try { p = w.Document.Folder.Self.Path; } catch(e) {}
                if (!p && w.LocationURL) {
                    var u = w.LocationURL;
                    if (u.indexOf('file:///') == 0) {
                        p = decodeURI(u.substring(8)).replace(/\//g, '\\');
                    }
                }
                if (p) {
                    p = p.toLowerCase().replace(/\\+$/, '');
                    if (p == target) {
                        try {
                            found_sort = w.Document.SortColumns;
                        } catch(e) {}
                        break;
                    }
                }
            }
        } catch(e) {}
    }

    WScript.Echo(found_sort);
} catch(err) {}
'''

_LAST_QUERY_TIME = 0
_LAST_QUERY_RESULT = {}

def get_live_explorer_sort_columns(folder_path):
    """查询 Windows 资源管理器中该文件夹当前的实时排序列配置 (如 'prop:System.ItemNameDisplay;' 或 'prop:-System.DateModified;')"""
    if sys.platform != 'win32' or not folder_path or not os.path.exists(folder_path):
        return ""

    norm_path = os.path.abspath(folder_path)
    now = time.time()

    # 缓存 300ms 避免过度频繁执行子进程
    if norm_path in _LAST_QUERY_RESULT and (now - _LAST_QUERY_TIME) < 0.3:
        return _LAST_QUERY_RESULT[norm_path]

    target_txt = os.path.join(tempfile.gettempdir(), "_labelimg2_target_folder.txt")
    js_script = os.path.join(tempfile.gettempdir(), "_labelimg2_query_sort.js")

    try:
        with open(target_txt, "w", encoding="utf-8") as f:
            f.write(norm_path)

        if not os.path.exists(js_script):
            with open(js_script, "w", encoding="utf-8") as f:
                f.write(JS_SORT_QUERY_SCRIPT)

        res = subprocess.run(
            ["cscript.exe", "//Nologo", "//E:JScript", js_script, target_txt],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",
            timeout=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        sort_col = res.stdout.strip()
        globals()['_LAST_QUERY_TIME'] = now
        _LAST_QUERY_RESULT[norm_path] = sort_col
        return sort_col
    except Exception:
        return ""


def sort_images_by_folder_order(image_paths, folder_path):
    """
    根据所选文件夹当前的真实排序方式（实时动态对齐资源管理器）排列图片列表
    """
    if not image_paths:
        return []

    sort_col = get_live_explorer_sort_columns(folder_path)
    # 若无打开的 Explorer 窗口或返回空，默认采用 Windows 系统原生自然名称递增排序
    if not sort_col:
        sort_col = "prop:System.ItemNameDisplay;"

    sort_col_lower = sort_col.lower()

    # 1. 按修改时间排序 (DateModified)
    if "datemodified" in sort_col_lower:
        is_desc = "-" in sort_col
        def mtime_key(p):
            try: return os.path.getmtime(p)
            except Exception: return 0
        return sorted(image_paths, key=mtime_key, reverse=is_desc)

    # 2. 按创建时间 / 项目日期排序 (DateCreated / ItemDate)
    elif "datecreated" in sort_col_lower or "itemdate" in sort_col_lower:
        is_desc = "-" in sort_col
        def ctime_key(p):
            try: return os.path.getctime(p)
            except Exception: return 0
        return sorted(image_paths, key=ctime_key, reverse=is_desc)

    # 3. 按文件大小排序 (Size)
    elif "size" in sort_col_lower:
        is_desc = "-" in sort_col
        def size_key(p):
            try: return os.path.getsize(p)
            except Exception: return 0
        return sorted(image_paths, key=size_key, reverse=is_desc)

    # 4. 按文件类型 / 扩展名排序 (ItemTypeText)
    elif "itemtypetext" in sort_col_lower:
        is_desc = "-" in sort_col
        def type_key(p):
            ext = os.path.splitext(p)[1].lower()
            return (ext, natural_sort_key(p))
        return sorted(image_paths, key=type_key, reverse=is_desc)

    # 5. 按名称排序 (ItemNameDisplay 或其他，支持增序与倒序)
    else:
        is_desc = "-" in sort_col
        if WIN_STRCMP is not None:
            def win_name_key(p):
                return (os.path.dirname(p).lower(), WIN_STRCMP(os.path.basename(p)))
            try:
                return sorted(image_paths, key=win_name_key, reverse=is_desc)
            except Exception:
                return sorted(image_paths, key=natural_sort_key, reverse=is_desc)
        else:
            return sorted(image_paths, key=natural_sort_key, reverse=is_desc)
