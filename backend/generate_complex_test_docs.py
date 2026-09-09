import os
import sys
from fpdf import FPDF

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

class ForensicPDF(FPDF):
    def __init__(self, doc_title=""):
        super().__init__()
        self.doc_title = doc_title
        if os.path.exists(FONT_PATH):
            self.add_font("DejaVu", "", FONT_PATH)
        if os.path.exists(FONT_BOLD_PATH):
            self.add_font("DejaVu", "B", FONT_BOLD_PATH)
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        
    def header(self):
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "SISTEM JUDICIAR & CRIMINALISTIC - DOCUMENT DE PROBĂ ARHIVAT", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"Pagina {self.page_no()} | Certificat de Conformitate Criptografică SHA-256", align="C")

def build_pdf_1(out_path):
    pdf = ForensicPDF("PROCES-VERBAL DE CONTROL FISCAL")
    
    # Header Institutie
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(20, 30, 60)
    pdf.cell(0, 8, "MINISTERUL FINANȚELOR - AGENȚIA NAȚIONALĂ DE ADMINISTRARE FISCALĂ", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 6, "DIRECȚIA GENERALĂ ANTIFRAUDĂ FISCALĂ - DIRECȚIA REGIONALĂ CLUJ", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.set_draw_color(180, 180, 180)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "PROCES-VERBAL DE CONSTATARE ȘI CONTROL FISCAL", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, "Nr. Înregistrare: DGAF-7741 / Data Încheierii: 14.03.2025", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "I. DATE DE IDENTIFICARE ALE CONTROLULUI ȘI PĂRȚILOR", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5, 
        "Subsemnații Ștefan Moraru, inspector principal, și Laura Dinescu, inspector de specialitate, ambii în cadrul "
        "DGAF Regional Cluj, am procedat în data de 14.03.2025 la efectuarea unui control inopinat la sediul și punctele "
        "de lucru ale contribuabilului SC DELTA LOGISTIC DISTRIBUTIE SRL.\n"
        "Date entitate controlată: CUI: RO34918231, Reg. Com.: J12/1420/2015, Sediu Social: Mun. Cluj-Napoca, B-dul Muncii nr. 88, jud. Cluj.\n"
        "Reprezentant legal prezent: Ion Teodorescu, în calitate de Administrator, posesor CNP 1750820120033."
    )
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "II. OBIECTIVUL VERIFICĂRII ȘI CONSTATĂRI PRIVIND TRASABILITATEA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Obiectivul verificării a constat în verificarea trasabilității achizițiilor și livrărilor de carburanți (produse accizabile) "
        "pentru perioada 01.01.2024 - 31.12.2024, cu precădere relația comercială cu furnizorul SC PETRO-BLACK OIL SRL.\n"
        "În urma inventarierii fizice a rezervoarelor de stocare din depozitul B-dul Muncii și a confruntării cu registrul "
        "electronic de gestiune, s-au constatat diferențe negative nejustificate, după cum urmează:"
    )
    pdf.ln(3)
    
    # Tabel
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(235, 240, 250)
    col_w = [40, 25, 28, 28, 28, 31]
    headers = ["Produs Petrolier", "Cod Vamal", "Stoc Scriptic", "Stoc Faptic", "Diferență", "Prejudiciu Estimat"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("DejaVu", "", 8)
    rows = [
        ["Motorină Euro 5 Diesel", "27101943", "125.000 litri", "82.500 litri", "-42.500 litri", "276.250 RON"],
        ["Benzină Fără Plumb 95", "27101245", "45.000 litri", "45.100 litri", "+100 litri", "0.00 RON"],
        ["Ulei Motor Sintetic 5W30", "27101981", "3.200 litri", "1.800 litri", "-1.400 litri", "42.000 RON"]
    ]
    for r in rows:
        for i, val in enumerate(r):
            pdf.cell(col_w[i], 6, val, border=1, align="C" if i > 0 else "L")
        pdf.ln()
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "III. CONCLUZII, SANCȚIUNI ȘI MĂSURI DISPUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "1. Prejudiciul fiscal total cauzat bugetului de stat (TVA + accize sustrase) este calculat la suma de 318.250 RON.\n"
        "2. Fapta întrunește elementele constitutive ale infracțiunii de evaziune fiscală prevăzută de Legea 241/2005 art. 9 alin. (1) lit. b.\n"
        "3. Se dispune instituirea sechestrului asigurător asupra conturilor bancare deschise la Banca Transilvania (IBAN: RO44BTRL00007777888899XX) "
        "și indisponibilizarea a 2 cisterne de transport marca Scania (nr. înmatriculare CJ-12-DEL și CJ-14-DEL).\n"
        "4. Sesizarea organelor de urmărire penală din cadrul Parchetului de pe lângă Tribunalul Cluj."
    )
    pdf.ln(5)
    
    pdf.cell(90, 5, "Inspectori Antifraudă: Ștefan Moraru, Laura Dinescu")
    pdf.cell(90, 5, "Reprezentant Contribuabil: Ion Teodorescu", align="R")
    pdf.output(out_path)

def build_pdf_2(out_path):
    pdf = ForensicPDF("RAPORT DE EXPERTIZĂ CRIMINALISTICĂ CIBERNETICĂ")
    
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(15, 45, 80)
    pdf.cell(0, 8, "INSTITUTUL NAȚIONAL DE EXPERTIZE CRIMINALISTICE", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "LABORATORUL INTERJUDEȚEAN DE CRIMINALISTICĂ INFORMATICĂ BUCUREȘTI", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "RAPORT DE EXPERTIZĂ TEHNICĂ CIBERNETICĂ & DIGITAL FORENSICS", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "Dosar Penal nr. 144/P/2025 | Parchetul de pe lângă Tribunalul București", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5, "Raport nr. EXP-2025/089 | Data emiterii: 05.02.2025", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "1. DATE TEHNICE ALE CORPULUI DELICT ȘI INTEGRITATEA PROBEI", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Expert criminalist autorizat: ing. Bogdan-Mihai Iancu (Legitimație MJ nr. 4412/2018).\n"
        "Dispozitiv analizat: Server Enterprise Rackabil marca Dell PowerEdge R740, Serial Number (Service Tag): 8KJ29L1.\n"
        "Proveniență: Ridicat din camera tehnică a SC OMEGA SYSTEMS COMPUTING SRL (CUI RO29384751).\n"
        "Imagine medico-legală (Bit-stream image RAW E01) prelevată cu dispozitiv certificat Tableau TD3.\n"
        "Amprentă Criptografică SHA-256: 9b8c3d1f05e2a6b8c9d4e7f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1\n"
        "Sistem de operare găsit pe disc: Linux Ubuntu 22.04 LTS x86_64, Adresă IP statică compromisă: 193.226.11.45."
    )
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "2. ANALIZA TIMELINE-ULUI INTRUZIUNII ȘI ARTEFACTELOR DE EXFILTRARE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Analiza jurnalelor de sistem (/var/log/auth.log, audit.log și bash history) relevă compromiterea prin "
        "atac forță brută pe serviciul OpenSSH (port 2222) urmat de executarea unui script de recunoaștere laterală:"
    )
    pdf.ln(2)
    
    # Tabel Loguri
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    col_w = [32, 28, 18, 22, 50, 30]
    headers = ["Timestamp UTC", "IP Sursă", "Port", "Utilizator", "Comandă / Malware", "Volum Date"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("DejaVu", "", 7.5)
    logs = [
        ["2025-01-28 02:14:22", "194.102.34.12", "44321", "root", "SSH Brute-Force Success", "-"],
        ["2025-01-28 02:18:05", "194.102.34.12", "44321", "root", "Drop Trojan.Spy.AgentTesla", "12.4 MB"],
        ["2025-01-28 02:45:10", "85.120.45.99", "50220", "root", "pg_dump -d omega_clients.sql", "1.8 GB DB"],
        ["2025-01-28 03:22:40", "85.120.45.99", "50220", "root", "SCP Transfer C2 Netherlands", "3.4 GB arhivă"]
    ]
    for r in logs:
        for i, val in enumerate(r):
            pdf.cell(col_w[i], 5.5, val, border=1, align="C" if i in [0,1,2,3,5] else "L")
        pdf.ln()
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "3. CONCLUZIILE EXPERTIZEI CRIMINALE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "a) Atacul cibernetic s-a desfășurat în intervalul orar 02:14 - 03:40 UTC în noaptea de 28.01.2025.\n"
        "b) Atacatorul a exfiltrat un volum total măsurat de 5.21 GB ce conține baza de date completă a clienților și tranzacțiilor.\n"
        "c) Serverul de comandă și control (C2) identificat este localizat pe adresa IP 85.120.45.99 aparținând unui furnizor din Amsterdam, Olanda.\n"
        "d) Nu s-au detectat alterări ale integrității fizice ale discului după momentul sigilării de către organele de poliție."
    )
    pdf.ln(4)
    pdf.cell(0, 5, "Expert Criminalist: ing. Bogdan-Mihai Iancu (Semnătură & Sigiliu Oficial)", align="R")
    pdf.output(out_path)

def build_pdf_3(out_path):
    pdf = ForensicPDF("CONTRACT DE CESIUNE CREANȚE ȘI IPOTECĂ")
    
    pdf.set_font("DejaVu", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "ROMÂNIA - UNIUNEA NAȚIONALĂ A NOTARILOR PUBLICI", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "BIROUL NOTARIAL NOTAR PUBLIC MARIANA DUMITRESCU", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5, "Sediul: Mun. București, Str. Știrbei Vodă nr. 42, Sector 1", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, "CONTRACT DE CESIUNE ONEROASĂ DE CREANȚĂ ȘI TRANSMITERE IPOTECĂ", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "Autentificat sub Nr. 45/CES din data de 22.01.2025", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "PĂRȚILE CONTRACTANTE:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "1. SC PRIMA CREDIT INVEST IFN SA, cu sediul în București, CUI RO28491029, J40/3312/2011, "
        "reprezentată legal prin Director General Mihai Enache, în calitate de CEDENT, pe de o parte, și\n"
        "2. INVEST CAPITAL MALTA HOLDING LTD, persoană juridică malteză, nr. înmatriculare C-88912, NIF fiscal românesc 9001238910, "
        "reprezentată prin mandatar cu procură notarială Robert Grigorescu, în calitate de CESIONAR, pe de altă parte.\n"
        "Cu privire la situația debitorului cedat Dan Alexandru Voinea (CNP 1820914400123, domiciliat în Cluj-Napoca, Str. Observatorului nr. 12)."
    )
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "OBIECTUL CESIUNII ȘI PREȚUL TRANZACȚIEI:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Art. 1. Cedentul transmite Cesionarului toate drepturile izvorâte din Contractul de Credit Ipotecar nr. CR-2021-9012 din 15.06.2021.\n"
        "Art. 2. Valoarea nominală a creanței cedate la data prezentului contract este de 285.000 EUR.\n"
        "Art. 3. Prețul cesiunii convenit de părți este de 71.250 EUR (reprezentând 25% din valoarea nominală, discount comercial 75%).\n"
        "Plata se va efectua în termen de 3 zile lucrătoare în contul IBAN RO99INGB0000999912345678 deschis la ING Bank România."
    )
    pdf.ln(3)
    
    # Tabel Garantii
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(245, 245, 235)
    col_w = [40, 30, 25, 30, 55]
    headers = ["Componentă Datorie", "Sold Datorat", "Monedă", "Tip Garanție", "Imobil Afectat Ipotecii (CF)"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("DejaVu", "", 8)
    datorii = [
        ["Principal Rămas", "250.800", "EUR", "Ipotecă Rang I", "CF 123456 Cluj-Napoca, Ap. 4B, 142mp"],
        ["Dobânzi Curente", "18.200", "EUR", "Ipotecă Rang I", "Evaluare oficială imobil: 340.000 EUR"],
        ["Penalități Contractuale", "16.000", "EUR", "Gaj Mobiliar", "Conturi debitor la Banca Transilvania"],
        ["TOTAL CREANȚĂ", "285.000", "EUR", "Rang Preferențial", "Drept de executare silită directă"]
    ]
    for r in datorii:
        for i, val in enumerate(r):
            pdf.cell(col_w[i], 5.5, val, border=1, align="C" if i in [1,2,3] else "L")
        pdf.ln()
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "NOTIFICARE ȘI EXECUTABILITATE:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Prezenta cesiune se va înscrie în Registrul Național de Publicitate Mobiliară (RNPM) și în Cartea Funciară 123456 Cluj-Napoca. "
        "Debitorul cedat va fi notificat prin executor judecătoresc conform art. 1578 Cod Civil."
    )
    pdf.ln(5)
    pdf.cell(90, 5, "Cedent: SC PRIMA CREDIT INVEST IFN")
    pdf.cell(90, 5, "Cesionar: INVEST CAPITAL MALTA LTD", align="R")
    pdf.output(out_path)

def build_pdf_4(out_path):
    pdf = ForensicPDF("HOTĂRÂRE AGA SC GLOBAL TECH VENTURES SRL")
    
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(10, 40, 20)
    pdf.cell(0, 8, "SC GLOBAL TECH VENTURES SRL", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "CUI: RO39481200 | J40/8812/2018 | Capital social: 100.000 RON", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5, "Sediul: Mun. București, Str. Barbu Văcărescu nr. 102, Clădirea Sky, Etaj 8", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, "HOTĂRÂREA ADUNĂRII GENERALE A ASOCIAȚILOR NR. 03/2025", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "Data desfășurării: 28.02.2025, ora 11:00", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "PREZENȚA ȘI CONVOCAREA:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "La ședința AGA desfășurată la sediul social sunt prezenți toți asociații societății, reprezentând 100% din capitalul social:\n"
        "1. Radu Mihalcea, deținător a 6.000 părți sociale (60% capital social, aport 60.000 RON).\n"
        "2. Elena Voinea, deținătoare a 4.000 părți sociale (40% capital social, aport 40.000 RON).\n"
        "Președinte de ședință a fost ales Radu Mihalcea, iar secretar de ședință d-na Carmen Barbu."
    )
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "HOTĂRÂRILE ADOPTATE ÎN UNANIMITATE:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Art. 1. Se aprobă Situațiile Financiare Anuale ale exercițiului financiar 2024. Profitul net contabil este de 1.500.000 RON.\n"
        "Art. 2. Se aprobă distribuirea sumei de 1.200.000 RON cu titlu de DIVIDENDE către asociați proporțional cu cota de participare.\n"
        "Diferența de 300.000 RON rămâne profit nerepartizat ca rezervă pentru investiții în infrastructură IT.\n"
        "Art. 3. Se aprobă reținerea la sursă a impozitului pe dividende în cotă legală de 8% (suma totală: 96.000 RON) "
        "și virarea acestuia către bugetul consolidat al statului până la data de 25 martie 2025.\n"
        "Art. 4. Plata dividendelor nete se va realiza în data de 15.03.2025 din contul bancar RO44BTRL00001234567890XX deschis la Banca Transilvania."
    )
    pdf.ln(3)
    
    # Tabel Dividende
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(230, 245, 230)
    col_w = [38, 20, 32, 28, 32, 30]
    headers = ["Nume Asociat", "Cotă %", "Dividend Brut", "Impozit 8%", "Dividend Net", "Bancă & Destinație"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("DejaVu", "", 8)
    div_rows = [
        ["Radu Mihalcea", "60%", "720.000 RON", "57.600 RON", "662.400 RON", "Banca Transilvania"],
        ["Elena Voinea", "40%", "480.000 RON", "38.400 RON", "441.600 RON", "ING Bank România"],
        ["TOTAL DISTRIBUIT", "100%", "1.200.000 RON", "96.000 RON", "1.104.000 RON", "Virament 15.03.2025"]
    ]
    for r in div_rows:
        for i, val in enumerate(r):
            pdf.cell(col_w[i], 5.5, val, border=1, align="C" if i > 0 else "L")
        pdf.ln()
    pdf.ln(4)
    
    pdf.cell(90, 5, "Asociat: Radu Mihalcea")
    pdf.cell(90, 5, "Asociat: Elena Voinea", align="R")
    pdf.output(out_path)

def build_pdf_5(out_path):
    pdf = ForensicPDF("BORDEROU DE ACHIZIȚIE CEREALE")
    
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(50, 40, 10)
    pdf.cell(0, 8, "AGRO EXPORT CEREALE ROMANIA SRL - BAZA SILOZ CĂLĂRAȘI SUD", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "CUI: RO19283746 | J51/320/2012 | Autorizație Depozitar Siloz nr. SL-881/2019", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5, "Sediul Silozului: Mun. Călărași, Șos. Portului nr. 5, jud. Călărași", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, "BORDEROU DE ACHIZIȚIE DE LA PRODUCĂTORI INDIVIDUALI", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "Seria BRD nr. 7709 | Data emiterii: 18.04.2025 | Ora cântăririi: 10:45", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "1. IDENTIFICARE PĂRȚI ȘI TRANSPORTATOR:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Cumpărător / Depozitar: AGRO EXPORT CEREALE ROMANIA SRL, reprezentat prin ing. gestionar Vasile Dobre.\n"
        "Vânzător (Producător agricol individual): Gheorghe V. Ilie, CNP 1580412510044, CI seria KL nr. 441029, "
        "domiciliat în sat Roseți, jud. Călărași, posesor Carnet de Producător nr. CP-2024/9912 eliberat de Primăria Roseți.\n"
        "Șofer și Vehicul: Marian Dumitru, autocamion MAN nr. înmatriculare CL-44-AGR (remorcă CL-45-AGR)."
    )
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "2. DETERMINARE CANTITATE ȘI CALCUL FINANCIAR:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5,
        "Produs achiziționat: Grâu comun de panificație calitatea I (Recolta 2024, conform STAS 104-98).\n"
        "Tichet cântar basculă electronică: seria TK nr. 2025-0812.\n"
        "- Greutate brută (camion încărcat): 58.700 kg\n"
        "- Greutate tară (camion gol): 16.200 kg\n"
        "- GREUTATE NETĂ PRELUATĂ: 42.500 kg (42,50 tone metrice)\n"
        "Preț unitar agreat: 0,95 RON / kg (scutit de TVA conform art. 310 Cod Fiscal pentru persoane fizice).\n"
        "VALOARE TOTALĂ DATORATĂ: 40.375,00 RON (Patruzeci mii trei sute șaptezeci și cinci lei).\n"
        "Metodă de plată: Ordin de plată în contul bancar IBAN RO77CEC00001234567890001 deschis la CEC Bank Sucursala Călărași."
    )
    pdf.ln(3)
    
    # Tabel Laborator
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(255, 250, 235)
    col_w = [45, 35, 30, 35, 35]
    headers = ["Parametru Calitativ", "Metodă Analiză", "Valoare Găsită", "Limită STAS 104", "Verdict Laborator"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("DejaVu", "", 8)
    lab_rows = [
        ["Umiditate", "SR EN ISO 712", "13.10 %", "max. 14.00 %", "CONFORM"],
        ["Corpuri străine (impurități)", "SR EN 15587", "1.80 %", "max. 2.00 %", "CONFORM"],
        ["Masa hectolitrică (MH)", "SR EN ISO 7971", "79.40 kg/hl", "min. 78.00 kg/hl", "CALITATE SUPERIOARĂ"],
        ["Gluten umed", "SR EN ISO 21415", "26.50 %", "min. 24.00 %", "PANIFICAȚIE CLASA A"],
        ["Indice de Cădere Hagberg", "SR EN ISO 3093", "310 secunde", "min. 220 secunde", "CONFORM"]
    ]
    for r in lab_rows:
        for i, val in enumerate(r):
            pdf.cell(col_w[i], 5.5, val, border=1, align="C" if i > 0 else "L")
        pdf.ln()
    pdf.ln(4)
    
    pdf.cell(90, 5, "Gestionar Siloz: ing. Vasile Dobre")
    pdf.cell(90, 5, "Vânzător Producător: Gheorghe V. Ilie", align="R")
    pdf.output(out_path)

if __name__ == "__main__":
    out_dir = "/app/test_documents" if os.path.exists("/app") else "/home/cfp-90/AI/V2/test_documents"
    os.makedirs(out_dir, exist_ok=True)
    
    files = [
        (build_pdf_1, "01_Proces_Verbal_Control_ANAF.pdf"),
        (build_pdf_2, "02_Raport_Expertiza_Cyber_Forensics.pdf"),
        (build_pdf_3, "03_Contract_Cesiune_Creante_Ipoteca.pdf"),
        (build_pdf_4, "04_Hotarare_AGA_Distribuire_Dividende.pdf"),
        (build_pdf_5, "05_Borderou_Achizitie_Cereale_Siloz.pdf")
    ]
    
    print("[*] Generare documente de test...")
    for builder, fname in files:
        full_p = os.path.join(out_dir, fname)
        builder(full_p)
        print(f"[+] Generat cu succes: {full_p} ({os.path.getsize(full_p)} bytes)")
