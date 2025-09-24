import tkinter as tk
from tkinter import font, ttk, filedialog, messagebox
import functools
import time
import json
import os
import locale
from datetime import datetime

class PraiseBoard:
    def __init__(self, root):
        self.root = root
        self.root.title('班级表扬榜')
        self.root.configure(bg='#87CEED')
        
        # 全屏状态变量
        self.fullscreen = False
        
        # 初始化首选项
        self.preferences = self.load_preferences()
        
        # 应用语言设置
        self.current_language = self.preferences.get('language', 'zh_CN')
        self.translations = self.load_translations(self.current_language)
        
        # 创建菜单栏
        self.create_menu()
        
        # 模式状态变量
        self.mode = tk.StringVar(value='praise')
        self.mode.trace('w', self.mark_modified)  # 跟踪模式变化
        self.students = {}
        self.current_file = None  # 当前文件路径
        self.modified = False  # 跟踪数据是否已修改
        
        # 模式选择控件
        # 创建标题框架
        title_frame = tk.Frame(root, bg='#87CEED')
        title_frame.pack(fill='x', padx=20, pady=10)

        # 模式选择控件
        mode_frame = tk.Frame(title_frame, bg='#87CEED')
        mode_frame.pack(side='left', pady=10)

        # 学科下拉菜单
        self.subject_combo = ttk.Combobox(
            title_frame,
            values=['语文','数学','英语','物理','化学','政治','历史','地理','生物','请输入文本','广告位招租'],
            font=('黑体', 30,'bold'),
            state='readonly',
            width=10
        )
        self.subject_combo.pack(side='left', padx=20)
        self.subject_combo.bind('<<ComboboxSelected>>', lambda e: self.mark_modified())
        
        tk.Radiobutton(mode_frame, text='✓', variable=self.mode, value='praise',
                      font=('宋体', 18), bg='#87CEED',fg='green').pack(side='left', padx=20)
        tk.Radiobutton(mode_frame, text='✗', variable=self.mode, value='criticism',
                      font=('宋体', 18), bg='#87CEED',fg='red').pack(side='left', padx=20)

        main_frame = tk.Frame(root, bg='#87CEED')
        main_frame.pack(padx=20, pady=20, fill='both', expand=True)

        # 创建两行分组框架
        row1_frame = tk.Frame(main_frame, bg='#87CEED')
        row1_frame.pack(fill='x')
        row2_frame = tk.Frame(main_frame, bg='#87CEED')
        row2_frame.pack(fill='x')
        
        # 创建6列分组框架（每行6组）
        group_frames = []
        for row_num in range(2):
            for col_num in range(6):
                group_frame = tk.Frame(row1_frame if row_num == 0 else row2_frame, bg='#87CEED')
                group_frame.grid(row=0, column=col_num, padx=10, sticky='nsew', pady=(0, 10))
                if row_num == 0:
                    row1_frame.grid_columnconfigure(col_num, weight=1)
                else:
                    row2_frame.grid_columnconfigure(col_num, weight=1)
                
                # 计算组号（第一行：1-6组；第二行：7-12组）
                group_num = row_num * 6 + col_num + 1
                group_title = f'第{group_num}组'
                tk.Label(group_frame, 
                        text=group_title,
                        font=('黑体', 30, 'bold'),
                        bg='#87CEED',
                        pady=10).pack(side='bottom', anchor='s', fill='x')
                
                # 创建组内学生容器（后打包填充上方空间）
                student_container = tk.Frame(group_frame, bg='#87CEED')
                student_container.pack(fill='both', expand=True)
                
                group_frames.append((group_frame, student_container))
            
        # 从文件按分组读取学生姓名
        with open('students_name.txt', 'r', encoding='utf-8') as f:
            all_students = [name.strip() for name in f.readlines()]
            groups = [all_students[i*4:(i+1)*4] for i in range(12)]  # 12组，每组4人

        # 动态生成学生标签
        for group_idx, group_students in enumerate(groups):
            group_frame, student_container = group_frames[group_idx]
            
            for student_idx, student_name in enumerate(group_students):
                # 创建学生条目容器
                container = tk.Frame(student_container, bg='#87CEED')
                container.pack(fill='x', pady=2)
            
                # 学生姓名标签
                lbl = tk.Label(container,
                            text=student_name,
                            font=('楷体', 30),
                            padx=10,
                            pady=10,
                            relief='ridge')
                lbl.pack(side='left')
                lbl.bind('<Button-1>', functools.partial(self.toggle_check, student_name))
                
                # 对勾标签
                check_label = tk.Label(container,
                                      text='',
                                      font=('Arial', 30),
                                      fg='green',
                                      padx=10,
                                      bg='#87CEED')
                check_label.pack(side='left', padx=5)
                
                # 初始化状态存储
                self.students[student_name] = {
                    'praise': tk.BooleanVar(value=False),
                    'criticism': tk.BooleanVar(value=False),
                    'check_label': check_label,
                }
                # 跟踪学生状态变化
                self.students[student_name]['praise'].trace('w', self.mark_modified)
                self.students[student_name]['criticism'].trace('w', self.mark_modified)
        
        # 时间显示标签
        self.time_label = tk.Label(title_frame,
                                text=self.translations.get('class_display_board', '班级实时表现公示栏'),
                                font=('黑体', 30, 'bold'),
                                bg='#87CEED',
                                padx=20,
                                pady=15)
        self.time_label.pack(side='left', expand=True, fill='x')
        self.time_label.pack(side='right', padx=20)
        self.update_time()
        
        # 绑定退出事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_preferences(self):
        """加载首选项设置"""
        preferences_file = 'preferences.json'
        default_preferences = {
            'language': 'zh_CN',
            'date_format': '年月日',
            'time_format': '时分秒'
        }
        
        if os.path.exists(preferences_file):
            try:
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 如果文件不存在或读取失败，使用默认设置并保存
        self.save_preferences(default_preferences)
        return default_preferences

    def save_preferences(self, preferences=None):
        """保存首选项设置"""
        if preferences is None:
            preferences = self.preferences
            
        try:
            with open('preferences.json', 'w', encoding='utf-8') as f:
                json.dump(preferences, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def load_translations(self, lang_code):
        """加载语言翻译文件"""
        lang_file = f'locales/{lang_code}.json'
        default_translations = {
            'class_display_board': '班级实时表现公示栏',
            'file': '文件',
            'save': '保存',
            'save_as': '另存为',
            'open': '打开',
            'preferences': '首选项',
            'fullscreen': '全屏',
            'exit': '退出',
            'language': '语言',
            'date_format': '日期格式',
            'time_format': '时间格式',
            'save_success': '数据已成功保存！',
            'save_error': '保存数据时出错: ',
            'load_success': '数据已成功加载！',
            'load_error': '加载数据时出错: ',
            'save_changes': '保存更改',
            'save_before_exit': '是否保存更改后再退出？',
            'save_before_load': '是否保存当前更改？'
        }
        
        # 如果语言文件存在，加载它
        if os.path.exists(lang_file):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    # 确保所有必要的键都存在
                    for key in default_translations:
                        if key not in translations:
                            translations[key] = default_translations[key]
                    return translations
            except:
                pass
        
        # 如果文件不存在或读取失败，返回默认翻译
        return default_translations

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.translations.get('file', '文件'), menu=file_menu)
        file_menu.add_command(label=self.translations.get('save', '保存'), command=self.save_data, accelerator="Ctrl+S")
        file_menu.add_command(label=self.translations.get('save_as', '另存为'), command=self.save_as_data, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label=self.translations.get('open', '打开'), command=self.load_data, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label=self.translations.get('preferences', '首选项'), command=self.show_preferences)
        file_menu.add_separator()
        file_menu.add_command(label=self.translations.get('fullscreen', '全屏'), command=self.toggle_fullscreen, accelerator="Alt+Enter")
        file_menu.add_separator()
        file_menu.add_command(label=self.translations.get('exit', '退出'), command=self.on_closing, accelerator="Ctrl+Q")
        
        # 绑定快捷键
        self.root.bind('<Alt-Return>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Alt-KP_Enter>', lambda e: self.toggle_fullscreen())  # 小键盘的Enter键
        self.root.bind('<Control-s>', lambda e: self.save_data())
        self.root.bind('<Control-S>', lambda e: self.save_data())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_as_data())
        self.root.bind('<Control-Shift-s>', lambda e: self.save_as_data())
        self.root.bind('<Control-o>', lambda e: self.load_data())
        self.root.bind('<Control-O>', lambda e: self.load_data())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-Q>', lambda e: self.on_closing())

    def show_preferences(self):
        """显示首选项对话框"""
        prefs_window = tk.Toplevel(self.root)
        prefs_window.title(self.translations.get('preferences', '首选项'))
        prefs_window.geometry('400x300')
        prefs_window.resizable(False, False)
        prefs_window.transient(self.root)
        prefs_window.grab_set()
        
        # 语言设置
        lang_label = tk.Label(prefs_window, text=self.translations.get('language', '语言'), font=('宋体', 12))
        lang_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')
        
        lang_var = tk.StringVar(value=self.preferences.get('language', 'zh_CN'))
        lang_combo = ttk.Combobox(
            prefs_window,
            textvariable=lang_var,
            values=[
                'zh_CN (中文简体)',
                'zh_TW (中文繁體)',
                'en_US (English US)',
                'en_UK (English UK)'
            ],
            state='readonly',
            width=20
        )
        lang_combo.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        # 日期格式设置
        date_label = tk.Label(prefs_window, text=self.translations.get('date_format', '日期格式'), font=('宋体', 12))
        date_label.grid(row=1, column=0, padx=10, pady=10, sticky='w')
        
        date_var = tk.StringVar(value=self.preferences.get('date_format', '年月日'))
        date_combo = ttk.Combobox(
            prefs_window,
            textvariable=date_var,
            values=['年月日', '月日年', '日月年'],
            state='readonly',
            width=20
        )
        date_combo.grid(row=1, column=1, padx=10, pady=10, sticky='w')
        
        # 时间格式设置
        time_label = tk.Label(prefs_window, text=self.translations.get('time_format', '时间格式'), font=('宋体', 12))
        time_label.grid(row=2, column=0, padx=10, pady=10, sticky='w')
        
        time_var = tk.StringVar(value=self.preferences.get('time_format', '时分秒'))
        time_combo = ttk.Combobox(
            prefs_window,
            textvariable=time_var,
            values=['时分秒', '时分'],
            state='readonly',
            width=20
        )
        time_combo.grid(row=2, column=1, padx=10, pady=10, sticky='w')
        
        # 确定和取消按钮
        button_frame = tk.Frame(prefs_window)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        def apply_preferences():
            # 提取语言代码
            lang_code = lang_var.get().split(' ')[0]
            
            # 更新首选项
            self.preferences = {
                'language': lang_code,
                'date_format': date_var.get(),
                'time_format': time_var.get()
            }
            
            # 保存首选项
            self.save_preferences()
            
            # 重新加载语言
            self.current_language = lang_code
            self.translations = self.load_translations(lang_code)
            
            # 更新界面
            self.update_ui_language()
            
            prefs_window.destroy()
            messagebox.showinfo("成功", "首选项已更新，部分更改可能需要重启程序生效")
        
        ok_button = tk.Button(button_frame, text="确定", command=apply_preferences, width=10)
        ok_button.pack(side='left', padx=10)
        
        cancel_button = tk.Button(button_frame, text="取消", command=prefs_window.destroy, width=10)
        cancel_button.pack(side='left', padx=10)

    def update_ui_language(self):
        """更新UI语言"""
        # 更新窗口标题
        title = self.translations.get('class_display_board', '班级表扬榜')
        if self.current_file:
            title += f' - {os.path.basename(self.current_file)}'
        if self.modified:
            title += ' *'
        self.root.title(title)
        
        # 更新时间显示标签
        self.time_label.config(text=self.translations.get('class_display_board', '班级实时表现公示栏'))
        
        # 注意：菜单项的语言更新需要重新创建菜单，这里暂时不实现
        # 因为Tkinter的菜单项不支持动态更新文本

    def mark_modified(self, *args):
        """标记数据已修改"""
        self.modified = True
        # 更新窗口标题显示修改状态
        title = self.translations.get('class_display_board', '班级表扬榜')
        if self.current_file:
            title += f' - {os.path.basename(self.current_file)}'
        if self.modified:
            title += ' *'
        self.root.title(title)

    def unmark_modified(self):
        """标记数据未修改"""
        self.modified = False
        # 更新窗口标题
        title = self.translations.get('class_display_board', '班级表扬榜')
        if self.current_file:
            title += f' - {os.path.basename(self.current_file)}'
        self.root.title(title)

    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)
        
        # 如果退出全屏，恢复窗口大小和位置
        if not self.fullscreen:
            self.root.geometry('1024x768')  # 恢复默认大小
            self.root.eval('tk::PlaceWindow . center')  # 居中显示

    def save_data(self):
        """保存数据到文件"""
        if self.current_file:
            # 如果已经有当前文件，直接保存
            if self._save_to_file(self.current_file):
                self.unmark_modified()
                return True
        else:
            # 否则调用另存为
            return self.save_as_data()
        return False

    def save_as_data(self):
        """另存为数据到文件"""
        # 获取文件保存路径
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="保存表扬榜数据"
        )
        
        if file_path:
            if self._save_to_file(file_path):
                self.current_file = file_path
                self.unmark_modified()
                return True
        return False

    def _save_to_file(self, file_path):
        """内部保存方法"""
        try:
            # 准备保存的数据
            data_to_save = {
                'subject': self.subject_combo.get(),
                'mode': self.mode.get(),
                'students': {}
            }
            
            # 收集学生状态
            for student, state in self.students.items():
                data_to_save['students'][student] = {
                    'praise': state['praise'].get(),
                    'criticism': state['criticism'].get()
                }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
                
            messagebox.showinfo("成功", self.translations.get('save_success', '数据已成功保存！'))
            return True
            
        except Exception as e:
            messagebox.showerror("错误", self.translations.get('save_error', '保存数据时出错: ') + str(e))
            return False

    def load_data(self):
        """从文件加载数据"""
        # 检查是否有未保存的更改
        if self.modified:
            response = messagebox.askyesnocancel(
                self.translations.get('save_changes', '保存更改'),
                self.translations.get('save_before_load', '是否保存当前更改？')
            )
            if response is None:  # 取消
                return
            elif response:  # 是
                if not self.save_data():
                    return  # 如果保存失败，不继续加载
        
        # 获取文件打开路径
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="打开表扬榜数据"
        )
        
        if not file_path or not os.path.exists(file_path):
            return
            
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复学科和模式
            if 'subject' in data:
                self.subject_combo.set(data['subject'])
            
            if 'mode' in data:
                self.mode.set(data['mode'])
            
            # 恢复学生状态
            if 'students' in data:
                for student, state in data['students'].items():
                    if student in self.students:
                        self.students[student]['praise'].set(state.get('praise', False))
                        self.students[student]['criticism'].set(state.get('criticism', False))
                        
                        # 更新显示
                        self.update_check_display(student)
            
            self.current_file = file_path
            self.unmark_modified()
            messagebox.showinfo("成功", self.translations.get('load_success', '数据已成功加载！'))
            
        except Exception as e:
            messagebox.showerror("错误", self.translations.get('load_error', '加载数据时出错: ') + str(e))

    def on_closing(self):
        """窗口关闭事件处理"""
        # 检查是否有未保存的更改
        if self.modified:
            response = messagebox.askyesnocancel(
                self.translations.get('save_changes', '保存更改'),
                self.translations.get('save_before_exit', '是否保存更改后再退出？')
            )
            if response is None:  # 取消
                return
            elif response:  # 是
                if not self.save_data():
                    return  # 如果保存失败，不退出
        
        self.root.quit()

    def update_time(self):
        """更新时间显示，根据首选项设置格式"""
        # 获取当前时间
        now = datetime.now()
        
        # 根据日期格式设置格式化日期
        date_format = self.preferences.get('date_format', '年月日')
        if date_format == '年月日':
            date_str = now.strftime('%Y年%m月%d日')
        elif date_format == '月日年':
            date_str = now.strftime('%m月%d日%Y年')
        else:  # 日月年
            date_str = now.strftime('%d日%m月%Y年')
        
        # 根据时间格式设置格式化时间
        time_format = self.preferences.get('time_format', '时分秒')
        if time_format == '时分秒':
            time_str = now.strftime('%H:%M:%S')
        else:  # 时分
            time_str = now.strftime('%H:%M')
        
        # 获取星期几
        weekday_map = {'0': '日', '1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六'}
        weekday = weekday_map[now.strftime('%w')]
        
        # 组合时间字符串
        current_time = f'{date_str} {time_str} 星期{weekday}'
        
        # 更新标签
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def toggle_mode(self):
        # 切换模式时更新所有学生显示
        for student in self.students:
            self.update_check_display(student)

    def toggle_check(self, student, event=None):
        current_mode = self.mode.get()
        current_state = self.students[student][current_mode].get()
        self.students[student][current_mode].set(not current_state)
        
        symbol = '✓' if current_mode == 'praise' else '✗'
        color = 'green' if current_mode == 'praise' else 'red'
        display_text = symbol if not current_state else ''
        self.students[student]['check_label'].config(
            text=display_text,
            fg=color
        )

    def update_check_display(self, student):
        current_mode = self.mode.get()
        state = self.students[student][current_mode].get()
        symbol = '✓' if current_mode == 'praise' else '✗'
        color = 'green' if current_mode == 'praise' else 'red'
        display_text = symbol if state else ''
        self.students[student]['check_label'].config(
            text=display_text,
            fg=color
        )


if __name__ == '__main__':
    # 创建locales目录（如果不存在）
    if not os.path.exists('locales'):
        os.makedirs('locales')
    
    # 创建默认语言文件（如果不存在）
    default_languages = {
        'zh_CN': {
            'class_display_board': '班级实时表现公示栏',
            'file': '文件',
            'save': '保存',
            'save_as': '另存为',
            'open': '打开',
            'preferences': '首选项',
            'fullscreen': '全屏',
            'exit': '退出',
            'language': '语言',
            'date_format': '日期格式',
            'time_format': '时间格式',
            'save_success': '数据已成功保存！',
            'save_error': '保存数据时出错: ',
            'load_success': '数据已成功加载！',
            'load_error': '加载数据时出错: ',
            'save_changes': '保存更改',
            'save_before_exit': '是否保存更改后再退出？',
            'save_before_load': '是否保存当前更改？'
        },
        'zh_TW': {
            'class_display_board': '班級實時表現公示欄',
            'file': '文件',
            'save': '保存',
            'save_as': '另存為',
            'open': '打開',
            'preferences': '首選項',
            'fullscreen': '全螢幕',
            'exit': '退出',
            'language': '語言',
            'date_format': '日期格式',
            'time_format': '時間格式',
            'save_success': '資料已成功保存！',
            'save_error': '保存資料時出錯: ',
            'load_success': '資料已成功載入！',
            'load_error': '載入資料時出錯: ',
            'save_changes': '保存更改',
            'save_before_exit': '是否保存更改後再退出？',
            'save_before_load': '是否保存當前更改？'
        },
        'en_US': {
            'class_display_board': 'Class Performance Board',
            'file': 'File',
            'save': 'Save',
            'save_as': 'Save As',
            'open': 'Open',
            'preferences': 'Preferences',
            'fullscreen': 'Fullscreen',
            'exit': 'Exit',
            'language': 'Language',
            'date_format': 'Date Format',
            'time_format': 'Time Format',
            'save_success': 'Data saved successfully!',
            'save_error': 'Error saving data: ',
            'load_success': 'Data loaded successfully!',
            'load_error': 'Error loading data: ',
            'save_changes': 'Save Changes',
            'save_before_exit': 'Save changes before exiting?',
            'save_before_load': 'Save current changes?'
        },
        'en_UK': {
            'class_display_board': 'Class Performance Board',
            'file': 'File',
            'save': 'Save',
            'save_as': 'Save As',
            'open': 'Open',
            'preferences': 'Preferences',
            'fullscreen': 'Fullscreen',
            'exit': 'Exit',
            'language': 'Language',
            'date_format': 'Date Format',
            'time_format': 'Time Format',
            'save_success': 'Data saved successfully!',
            'save_error': 'Error saving data: ',
            'load_success': 'Data loaded successfully!',
            'load_error': 'Error loading data: ',
            'save_changes': 'Save Changes',
            'save_before_exit': 'Save changes before exiting?',
            'save_before_load': 'Save current changes?'
        }
    }
    
    # 保存语言文件
    for lang_code, translations in default_languages.items():
        lang_file = f'locales/{lang_code}.json'
        if not os.path.exists(lang_file):
            try:
                with open(lang_file, 'w', encoding='utf-8') as f:
                    json.dump(translations, f, ensure_ascii=False, indent=4)
            except:
                pass
    
    root = tk.Tk()
    app = PraiseBoard(root)
    root.mainloop()