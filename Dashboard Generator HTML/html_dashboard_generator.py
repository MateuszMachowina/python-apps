import tkinter as tk
from tkinter import filedialog, colorchooser, ttk, messagebox
import pandas as pd
import plotly.express as px
import webbrowser
import os
from datetime import datetime

class ExcelReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generator Raportów Analitycznych")
        self.root.geometry("850x950")
        
        # Konfiguracja nowoczesnego, ciemnego motywu interfejsu
        self.setup_ui_theme()
        
        self.root.configure(padx=25, pady=25, bg=self.bg_color)

        # Zmienne stanów
        self.file_path = None
        self.df = None
        self.id_column = None
        self.accent_color = "#007ACC" # Profesjonalny niebieski

        # Słownik do przechowywania wybranych metod agregacji
        self.agg_methods = {}
        # Słownik z tłumaczeniami funkcji z polskiego na pandas
        self.agg_dict_pandas = {
            "Suma": "sum",
            "Średnia": "mean",
            "Maksimum": "max",
            "Minimum": "min"
        }

        # Interfejs
        self.create_widgets()

    def setup_ui_theme(self):
        # Kolory interfejsu
        self.bg_color = "#1e1e1e"
        self.fg_color = "#e0e0e0"
        self.btn_bg = "#333333"
        self.btn_active = "#005a9e"
        self.panel_bg = "#252526"
        self.border_color = "#404040"

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Główne style
        self.style.configure(".", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("TButton", padding=8, relief="flat", background=self.btn_bg, font=("Segoe UI", 10, "bold"))
        self.style.map("TButton", background=[('active', self.btn_active)])
        self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), padding=(0, 10, 0, 5))
        
        # Style specjalne dla ramki i etykiet agregacji
        self.style.configure("Panel.TFrame", background=self.panel_bg)
        self.style.configure("Panel.TLabel", background=self.panel_bg, foreground=self.fg_color)
        
        # Pola wyboru (Combobox)
        self.style.configure("TCombobox", fieldbackground=self.panel_bg, background=self.btn_bg, foreground=self.fg_color, borderwidth=0)
        self.style.map("TCombobox", fieldbackground=[('readonly', self.panel_bg)], foreground=[('readonly', self.fg_color)])

        # Fix na biały tekst na jasnym tle w liście rozwijanej Comboboxa
        self.root.option_add('*TCombobox*Listbox.background', self.panel_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', self.fg_color)
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.btn_active)
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')

        # Tabela (Treeview)
        self.style.configure("Treeview", background=self.panel_bg, foreground=self.fg_color, fieldbackground=self.panel_bg, borderwidth=0, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", background=self.btn_bg, foreground=self.fg_color, font=("Segoe UI", 9, "bold"), relief="flat")
        self.style.map("Treeview", background=[('selected', self.btn_active)])
        
        # Scrollbary
        self.style.configure("Vertical.TScrollbar", background=self.btn_bg, borderwidth=0, arrowcolor=self.fg_color)

    def create_widgets(self):

        # Stopka na samym dole aplikacji
        lbl_footer = ttk.Label(self.root, text="Stworzone przez: Mateusz Machowina", font=("Segoe UI", 9), foreground="#777777")
        lbl_footer.pack(side='bottom', pady=(15, 0))

        # 1. Źródło danych
        ttk.Label(self.root, text="Źródło danych", style="Header.TLabel").pack(anchor='w')
        self.btn_load = ttk.Button(self.root, text="Wybierz plik źródłowy (.xlsx)", command=self.load_excel)
        self.btn_load.pack(fill='x', pady=(0, 10))

        self.sheet_frame = ttk.Frame(self.root)
        ttk.Label(self.sheet_frame, text="Arkusz roboczy:").pack(side='left', padx=(0, 10))
        self.sheet_combo = ttk.Combobox(self.sheet_frame, state="readonly")
        self.sheet_combo.pack(side='left', fill='x', expand=True)
        self.sheet_combo.bind("<<ComboboxSelected>>", self.load_sheet_data)

        # 2. Definicja klucza głównego
        ttk.Label(self.root, text="Klucz agregacji (ID)", style="Header.TLabel").pack(anchor='w', pady=(15, 0))
        ttk.Label(self.root, text="Wskaż kolumnę w poniższej tabeli, która posłuży jako klucz główny raportu.", font=("Segoe UI", 9), foreground="#a0a0a0").pack(anchor='w', pady=(0, 5))
        
        self.tree_frame = ttk.Frame(self.root)
        self.tree_frame.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(self.tree_frame, show='headings', height=5)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.lbl_id = ttk.Label(self.root, text="Wybrany klucz: Brak", font=("Segoe UI", 10, "bold"), foreground="#ff6b6b")
        self.lbl_id.pack(anchor='w', pady=5)

        # 3. Metody Agregacji (PRZENIESIONE WYŻEJ)
        agg_header_container = ttk.Frame(self.root)
        agg_header_container.pack(fill='x', pady=(15, 0))
        
        ttk.Label(agg_header_container, text="Metody agregacji wskaźników (KPI)", style="Header.TLabel").pack(side='left')
        
        # Panel zmiany zbiorczej
        self.bulk_agg_combo = ttk.Combobox(agg_header_container, values=["Średnia", "Suma", "Maksimum", "Minimum"], state="readonly", width=12)
        self.bulk_agg_combo.current(0)
        self.bulk_agg_combo.pack(side='right', padx=5)
        
        btn_bulk_apply = ttk.Button(agg_header_container, text="Ustaw dla wszystkich", command=self.apply_bulk_aggregation)
        btn_bulk_apply.pack(side='right', padx=5)

        ttk.Label(self.root, text="Wybierz sposób łączenia danych dla poszczególnych kolumn po zgrupowaniu.", font=("Segoe UI", 9), foreground="#a0a0a0").pack(anchor='w', pady=(0, 5))
        
        self.agg_outer_frame = tk.Frame(self.root, bg=self.border_color, padx=1, pady=1)
        self.agg_outer_frame.pack(side="top", fill="both", expand=True)

        self.agg_canvas = tk.Canvas(self.agg_outer_frame, bg=self.panel_bg, highlightthickness=0, height=120)
        self.agg_scrollbar = ttk.Scrollbar(self.agg_outer_frame, orient="vertical", command=self.agg_canvas.yview)
        self.agg_frame = ttk.Frame(self.agg_canvas, style="Panel.TFrame")

        self.agg_frame.bind("<Configure>", lambda e: self.agg_canvas.configure(scrollregion=self.agg_canvas.bbox("all")))
        self.agg_canvas.create_window((0, 0), window=self.agg_frame, anchor="nw", width=750)
        self.agg_canvas.configure(yscrollcommand=self.agg_scrollbar.set)
        self.agg_canvas.pack(side="left", fill="both", expand=True)
        self.agg_scrollbar.pack(side="right", fill="y")

        # 4. Wykluczenia z analizy (PRZENIESIONE NIŻEJ)
        ttk.Label(self.root, text="Wykluczenia z analizy", style="Header.TLabel").pack(anchor='w', pady=(15, 0))
        self.ignore_frame = ttk.Frame(self.root)
        self.ignore_frame.pack(fill='x')
        self.ignore_listbox = tk.Listbox(
            self.ignore_frame, selectmode=tk.MULTIPLE, height=3,
            bg=self.panel_bg, fg=self.fg_color, selectbackground=self.btn_active, 
            borderwidth=0, highlightthickness=1, highlightcolor=self.btn_bg, font=("Segoe UI", 9),
            exportselection=False  # <--- POPRAWKA: Rozwiązuje problem podwójnego klikania w Comboboxach
        )
        self.ignore_listbox.pack(side='left', fill='x', expand=True)
        self.ignore_listbox.bind('<<ListboxSelect>>', self.update_agg_table)
        
        ignore_scroll = ttk.Scrollbar(self.ignore_frame, orient="vertical", command=self.ignore_listbox.yview)
        ignore_scroll.pack(side='right', fill='y')
        self.ignore_listbox.configure(yscrollcommand=ignore_scroll.set)

        # 5. Konfiguracja wizualna i Eksport
        ttk.Label(self.root, text="Eksport", style="Header.TLabel").pack(anchor='w', pady=(15, 0))
        self.btn_color = ttk.Button(self.root, text=f"Kolor wiodący raportu (obecny: {self.accent_color})", command=self.choose_color)
        self.btn_color.pack(fill='x', pady=(0, 10))
        self.btn_generate = ttk.Button(self.root, text="Generuj raport HTML", command=self.generate_report)
        self.btn_generate.pack(fill='x', pady=5)

    def apply_bulk_aggregation(self):
        method = self.bulk_agg_combo.get()
        for combo in self.agg_methods.values():
            combo.set(method)

    def load_excel(self):
        self.file_path = filedialog.askopenfilename(title="Wybierz plik źródłowy", filetypes=[("Arkusze Excel", "*.xlsx *.xls")])
        if not self.file_path: return
        try:
            self.excel_file = pd.ExcelFile(self.file_path)
            sheet_names = self.excel_file.sheet_names
            
            # Przywrócona logika pokazywania/ukrywania listy arkuszy
            if len(sheet_names) > 1:
                self.sheet_frame.pack(fill='x', pady=(0, 10), after=self.btn_load)
            else:
                self.sheet_frame.pack_forget()
                
            self.sheet_combo['values'] = sheet_names
            self.sheet_combo.current(0)
            self.load_sheet_data()
        except Exception as e: 
            messagebox.showerror("Błąd odczytu", str(e))

    def load_sheet_data(self, event=None):
        try:
            self.df = pd.read_excel(self.file_path, sheet_name=self.sheet_combo.get())
            self.update_ui_with_data()
        except Exception as e: messagebox.showerror("Błąd odczytu", str(e))

    def update_ui_with_data(self):
        self.tree.delete(*self.tree.get_children())
        self.ignore_listbox.delete(0, tk.END)
        self.id_column = None
        self.lbl_id.config(text="Wybrany klucz: Brak", foreground="#ff6b6b")
        if self.df is None: return
        columns = list(self.df.columns)
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.set_id_column(c))
            self.tree.column(col, width=100, anchor='center')
        for _, row in self.df.head(20).iterrows(): self.tree.insert("", "end", values=list(row))
        dt_cols = self.df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()
        for i, col in enumerate(columns):
            self.ignore_listbox.insert(tk.END, col)
            if col in dt_cols: self.ignore_listbox.selection_set(i)
        self.update_agg_table()

    def set_id_column(self, col_name):
        self.id_column = col_name
        self.lbl_id.config(text=f"Wybrany klucz: {self.id_column}", foreground="#69db7c")
        self.update_agg_table()

    def update_agg_table(self, event=None):
        # Zapisujemy obecny stan metod przed wyczyszczeniem
        saved_methods = {}
        for col, combo in self.agg_methods.items():
            try:
                saved_methods[col] = combo.get()
            except tk.TclError:
                pass # Ignorujemy, jeśli widget już nie istnieje
                
        for widget in self.agg_frame.winfo_children(): widget.destroy()
        self.agg_methods.clear()
        
        if self.df is None: return
        ignored = [self.ignore_listbox.get(i) for i in self.ignore_listbox.curselection()]
        numeric_cols = [c for c in self.df.select_dtypes(include='number').columns if c not in ignored and c != self.id_column]
        
        if not numeric_cols:
            ttk.Label(self.agg_frame, text="Brak kolumn numerycznych do agregacji.", style="Panel.TLabel", font=("Segoe UI", 9, "italic")).grid(row=0, column=0, padx=10, pady=10)
            return
            
        ttk.Label(self.agg_frame, text="Kolumna / Wskaźnik", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(self.agg_frame, text="Metoda", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky='w', pady=5)
        ttk.Separator(self.agg_frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        for i, col in enumerate(numeric_cols):
            ttk.Label(self.agg_frame, text=col, style="Panel.TLabel").grid(row=i+2, column=0, sticky='w', padx=10, pady=4)
            cb = ttk.Combobox(self.agg_frame, values=["Średnia", "Suma", "Maksimum", "Minimum"], state="readonly", width=20)
            
            # 2. DODANE: Odtwarzamy zapisany stan lub dajemy domyślny
            if col in saved_methods:
                cb.set(saved_methods[col])
            else:
                cb.current(0)
                
            cb.grid(row=i+2, column=1, sticky='w', pady=4)
            self.agg_methods[col] = cb

    def choose_color(self):
        color = colorchooser.askcolor(title="Wybierz kolor")[1]
        if color:
            self.accent_color = color
            self.btn_color.config(text=f"Kolor wiodący raportu (obecny: {self.accent_color})")

    def generate_report(self):
        if self.df is None or not self.id_column:
            messagebox.showwarning("Brak danych", "Wybierz plik i klucz agregacji.")
            return
        try:
            ignored_indices = self.ignore_listbox.curselection()
            ignored_cols = [self.ignore_listbox.get(i) for i in ignored_indices]
            
            df_filtered = self.df.drop(columns=ignored_cols).copy()
            
            agg_dict = {}
            for col, combo in self.agg_methods.items():
                if col in df_filtered.columns:
                    method_name = combo.get()
                    agg_dict[col] = self.agg_dict_pandas[method_name]
            
            if not agg_dict:
                messagebox.showwarning("Błąd", "Brak danych metrycznych do analizy.")
                return

            # Agregacja główna
            grouped = df_filtered.groupby(self.id_column).agg(agg_dict).reset_index()
            
            # Obliczenia dla kafelków podsumowujących (na surowych danych zgodnie z metodą)
            total_ids = len(grouped[self.id_column].unique())
            first_kpi_col = list(agg_dict.keys())[0]
            selected_method_name = self.agg_methods[first_kpi_col].get()
            pd_method = self.agg_dict_pandas[selected_method_name]
            
            # Liczenie na surowych danych zgodnie z wybraną metodą
            first_kpi_val = getattr(df_filtered[first_kpi_col], pd_method)()
            kpi_tile_title = f"{selected_method_name}: {first_kpi_col}"

            gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_name = os.path.basename(self.file_path)

            def format_pl(x):
                try: return f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', ' ')
                except: return x

            def format_int(x):
                try: return f"{int(x):,}".replace(',', ' ')
                except: return x

            table_html = grouped.to_html(index=False, classes='data-table', float_format=format_pl)
            
            html_graphs = ""
            for i, col in enumerate(agg_dict.keys()):
                fig = px.bar(grouped, x=self.id_column, y=col, template="plotly_dark", color_discrete_sequence=[self.accent_color])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#A0AEC0"), margin=dict(l=20, r=20, t=30, b=20), xaxis_title="", yaxis_title="", bargap=0.2)
                html_graphs += f'<div class="card"><h3 class="card-title">Rozkład KPI: {col} ({self.agg_methods[col].get()})</h3><div class="chart-wrapper">{fig.to_html(full_html=False, include_plotlyjs=("cdn" if i==0 else False), config={"responsive": True})}</div></div>'

            html_template = f"""
            <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>Raport Analityczny</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
            <style>
                :root {{ --bg-color: #0b0c10; --card-bg: #15161d; --accent: {self.accent_color}; --text-main: #e2e8f0; --text-muted: #94a3b8; --border-color: rgba(255, 255, 255, 0.08); }}
                body {{ background-color: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 40px 20px; background-image: radial-gradient(circle at 50% 0%, rgba(255,255,255,0.02) 0%, transparent 60%); }}
                .container {{ max-width: 1200px; margin: auto; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                h1 {{ font-size: 2.2rem; font-weight: 800; color: #ffffff; text-shadow: 0 0 15px rgba(255,255,255,0.1); margin-bottom: 10px; }}
                .timestamp {{ color: var(--text-muted); font-size: 0.95rem; font-weight: 400; }}
                
                /* SCORECARDY */
                .scorecards-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }}
                .scorecard {{ background-color: var(--card-bg); border-radius: 12px; padding: 25px; border: 1px solid var(--border-color); border-left: 4px solid var(--accent); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }}
                .scorecard p {{ font-size: 0.9rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin: 0 0 10px 0; }}
                .scorecard h3 {{ font-size: 2.2rem; font-weight: 800; margin: 0; color: #ffffff; }}

                /* KARTY */
                .card {{ background-color: var(--card-bg); border-radius: 12px; padding: 25px; margin-bottom: 30px; border: 1px solid var(--border-color); position: relative; box-shadow: 0 15px 35px rgba(0,0,0,0.4); min-width: 0; }}
                .card::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px; background: var(--accent); border-radius: 12px 12px 0 0; box-shadow: 0 0 15px var(--accent); }}
                .card-title {{ margin-top: 0; color: #ffffff; font-size: 1.1rem; font-weight: 600; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; margin-bottom: 20px; }}

                .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
                .data-table th, .data-table td {{ padding: 14px 20px; text-align: right; border-bottom: 1px solid var(--border-color); }}
                .data-table th {{ background-color: rgba(0,0,0,0.2); color: var(--text-muted); font-weight: 600; }}
                .data-table tbody tr:hover {{ background-color: rgba(255,255,255,0.02); }}
                
                .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 30px; }}
                
                /* STOPKA - STYLE */
                .footer-simple {{ text-align: center; padding: 30px 0 10px 0; margin-top: 20px; border-top: 1px solid var(--border-color); color: var(--text-muted); font-size: 0.9rem; }}
                
                /* STYLE DLA ZAAWANSOWANEJ STOPKI (na przyszłość) */
                footer {{ text-align: center; padding: 30px 0 10px 0; margin-top: 20px; border-top: 1px solid var(--border-color); color: var(--text-muted); font-size: 0.9rem; line-height: 1.5; }}
                footer a {{ color: var(--accent); text-decoration: none; transition: color 0.2s; }}
                footer a:hover {{ color: #ffffff; }}
                .github-link {{ display: inline-flex; align-items: center; justify-content: center; gap: 6px; font-weight: 600; }}
                .github-icon {{ width: 18px; height: 18px; fill: currentColor; }}
            </style></head><body><div class="container">
            <div class="header"><h1>Raport Analityczny</h1><div class="timestamp">Wygenerowano: {gen_time} | Plik źródłowy: <b>{file_name}</b> | Klucz agregacji: {self.id_column}</div></div>
            
            <div class="scorecards-container">
                <div class="scorecard"><p>Unikalne Rekordy ({self.id_column})</p><h3>{format_int(total_ids)}</h3></div>
                <div class="scorecard"><p>{kpi_tile_title}</p><h3>{format_pl(first_kpi_val)}</h3></div>
            </div>

            <div class="card">
                <h3 class="card-title">Zestawienie tabelaryczne (dane zagregowane)</h3>
                <div style="overflow-x:auto">{table_html}</div>
            </div>
            
            <div class="charts-grid">{html_graphs}</div>
            
            <!-- V2 prosta stopka -->
            <!-- 
            <div class="footer-simple">Stworzone przez: Mateusz Machowina</div>
            -->

            <!-- V1 rozbudowana stopka z linkami i ikoną GitHub -->
            <footer>
              <p style="font-size: 0.9em; color: #cfd8dc; display: flex; justify-content: center; align-items: center; gap: 6px; margin: 0; flex-wrap: nowrap;">
                Stworzone przez: 
                <a href="https://github.com/MateuszMachowina" target="_blank" class="github-link">
                  <svg class="github-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48 0-.24-.01-.87-.01-1.71-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.1-1.46-1.1-1.46-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.55-1.11-4.55-4.95 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.56 9.56 0 012.5-.34 9.5 9.5 0 012.5.34c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.85-2.34 4.7-4.57 4.95.36.31.68.92.68 1.85 0 1.34-.01 2.42-.01 2.75 0 .27.18.58.69.48A10 10 0 0022 12c0-5.52-4.48-10-10-10z"/>
                  </svg>
                  Mateusz Machowina
                </a>
              </p>
            </footer>
            
            </div>
            <script>window.addEventListener('load', function() {{ setTimeout(function() {{ window.dispatchEvent(new Event('resize')); }}, 150); }});</script>
            </body></html>"""
            
            # Pobranie folderu, w którym znajduje się plik Excel. Opcjonalnie można zmienić na Desktop, gdy jest błąd Errno 9
            #output_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            output_dir = os.path.dirname(self.file_path)
            output_file_path = os.path.join(output_dir, "raport_analityczny.html")
            
            # Zapis pliku obok excela
            with open(output_file_path, "w", encoding="utf-8") as f: 
                f.write(html_template)
            
            # Otwarcie pliku w przeglądarce
            webbrowser.open('file://' + output_file_path.replace('\\', '/'))
        except Exception as e: messagebox.showerror("Błąd operacji", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelReportApp(root)
    root.mainloop()
