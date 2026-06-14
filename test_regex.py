import re

text = """
 | Data                    | Descriere                                                                                                           | Descriere                                                                                                           | Debit                      | Credit                | Sold(RON)             |
 | 02 februarie 2026       | +CMS CLT-3428656838 Card 5418-95XX-XXXX-5902 2026.01.30 LIDL RO-388 ROM-TIMISOARA 61718258 Auth code 682642 27 96 RON CUMPARARE PRIN POS            | +CMS CLT-3428656838 Card 5418-95XX-XXXX-5902 2026.01.30 LIDL RO-388 ROM-TIMISOARA 61718258 Auth code 682642 27 96 RON CUMPARARE PRIN POS            | 27.96                      |                       | 3,422.40              |
 | 04 februarie 2026 | +CMS CLT-3430424779 Card 5418-95XX-XXXX-5902 2026.02.03 UBER *TRIP NLD-AMSTERDAM 39431238 Auth code 629169 5 00 RON CUMPARARE PRIN POS     |    5    |          |     3317.18 |
"""

month_map = {
    'ianuarie': '01', 'februarie': '02', 'martie': '03', 'aprilie': '04',
    'mai': '05', 'iunie': '06', 'iulie': '07', 'august': '08',
    'septembrie': '09', 'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'
}

def test_extract(content):
    # Regex flexibil: Data + restul liniei
    pattern = r'\|\s*([0-9]{2})\s+([a-zăâîșț]+)\s+(202[0-9])\s*\|(.*)'
    matches = re.finditer(pattern, content, re.IGNORECASE)
    
    for match in matches:
        zi = match.group(1)
        luna_nume = match.group(2).lower()
        an = match.group(3)
        rest = match.group(4)
        
        cols = [c.strip() for c in rest.split('|')]
        # Curățăm coloanele goale de la final rezultate din split-ul ultimului |
        if cols and not cols[-1]: cols.pop()
        
        # print(f"DEBUG: {zi} {luna_nume} {an} | COLS: {cols}")
        
        # Căutăm sumele (Debit/Credit)
        # De obicei sunt ultimele 3 coloane: Debit, Credit, Sold
        # SAU ultimele 2 coloane dacă nu e Sold
        
        # Identificăm descrierea (prima coloană sau primele două)
        desc = cols[0]
        
        # Identificăm sumele
        amounts = []
        for c in cols[1:]:
            clean = "".join(ch for ch in c.replace(',', '.') if ch.isdigit() or ch == '.')
            try:
                if clean: amounts.append(float(clean))
                else: amounts.append(None)
            except: amounts.append(None)
            
        # Analiză logică coloane
        # Dacă avem 2 coloane rămase (Debit, Credit) sau 3 (Debit, Credit, Sold)
        # Cazul 1: | Desc | Desc | Debit | Credit | Sold | -> cols are [Desc, Desc, Debit, Credit, Sold] (len 5)
        # Cazul 2: | Desc | Debit | Credit | Sold | -> cols are [Desc, Debit, Credit, Sold] (len 4)
        
        suma = 0
        tip = "PLATA"
        
        if len(cols) >= 4:
            # Ultimele 3 sunt de obicei Debit, Credit, Sold
            debit = amounts[-3]
            credit = amounts[-2]
            
            if credit is not None and credit > 0:
                suma = credit
                tip = "INCASARE"
            elif debit is not None and debit > 0:
                suma = debit
                tip = "PLATA"
        
        print(f"RESULT: {an}-{month_map.get(luna_nume)}-{zi} | {tip}: {desc[:50]}... | Suma: {suma}")

if __name__ == "__main__":
    test_extract(text)
