import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gestão Escolar")
        self.root.geometry("800x600")
        
        self.periodos_bimestres = {
            "1º Bimestre": {"inicio": "01/02/2026", "fim": "30/04/2026"},
            "2º Bimestre": {"inicio": "01/05/2026", "fim": "15/07/2026"},
            "3º Bimestre": {"inicio": "01/08/2026", "fim": "30/09/2026"},
            "4º Bimestre": {"inicio": "01/10/2026", "fim": "20/12/2026"}
        }
        
        self.setup_ui()

    def setup_ui(self):
        frame_periodo = ttk.LabelFrame(self.root, text="Configuração de Períodos (dd/mm/aaaa)")
        frame_periodo.pack(padx=10, pady=10, fill="x")

        self.tree = ttk.Treeview(frame_periodo, columns=("Bimestre", "Início", "Fim"), show="headings")
        self.tree.heading("Bimestre", text="Bimestre")
        self.tree.heading("Início", text="Início")
        self.tree.heading("Fim", text="Fim")
        self.tree.pack(padx=5, pady=5, fill="x")

        for b, datas in self.periodos_bimestres.items():
            self.tree.insert("", "end", values=(b, datas["inicio"], datas["fim"]))

        btn_validar = ttk.Button(self.root, text="Validar Lançamento", command=self.validar_data_lancamento)
        btn_validar.pack(pady=10)

    def validar_data_lancamento(self):
        data_atual = datetime.now()
        data_str = data_atual.strftime("%d/%m/%Y")
        
        bimestre_ativo = None
        for b, datas in self.periodos_bimestres.items():
            inicio = datetime.strptime(datas["inicio"], "%d/%m/%Y")
            fim = datetime.strptime(datas["fim"], "%d/%m/%Y")
            
            if inicio <= data_atual <= fim:
                bimestre_ativo = b
                break
        
        if bimestre_ativo:
            messagebox.showinfo("Sucesso", f"Hoje é {data_str}. Lançamentos permitidos para o {bimestre_ativo}.")
        else:
            messagebox.showwarning("Bloqueado", f"Hoje é {data_str}. Fora do período de lançamento de notas.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
