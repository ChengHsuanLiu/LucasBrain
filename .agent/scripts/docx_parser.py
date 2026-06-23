import os
import sys
import docx

def parse_docx(file_path, output_path=None):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False
        
    try:
        doc = docx.Document(file_path)
        md_lines = []
        
        # We can iterate through paragraphs and tables in order of appearance
        # using the internal document element body
        for element in doc.element.body:
            if element.tag.endswith('p'):
                # Paragraph
                p = docx.text.paragraph.Paragraph(element, doc)
                text = p.text.strip()
                if text:
                    # Handle basic styles (headings)
                    if p.style.name.startswith('Heading 1'):
                        md_lines.append(f"\n# {text}\n")
                    elif p.style.name.startswith('Heading 2'):
                        md_lines.append(f"\n## {text}\n")
                    elif p.style.name.startswith('Heading 3'):
                        md_lines.append(f"\n### {text}\n")
                    elif p.style.name.startswith('List'):
                        md_lines.append(f"- {text}")
                    else:
                        md_lines.append(text)
            elif element.tag.endswith('tbl'):
                # Table
                tbl = docx.table.Table(element, doc)
                md_lines.append("")
                for r_idx, row in enumerate(tbl.rows):
                    # Clean cell text (remove newlines inside cells for clean MD tables)
                    row_text = [cell.text.replace('\n', ' ').strip() for cell in row.cells]
                    md_lines.append("| " + " | ".join(row_text) + " |")
                    if r_idx == 0:
                        # Append MD table header divider
                        md_lines.append("| " + " | ".join(['---'] * len(row.cells)) + " |")
                md_lines.append("")
                
        content = "\n".join(md_lines)
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write(content)
            print(f"Successfully converted {file_path} to {output_path}")
        else:
            print(content)
        return True
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python docx_parser.py <input_docx_path> [output_md_path]")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    parse_docx(in_file, out_file)
