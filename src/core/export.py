import os
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter

def export_text(filepath, p_text, q_text, r_text, div_steps, curl_steps):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("VectorMachine Export\n")
        f.write("="*20 + "\n\n")
        
        f.write(f"Vector Field: F = < {p_text}, {q_text}, {r_text} >\n\n")
        
        if div_steps:
            f.write("Divergence:\n")
            f.write("-" * 10 + "\n")
            f.write(f"Formula: {div_steps['formula']}\n")
            f.write(f"Unsimplified: {div_steps['unsimplified']}\n")
            f.write(f"Final Simplified: {div_steps['final']}\n\n")
            
        if curl_steps:
            f.write("Curl:\n")
            f.write("-" * 10 + "\n")
            f.write(f"i component: {curl_steps['i_comp_unsimplified']} -> {curl_steps['final_i']}\n")
            f.write(f"j component: {curl_steps['j_comp_unsimplified']} -> {curl_steps['final_j']}\n")
            f.write(f"k component: {curl_steps['k_comp_unsimplified']} -> {curl_steps['final_k']}\n")
            f.write(f"Final Vector: < {curl_steps['final_i']}, {curl_steps['final_j']}, {curl_steps['final_k']} >\n")

def export_markdown(filepath, p_text, q_text, r_text, div_steps, curl_steps):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# VectorMachine Export\n\n")
        
        f.write(f"**Vector Field:** `F = < {p_text}, {q_text}, {r_text} >`\n\n")
        
        if div_steps:
            f.write("## Divergence\n")
            f.write(f"- **Formula**: `{div_steps['formula']}`\n")
            f.write(f"- **Unsimplified**: `{div_steps['unsimplified']}`\n")
            f.write(f"- **Final Simplified**: `{div_steps['final']}`\n\n")
            
        if curl_steps:
            f.write("## Curl\n")
            f.write(f"- **i component**: `{curl_steps['i_comp_unsimplified']}` &rarr; `{curl_steps['final_i']}`\n")
            f.write(f"- **j component**: `{curl_steps['j_comp_unsimplified']}` &rarr; `{curl_steps['final_j']}`\n")
            f.write(f"- **k component**: `{curl_steps['k_comp_unsimplified']}` &rarr; `{curl_steps['final_k']}`\n")
            f.write(f"- **Final Vector**: `< {curl_steps['final_i']}, {curl_steps['final_j']}, {curl_steps['final_k']} >`\n")

def export_pdf(filepath, html_content):
    doc = QTextDocument()
    doc.setHtml(html_content)
    
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(filepath)
    
    doc.print_(printer)
