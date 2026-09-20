#!/usr/bin/env python3
"""
Generator & Injector pentru 10 documente criminalistice avansate interconectate
în Cazul 12 (SC AGROTERRA LOGISTICS & DISTRIBUTION SRL).
Documentele adâncesc investigația pe Nordic Consulting, lipsurile de la Silozul Brăila,
controlul inopinat ANAF Antifraudă, extrasele bancare ING cu retrageri cash,
adresa Băncii Transilvania și raportul de inventar anual.
"""

import os
import sys
import hashlib
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register DejaVuSans for 100% accurate Romanian diacritics
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

OUTPUT_DIR = "/app/uploads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontName="DejaVuSans-Bold",
    fontSize=13,
    leading=17,
    alignment=1, # Center
    textColor=colors.HexColor("#1A365D"),
    spaceAfter=12
)

subtitle_style = ParagraphStyle(
    "DocSubTitle",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=9,
    leading=13,
    alignment=1,
    textColor=colors.HexColor("#4A5568"),
    spaceAfter=15
)

body_style = ParagraphStyle(
    "DocBody",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=8.5,
    leading=12.5,
    textColor=colors.HexColor("#2D3748")
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
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#4A5568")
)

table_header_style = ParagraphStyle(
    "TableHeader",
    parent=styles["Normal"],
    fontName="DejaVuSans-Bold",
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#FFFFFF")
)

table_cell_style = ParagraphStyle(
    "TableCell",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#2D3748")
)

chat_msg_style = ParagraphStyle(
    "ChatMsg",
    parent=styles["Normal"],
    fontName="DejaVuSans",
    fontSize=8.5,
    leading=12.5,
    textColor=colors.HexColor("#1A202C")
)

chat_meta_style = ParagraphStyle(
    "ChatMeta",
    parent=styles["Normal"],
    fontName="DejaVuSans-Bold",
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#2B6CB0")
)

def create_pdf(filename, flowables):
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=1.8*cm,
        rightMargin=1.8*cm,
        topMargin=1.8*cm,
        bottomMargin=1.8*cm
    )
    doc.build(flowables)
    print(f"[+] Generat PDF: {filename}")
    return filepath

print("[*] Începem generarea celor 10 documente criminalistice interconectate...")

# ==============================================================================
# 1. PROCES-VERBAL ANAF ANTIFRAUDĂ (CONTROL INOPINAT)
# ==============================================================================
doc1_name = "PROCES_VERBAL_ANAF_Antifrauda_Control_Inopinat_Octombrie_2024.pdf"
doc1_story = [
    Paragraph("MINISTERUL FINANȚELOR • AGENȚIA NAȚIONALĂ DE ADMINISTRARE FISCALĂ<br/>DIRECȚIA GENERALĂ ANTIFRAUDĂ FISCALĂ • DIRECȚIA REGIONALĂ 3 ALEXANDRIA", header_box_style),
    HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#C53030"), spaceAfter=12),
    Paragraph("PROCES-VERBAL DE CONTROL INOPINAT", title_style),
    Paragraph("<b>Nr. 18492 / 14.10.2024</b> • Încheiat la sediul SC AGROTERRA LOGISTICS & DISTRIBUTION SRL", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "Subsemnații inspectori antifraudă Popescu Gabriel și Ionescu Dumitru, în temeiul Legii nr. 207/2015 privind Codul de procedură fiscală și OUG nr. 74/2013, am efectuat un control inopinat la contribuabilul <b>SC AGROTERRA LOGISTICS & DISTRIBUTION SRL</b> (CUI RO34891204, J40/1102/2015), reprezentată legal prin administrator <b>Radu Teodorescu</b>.<br/><br/>"
        "<b>OBIECTUL CONTROLULUI:</b> Verificarea realității și conținutului economic al tranzacțiilor înregistrate cu furnizorul <b>SC NORDIC CONSULTING & MANAGEMENT SRL</b> (CUI RO39481022, Giurgiu), precum și a fluxurilor logistice de cereale derulate în perioada 2023 - 2024.<br/><br/>"
        "<b>CONSTATĂRI PRINCIPALE:</b><br/>"
        "1. În perioada analizată, societatea verificată a dedus cheltuieli de consultanță și management în cuantum de <b>183.150,00 RON</b> (Factura NOR-2023-0112 în valoare de 74.250 RON și Factura NOR-2024-0095 în valoare de 108.900 RON).<br/>"
        "2. Organele de control au solicitat documente justificative, rapoarte de activitate și foi de pontaj care să ateste prestarea efectivă a serviciilor. Administratorul nu a putut prezenta rapoarte contemporane emiterii facturilor, prezentând doar un material sumar nesemnat.<br/>"
        "3. Din interogarea bazei de date REVISAL și D112 rezultă că furnizorul SC NORDIC CONSULTING & MANAGEMENT SRL <b>nu deține niciun salariat</b> și nu are subcontractori declarați pentru perioada 2023-2024.<br/>"
        "4. Din analiza logurilor conexiunilor bancare electronice (IP Log) furnizate de instituțiile de credit, se constată că ordinele de plată ale AGROTERRA și operațiunile din contul NORDIC CONSULTING au fost accesate în repetate rânduri de la <b>aceeași adresă IP statică</b> (86.120.x.x) alocată sediului administrativ al AGROTERRA din București.<br/>"
        "5. În ceea ce privește livrările de cereale din data de 18.06.2024 (Aviz nr. 0089 de 450,00 tone), s-a constatat că societatea a încasat integral contravaloarea de 539.550 RON de la client, deși la Silozul Brăila au intrat faptic doar 388,50 tone, diferența de 61,50 tone fiind descărcată fără justificare fiscală.<br/><br/>"
        "<b>CONCLUZII ȘI MĂSURI:</b> Se dispune sesizarea organelor de urmărire penală conform art. 9 alin. (1) lit. c) din Legea 241/2005 pentru evaziune fiscală prin operațiuni fictive și înaintarea dosarului către Serviciul de Inspecție Fiscală pentru stabilirea bazei de impunere.",
        body_style
    ),
    Spacer(1, 15),
    Table([
        [Paragraph("<b>Inspectori DGAF:</b><br/>Popescu Gabriel (semnătură)<br/>Ionescu Dumitru (semnătură)", body_style),
         Paragraph("<b>Reprezentant Contribuabil:</b><br/>Radu Teodorescu - Administrator<br/><i>„Am luat la cunoștință, formulez obiecțiuni în termen legal.”</i>", body_style)]
    ], colWidths=[8.5*cm, 8.5*cm])
]
create_pdf(doc1_name, doc1_story)

# ==============================================================================
# 2. DECIZIE DE IMPUNERE FISCALĂ ANAF
# ==============================================================================
doc2_name = "DECIZIE_IMPUNERE_ANAF_Nr_88204_Noiembrie_2024.pdf"
doc2_story = [
    Paragraph("MINISTERUL FINANȚELOR • AGENȚIA NAȚIONALĂ DE ADMINISTRARE FISCALĂ<br/>DIRECȚIA GENERALĂ DE ADMINISTRARE A MARILOR CONTRIBUABILI", header_box_style),
    HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A365D"), spaceAfter=12),
    Paragraph("DECIZIE DE IMPUNERE", title_style),
    Paragraph("<b>Nr. 88204 / 05.11.2024</b> • Privind obligațiile fiscale principale și accesorii", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "În baza Procesului-Verbal de Control nr. 18492/14.10.2024 încheiat de Direcția Generală Antifraudă Fiscală, s-au recalculat obligațiile fiscale datorate de contribuabilul <b>SC AGROTERRA LOGISTICS & DISTRIBUTION SRL</b> (CUI RO34891204).<br/><br/>"
        "Se constată caracterul artificial și nedeductibil al achizițiilor de servicii de la SC NORDIC CONSULTING & MANAGEMENT SRL (Facturile NOR-2023-0112 și NOR-2024-0095), precum și neînregistrarea veniturilor reale din diferențele de custodie.<br/><br/>"
        "<b>SITUAȚIA OBLIGAȚIILOR STABILITE SUPLIMENTAR:</b>",
        body_style
    ),
    Spacer(1, 8),
    Table([
        [Paragraph("<b>Tip Impozit / Taxă</b>", table_header_style), Paragraph("<b>Baza Impozabilă (RON)</b>", table_header_style), Paragraph("<b>Debit Principal (RON)</b>", table_header_style), Paragraph("<b>Dobânzi & Penalități (RON)</b>", table_header_style), Paragraph("<b>Total Datorat (RON)</b>", table_header_style)],
        [Paragraph("Taxa pe Valoarea Adăugată (TVA)", table_cell_style), Paragraph("183.150,00", table_cell_style), Paragraph("34.800,00", table_cell_style), Paragraph("7.820,00", table_cell_style), Paragraph("42.620,00", table_cell_style)],
        [Paragraph("Impozit pe Profit (16%)", table_cell_style), Paragraph("183.150,00", table_cell_style), Paragraph("29.304,00", table_cell_style), Paragraph("6.460,00", table_cell_style), Paragraph("35.764,00", table_cell_style)],
        [Paragraph("<b>TOTAL GENERAL</b>", table_header_style), Paragraph("<b>-</b>", table_header_style), Paragraph("<b>64.104,00</b>", table_header_style), Paragraph("<b>14.280,00</b>", table_header_style), Paragraph("<b>78.384,00</b>", table_header_style)]
    ], colWidths=[4.2*cm, 3.2*cm, 3.2*cm, 3.2*cm, 3.2*cm], style=[
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#ED8936")),
        ('PADDING', (0,0), (-1,-1), 4)
    ]),
    Spacer(1, 12),
    Paragraph(
        "<b>TERMEN DE PLATĂ:</b> Suma totală de <b>78.384,00 RON</b> va fi achitată în contul unic deschis la Trezoreria Sector 1 București în termen de 30 de zile de la comunicarea prezentei decizii. În caz de neplată, se va proceda la executarea silită prin poprirea conturilor bancare deschise la Banca Transilvania și BCR.<br/>"
        "Prezenta decizie poate fi contestată în termen de 45 de zile conform art. 268 din Codul de procedură fiscală.",
        body_style
    ),
    Spacer(1, 15),
    Paragraph("Șef Serviciu Inspecție Fiscală: Ec. Viorica Stănescu (ștampilă oficială și semnătură)", body_bold)
]
create_pdf(doc2_name, doc2_story)

# ==============================================================================
# 3. EXTRAS DE CONT BANCAR ING - NORDIC CONSULTING MANAGEMENT (RETRAGERI CASH)
# ==============================================================================
doc3_name = "EXTRAS_BANCAR_ING_Nordic_Consulting_Management_Iulie_2024.pdf"
doc3_story = [
    Paragraph("ING BANK N.V. AMSTERDAM • SUCURSALA BUCUREȘTI<br/>EXTRAS DE CONT PENTRU PERSOANE JURIDICE", header_box_style),
    HRFlowable(width="100%", thickness=1, color=colors.HexColor("#FF6200"), spaceAfter=10),
    Paragraph("EXTRAS DE CONT CURENT • IUNIE - IULIE 2024", title_style),
    Paragraph("Titular: <b>SC NORDIC CONSULTING & MANAGEMENT SRL</b> • CUI: RO39481022 • IBAN: RO49INGB0000999901234567 • Moneda: RON", subtitle_style),
    Spacer(1, 6),
    Table([
        [Paragraph("<b>Data</b>", table_header_style), Paragraph("<b>Referință / Tip Operațiune</b>", table_header_style), Paragraph("<b>Detalii Tranzacție & Partener</b>", table_header_style), Paragraph("<b>Debit (-)</b>", table_header_style), Paragraph("<b>Credit (+)</b>", table_header_style), Paragraph("<b>Sold (RON)</b>", table_header_style)],
        [Paragraph("20.06.2024", table_cell_style), Paragraph("Sold precedent", table_cell_style), Paragraph("Report sold disponibil", table_cell_style), Paragraph("-", table_cell_style), Paragraph("-", table_cell_style), Paragraph("250,00", table_cell_style)],
        [Paragraph("26.06.2024", table_cell_style), Paragraph("OP 418 / Virament", table_cell_style), Paragraph("Încasare cval Factura NOR-2024-0095 de la <b>SC AGROTERRA LOGISTICS SRL</b>", table_cell_style), Paragraph("-", table_cell_style), Paragraph("108.900,00", table_cell_style), Paragraph("109.150,00", table_cell_style)],
        [Paragraph("27.06.2024", table_cell_style), Paragraph("ATM / Card 9021", table_cell_style), Paragraph("Retragere numerar ATM ING Giurgiu - card asociat George Costea", table_cell_style), Paragraph("15.000,00", table_cell_style), Paragraph("-", table_cell_style), Paragraph("94.150,00", table_cell_style)],
        [Paragraph("28.06.2024", table_cell_style), Paragraph("Ghișeu / Retragere", table_cell_style), Paragraph("Retragere numerar ghișeu - George Costea (mențiune: restituire împrumut asociat)", table_cell_style), Paragraph("40.000,00", table_cell_style), Paragraph("-", table_cell_style), Paragraph("54.150,00", table_cell_style)],
        [Paragraph("29.06.2024", table_cell_style), Paragraph("Ghișeu / Retragere", table_cell_style), Paragraph("Retragere numerar ghișeu ING Sucursala Unirii București - George Costea", table_cell_style), Paragraph("40.000,00", table_cell_style), Paragraph("-", table_cell_style), Paragraph("14.150,00", table_cell_style)],
        [Paragraph("02.07.2024", table_cell_style), Paragraph("Comision", table_cell_style), Paragraph("Comision administrare pachet banking și eliberare numerar", table_cell_style), Paragraph("150,00", table_cell_style), Paragraph("-", table_cell_style), Paragraph("14.000,00", table_cell_style)]
    ], colWidths=[2.2*cm, 2.8*cm, 6.0*cm, 2.0*cm, 2.2*cm, 2.0*cm], style=[
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#FF6200")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('PADDING', (0,0), (-1,-1), 4)
    ]),
    Spacer(1, 10),
    Paragraph("Total rulaj debitor: 95.150,00 RON • Total rulaj creditor: 108.900,00 RON • Rulaj numerar retras în 72 ore: <b>95.000,00 RON</b>.", body_bold)
]
create_pdf(doc3_name, doc3_story)

# ==============================================================================
# 4. CONTRACT ÎMPRUMUT ASOCIAT (INSTRUMENT DISIMULARE RETRAGERI CASH)
# ==============================================================================
doc4_name = "CONTRACT_IMPRUMUT_ASOCIAT_Nordic_Consulting_GeorgeCostea_2023.pdf"
doc4_story = [
    Paragraph("DOCUMENT INTERN PERSOANĂ JURIDICĂ • REGISTRU CONTRACTE NORDIC", header_box_style),
    HRFlowable(width="100%", thickness=1, color=colors.HexColor("#4A5568"), spaceAfter=12),
    Paragraph("CONTRACT DE ÎMPRUMUT ASOCIAT (FĂRĂ DOBÂNDĂ)", title_style),
    Paragraph("<b>Nr. 12 / 15.01.2023</b> • Încheiat la Giurgiu", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "<b>PĂRȚILE CONTRACTANTE:</b><br/>"
        "1. <b>George V. Costea</b>, cetățean român, domiciliat în Mun. Giurgiu, identificat prin CI seria GG nr. 391024, în calitate de <i>Asociat Unic și Administrator</i>,<br/>"
        "și<br/>"
        "2. <b>SC NORDIC CONSULTING & MANAGEMENT SRL</b>, persoană juridică română, CUI RO39481022, în calitate de <i>Societate Împrumutată</i>.<br/><br/>"
        "<b>ART. 1. OBIECTUL CONTRACTULUI:</b><br/>"
        "Asociatul unic acordă societății un împrumut financiar temporar în cuantum de <b>150.000,00 RON</b>, acordat în numerar, având ca destinație susținerea capitalului de lucru și a cheltuielilor curente de operare ale societății.<br/><br/>"
        "<b>ART. 2. TERMENE ȘI RESTITUIRE:</b><br/>"
        "Împrumutul este acordat fără dobândă. Restituirea sumelor se va efectua eșalonat, în numerar sau prin virament bancar, pe măsura constituirii disponibilităților bănești în contul societății, cu termen limită 31.12.2025.<br/><br/>"
        "<b>ART. 3. CLAUZE FINALE:</b><br/>"
        "Părțile convin ca orice sumă încasată de societate din contracte de consultanță să poată fi alocată cu prioritate rambursării împrumutului asociatului.",
        body_style
    ),
    Spacer(1, 20),
    Table([
        [Paragraph("<b>ÎMPRUMUTĂTOR (Asociat Unic)</b><br/>George V. Costea<br/>(Semnătură olografă)", body_style),
         Paragraph("<b>SOCIETATEA ÎMPRUMUTATĂ</b><br/>SC NORDIC CONSULTING SRL<br/>Reprezentată prin George Costea<br/>(Ștampilă societate)", body_style)]
    ], colWidths=[8.5*cm, 8.5*cm])
]
create_pdf(doc4_name, doc4_story)

# ==============================================================================
# 5. EXPORT CHAT WHATSAPP: RADU TEODORESCU & AVOCAT CRISTIAN POPA
# ==============================================================================
doc5_name = "EXPORT_CHAT_WHATSAPP_RaduTeodorescu_AvocatPopa_Octombrie2024.pdf"
doc5_story = [
    Paragraph("ARHIVĂ DIGITALĂ CRIMINALISTICĂ • DISPOZITIV RADU TEODORESCU", header_box_style),
    HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15),
    Paragraph("EXPORT CONVERSAȚIE WHATSAPP • GESTIUNE CONTROL FISCAL", title_style),
    Paragraph("Participanți: <b>Radu Teodorescu</b> (Administrator Agroterra) & <b>Avocat Cristian Popa</b><br/>Interval extras: 15.10.2024 - 18.10.2024", subtitle_style),
    Spacer(1, 8)
]
chat5_msgs = [
    ("15.10.2024, 18:30", "Radu Teodorescu", "Domnule avocat, au venit cei de la Antifrauda in control inopinat ieri. Au luat la puricat facturile cu Nordic din 2023 si 2024. Ne cer rapoarte de activitate si livrabile pentru consultanta. Zic ca Nordic nu are niciun angajat si ca au extras IP-urile de internet banking."),
    ("15.10.2024, 18:45", "Avocat Cristian Popa", "E groasa daca au legat IP-urile de la voi de contul lui Nordic. Trebuie urgent sa depunem la dosar rapoarte de activitate semnate de George Costea inainte sa emita decizia de impunere. Aveti rapoarte intocmite contemporan cu facturile?"),
    ("15.10.2024, 18:52", "Radu Teodorescu", "Nu avem niciun raport din pacate. Mihai s-a ocupat doar de contract si plati. I-am zis lui Costea sa faca ceva pe repede inainte, dar omul zice ca e plecat din tara si nu are cum sa scrie analize economice."),
    ("16.10.2024, 09:15", "Avocat Cristian Popa", "Pregatiti voi la sediu un raport de vreo 10-15 pagini despre piata cerealelor, tabele si grafice descarcate de pe net de pe bursele de marfuri, il datati retroactiv pe 24 iunie 2024 pentru factura NOR-2024-0095 de 108.900 lei, i-l trimiteti pe mail lui Costea sa-l semneze olograf si mi-l aduceti la birou. Trebuie sa justificam substanta economica!"),
    ("18.10.2024, 14:20", "Radu Teodorescu", "Am compilat raportul pe trading cereale, l-a semnat Costea scanat. Dar mai e o buba mare: la banca a vazut Antifrauda ca a doua zi dupa ce i-am virat banii lui Nordic, Costea a scos 95.000 lei cash de la bancomat si ghiseu. Sper sa nu ne cheme la penal."),
    ("18.10.2024, 14:35", "Avocat Cristian Popa", "La numerar o dam pe restituire imprumut asociat, are contract vechi facut din 2023. Important e sa castigam timp pana la contestatie.")
]
for sender_time, sender_name, content in chat5_msgs:
    msg_table = Table([
        [Paragraph(f"<b>[{sender_time}] {sender_name}:</b>", chat_meta_style)],
        [Paragraph(content, chat_msg_style)]
    ], colWidths=[17.0*cm], style=[
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 6)
    ])
    doc5_story.append(msg_table)
    doc5_story.append(Spacer(1, 5))
create_pdf(doc5_name, doc5_story)

# ==============================================================================
# 6. RAPORT DE ACTIVITATE FABRICAT RETROACTIV (NORDIC CONSULTING)
# ==============================================================================
doc6_name = "RAPORT_ACTIVITATE_Nordic_Consulting_Factura_NOR-2024-0095.pdf"
doc6_story = [
    Paragraph("SC NORDIC CONSULTING & MANAGEMENT SRL • DEPARTAMENT TRADING", header_box_style),
    HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2B6CB0"), spaceAfter=12),
    Paragraph("RAPORT DE ACTIVITATE PRIVIND ASISTENȚA STRATEGICĂ ÎN TRADING", title_style),
    Paragraph("Livrabil aferent Facturii fiscale nr. <b>NOR-2024-0095 / 25.06.2024</b> (Valoare: 108.900 RON)<br/>Perioada de referință: Trimestrul II 2024 • Data raportului: 24.06.2024", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "<b>BENEFICIAR:</b> SC AGROTERRA LOGISTICS & DISTRIBUTION SRL<br/>"
        "<b>PRESTATOR:</b> SC NORDIC CONSULTING & MANAGEMENT SRL (Consultant: George V. Costea)<br/><br/>"
        "<b>1. OBIECTIVELE MANDATULUI DE CONSULTANȚĂ:</b><br/>"
        "Prezentul raport atestă activitățile prestate de Nordic Consulting în baza Contractului nr. 8/12.04.2023, constând în elaborarea scenariilor optime de livrare pentru campania agricolă de vară 2024, monitorizarea fluctuației cotațiilor Euronext/MATIF la grâu și optimizarea lanțului logistic pe ruta Bărăgan - Port Constanța.<br/><br/>"
        "<b>2. CONSTATĂRI DE PIAȚĂ ȘI RECOMANDĂRI STRATEGICE:</b><br/>"
        "- Cotațiile bursiere la grâu panificație au înregistrat o volatilitate de +/- 14 EUR/tonă în portul Constanța în lunile mai-iunie 2024.<br/>"
        "- Se recomandă menținerea contractelor ferme de vânzare la prețuri cuprinse între 220 și 235 EUR/to și externalizarea riscului de manipulare către operatorii de siloz din zona Brăila / Galați.<br/>"
        "- În cazul apariției unor abateri cantitative pe traseul de transport rutier, se recomandă compensarea valorică prin servicii conexe și conservarea relațiilor cu clienții majori din Republica Moldova.<br/><br/>"
        "<b>3. CONCLUZII FINALE:</b><br/>"
        "Serviciile de consultanță facturate au generat o optimizare estimată de minim 25.000 EUR pentru beneficiar prin evitarea vânzărilor la minime bursiere.",
        body_style
    ),
    Spacer(1, 20),
    Table([
        [Paragraph("<b>PRESTATOR:</b><br/>SC NORDIC CONSULTING & MANAGEMENT SRL<br/>Consultant George V. Costea (semnătură olografă)", body_style),
         Paragraph("<b>RECEPȚIONAT BENEFICIAR:</b><br/>SC AGROTERRA LOGISTICS SRL<br/>Director Comercial Mihai Stanciu (semnătură)", body_style)]
    ], colWidths=[8.5*cm, 8.5*cm])
]
create_pdf(doc6_name, doc6_story)

# ==============================================================================
# 7. PROCES-VERBAL CONSTATARE DIFERENȚE SILOZ BRĂILA (LIPSA 61.50 TONE)
# ==============================================================================
doc7_name = "PROCES_VERBAL_CONSTATARE_DIFERENTE_Siloz_Braila_18_Iunie_2024.pdf"
doc7_story = [
    Paragraph("OPERATOR PORTUAR & SILOZ DE CEREALE • BAZA SILOZ DUNĂREAN BRĂILA", header_box_style),
    HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D69E2E"), spaceAfter=12),
    Paragraph("PROCES-VERBAL DE CONSTATARE DIFERENȚE CANTITATIVE LA DESCĂRCARE", title_style),
    Paragraph("<b>Nr. 418 / 18.06.2024, ora 17:15</b> • Siloz Celula C-14 Dunăre", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "Încheiat astăzi, 18.06.2024, la sediul Bazei Siloz Dunărean Brăila, între comisia de recepție formată din <b>Ing. Marin Enache</b> (Șef Siloz) și delegatul transportatorului <b>Vasile Dumitru</b> (Șofer Coordonator, CI seria RR nr. 491024), delegat al SC TRANS-CARGO NORD SRL / AGROTERRA.<br/><br/>"
        "<b>CONSTATĂRI LA CÂNTĂRIRE POD BASCULĂ:</b><br/>"
        "- Document de însoțire: Aviz de Însoțire a Mărfii seria AVZ nr. 0089 din 18.06.2024 emis de SC AGROTERRA LOGISTICS SRL.<br/>"
        "- Număr mijloace de transport sosite: convoi de <b>18 autocamioane</b> (cap tractor + semiremorcă basculabilă).<br/>"
        "- Cantitate declarată pe aviz: <b>450,00 tone grâu panificație</b> (câte 25,00 tone/camion).<br/>"
        "- Masa totală brută cântărită la intrare pe cântar electronic omologat metrologic: <b>681,10 tone</b>.<br/>"
        "- Masa totală a camioanelor goale (tara) la ieșire: <b>292,60 tone</b>.<br/>"
        "- <b>CANTITATE NETĂ EFECTIV INTRODUSĂ ÎN CELULELE SILOZULUI: 388,50 TONE.</b><br/>"
        "- <b>DIFERENȚĂ CANTITATIVĂ ÎN MINUS CONSTATATĂ: -61,50 TONE (-13,66%).</b><br/><br/>"
        "<b>MENTIUNI ȘI DISPOZIȚII:</b><br/>"
        "Conducerea silozului a refuzat inițial descărcarea fără confirmare scrisă a suportării diferenței. La ora 14:35, ca urmare a acordului telefonic transmis de administratorul Cumpărătorului (Radu Teodorescu), s-a procedat la descărcarea cerealelor în celula C-14, menționându-se pe borderoul de cântar nr. 2024-089 cantitatea real recepționată de 388,50 tone.",
        body_style
    ),
    Spacer(1, 20),
    Table([
        [Paragraph("<b>COMISIE SILOZ:</b><br/>Ing. Marin Enache - Șef Siloz Brăila<br/>(Semnătură și ștampilă metrologică)", body_style),
         Paragraph("<b>DELEGAT TRANSPORT:</b><br/>Vasile Dumitru - Coordonator Flotă<br/><i>„Confirm descărcarea faptică a 388,50 tone.”</i>", body_style)]
    ], colWidths=[8.5*cm, 8.5*cm])
]
create_pdf(doc7_name, doc7_story)

# ==============================================================================
# 8. NOTĂ CONTABILĂ DE REGULARIZARE STOC AGROTERRA (ARTIFICIU CONTABIL)
# ==============================================================================
doc8_name = "NOTA_CONTABILA_REGULARIZARE_STOC_NC-2024-0618.pdf"
doc8_story = [
    Paragraph("SC AGROTERRA LOGISTICS & DISTRIBUTION SRL • DEPARTAMENT CONTABILITATE", header_box_style),
    HRFlowable(width="100%", thickness=1, color=colors.HexColor("#718096"), spaceAfter=12),
    Paragraph("NOTĂ CONTABILĂ DE REGULARIZARE GESTIUNE STOCURI", title_style),
    Paragraph("<b>Nr. NC-2024-0618 din 25.06.2024</b> • Jurnal Operațiuni Diverse", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "Prezenta notă contabilă reglementează scriptic diferența cantitativă de <b>61,50 tone grâu</b> rezultată la descărcarea convoiului de 18 camioane la Silozul Brăila din data de 18.06.2024 (Aviz nr. 0089).<br/>"
        "Întocmită de: Elena Dumitrescu (Contabil șef) • Aprobată de: Radu Teodorescu (Administrator).<br/><br/>"
        "<b>ÎNREGISTRĂRI CONTABILE:</b>",
        body_style
    ),
    Spacer(1, 8),
    Table([
        [Paragraph("<b>Cont Debitor</b>", table_header_style), Paragraph("<b>Cont Creditor</b>", table_header_style), Paragraph("<b>Suma (RON)</b>", table_header_style), Paragraph("<b>Explicația Operațiunii</b>", table_header_style)],
        [Paragraph("6588<br/><i>Alte cheltuieli de exploatare</i>", table_cell_style), Paragraph("371<br/><i>Mărfuri (Grâu panificație)</i>", table_cell_style), Paragraph("73.800,00", table_cell_style), Paragraph("Descărcare stoc scriptic 61,50 tone grâu @ 1.200 lei/to asimilate perisabilităților și tasării la transport conform Deciziei interne nr. 44/2024.", table_cell_style)],
        [Paragraph("4111.02<br/><i>Cereal Grup Moldova SA</i>", table_cell_style), Paragraph("707<br/><i>Venituri din vânzarea mărfurilor</i>", table_cell_style), Paragraph("539.550,00", table_cell_style), Paragraph("Menținere facturare integrală pe cantitatea contractuală de 450 tone (Factura FACT-2024-0089).", table_cell_style)]
    ], colWidths=[4.0*cm, 4.0*cm, 2.5*cm, 6.5*cm], style=[
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#718096")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('PADDING', (0,0), (-1,-1), 4)
    ]),
    Spacer(1, 10),
    Paragraph(
        "<b>OBSERVAȚIE DE CONFORMITATE:</b> Conform Normelor legale privind perisabilitățile (HG 831/2004), perisabilitatea maximă admisă pentru transportul cerealelor este de <b>0,50%</b> (maxim 2,25 tone la un volum de 450 to). Înregistrarea a 61,50 tone (13,66%) pe cheltuieli nedeductibile fără proces-verbal de distrugere sau autorizație fitosanitară reprezintă risc fiscal major.",
        body_style
    ),
    Spacer(1, 15),
    Table([
        [Paragraph("<b>Întocmit:</b> Elena Dumitrescu (Contabilitate)", body_style),
         Paragraph("<b>Aprobat:</b> Radu Teodorescu (Administrator)", body_style)]
    ], colWidths=[8.5*cm, 8.5*cm])
]
create_pdf(doc8_name, doc8_story)

# ==============================================================================
# 9. ADRESĂ OFICIALĂ BANCA TRANSILVANIA (AUDIT GARANȚII LINIE CREDIT)
# ==============================================================================
doc9_name = "ADRESA_BANCA_TRANSILVANIA_Audit_Garantii_Credit_Noiembrie_2024.pdf"
doc9_story = [
    Paragraph("BANCA TRANSILVANIA S.A. • DIVIZIA AGRIBUSINESS & CORPORATE RISK<br/>SUCURSALA BUCUREȘTI NORD", header_box_style),
    HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#D69E2E"), spaceAfter=12),
    Paragraph("NOTIFICARE DE CONFORMITATE ȘI AUDIT GAJURI STOCURI", title_style),
    Paragraph("<b>Nr. BT-CRD-88219 / 20.11.2024</b> • Referință Contract Credit nr. 412/18.05.2022", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "Către: <b>SC AGROTERRA LOGISTICS & DISTRIBUTION SRL</b><br/>"
        "În atenția: Domnului Radu Teodorescu - Administrator<br/><br/>"
        "Stimate domnule Teodorescu,<br/><br/>"
        "Prin prezenta vă aducem la cunoștință că, în cadrul monitorizării trimestriale a facilității de credit acordate prin Contractul de Credit nr. 412/18.05.2022 (linie de credit pentru capital de lucru în cuantum de <b>2.500.000,00 RON</b>), Direcția de Risc a Băncii a luat act de măsurile de control fiscal instituite de ANAF Antifraudă.<br/><br/>"
        "Având în vedere că facilitatea de credit este garantată cu <b>Gaj fără deposedare asupra stocurilor de cereale</b> aflate în custodie la Silozul Brăila și Silozul Călărași conform Recipisei de Gaj nr. 99201:<br/>"
        "1. Vă solicităm transmiterea în termen de <b>5 zile lucrătoare</b> a dovezilor de existență fizică a stocului minim gajat de <b>1.200 tone grâu</b> și raportul de inspectare a stocurilor întocmit de o companie independentă de supraveghere (SGS sau Bureau Veritas).<br/>"
        "2. Vă solicităm clarificări cu privire la neconcordanțele volumice semnalate de organele fiscale referitoare la livrările din data de 18.06.2024.<br/><br/>"
        "În situația în care societatea dumneavoastră nu face dovada integrității cantitative a stocurilor ipotecate până la data de <b>15.12.2024</b>, Banca își rezervă dreptul contractual de a declara <b>scadența anticipată a întregului credit</b> și de a iniția executarea silită a biletelor la ordin avalizate de administrator.",
        body_style
    ),
    Spacer(1, 15),
    Paragraph("Cu stimă,<br/><b>Director Risc Corporativ:</b> Laurențiu Dobre<br/><b>Manager Relații Agribusiness:</b> Carmen Preda<br/>(Semnături autorizate și ștampilă bancară)", body_style)
]
create_pdf(doc9_name, doc9_story)

# ==============================================================================
# 10. RAPORT FINAL AUDIT INTERN INVENTARIERE ANUALĂ STOCURI
# ==============================================================================
doc10_name = "RAPORT_AUDIT_INTERN_INVENTAR_ANUAL_Decembrie_2024.pdf"
doc10_story = [
    Paragraph("SC AGROTERRA LOGISTICS & DISTRIBUTION SRL • DEPARTAMENT AUDIT INTERN", header_box_style),
    HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A365D"), spaceAfter=12),
    Paragraph("RAPORT DE AUDIT INTERN PRIVIND REZULTATELE INVENTARIERII ANUALE", title_style),
    Paragraph("<b>Nr. 904 / 22.12.2024</b> • Inventarierea generală a patrimoniului la 30.11.2024", subtitle_style),
    Spacer(1, 8),
    Paragraph(
        "În conformitate cu Decizia de Inventariere nr. 52/15.11.2024 emisă de conducerea societății, Comisia de inventariere formată din <b>Ec. Ioana Rădulescu</b> (Auditor intern), <b>Ing. Marin Enache</b> (Gestionar siloz) și <b>Vasile Dumitru</b> (Membru) a procedat la confruntarea stocurilor faptice cu cele scriptice din evidența contabilă.<br/><br/>"
        "<b>SITUAȚIA COMPARATIVĂ A STOCURILOR DE CEREALE:</b>",
        body_style
    ),
    Spacer(1, 8),
    Table([
        [Paragraph("<b>Sortiment Marfă</b>", table_header_style), Paragraph("<b>Locație Depozitare</b>", table_header_style), Paragraph("<b>Stoc Scriptic (To)</b>", table_header_style), Paragraph("<b>Stoc Faptic (To)</b>", table_header_style), Paragraph("<b>Diferență (To)</b>", table_header_style), Paragraph("<b>Valoare Prejudiciu (RON)</b>", table_header_style)],
        [Paragraph("Grâu panificație", table_cell_style), Paragraph("Siloz Brăila (Celula C-14)", table_cell_style), Paragraph("450,00", table_cell_style), Paragraph("388,50", table_cell_style), Paragraph("<b>-61,50</b>", table_cell_style), Paragraph("73.800,00", table_cell_style)],
        [Paragraph("Grâu calitatea I", table_cell_style), Paragraph("Siloz Călărași", table_cell_style), Paragraph("1.000,00", table_cell_style), Paragraph("919,20", table_cell_style), Paragraph("<b>-80,80</b>", table_cell_style), Paragraph("96.960,00", table_cell_style)],
        [Paragraph("Porumb boabe", table_cell_style), Paragraph("Siloz Giurgiu", table_cell_style), Paragraph("800,00", table_cell_style), Paragraph("800,00", table_cell_style), Paragraph("0,00", table_cell_style), Paragraph("0,00", table_cell_style)],
        [Paragraph("<b>TOTAL LIPSURI</b>", table_header_style), Paragraph("<b>-</b>", table_header_style), Paragraph("<b>2.250,00</b>", table_header_style), Paragraph("<b>2.107,70</b>", table_header_style), Paragraph("<b>-142,30</b>", table_header_style), Paragraph("<b>170.760,00</b>", table_header_style)]
    ], colWidths=[3.2*cm, 3.8*cm, 2.4*cm, 2.4*cm, 2.2*cm, 3.0*cm], style=[
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E53E3E")),
        ('PADDING', (0,0), (-1,-1), 4)
    ]),
    Spacer(1, 10),
    Paragraph(
        "<b>CONCLUZIILE AUDITULUI:</b><br/>"
        "1. S-a constatat un deficit total nejustificat de <b>142,30 tone grâu</b>, în valoare de <b>170.760,00 RON</b>.<br/>"
        "2. Regularizarea sumelor prin note contabile de perisabilitate (precum NC-2024-0618) contravine legislației în vigoare și a fost deja contestată de ANAF Antifraudă în Procesul-Verbal nr. 18492/2024.<br/>"
        "3. Lipsa celor 142,30 tone pune în pericol menținerea liniei de credit de la Banca Transilvania, stocul faptic fiind sub plafonul gajat.<br/>"
        "4. Se recomandă luarea de măsuri urgente de recuperare sau sesizarea organelor abilitate.",
        body_style
    ),
    Spacer(1, 15),
    Table([
        [Paragraph("<b>Auditor Intern:</b><br/>Ec. Ioana Rădulescu<br/>(Semnătură)", body_style),
         Paragraph("<b>Comisie Inventar:</b><br/>Marin Enache (Gestionar)<br/>Vasile Dumitru (Membru)", body_style)]
    ], colWidths=[8.5*cm, 8.5*cm])
]
create_pdf(doc10_name, doc10_story)

print("[*] Toate cele 10 PDF-uri au fost generate cu succes în /app/uploads!")
