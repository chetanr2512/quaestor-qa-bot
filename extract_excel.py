import pandas as pd
xls = pd.ExcelFile(r'D:\coding ai  agent\QA testing agent\Innomesh Portal v4 - Regression Test Plan.xlsx')
out = ''
for s in xls.sheet_names:
    df = pd.read_excel(xls, s).fillna('')
    out += f'\n\n--- SHEET: {s} ---\n' + df.to_csv(index=False)
print('Total characters:', len(out))
print('First 1000 chars:', out[:1000])
