import fitz
import sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open(r'D:\coding ai  agent\QA testing agent\C2 Jitender -- Tri-POD QA Assignment.pdf')
for page in doc:
    print(page.get_text())
