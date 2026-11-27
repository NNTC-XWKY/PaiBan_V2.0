# -*- coding: utf-8 -*-
"""
餐饮/酒店智能排班管理系统
Windows 桌面版；Python 3.10+；仅使用标准库。
"""
import csv, json, random, sys, os
from datetime import date, datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# 打包为 EXE 后，数据文件保存在 EXE 同目录，避免写入临时解压目录
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "schedule_data.json")

DEFAULT_SHIFTS = [
    {"name": "早班", "start": "07:00", "end": "15:00", "mode": "两班/三班通用", "min": 2, "max": 8},
    {"name": "中班", "start": "15:00", "end": "23:00", "mode": "三班制", "min": 2, "max": 8},
    {"name": "夜班", "start": "23:00", "end": "07:00", "mode": "两班/三班通用", "min": 2, "max": 8},
]
DEFAULT_DATA = {"employees": [], "shifts": DEFAULT_SHIFTS, "assignments": [], "settings": {"rest_hours": 11}}

class RosterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("排班管家")
        self.root.geometry("1360x820")
        self.root.minsize(760, 540)
        self.root.configure(bg="#F3F5F8")
        self.data = self.load_data()
        self.build_ui()
        self.refresh_all()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                for k, v in DEFAULT_DATA.items():
                    d.setdefault(k, v)
                return d
            except Exception:
                pass
        return json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def build_ui(self):
        # C 方案：左侧导航 + 右侧内容区。每个页面均可纵向滚动。
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        header = ttk.Frame(self.root, style="AppHeader.TFrame", padding=(20, 12))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(header, text="排班管家", style="AppHeaderTitle.TLabel").pack(side="left")
        ttk.Label(header, text="餐饮 / 酒店人员排班与工时管理", style="AppHeaderSub.TLabel").pack(side="left", padx=(18, 0))
        self.sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", padding=(12, 18))
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.configure(width=188)
        ttk.Label(self.sidebar, text="工作台", style="SidebarCaption.TLabel").pack(anchor="w", padx=10, pady=(0, 12))
        self.content = ttk.Frame(self.root, style="Content.TFrame", padding=12)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1); self.content.grid_columnconfigure(0, weight=1)
        self.pages = {}; self.nav_buttons = {}
        page_specs = [("roster", "排班总览"), ("staff", "员工管理"), ("shifts", "班次设置"), ("stats", "工时统计")]
        for key, label in page_specs:
            btn = ttk.Button(self.sidebar, text=label, style="Nav.TButton", command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", pady=4); self.nav_buttons[key] = btn
            outer = ttk.Frame(self.content, style="Content.TFrame")
            canvas = tk.Canvas(outer, bg="#F3F5F8", highlightthickness=0)
            vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vbar.set)
            inner = ttk.Frame(canvas, style="Content.TFrame", padding=(4, 4, 8, 12))
            window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.bind("<Configure>", lambda e, c=canvas, w=window_id: c.itemconfigure(w, width=e.width))
            canvas.grid(row=0, column=0, sticky="nsew"); vbar.grid(row=0, column=1, sticky="ns")
            outer.grid_rowconfigure(0, weight=1); outer.grid_columnconfigure(0, weight=1)
            self.pages[key] = (outer, inner, canvas)
        self.roster_tab = self.pages["roster"][1]; self.staff_tab = self.pages["staff"][1]
        self.shift_tab = self.pages["shifts"][1]; self.stats_tab = self.pages["stats"][1]
        self.build_roster(); self.build_staff(); self.build_shifts(); self.build_stats()
        self.show_page("roster")

    def show_page(self, key):
        for page_key, (outer, _, _) in self.pages.items():
            outer.grid_forget(); self.nav_buttons[page_key].configure(style="Nav.TButton")
        self.pages[key][0].grid(row=0, column=0, sticky="nsew")
        self.nav_buttons[key].configure(style="NavActive.TButton")

    def make_tree(self, parent, columns, headings, widths, height=14, stretch_cols=()):
        """带横向/纵向滚动条的数据表格，窄窗口下可滚动查看全部列。"""
        wrap = ttk.Frame(parent, style="Panel.TFrame", padding=6)
        wrap.pack(fill="both", expand=True, pady=(6, 0))
        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=65, anchor="center", stretch=(col in stretch_cols))
        ybar = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky="nsew"); ybar.grid(row=0, column=1, sticky="ns"); xbar.grid(row=1, column=0, sticky="ew")
        wrap.grid_rowconfigure(0, weight=1); wrap.grid_columnconfigure(0, weight=1)
        tree.tag_configure("even", background="#F0F5FA", foreground="#26364A")
        tree.tag_configure("odd", background="#FFFFFF", foreground="#26364A")
        return tree

    def build_roster(self):
        ttk.Label(self.roster_tab, text="排班总览", style="PageTitle.TLabel").pack(anchor="w", pady=(0, 3))
        ttk.Label(self.roster_tab, text="查看每日班次、员工工时及同班人员；双击记录可手动调整。", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        controls = ttk.LabelFrame(self.roster_tab, text="排班操作", padding=10); controls.pack(fill="x", pady=(0, 8))
        self.start_var = tk.StringVar(value=date.today().isoformat()); self.days_var = tk.StringVar(value="7"); self.mode_var = tk.StringVar(value="三班倒")
        fields = ttk.Frame(controls, style="Panel.TFrame"); fields.pack(fill="x")
        ttk.Label(fields, text="开始日期").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(fields, textvariable=self.start_var, width=13).grid(row=0, column=1, sticky="w", padx=(0, 14), pady=4)
        ttk.Label(fields, text="排班天数").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        ttk.Combobox(fields, textvariable=self.days_var, values=["7", "14", "28", "30", "31"], width=6, state="readonly").grid(row=0, column=3, sticky="w", padx=(0, 14), pady=4)
        ttk.Label(fields, text="排班模式").grid(row=0, column=4, sticky="w", padx=(0, 6), pady=4)
        ttk.Combobox(fields, textvariable=self.mode_var, values=["两班倒", "三班倒"], width=9, state="readonly").grid(row=0, column=5, sticky="w", pady=4)
        actions = ttk.Frame(controls, style="Panel.TFrame"); actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="自动生成排班", style="Primary.TButton", command=self.auto_schedule).pack(side="left", padx=(0, 6), pady=3)
        ttk.Button(actions, text="手动调整选中项", command=self.edit_assignment).pack(side="left", padx=6, pady=3)
        ttk.Button(actions, text="删除选中项", command=self.delete_assignment).pack(side="left", padx=6, pady=3)
        ttk.Button(actions, text="导出完整排班表 CSV", style="Success.TButton", command=self.export_csv).pack(side="left", padx=6, pady=3)
        cols = ("date", "weekday", "shift", "time", "shift_hours", "employee", "role", "other_staff", "month_hours")
        headings = ("日期", "星期", "班次", "上班时间", "本班工时(h)", "员工", "岗位", "其他值班员工", "员工当月累计(h)")
        widths = (108, 68, 92, 112, 112, 125, 105, 280, 155)
        self.roster = self.make_tree(self.roster_tab, cols, headings, widths, height=16, stretch_cols=("other_staff",))
        self.roster.bind("<Double-1>", lambda e: self.edit_assignment())

    def build_staff(self):
        ttk.Label(self.staff_tab, text="员工管理", style="PageTitle.TLabel").pack(anchor="w", pady=(0, 3))
        ttk.Label(self.staff_tab, text="维护员工姓名、岗位、用工类型及在职状态。", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        form = ttk.LabelFrame(self.staff_tab, text="新增 / 编辑员工", padding=10); form.pack(fill="x", pady=(0, 8))
        self.staff_name=tk.StringVar(); self.staff_role=tk.StringVar(value="服务员"); self.staff_type=tk.StringVar(value="全职"); self.staff_active=tk.BooleanVar(value=True)
        fields=ttk.Frame(form,style="Panel.TFrame");fields.pack(fill="x")
        for i,(label,var,width) in enumerate([("姓名",self.staff_name,14),("岗位",self.staff_role,14),("用工类型",self.staff_type,12)]):
            ttk.Label(fields,text=label).grid(row=0,column=i*2,sticky="w",padx=(0,5),pady=4)
            ttk.Entry(fields,textvariable=var,width=width).grid(row=0,column=i*2+1,sticky="w",padx=(0,12),pady=4)
        ttk.Checkbutton(fields,text="在职",variable=self.staff_active).grid(row=0,column=6,sticky="w",padx=5)
        actions=ttk.Frame(form,style="Panel.TFrame");actions.pack(fill="x",pady=(8,0))
        ttk.Button(actions,text="添加员工",style="Primary.TButton",command=self.add_employee).pack(side="left",padx=(0,6))
        ttk.Button(actions,text="更新选中员工",command=self.update_employee).pack(side="left",padx=6)
        ttk.Button(actions,text="删除选中员工",style="Danger.TButton",command=self.delete_employee).pack(side="left",padx=6)
        self.staff_tree=self.make_tree(self.staff_tab,("name","role","type","active"),("姓名","岗位","用工类型","状态"),(180,180,150,110),height=16)
        self.staff_tree.bind("<<TreeviewSelect>>",self.on_staff_select)

    def build_shifts(self):
        ttk.Label(self.shift_tab,text="班次设置",style="PageTitle.TLabel").pack(anchor="w",pady=(0,3))
        ttk.Label(self.shift_tab,text="按门店实际情况设置班次时间及每班最低 / 最高人数。两班倒默认使用早班、夜班；三班倒使用前三个班次。",style="Muted.TLabel",wraplength=850).pack(anchor="w",pady=(0,10))
        self.shift_tree=self.make_tree(self.shift_tab,("name","start","end","min","max"),("班次名称","开始时间","结束时间","最低人数","最高人数"),(180,150,150,120,120),height=9)
        form=ttk.LabelFrame(self.shift_tab,text="新增 / 编辑班次",padding=10);form.pack(fill="x",pady=10)
        self.sh_name=tk.StringVar();self.sh_start=tk.StringVar();self.sh_end=tk.StringVar();self.sh_min=tk.StringVar(value="2");self.sh_max=tk.StringVar(value="8")
        fields=ttk.Frame(form,style="Panel.TFrame");fields.pack(fill="x")
        for i,(label,var,width) in enumerate([("名称",self.sh_name,12),("开始时间",self.sh_start,9),("结束时间",self.sh_end,9),("最低人数",self.sh_min,5),("最高人数",self.sh_max,5)]):
            ttk.Label(fields,text=label).grid(row=0,column=i*2,sticky="w",padx=(0,5),pady=4)
            ttk.Entry(fields,textvariable=var,width=width).grid(row=0,column=i*2+1,sticky="w",padx=(0,12),pady=4)
        actions=ttk.Frame(form,style="Panel.TFrame");actions.pack(fill="x",pady=(8,0))
        ttk.Button(actions,text="新增班次",style="Primary.TButton",command=self.add_shift).pack(side="left",padx=(0,6))
        ttk.Button(actions,text="更新选中班次",command=self.update_shift).pack(side="left",padx=6)
        ttk.Button(actions,text="删除选中班次",style="Danger.TButton",command=self.delete_shift).pack(side="left",padx=6)
        self.shift_tree.bind("<<TreeviewSelect>>",self.on_shift_select)

    def build_stats(self):
        ttk.Label(self.stats_tab,text="工时统计",style="PageTitle.TLabel").pack(anchor="w",pady=(0,3))
        ttk.Label(self.stats_tab,text="按自然月统计员工排班工时、班次数及与平均工时的差值。",style="Muted.TLabel").pack(anchor="w",pady=(0,10))
        bar=ttk.LabelFrame(self.stats_tab,text="统计条件",padding=10);bar.pack(fill="x",pady=(0,8))
        self.stats_month=tk.StringVar(value=date.today().strftime("%Y-%m"))
        ttk.Label(bar,text="统计月份 (YYYY-MM)：").pack(side="left")
        ttk.Entry(bar,textvariable=self.stats_month,width=10).pack(side="left",padx=8)
        ttk.Button(bar,text="刷新统计",style="Primary.TButton",command=self.refresh_stats).pack(side="left")
        self.stats_summary=ttk.Label(self.stats_tab,text="按自然月汇总排班工时",style="Summary.TLabel");self.stats_summary.pack(anchor="w",pady=(0,8))
        self.stats_tree=self.make_tree(self.stats_tab,("name","role","hours","shifts","difference"),("员工","岗位","月工时(h)","班次数","与平均工时差(h)"),(180,160,140,120,180),height=16)

    @staticmethod
    def shift_duration(time_text):
        try:
            start_text, end_text = time_text.split("-", 1)
            start = datetime.strptime(start_text, "%H:%M")
            end = datetime.strptime(end_text, "%H:%M")
            if end <= start:
                end += timedelta(days=1)
            return (end - start).total_seconds() / 3600
        except Exception:
            return 0.0

    def refresh_stats(self):
        if not hasattr(self, "stats_tree"):
            return
        month = self.stats_month.get().strip()
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            self.stats_summary.config(text="月份格式错误，请使用 YYYY-MM，例如 2026-11")
            return
        totals = {e["id"]: 0.0 for e in self.data["employees"]}
        counts = {e["id"]: 0 for e in self.data["employees"]}
        for a in self.data["assignments"]:
            if str(a.get("date", "")).startswith(month) and a.get("employee_id") in totals:
                totals[a["employee_id"]] += self.shift_duration(a.get("time", ""))
                counts[a["employee_id"]] += 1
        active_ids = [e["id"] for e in self.data["employees"] if e.get("active")]
        average = sum(totals[i] for i in active_ids) / len(active_ids) if active_ids else 0
        self.stats_tree.delete(*self.stats_tree.get_children())
        emap = {e["id"]: e for e in self.data["employees"]}
        for e in sorted(self.data["employees"], key=lambda x: x.get("name", "")):
            hours = totals[e["id"]]
            diff = hours - average if e.get("active") else 0
            self.stats_tree.insert("", "end", iid=e["id"], values=(e.get("name", ""), e.get("role", ""), f"{hours:.1f}", counts[e["id"]], f"{diff:+.1f}"))
        self.stats_summary.config(text=f"{month}：在职员工 {len(active_ids)} 人｜总工时 {sum(totals.values()):.1f} 小时｜在职员工平均 {average:.1f} 小时")

    def refresh_all(self):
        self.refresh_staff(); self.refresh_shifts(); self.refresh_roster(); self.refresh_stats()

    def refresh_staff(self):
        self.staff_tree.delete(*self.staff_tree.get_children())
        for e in self.data["employees"]:
            self.staff_tree.insert("", "end", iid=e["id"], values=(e["name"],e["role"],e["type"],"在职" if e["active"] else "停用"))

    def refresh_shifts(self):
        self.shift_tree.delete(*self.shift_tree.get_children())
        for s in self.data["shifts"]:
            self.shift_tree.insert("", "end", iid=s["name"], values=(s["name"],s["start"],s["end"],s["min"],s["max"]))

    def refresh_roster(self):
        self.roster.delete(*self.roster.get_children())
        emap = {e["id"]: e for e in self.data["employees"]}
        ordered = sorted(self.data["assignments"], key=lambda x: (x.get("date", ""), x.get("shift", ""), x.get("employee_id", "")))
        # 按员工和自然月累计工时；跨月排班分别计入对应月份
        month_totals = {}
        for a in ordered:
            key = (a.get("employee_id"), str(a.get("date", ""))[:7])
            month_totals[key] = month_totals.get(key, 0.0) + self.shift_duration(a.get("time", ""))
        # 建立“日期 + 班次”分组，当前行显示同班其他员工姓名
        shift_groups = {}
        for item in ordered:
            group_key = (item.get("date", ""), item.get("shift", ""))
            shift_groups.setdefault(group_key, []).append(item.get("employee_id"))
        for i, a in enumerate(ordered):
            e = emap.get(a.get("employee_id"), {})
            try:
                wd = ["周一","周二","周三","周四","周五","周六","周日"][date.fromisoformat(a["date"]).weekday()]
            except Exception:
                wd = ""
            hours = self.shift_duration(a.get("time", ""))
            month = str(a.get("date", ""))[:7]
            month_hours = month_totals.get((a.get("employee_id"), month), 0.0)
            peers = []
            for peer_id in shift_groups.get((a.get("date", ""), a.get("shift", "")), []):
                if peer_id != a.get("employee_id"):
                    peer = emap.get(peer_id, {})
                    peer_name = peer.get("name", "[员工已删除]")
                    if peer_name not in peers:
                        peers.append(peer_name)
            other_staff = "、".join(peers) if peers else "—"
            values = (a.get("date", ""), wd, a.get("shift", ""), a.get("time", ""), f"{hours:.1f}", e.get("name", "[员工已删除]"), e.get("role", ""), other_staff, f"{month_hours:.1f}")
            self.roster.insert("", "end", iid=str(i), values=values, tags=("even" if i % 2 == 0 else "odd",))

    def add_employee(self):
        name=self.staff_name.get().strip()
        if not name: messagebox.showwarning("提示","请输入员工姓名"); return
        if any(e["name"]==name for e in self.data["employees"]): messagebox.showwarning("提示","员工姓名已存在"); return
        self.data["employees"].append({"id":str(int(datetime.now().timestamp()*1000000)),"name":name,"role":self.staff_role.get().strip() or "未设置","type":self.staff_type.get().strip() or "全职","active":self.staff_active.get()})
        self.save(); self.refresh_all(); self.staff_name.set("")

    def selected_staff(self):
        sel=self.staff_tree.selection()
        if not sel: return None
        return next((e for e in self.data["employees"] if e["id"]==sel[0]),None)

    def on_staff_select(self,_=None):
        e=self.selected_staff()
        if e:
            self.staff_name.set(e["name"]); self.staff_role.set(e["role"]); self.staff_type.set(e["type"]); self.staff_active.set(e["active"])

    def update_employee(self):
        e=self.selected_staff()
        if not e: messagebox.showinfo("提示","请先选择员工"); return
        name=self.staff_name.get().strip()
        if not name: messagebox.showwarning("提示","姓名不能为空"); return
        e.update(name=name,role=self.staff_role.get().strip(),type=self.staff_type.get().strip(),active=self.staff_active.get())
        self.save(); self.refresh_all()

    def delete_employee(self):
        e=self.selected_staff()
        if not e: return
        if messagebox.askyesno("确认",f"删除员工 {e['name']}？历史排班记录会保留。"):
            self.data["employees"].remove(e); self.save(); self.refresh_all()

    def selected_shift(self):
        sel=self.shift_tree.selection()
        if not sel:return None
        return next((s for s in self.data["shifts"] if s["name"]==sel[0]),None)

    def on_shift_select(self,_=None):
        s=self.selected_shift()
        if s:
            self.sh_name.set(s["name"]);self.sh_start.set(s["start"]);self.sh_end.set(s["end"]);self.sh_min.set(str(s["min"]));self.sh_max.set(str(s["max"]))

    def add_shift(self):
        try:
            s={"name":self.sh_name.get().strip(),"start":self.sh_start.get().strip(),"end":self.sh_end.get().strip(),"min":int(self.sh_min.get()),"max":int(self.sh_max.get())}
            datetime.strptime(s["start"],"%H:%M");datetime.strptime(s["end"],"%H:%M")
            if not s["name"] or s["min"]<0 or s["max"]<s["min"]: raise ValueError()
            if any(x["name"]==s["name"] for x in self.data["shifts"]): raise ValueError()
        except: messagebox.showerror("输入错误","请检查班次名称、时间及人数范围（时间格式 HH:MM）。");return
        self.data["shifts"].append(s);self.save();self.refresh_all()

    def update_shift(self):
        s=self.selected_shift()
        if not s: messagebox.showinfo("提示","请先选择班次");return
        old=s["name"]
        try:
            new={"name":self.sh_name.get().strip(),"start":self.sh_start.get().strip(),"end":self.sh_end.get().strip(),"min":int(self.sh_min.get()),"max":int(self.sh_max.get())}
            datetime.strptime(new["start"],"%H:%M");datetime.strptime(new["end"],"%H:%M")
            if not new["name"] or new["min"]<0 or new["max"]<new["min"]:raise ValueError()
        except:messagebox.showerror("输入错误","请检查班次设置。");return
        s.update(new)
        for a in self.data["assignments"]:
            if a["shift"]==old:
                a["shift"]=new["name"];a["time"]=new["start"]+"-"+new["end"]
        self.save();self.refresh_all()

    def delete_shift(self):
        s=self.selected_shift()
        if not s:return
        if any(a["shift"]==s["name"] for a in self.data["assignments"]):
            messagebox.showwarning("无法删除","该班次已有排班记录，请先删除或调整相关排班。");return
        self.data["shifts"].remove(s);self.save();self.refresh_all()

    def active_shifts(self):
        mode=self.mode_var.get()
        shifts=self.data["shifts"]
        if mode=="两班倒":
            chosen=[s for s in shifts if s["name"] in ("早班","夜班")]
            return chosen if len(chosen)>=2 else shifts[:2]
        return shifts[:3]

    def auto_schedule(self):
        try:
            start=date.fromisoformat(self.start_var.get().strip()); days=int(self.days_var.get())
        except:messagebox.showerror("日期错误","请输入正确开始日期，格式 YYYY-MM-DD。");return
        staff=[e for e in self.data["employees"] if e["active"]]
        if not staff:messagebox.showwarning("缺少员工","请先在员工管理中添加在职员工。");return
        shifts=self.active_shifts()
        if len(shifts)<2:messagebox.showwarning("班次不足","请至少设置两个班次。");return
        if not messagebox.askyesno("确认生成",f"将生成 {start} 起 {days} 天的{self.mode_var.get()}排班，并替换该日期范围内现有排班。继续？"):return
        end=start+timedelta(days=days)
        self.data["assignments"]=[a for a in self.data["assignments"] if not(start.isoformat()<=a["date"]<end.isoformat())]
        # 按自然月累计工时进行均衡；随机性仅用于打破接近的候选人排序
        month_hours = {e["id"]: 0.0 for e in staff}
        month_counts = {e["id"]: 0 for e in staff}
        for old in self.data["assignments"]:
            eid = old.get("employee_id")
            if eid in month_hours and str(old.get("date", "")).startswith(start.strftime("%Y-%m")):
                month_hours[eid] += self.shift_duration(old.get("time", ""))
                month_counts[eid] += 1
        last_end = {}
        for old in self.data["assignments"]:
            eid = old.get("employee_id")
            try:
                od = date.fromisoformat(old["date"])
                ost = datetime.combine(od, datetime.strptime(old["time"].split("-", 1)[0], "%H:%M").time())
                oen = ost + timedelta(hours=self.shift_duration(old["time"]))
                if eid not in last_end or oen > last_end[eid]:
                    last_end[eid] = oen
            except Exception:
                pass
        assignments = []
        rest_hours = int(self.data.get("settings", {}).get("rest_hours", 11))
        for day_i in range(days):
            d = start + timedelta(days=day_i)
            for shift in shifts:
                try:
                    st = datetime.combine(d, datetime.strptime(shift["start"], "%H:%M").time())
                    en = datetime.combine(d, datetime.strptime(shift["end"], "%H:%M").time())
                    if en <= st:
                        en += timedelta(days=1)
                except Exception:
                    continue
                target = min(max(1, int(shift["min"])), max(1, int(shift.get("max", 50))))
                chosen = 0
                while chosen < target:
                    eligible = []
                    for employee in staff:
                        eid = employee["id"]
                        prev = last_end.get(eid)
                        if prev is not None and (st - prev).total_seconds() / 3600 < rest_hours:
                            continue
                        if any(x["employee_id"] == eid and x["date"] == d.isoformat() for x in assignments):
                            continue
                        # 工时优先，其次班次数；微小随机扰动保持中等随机性
                        score = month_hours[eid] + random.uniform(-0.35, 0.35)
                        eligible.append((score, month_counts[eid], random.random(), employee))
                    if not eligible:
                        break
                    eligible.sort(key=lambda item: (item[0], item[1], item[2]))
                    employee = eligible[0][3]
                    eid = employee["id"]
                    assignments.append({"date": d.isoformat(), "shift": shift["name"], "time": shift["start"] + "-" + shift["end"], "employee_id": eid})
                    month_hours[eid] += self.shift_duration(shift["start"] + "-" + shift["end"])
                    month_counts[eid] += 1
                    last_end[eid] = en
                    chosen += 1
        self.data["assignments"].extend(assignments)
        self.save();self.refresh_all()
        messagebox.showinfo("完成",f"已生成 {len(assignments)} 条排班记录。\n如部分班次人数不足，请增加可排员工或调整休息间隔 / 班次最低人数。")

    def edit_assignment(self):
        sel=self.roster.selection()
        if not sel:messagebox.showinfo("提示","请先选择一条排班记录。");return
        idxs=sorted(self.data["assignments"],key=lambda x:(x["date"],x["shift"],x["employee_id"]))
        target=idxs[int(sel[0])]
        old_emp=next((e.get("name", "[员工已删除]") for e in self.data["employees"] if e.get("id")==target.get("employee_id")), "[员工已删除]")
        win=tk.Toplevel(self.root);win.title("手动调整排班");win.resizable(False,False);win.grab_set()
        frm=ttk.Frame(win,padding=16);frm.pack()
        dvar=tk.StringVar(value=target["date"]);svar=tk.StringVar(value=target["shift"])
        emap={e["name"]:e["id"] for e in self.data["employees"]}
        current=next((e["name"] for e in self.data["employees"] if e["id"]==target["employee_id"]),old_emp)
        evar=tk.StringVar(value=current)
        for i,(lab,var) in enumerate([("日期",dvar),("班次",svar),("员工",evar)]):
            ttk.Label(frm,text=lab).grid(row=i,column=0,sticky="w",pady=5)
            values=[s["name"] for s in self.data["shifts"]] if lab=="班次" else (list(emap) if lab=="员工" else None)
            if values:ttk.Combobox(frm,textvariable=var,values=values,state="readonly",width=22).grid(row=i,column=1,pady=5)
            else:ttk.Entry(frm,textvariable=var,width=25).grid(row=i,column=1,pady=5)
        def save_edit():
            try:date.fromisoformat(dvar.get())
            except:messagebox.showerror("日期错误","日期格式应为 YYYY-MM-DD");return
            shift=next((s for s in self.data["shifts"] if s["name"]==svar.get()),None)
            if not shift or evar.get() not in emap:messagebox.showerror("错误","请选择有效班次和员工");return
            target.update(date=dvar.get(),shift=shift["name"],time=shift["start"]+"-"+shift["end"],employee_id=emap[evar.get()])
            self.save();self.refresh_all();win.destroy()
        ttk.Button(frm,text="保存调整",command=save_edit).grid(row=3,column=0,columnspan=2,pady=10)
    def delete_assignment(self):
        sel=self.roster.selection()
        if not sel:return
        idxs=sorted(self.data["assignments"],key=lambda x:(x["date"],x["shift"],x["employee_id"]))
        target=idxs[int(sel[0])]
        if messagebox.askyesno("确认","删除选中的排班记录？"):
            self.data["assignments"].remove(target);self.save();self.refresh_all()

    def export_csv(self):
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV 文件","*.csv")],initialfile="排班管家_完整排班表.csv")
        if not path:return
        emap={e["id"]:e for e in self.data["employees"]}
        ordered=sorted(self.data["assignments"],key=lambda x:(x.get("date", ""),x.get("shift", ""),x.get("employee_id", "")))
        month_totals={};groups={}
        for a in ordered:
            key=(a.get("employee_id"),str(a.get("date", ""))[:7])
            month_totals[key]=month_totals.get(key,0.0)+self.shift_duration(a.get("time", ""))
            groups.setdefault((a.get("date", ""),a.get("shift", "")),[]).append(a.get("employee_id"))
        headers=["日期","星期","班次","上班时间","本班工时(h)","员工","岗位","其他值班员工","员工当月累计(h)"]
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f);w.writerow(headers)
            for a in ordered:
                e=emap.get(a.get("employee_id"),{})
                try: weekday=["周一","周二","周三","周四","周五","周六","周日"][date.fromisoformat(a["date"]).weekday()]
                except Exception: weekday=""
                peers=[]
                for peer_id in groups.get((a.get("date", ""),a.get("shift", "")),[]):
                    if peer_id!=a.get("employee_id"):
                        peer_name=emap.get(peer_id,{}).get("name","[员工已删除]")
                        if peer_name not in peers:peers.append(peer_name)
                month=str(a.get("date", ""))[:7]
                w.writerow([a.get("date", ""),weekday,a.get("shift", ""),a.get("time", ""),f"{self.shift_duration(a.get('time', '')):.1f}",e.get("name","[员工已删除]"),e.get("role",""),"、".join(peers) if peers else "—",f"{month_totals.get((a.get('employee_id'),month),0.0):.1f}"])
        messagebox.showinfo("导出成功",f"已导出排班表界面中的全部 9 列数据：\n{path}")

if __name__ == "__main__":
    root=tk.Tk()
    style = ttk.Style()
    try: style.theme_use("clam")
    except Exception: pass
    style.configure(".", font=("Microsoft YaHei UI", 10), foreground="#26364A")
    style.configure("TFrame", background="#F3F5F8")
    style.configure("Content.TFrame", background="#F3F5F8")
    style.configure("Panel.TFrame", background="#FFFFFF")
    style.configure("AppHeader.TFrame", background="#1B2A40")
    style.configure("AppHeaderTitle.TLabel", background="#1B2A40", foreground="#FFFFFF", font=("Microsoft YaHei UI", 20, "bold"))
    style.configure("AppHeaderSub.TLabel", background="#1B2A40", foreground="#B9C8DA", font=("Microsoft YaHei UI", 10))
    style.configure("Sidebar.TFrame", background="#17243A")
    style.configure("SidebarCaption.TLabel", background="#17243A", foreground="#91A4BC", font=("Microsoft YaHei UI", 10, "bold"))
    style.configure("TLabel", background="#F3F5F8", foreground="#334155")
    style.configure("Muted.TLabel", background="#F3F5F8", foreground="#718096")
    style.configure("PageTitle.TLabel", background="#F3F5F8", foreground="#20334B", font=("Microsoft YaHei UI", 19, "bold"))
    style.configure("Summary.TLabel", background="#E8F0F8", foreground="#245B91", padding=10, font=("Microsoft YaHei UI", 10, "bold"))
    style.configure("TLabelframe", background="#FFFFFF", bordercolor="#DCE4ED", relief="solid")
    style.configure("TLabelframe.Label", background="#FFFFFF", foreground="#203B5A", font=("Microsoft YaHei UI", 10, "bold"))
    style.configure("Treeview", rowheight=31, font=("Microsoft YaHei UI", 10), background="#FFFFFF", fieldbackground="#FFFFFF", bordercolor="#DCE5EF")
    style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"), padding=(8, 9), background="#E8EEF5", foreground="#203B5A")
    style.map("Treeview", background=[("selected", "#D5E6F8")], foreground=[("selected", "#173B63")])
    style.configure("TButton", padding=(9, 7), background="#E8EDF3", foreground="#263B55", bordercolor="#D4DDE7")
    style.map("TButton", background=[("active", "#DCE7F2"), ("pressed", "#CCDCEB")])
    style.configure("Nav.TButton", padding=(12, 11), anchor="w", background="#17243A", foreground="#C4D0DE", borderwidth=0, font=("Microsoft YaHei UI", 10))
    style.map("Nav.TButton", background=[("active", "#243A56")], foreground=[("active", "#FFFFFF")])
    style.configure("NavActive.TButton", padding=(12, 11), anchor="w", background="#2868A8", foreground="#FFFFFF", borderwidth=0, font=("Microsoft YaHei UI", 10, "bold"))
    style.map("NavActive.TButton", background=[("active", "#3279BE")], foreground=[("active", "#FFFFFF")])
    style.configure("Primary.TButton", padding=(10, 8), background="#2868A8", foreground="#FFFFFF", font=("Microsoft YaHei UI", 10, "bold"))
    style.map("Primary.TButton", background=[("active", "#347ABD"), ("pressed", "#1D568F")])
    style.configure("Success.TButton", padding=(10, 8), background="#16866F", foreground="#FFFFFF", font=("Microsoft YaHei UI", 10, "bold"))
    style.map("Success.TButton", background=[("active", "#1B9B80")])
    style.configure("Danger.TButton", padding=(10, 8), foreground="#A33B3B")
    style.configure("TEntry", padding=5); style.configure("TCombobox", padding=5)
    style.configure("TCheckbutton", background="#FFFFFF")
    RosterApp(root)
    root.mainloop()
