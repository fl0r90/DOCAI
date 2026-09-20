#!/usr/bin/env python3
"""
Generator de contracte cu clauze încâlcite, acte adiționale succesive și modificări subtile
pentru testarea inteligenței juridice (Granite 4.2:8b la procesare vs Qwen 3.5:9b la chat).
Dosar: Agroterra (Case ID: 12)
"""

import os
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Înregistrare fonturi DejaVu pentru diacritice românești 100% corecte
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

OUTPUT_DIR = "/app/uploads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontName="DejaVuSans-Bold",
    fontSize=12,
    leading=16,
    alignment=1,
    textColor=colors.HexColor("#1A365D"),
    spaceAfter=8
)

subtitle_style = ParagraphStyle(
    "DocSubTitle",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=8.5,
    leading=12,
    alignment=1,
    textColor=colors.HexColor("#4A5568"),
    spaceAfter=12
)

body_style = ParagraphStyle(
    "DocBody",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=8,
    leading=11.5,
    textColor=colors.HexColor("#2D3748"),
    spaceAfter=6
)

body_bold = ParagraphStyle(
    "DocBodyBold",
    parent=body_style,
    fontName="DejaVuSans-Bold"
)

header_box_style = ParagraphStyle(
    "HeaderBox",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=7.5,
    leading=10,
    textColor=colors.HexColor("#4A5568")
)

def create_pdf(filename, flowables):
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=1.6*cm,
        rightMargin=1.6*cm,
        topMargin=1.6*cm,
        bottomMargin=1.6*cm
    )
    doc.build(flowables)
    print(f"[+] Generat cu succes: {filepath}")
    return filepath

def generate_contract_base():
    fname = "CTR-2024-005_Contract_Furnizare_Seminte_si_Tratamente_AGRO-DISTRIB.pdf"
    flowables = [
        Paragraph("REPUBLICA ROMÂNIA • CADRU COMERCIAL CORPORATIV", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=10),
        Paragraph("CONTRACT DE FURNIZARE SEZONIERĂ DE INPUTURI AGRICOLE", title_style),
        Paragraph("<b>Nr. CTR-2024-005 din data de 15 Februarie 2024</b>", subtitle_style),
        
        Paragraph("<b>CAPITOLUL I. PĂRȚILE CONTRACTANTE</b>", body_bold),
        Paragraph("<b>1.1. SC AGRO-DISTRIB SUD SRL</b>, cu sediul în Municipiul Călărași, Str. Industriei nr. 42, Jud. Călărași, înregistrată la Registrul Comerțului sub nr. J51/312/2018, Cod Unic de Înregistrare RO39281744, cont bancar RO44BTRL05101202888899XX deschis la Banca Transilvania, reprezentată legal prin Director General Ing. Vasile Dumitrescu, în calitate de <b>FURNIZOR</b>, și", body_style),
        Paragraph("<b>1.2. SC AGROTERRA LOGISTICS & DISTRIBUTION SRL</b>, cu sediul în Municipiul București, Sector 1, Șos. Nordului nr. 82-84, înregistrată la Registrul Comerțului sub nr. J40/8812/2021, Cod Unic de Înregistrare RO44102938, reprezentată legal prin Administrator Mihai Stanciu, în calitate de <b>BENEFICIAR</b>.", body_style),
        Spacer(1, 4),

        Paragraph("<b>CAPITOLUL II. OBIECTUL CONTRACTULUI</b>", body_bold),
        Paragraph("<b>Art. 2.1.</b> Obiectul prezentului contract îl reprezintă vânzarea și livrarea de semințe de porumb hibrid de înaltă productivitate tratate fungicid și a pachetelor de fertilizare foliară și erbicide aferente campaniei agricole 2024, conform comenzilor scrise confirmate.", body_style),
        Spacer(1, 4),

        Paragraph("<b>CAPITOLUL III. PREȚUL ȘI MODALITATEA DE FACTURARE</b>", body_bold),
        Paragraph("<b>Art. 3.1.</b> Prețul unitar ferm de vânzare convenit între părți este de <b>2.800,00 RON / tonă metrică</b> (exclusiv TVA).", body_style),
        Paragraph("<b>Art. 3.2.</b> Facturarea se va efectua eșalonat, pe fiecare lot efectiv recepționat la destinație, pe baza avizelor de însoțire și a proceselor-verbale de recepție calitativă.", body_style),
        Spacer(1, 4),

        Paragraph("<b>CAPITOLUL IV. TERMENE DE PLATĂ ȘI SCADENȚĂ</b>", body_bold),
        Paragraph("<b>Art. 4.1.</b> Beneficiarul se obligă să achite contravaloarea facturilor fiscale emise în termen de <b>30 de zile calendaristice</b> de la data recepției documentate a mărfii.", body_style),
        Paragraph("<b>Art. 4.2.</b> Plata se efectuează prin ordin de plată bancar în contul indicat de Furnizor.", body_style),
        Spacer(1, 4),

        Paragraph("<b>CAPITOLUL V. RĂSPUNDEREA CONTRACTUALĂ ȘI PENALITĂȚI</b>", body_bold),
        Paragraph("<b>Art. 5.1.</b> Pentru fiecare zi de întârziere la plată dincolo de scadența de 30 de zile, Beneficiarul datorează Furnizorului o <b>penalitate de întârziere de 0,1% pe zi</b> din suma restantă neachitată.", body_style),
        Paragraph("<b>Art. 5.2.</b> <b>Plafonare Penalități:</b> Cuantumul total al penalităților de întârziere calculate conform Art. 5.1 <b>nu va putea depăși sub nicio formă plafonul maxim de 10%</b> din valoarea debitului principal datorat.", body_style),
        Spacer(1, 4),

        Paragraph("<b>CAPITOLUL VI. STINGEREA DATORIILOR ȘI REZILIEREA</b>", body_bold),
        Paragraph("<b>Art. 6.1.</b> Stingerea debitelor reciproce se realizează conform dispozițiilor de drept comun din Codul Civil român.", body_style),
        Paragraph("<b>Art. 6.2.</b> Rezilierea de plin drept intervine în cazul în care întârzierea la plată depășește 45 de zile lucrătoare, cu punere în întârziere prealabilă de 15 zile.", body_style),
        Spacer(1, 10),

        Table([
            [Paragraph("<b>FURNIZOR:</b><br/>SC AGRO-DISTRIB SUD SRL<br/>Director Gen. Vasile Dumitrescu", body_style),
             Paragraph("<b>BENEFICIAR:</b><br/>SC AGROTERRA LOGISTICS SRL<br/>Administrator Mihai Stanciu", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm], style=[
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0,0), (-1,-1), 8)
        ])
    ]
    return create_pdf(fname, flowables)

def generate_addendum_1():
    fname = "ACT-2024-05_Act_Aditional_1_CTR-2024-005_Preturi_si_Penalitati.pdf"
    flowables = [
        Paragraph("REPUBLICA ROMÂNIA • MODIFICĂRI CONTRACTUALE FORMALE", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=10),
        Paragraph("ACT ADIȚIONAL NR. 1 LA CONTRACTUL DE FURNIZARE", title_style),
        Paragraph("<b>Referință: Contract Cadru Nr. CTR-2024-005 din data de 15.02.2024</b><br/>Încheiat astăzi, <b>20 Iunie 2024</b>", subtitle_style),

        Paragraph("<b>PĂRȚILE:</b> SC AGRO-DISTRIB SUD SRL (Furnizor) și SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (Beneficiar).", body_style),
        Paragraph("Având în vedere fluctuațiile accentuate ale cotațiilor la materii prime și introducerea obligativității transmiterii transporturilor rutiere de mărfuri prin sistemul național de monitorizare, părțile convin următoarele modificări ale Contractului de bază nr. CTR-2024-005:", body_style),
        Spacer(1, 6),

        Paragraph("<b>ARTICOLUL 1. MODIFICAREA REGIMULUI DE PREȚ ȘI DEROGARE TEMPORALĂ</b>", body_bold),
        Paragraph("Articolul 3.1 din Contractul nr. CTR-2024-005 se modifică și va avea următorul conținut:<br/>"
                  "<i>„Prețul unitar de vânzare al produselor se majorează la <b>3.200,00 RON / tonă metrică</b> (exclusiv TVA). "
                  "Prin derogare expresă de la aplicarea generală, acest nou preț de 3.200,00 RON/to este aplicabil <b>strict și exclusiv loturilor livrate și recepționate ulterior datei de 15 Iulie 2024</b>. "
                  "Toate loturile livrate sau recepționate până la data de 15 Iulie 2024 inclusiv rămân facturate la prețul originar stipulat în contractul de bază, respectiv 2.800,00 RON / tonă.”</i>", body_style),
        Spacer(1, 4),

        Paragraph("<b>ARTICOLUL 2. TERMEN DE SCADENȚĂ ȘI CONDIȚIE SUSPENSIVĂ RO E-TRANSPORT</b>", body_bold),
        Paragraph("Articolul 4.1 din Contractul de bază se reformulează astfel:<br/>"
                  "<i>„Termenul de achitare a facturilor emise se reduce de la 30 de zile la <b>15 zile calendaristice</b>. "
                  "Totuși, prin voința concordantă a părților, termenul de 15 zile <b>nu începe să curgă și factura nu devine exigibilă</b> decât de la data la care Furnizorul pune la dispoziția Beneficiarului confirmarea generării și transmiterii <b>codului UIT valabil în sistemul RO e-Transport</b> pentru cursa respectivă. "
                  "În lipsa dovezii codului UIT transmis, scadența este suspendată de drept fără penalități.”</i>", body_style),
        Spacer(1, 4),

        Paragraph("<b>ARTICOLUL 3. MAJORAREA PENALITĂȚILOR ȘI ABROGAREA PLAFONĂRII</b>", body_bold),
        Paragraph("Articolele 5.1 și 5.2 din Contractul nr. CTR-2024-005 se unifică și se modifică după cum urmează:<br/>"
                  "<i>„În ipoteza nerespectării termenului de plată exigibil, Beneficiarul datorează <b>penalități de întârziere majorate la cota de 0,3% pe fiecare zi de întârziere</b> calculată asupra soldului neachitat. "
                  "Părțile decid în mod irevocabil <b>abrogarea expresă a oricărei dispoziții referitoare la plafonare din contractul de bază</b>, eliminându-se limita de 10% prevăzută inițial la Art. 5.2, penalitățile urmând a curge fără plafon până la stingerea debitului.”</i>", body_style),
        Spacer(1, 4),

        Paragraph("<b>ARTICOLUL 4. DISPOZIȚII FINALE</b>", body_bold),
        Paragraph("Celelalte clauze ale Contractului de bază nr. CTR-2024-005 din 15.02.2024 rămân neschimbate și își păstrează întreaga forță juridică.", body_style),
        Spacer(1, 10),

        Table([
            [Paragraph("<b>PENTRU FURNIZOR:</b><br/>SC AGRO-DISTRIB SUD SRL", body_style),
             Paragraph("<b>PENTRU BENEFICIAR:</b><br/>SC AGROTERRA LOGISTICS SRL", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm], style=[
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0,0), (-1,-1), 8)
        ])
    ]
    return create_pdf(fname, flowables)

def generate_addendum_2():
    fname = "ACT-2024-06_Act_Aditional_2_CTR-2024-005_Discount_Retroactiv_Imputatie.pdf"
    flowables = [
        Paragraph("REPUBLICA ROMÂNIA • MODIFICĂRI CONTRACTUALE SUBTILE", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=10),
        Paragraph("ACT ADIȚIONAL NR. 2 LA CONTRACTUL DE FURNIZARE", title_style),
        Paragraph("<b>Referință: Contract Nr. CTR-2024-005 din 15.02.2024 (Modificat prin Actul Adițional Nr. 1 din 20.06.2024)</b><br/>Încheiat astăzi, <b>10 Septembrie 2024</b>", subtitle_style),

        Paragraph("<b>PĂRȚILE:</b> SC AGRO-DISTRIB SUD SRL (Furnizor) și SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (Beneficiar).", body_style),
        Paragraph("Având în vedere volumul semnificativ de tranzacționare înregistrat în a doua parte a anului comercial și dorința părților de a stimula consolidarea parteneriatului prin mecanisme de loialitate și securizare financiară, se convin următoarele:", body_style),
        Spacer(1, 6),

        Paragraph("<b>ARTICOLUL 1. BONUSUL DE VOLUM ȘI RECALCULAREA RETROACTIVĂ A PREȚULUI</b>", body_bold),
        Paragraph("La Capitolul III se introduce un alineat nou, Art. 3.3, cu următorul conținut:<br/>"
                  "<i>„Dacă până la data de <b>01 Noiembrie 2024</b> cantitatea totală cumulată livrată și recepționată de către Beneficiar atinge sau depășește pragul cantitativ de <b>400 de tone metrice</b>, prețul de vânzare pentru <b>întreaga cantitate contractată și livrată în cursul anului 2024 (atât pentru livrările anterioare datei de 15 Iulie, cât și pentru livrările ulterioare)</b> se recalculează retroactiv la prețul unic de favoare de <b>2.950,00 RON / tonă metrică</b>. "
                  "Diferența rezultată din recalibrarea tarifară retroactivă se va regulariza obligatoriu prin emiterea de către Furnizor a unei facturi de stornare/creditare în favoarea Beneficiarului în cel mult 10 zile calendaristice de la atingerea pragului.”</i>", body_style),
        Spacer(1, 4),

        Paragraph("<b>ARTICOLUL 2. DEROGARE PRIVIND ORDINEA DE IMPUTAȚIE A PLĂȚILOR</b>", body_bold),
        Paragraph("Articolul 6.1 din Contractul de bază se înlocuiește prin derogare specială cu următoarea prevedere:<br/>"
                  "<i>„<b>Prin derogare expresă de la normele dispozitive ale Art. 1506 - 1509 din Codul Civil</b>, orice plată sau transfer bancar efectuat de către Beneficiar în contul Furnizorului <b>se va imputa cu prioritate absolută asupra debitului principal restant (valoarea facturilor de marfă)</b>, stingând creanța principală. "
                  "Numai după acoperirea și stingerea integrală a contravalorii mărfii livrate, fondurile rămase vor putea fi alocate stingerii penalităților de întârziere calculate conform Actului Adițional nr. 1.”</i>", body_style),
        Spacer(1, 4),

        Paragraph("<b>ARTICOLUL 3. REINTRODUCEREA UNUI PLAFON MAXIM GLOBAL ASUPRA PENALITĂȚILOR</b>", body_bold),
        Paragraph("Completare la regimul răspunderii contractuale:<br/>"
                  "<i>„Deși prin Actul Adițional nr. 1 s-a eliminat plafonul inițial de 10% per factură, părțile agreează că <b>valoarea cumulată a tuturor penalităților de întârziere pretinse sau percepute de Furnizor pe întreaga durată de derulare a relației contractuale este limitată expres și nu poate depăși sub nicio circumstanță 20% din valoarea cumulată totală a livrărilor recepționate</b> efectiv de către Beneficiar.”</i>", body_style),
        Spacer(1, 4),

        Paragraph("<b>ARTICOLUL 4. EFECTE JURIDICE</b>", body_bold),
        Paragraph("Prezentul act adițional completează și modifică în mod corespunzător Contractul cadru CTR-2024-005 și Actul Adițional nr. 1. Dispozițiile neamendate rămân în vigoare.", body_style),
        Spacer(1, 10),

        Table([
            [Paragraph("<b>PENTRU FURNIZOR:</b><br/>SC AGRO-DISTRIB SUD SRL", body_style),
             Paragraph("<b>PENTRU BENEFICIAR:</b><br/>SC AGROTERRA LOGISTICS SRL", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm], style=[
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0,0), (-1,-1), 8)
        ])
    ]
    return create_pdf(fname, flowables)

if __name__ == "__main__":
    print("[*] Generare PDF-uri puzzle contractual...")
    f1 = generate_contract_base()
    f2 = generate_addendum_1()
    f3 = generate_addendum_2()
    print("[+] Toate cele 3 PDF-uri au fost generate cu succes în /app/uploads!")
