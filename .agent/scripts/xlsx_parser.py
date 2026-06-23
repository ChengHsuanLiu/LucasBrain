import os
import sys
import openpyxl

def parse_xlsx(file_path, output_path=None):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False
        
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        md_lines = []
        
        for sheet_idx, sheet in enumerate(wb.worksheets):
            md_lines.append(f"\n# Sheet: {sheet.title}\n")
            
            # Read rows
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                md_lines.append("*(Empty Sheet)*")
                continue
                
            # Filter out rows that are entirely None
            non_empty_rows = []
            for r in rows:
                if any(val is not None for val in r):
                    non_empty_rows.append(r)
            
            if not non_empty_rows:
                md_lines.append("*(No data found in rows)*")
                continue
                
            # Convert values to strings safely
            clean_rows = []
            max_cols = 0
            for r in non_empty_rows:
                str_row = []
                for val in r:
                    if val is None:
                        str_row.append("")
                    else:
                        # Clean inner newlines for markdown table compatibility
                        str_row.append(str(val).replace('\n', ' ').strip())
                clean_rows.append(str_row)
                max_cols = max(max_cols, len(str_row))
                
            # Format as markdown table
            for r_idx, r in enumerate(clean_rows):
                # Ensure all rows have the same length (pad with empty cells if needed)
                padded_row = r + [""] * (max_cols - len(r))
                md_lines.append("| " + " | ".join(padded_row) + " |")
                if r_idx == 0:
                    md_lines.append("| " + " | ".join(['---'] * max_cols) + " |")
                    
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
        print(f"Error parsing XLSX: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python xlsx_parser.py <input_xlsx_path> [output_md_path]")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    parse_xlsx(in_file, out_file)
