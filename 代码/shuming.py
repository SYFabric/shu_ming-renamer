# ============================================================
# 按通配符规则批量重命名文件 —— 带图形界面（UI）版本
# ============================================================
# 功能简介：
#   1) 选择一个文件夹（路径输入框 / 浏览按钮）
#   2) 在"文件名匹配模式"里填写模板，用一个"通配符字符"标出
#      原文件名中"要保留下来、作为新文件名"的那一段
#   3) 点"预览改名"查看每个文件会被改成什么
#   4) 确认无误后点"执行重命名"真正改文件名
# 例：模式 asXXX——()&.srt ，通配符 & ，文件 asXXX——()1.srt -> 1.srt
# ============================================================


# os：用来操作文件和文件夹（判断路径、列目录、重命名等）
# re：正则表达式模块，用来按"模式"去匹配文件名、提取想要的那段内容
import os
import re
import ctypes

# 窗口图标路径（必须是 .ico 格式，改成你自己的路径）
ICON_PATH = r"E:\快捷\CODE\Python\鼠鸣\代码\icon.ico"

# tkinter 是 Python 自带的图形界面库。
# 这里先"延迟导入"：只在真正需要用到界面时才导入 tkinter。
# 这样做的好处是：在没有显示器的环境（如服务器/沙盒）里，
# 我们依然可以单独测试后面的"核心逻辑"函数，而不会因 tkinter 报错。
tk = None  # 用来缓存 tkinter 模块本身
def _ensure_tk():
    # 声明要修改外层（全局）变量 tk、ttk、filedialog、messagebox
    global tk, ttk, filedialog, messagebox
    if tk is None:  # 如果还没导入过，就导入一次
        import tkinter as _tk                 # 导入 tkinter，起个别名 _tk
        from tkinter import ttk as _ttk, filedialog as _fd, messagebox as _mb
        tk = _tk      # 保存模块引用，下次就不用再导入
        ttk = _ttk    # ttk：带现代外观的界面控件（按钮、输入框等）
        filedialog = _fd    # 文件/文件夹选择对话框
        messagebox = _mb    # 弹出提示/确认/错误对话框


# ============================================================
# 核心逻辑部分（不依赖界面，可独立测试）
# ============================================================

# 旧规则（兼容老用法）：匹配形如  a(1).txt / b(20).pdf 的文件名
# 解释：^(.*) 任意开头，\( 左括号，(\d+) 一串数字，\) 右括号，(\.[^.]*)$ 后缀
# 例：对 "a(1).txt" 会捕获 主体"a"、数字"1"、后缀".txt"
LEGACY_PATTERN = re.compile(r'^(.*)\((\d+)\)(\.[^.]*)$')


def compile_pattern(match_pattern, wildcard_char):
    """
    把用户写的"匹配模式"编译成正则表达式对象。
    参数：
        match_pattern : 用户在界面上填的模板，如 asXXX——()&.srt
        wildcard_char : 用户指定的通配符字符，如 &（默认 *）
    返回：
        (正则表达式对象, 错误信息) ；若成功，错误信息为 None
    """
    if not match_pattern:
        return None, "匹配模式为空"

    wc = wildcard_char or "*"   # 若没填通配符，默认用 *

    # 第 1 步：把整个模式按"正则特殊字符"转义，避免 . ( ) 等被当作正则语法
    escaped = re.escape(match_pattern)

    # 第 2 步：把"通配符"那个字符的转义结果，替换成一个"捕获组 (.*?)"
    # (.*?) 表示：匹配任意内容，但尽可能少（非贪婪），并把匹配到的内容捕获下来
    escaped_wc = re.escape(wc)          # 通配符自身可能需要转义（如 * -> \*）
    regex_str = escaped.replace(escaped_wc, r'(.*?)')

    try:
        return re.compile(regex_str), None   # 编译成功，返回正则对象
    except re.error as e:
        return None, f"模式编译失败：{e}"   # 编译失败，返回错误提示


def _plan_one(name, regex, wildcard_used):
    """
    对【单个文件名】计算它改名后的结果。
    参数：
        name          : 原文件名，如 asXXX——()1.srt
        regex         : 编译好的正则表达式对象（None 表示走旧规则）
        wildcard_used : 通配符字符（本函数暂未使用，保留参数）
    返回：
        (新文件名 或 None, 状态字符串)
        状态：rename=可改名 / skip_no_match=不匹配规则
    """
    if regex is None:
        # ---- 旧规则：提取括号 () 里的数字 ----
        m = LEGACY_PATTERN.match(name)
        if not m:
            return None, "skip_no_match"   # 不匹配旧规则，跳过
        ext = m.group(3)     # 第 3 个捕获组：后缀，如 .txt
        body = m.group(2)    # 第 2 个捕获组：括号内的数字，如 1
        return f"{body}{ext}", "rename"   # 例：1 + .srt -> 1.srt

    # ---- 新规则：用用户自定义模式匹配 ----
    m = regex.match(name)
    if not m:
        return None, "skip_no_match"   # 文件名不符合模式，跳过

    # 取第 1 个捕获组（即通配符位置实际对应到的内容）
    captured = m.group(1) if m.groups() else ""
    captured = captured.strip()   # 去掉首尾空白
    if not captured:
        return None, "skip_no_match"   # 没捕获到内容，跳过

    # 扩展名：优先使用【原文件自身】的扩展名，而不是模式里写死的扩展名
    # 这样即使模式里写的是 .srt，遇到 .srt 文件也会保留为 .srt
    _, ext = os.path.splitext(name)
    if not ext:
        ext = ""
    return f"{captured}{ext}", "rename"   # 例：捕获到 1 -> 1.srt


def build_preview(folder_path, match_pattern=None, wildcard_char=None):
    """
    扫描整个文件夹，生成"改名预览"列表。
    返回：列表，每项 = (原文件名, 新文件名或None, 状态)
    状态：rename / skip_no_match / skip_exists（目标已存在）
    若文件夹不存在，返回 None。
    """
    if not os.path.isdir(folder_path):
        return None   # 路径不是合法文件夹

    regex = None
    if match_pattern:
        # 用户填了模式：编译成正则；若编译失败也忽略（后面逐个文件会 skip）
        regex, _err = compile_pattern(match_pattern, wildcard_char)

    results = []
    # 遍历文件夹里按名字排序后的所有条目
    for name in sorted(os.listdir(folder_path)):
        src = os.path.join(folder_path, name)
        if not os.path.isfile(src):
            continue   # 只处理"文件"，跳过子文件夹

        new_name, status = _plan_one(name, regex, wildcard_char)
        if status != "rename":
            # 不匹配规则：记录为跳过
            results.append((name, None, "skip_no_match"))
            continue

        # 检查"目标文件名"是否已经存在，避免覆盖已有文件
        dst = os.path.join(folder_path, new_name)
        if os.path.exists(dst):
            results.append((name, new_name, "skip_exists"))
        else:
            results.append((name, new_name, "rename"))
    return results


def do_rename(folder_path, match_pattern=None, wildcard_char=None):
    """
    真正执行重命名操作。
    返回 (成功改名数量, 跳过数量)；若路径非法返回 None。
    """
    results = build_preview(folder_path, match_pattern, wildcard_char)
    if results is None:
        return None

    renamed = 0
    skipped = 0
    for name, new_name, status in results:
        if status != "rename":
            skipped += 1   # 不匹配或目标已存在，都算跳过
            continue
        src = os.path.join(folder_path, name)
        dst = os.path.join(folder_path, new_name)
        try:
            os.rename(src, dst)   # 调用系统重命名
            renamed += 1
        except OSError:
            skipped += 1          # 重命名失败（权限/占用等）也跳过
    return renamed, skipped


# ============================================================
# 图形界面部分（GUI）
# ============================================================
class RenameApp:
    """重命名工具的主窗口类，负责搭建界面和处理按钮点击事件。"""

    def __init__(self, root):
        _ensure_tk()              # 确保 tkinter 已导入
        self.root = root          # root 是主窗口对象
        root.title("鼠鸣v1.0.0：通配符规则重命名工具_bySYFabric")   # 窗口标题
        root.geometry("760x560")               # 窗口初始大小 宽x高
        # 设置窗口图标（文件不存在也不报错，不影响程序运行）
        try:
            root.iconbitmap(ICON_PATH)
        except Exception:
            pass

        # ---------- 1) 路径选择框 ----------
        # LabelFrame：带标题的分组框，用于把相关控件框在一起
        path_frame = ttk.LabelFrame(root, text="文件夹路径")
        path_frame.pack(fill="x", padx=10, pady=8)   # 横向填满，外边距 10/8

        # 用 StringVar 绑定输入框，方便用代码读写输入框内容
        self.path_var = tk.StringVar(value=r"在此处输入路径 或直接点击右侧浏览按钮选择路径")
        # Entry：单行文本输入框，width=70 个字符宽
        ttk.Entry(path_frame, textvariable=self.path_var, width=70).pack(
            side="left", padx=6, pady=6, fill="x", expand=True)
        # 浏览按钮：点击后调用 self.on_browse 弹出文件夹选择对话框
        ttk.Button(path_frame, text="浏览...", command=self.on_browse).pack(
            side="right", padx=6, pady=6)

        # ---------- 2) 匹配规则框 ----------
        rule_frame = ttk.LabelFrame(root, text="重命名规则")
        rule_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(rule_frame, text="文件名匹配模式：").grid(
            row=0, column=0, padx=6, pady=4, sticky="w")   # sticky="w" 左对齐
        self.pattern_var = tk.StringVar()   # 模式输入框的变量
        ttk.Entry(rule_frame, textvariable=self.pattern_var, width=40).grid(
            row=0, column=1, padx=6, pady=4, sticky="we")

        ttk.Label(rule_frame, text="通配符字符：").grid(
            row=0, column=2, padx=6, pady=4, sticky="w")
        self.wildcard_var = tk.StringVar(value="*")   # 通配符，默认 *
        ttk.Entry(rule_frame, textvariable=self.wildcard_var, width=6).grid(
            row=0, column=3, padx=6, pady=4)

        # 一行灰色提示文字
        ttk.Label(rule_frame, text="手动更改需要被识别为数字的部分 如a(*).txt\n通配符可自定义 设置后点击预览改名 执行前请做好备份",
                  foreground="#888").grid(row=1, column=0, columnspan=4, padx=6, sticky="w")
        rule_frame.columnconfigure(1, weight=1)   # 让模式输入框随窗口拉伸

        # ---------- 3) 操作按钮 ----------
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", padx=10)
        ttk.Button(btn_frame, text="预览改名", command=self.on_preview).pack(
            side="left", padx=4)
        ttk.Button(btn_frame, text="执行重命名", command=self.on_execute).pack(
            side="left", padx=4)

        # ---------- 4) 预览窗口（表格） ----------
        preview_frame = ttk.LabelFrame(root, text="改名前后预览（原名 → 新名）")
        preview_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # Treeview：可显示多列数据的表格控件
        self.tree = ttk.Treeview(
            preview_frame,
            columns=("old", "new", "status"),   # 三列：原名/新名/状态
            show="headings", height=18)          # 只显示表头，不显示首列
        self.tree.heading("old", text="原名")
        self.tree.heading("new", text="新名")
        self.tree.heading("status", text="状态")
        self.tree.column("old", width=280)
        self.tree.column("new", width=200)
        self.tree.column("status", width=180)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        # 底部状态栏文字
        self.status_var = tk.StringVar(value="请选择文件夹后点击「预览改名」")
        ttk.Label(root, textvariable=self.status_var, foreground="#555").pack(
            padx=10, pady=4, anchor="w")

        # 程序启动时，对默认路径做一次"自动填充匹配模式框"
        self.after_init_autofill()

    def _set_path(self, folder):
        """统一入口：写入路径并重新自动填充匹配模式框。供浏览共用。"""
        self.path_var.set(folder)
        self.autofill_pattern_from_path()

    def autofill_pattern_from_path(self):
        """
        读取当前路径下的【第一个文件】，把它的文件名【原样】填入匹配模式框。
        不做任何推导——通配符位置由用户自己改。
        """
        folder = self.path_var.get().strip()
        if not folder or not os.path.isdir(folder):
            return   # 路径为空或不是文件夹，什么都不做
        # 列出该文件夹下所有"文件"（排除子文件夹），按名排序
        files = [n for n in sorted(os.listdir(folder))
                 if os.path.isfile(os.path.join(folder, n))]
        if not files:
            return   # 文件夹为空，不做处理
        self.pattern_var.set(files[0])   # 把第一个文件名原样填入模式框
        self.status_var.set(
            f"已根据首个文件「{files[0]}」自动填充匹配模式（请自行设置通配符位置）")

    def after_init_autofill(self):
        # 用 after 延迟一小段时间（50 毫秒）再执行自动填充，
        # 确保窗口已经完全构建好、能正确显示状态文字。
        self.root.after(50, self.autofill_pattern_from_path)

    def on_browse(self):
        """浏览按钮回调：弹出文件夹选择对话框，选完后更新路径并重新自动填充。"""
        chosen = filedialog.askdirectory(
            initialdir=self.path_var.get() or os.getcwd())   # 初始目录为当前路径
        if chosen:
            self._set_path(chosen)   # 统一入口：写路径 + 自动填充模式框

    def _get_rule(self):
        """读取界面上的"模式"和"通配符"两个输入，返回 (模式, 通配符)。"""
        pat = self.pattern_var.get().strip()
        wc = self.wildcard_var.get().strip() or "*"
        return pat, wc

    def _refresh_tree(self, results):
        """把预览结果刷新到表格（Treeview）中。"""
        self.tree.delete(*self.tree.get_children())   # 先清空旧数据
        for name, new_name, status in results:
            if status == "rename":
                self.tree.insert("", "end", values=(name, new_name, "将重命名"))
            elif status == "skip_exists":
                self.tree.insert("", "end", values=(name, new_name, "跳过：目标已存在"))
            else:
                self.tree.insert("", "end", values=(name, "-", "跳过：不匹配规则"))

    def on_preview(self):
        """预览按钮回调：扫描文件夹并在表格中展示改名前后对照。"""
        folder = self.path_var.get().strip()
        pat, wc = self._get_rule()

        # 若用户填了模式，先校验它能否编译成功
        if pat:
            _regex, err = compile_pattern(pat, wc)
            if err:
                messagebox.showerror("模式错误", err)
                return

        results = build_preview(folder, pat or None, wc)
        if results is None:
            messagebox.showerror("错误", f"路径不存在或不是文件夹：\n{folder}")
            return

        self._refresh_tree(results)
        will_rename = sum(1 for r in results if r[2] == "rename")
        skip = len(results) - will_rename
        self.status_var.set(f"预览完成：可重命名 {will_rename} 个，跳过 {skip} 个")

    def on_execute(self):
        """执行按钮回调：先预览，弹确认框，用户确认后才真正改名。"""
        folder = self.path_var.get().strip()
        pat, wc = self._get_rule()

        if pat:
            _regex, err = compile_pattern(pat, wc)
            if err:
                messagebox.showerror("模式错误", err)
                return

        results = build_preview(folder, pat or None, wc)
        if results is None:
            messagebox.showerror("错误", f"路径不存在或不是文件夹：\n{folder}")
            return

        will_rename = sum(1 for r in results if r[2] == "rename")
        if will_rename == 0:
            messagebox.showinfo("提示", "没有可重命名的文件。")
            return

        # 弹确认框，用户点"是"才继续
        if not messagebox.askyesno("确认执行",
                f"即将重命名 {will_rename} 个文件，是否继续？"):
            return

        ret = do_rename(folder, pat or None, wc)
        if ret is None:
            messagebox.showerror("错误", f"路径无效：\n{folder}")
            return

        renamed, skipped = ret
        # 执行完再刷新一次预览（状态会变为"目标已存在/跳过"）
        self._refresh_tree(build_preview(folder, pat or None, wc))
        self.status_var.set(f"完成：成功重命名 {renamed} 个，跳过 {skipped} 个")
        messagebox.showinfo("完成", f"成功重命名 {renamed} 个文件，跳过 {skipped} 个。")


def main():
    """程序入口：创建主窗口并启动界面主循环。"""
    _ensure_tk()
    # ↓↓↓ 新增：让任务栏把本程序当作独立应用，从而使用自定义图标 ↓↓↓
    try:
        myappid = "syfabric.shuming.renamer.v1"  # 任意唯一字符串即可
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
    # ↑↑↑ 新增结束 ↑↑↑
    root = tk.Tk()        # 创建顶层窗口
    RenameApp(root)       # 用我们的应用类去搭建界面
    root.mainloop()       # 进入事件循环，等待用户点击按钮等操作


if __name__ == "__main__":
    main()   # 当直接运行本文件时，调用 main() 启动程序
