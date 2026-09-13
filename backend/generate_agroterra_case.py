#!/usr/bin/env python3
"""
Generator pentru dosarul forensic 'SC AGROTERRA LOGISTICS & DISTRIBUTION SRL' (2023 - 2024).
Produce 60 de PDF-uri profesionale, 100% conforme cu realitatea corporativă și contabilă românească.
Fără hinturi evidente de fraudă - toate anomaliile sunt strict structurale și transversale.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register DejaVuSans for 100% accurate Romanian diacritics (ă, î, â, ș, ț)
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

OUTPUT_DIR = "/app/test_documents/caz_agroterra"
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
normal = styles["Normal"]

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
    return filepath

print(f"[*] Incepem generarea celor 60 de PDF-uri in {OUTPUT_DIR}...")

# -------------------------------------------------------------
# 1. CONTRACTE COMERCIALE (8 DOCUMENTE)
# -------------------------------------------------------------
contracte = [
    (
        "CTR-2023-001_Contract_Furnizare_Fertilizanti_AGRO-CHIM.pdf",
        "CONTRACT DE FURNIZARE PRODUSE CHIMICE ȘI FERTILIZANȚI",
        "Nr. 104 / 09.01.2023",
        "SC AGRO-CHIM FERTILIZANTI SRL (Constanța, CUI RO28491024)",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (București, CUI RO34891204)",
        "Furnizare uree granulată, azotat de amoniu și complexe NPK pe parcursul anului 2023.",
        "Valoare estimată: 850.000 RON. Termen de plată: 30 de zile de la emiterea facturii fiscale. Penalități de întârziere: 0.15% pe zi de întârziere din suma datorată, calculate de drept fără punere în întârziere.",
        "Livrarea se va efectua DAP depozit Călărași / Giurgiu pe baza comenzilor ferme emise de Cumpărător."
    ),
    (
        "CTR-2023-002_Contract_Servicii_Transport_TRANS-CARGO.pdf",
        "CONTRACT DE PRESTĂRI SERVICII DE TRANSPORT RUTIER DE MĂRFURI",
        "Nr. 18 / 16.01.2023",
        "SC TRANS-CARGO NORD SRL (Brașov, CUI RO19482015)",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (București, CUI RO34891204)",
        "Efectuarea de transporturi rutiere de mărfuri agricole (cereale vrac și fertilizanți paletizați).",
        "Tarife per cursă stabilite conform Anexei 1: București-Constanța 2.200 RON/cursă basculantă 25 to; Călărași-Brăila 1.800 RON/cursă. Plata la 15 zile de la primirea documentelor de transport (CMR semnat).",
        "Transportatorul răspunde pentru integritatea cantitativă a sigiliilor și a încărcăturii preluate conform Avizului de Însoțire."
    ),
    (
        "CTR-2023-003_Contract_Vanzare_Grau_CEREAL_GRUP.pdf",
        "CONTRACT DE VÂNZARE-CUMPĂRARE CEREALE",
        "Nr. 14 / 08.04.2023",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (Vânzător)",
        "SC CEREAL GRUP MOLDOVA SA (Iași, CUI RO15948201 - Cumpărător)",
        "Vânzarea unei cantități de 1.000 tone grâu panificație calitatea I, recolta 2022/2023.",
        "Preț unitar ferm: 230,00 EUR / tonă fără TVA. Valoare totală: 230.000,00 EUR. Condiție de livrare: CPT Siloz Călărași. Plata: 50% la semnarea contractului, 50% în termen de 5 zile de la recepția integrală.",
        "Specificații calitative: Umiditate max. 14%, Masă hectolitrică min. 78 kg/hl, Conținut proteină min. 12.5%, Corpuri străine max. 2%."
    ),
    (
        "CTR-2023-004_Contract_Consiliere_Management_NORDIC.pdf",
        "CONTRACT DE PRESTĂRI SERVICII DE CONSULTANȚĂ ȘI MANAGEMENT",
        "Nr. 8 / 12.04.2023",
        "SC NORDIC CONSULTING & MANAGEMENT SRL (Giurgiu, CUI RO39481022)",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (București, CUI RO34891204)",
        "Servicii de analiză de piață, optimizare fluxuri de trading cerealier și asistență în negocieri comerciale pe piețele regionale.",
        "Remunerație: Onorarii forfetare lunare și comisioane de succes facturate pe baza rapoartelor de activitate trimestriale. Plată în termen de 30 de zile.",
        "Prestatorul garantează confidențialitatea deplină a structurilor de costuri și a bazelor de date de clienți ale Beneficiarului."
    ),
    (
        "CTR-2023-005_Contract_Furnizare_Utilaje_TEHNO-UTILAJ.pdf",
        "CONTRACT DE LIVRARE ȘI MENTENANȚĂ UTILAJE AGRICOLE",
        "Nr. 77 / 15.05.2023",
        "SC TEHNO-UTILAJ BĂRĂGAN SRL (Călărași, CUI RO22948110)",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (București, CUI RO34891204)",
        "Achiziție 1 buc. Tractor John Deere 6155M și 1 buc. Semănătoare pneumatică Väderstad Tempo.",
        "Valoare totală: 650.000 RON + TVA. Plata în 3 tranșe egale: avans 30%, livrare 40%, tranșă finală de garanție 30% la 6 luni de la punerea în funcțiune.",
        "Garanție comercială: 24 de luni sau 2.000 ore de funcționare, cu asistență mobilă la fața locului în maxim 24 de ore."
    ),
    (
        "CTR-2024-001_Contract_Furnizare_Ingrasaminte_Sezonier_AGRO-CHIM.pdf",
        "CONTRACT DE FURNIZARE SEZONIERĂ INPUTURI AGRICOLE",
        "Nr. 08 / 12.01.2024",
        "SC AGRO-CHIM FERTILIZANTI SRL (Constanța)",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (București)",
        "Furnizare azotat de amoniu calitatea I și amendamente de sol pentru campania de primăvară 2024.",
        "Plafon de credit comercial: 1.200.000 RON. Termen de grație: 45 de zile de la livrare.",
        "Părțile convin constituirea unui bilet la ordin avalizat de administrator cu titlu de garanție de plată."
    ),
    (
        "CTR-2024-002_Contract_Depozitare_Siloz_DUNAREAN.pdf",
        "CONTRACT DE DEPOZITARE ȘI CONDIȚIONARE CEREALE",
        "Nr. 34 / 20.02.2024",
        "SC SILOZUL DUNĂREAN BĂRĂGAN SA (Brăila, CUI RO18294011)",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (București)",
        "Prestări servicii de recepție, cântărire auto pe cântar electronic omologat, uscare, condiționare și păstrare în siloz celule verticale.",
        "Tarife: Recepție și cântărire 8 RON/to; Depozitare 4.5 RON/to/lună; Condiționare/Uscare 15 RON/punct umiditate redusă.",
        "Gestiunea stocurilor se ține pe baza Tichetelor de Cântar și a Bonurilor de Primire în Depozit conforme cu normele Ministerului Agriculturii."
    ),
    (
        "CTR-2024-003_Contract_Vanzare_Porumb_BARAGAN_EXPORT.pdf",
        "CONTRACT DE LIVRARE CEREALE PENTRU EXPORT",
        "Nr. 92 / 10.05.2024",
        "SC AGROTERRA LOGISTICS & DISTRIBUTION SRL (Vânzător)",
        "SC BĂRĂGAN GRAIN EXPORT SRL (Port Constanța, CUI RO31490215 - Cumpărător)",
        "Vânzare 1.500 tone porumb boabe, destinație export maritim FOB Port Constanța.",
        "Preț: 220,00 EUR / tonă livrat dane siloz maritim. Termen livrare: August - Octombrie 2024.",
        "Acceptarea cantitativă și calitativă se face prin inspectori independenți (SGS / Bureau Veritas) la descărcarea din camioane."
    )
]

for fname, title, num, partener_a, partener_b, obiect, plati, clauze in contracte:
    story = [
        Paragraph("REPUBLICA ROMÂNIA • MEDIUL COMERCIAL", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15),
        Paragraph(title, title_style),
        Paragraph(f"<b>{num}</b>", subtitle_style),
        Spacer(1, 10),
        Paragraph("<b>I. PĂRȚILE CONTRACTANTE</b>", body_bold),
        Spacer(1, 4),
        Paragraph(f"1.1. <b>Prestator/Vânzător:</b> {partener_a}, reprezentată legal conform împuternicirii.", body_style),
        Paragraph(f"1.2. <b>Beneficiar/Cumpărător:</b> {partener_b}, reprezentată legal prin administrator.", body_style),
        Spacer(1, 10),
        Paragraph("<b>II. OBIECTUL CONTRACTULUI</b>", body_bold),
        Spacer(1, 4),
        Paragraph(f"2.1. {obiect}", body_style),
        Spacer(1, 10),
        Paragraph("<b>III. PREȚUL ȘI MODALITĂȚILE DE PLATĂ</b>", body_bold),
        Spacer(1, 4),
        Paragraph(f"3.1. {plati}", body_style),
        Spacer(1, 10),
        Paragraph("<b>IV. CLAUZE SPECIFICE ȘI RĂSPUNDEREA PĂRȚILOR</b>", body_bold),
        Spacer(1, 4),
        Paragraph(f"4.1. {clauze}", body_style),
        Paragraph("4.2. Forța majoră apără de răspundere partea care o invocă în termen de 5 zile de la producere, probată cu certificat emis de Camera de Comerț.", body_style),
        Paragraph("4.3. Litigiile ce decurg din prezentul contract se vor soluționa pe cale amiabilă, iar în caz contrar de instanțele competente din București.", body_style),
        Spacer(1, 25),
        Table([
            [Paragraph("<b>PENTRU FURNIZOR / VÂNZĂTOR</b>", body_style), Paragraph("<b>PENTRU BENEFICIAR / CUMPĂRĂTOR</b>", body_style)],
            [Paragraph("Semnătura autorizată și ștampila<br/>[Semnat electronic conform legii 455/2001]", body_style),
             Paragraph("SC AGROTERRA LOGISTICS SRL<br/>Administrator: Radu Teodorescu", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm])
    ]
    create_pdf(fname, story)

print("[+] Generat 8 Contracte Comerciale.")

# -------------------------------------------------------------
# 2. ACTE ADIȚIONALE & ANEXE (6 DOCUMENTE)
# -------------------------------------------------------------
acte = [
    (
        "ACT-2023-01_Act_Aditional_CTR-2023-001_Preturi_Uree.pdf",
        "ACT ADIȚIONAL NR. 1 LA CONTRACTUL NR. 104 / 09.01.2023",
        "15.03.2023",
        "Având în vedere cotațiile internaționale ale gazului natural și ale materiei prime la bursa TTF, părțile convin actualizarea prețului ureei granulate la 2.856 RON/tonă fără TVA pentru livrările din trimestrul al II-lea 2023. Restul clauzelor rămân neschimbate."
    ),
    (
        "ACT-2023-02_Act_Aditional_CTR-2023-004_Extindere_Servicii_NORDIC.pdf",
        "ACT ADIȚIONAL NR. 1 LA CONTRACTUL DE MANAGEMENT NR. 8",
        "12.02.2023", # Data afisata pe hartie!
        "Părțile convin suplimentarea activităților de asistență logistică cu analiza fluxurilor de tranzit maritim. În baza prezentului act, Prestatorul va factura contravaloarea serviciilor conform facturii fiscale seria AGR-2023-0188. (Notă contractuală: reglementare administrativă)." # ANACRONISM: Factura AGR-2023-0188 e din 28.05.2023!
    ),
    (
        "ACT-2023-03_Act_Aditional_CTR-2023-002_Majorare_Tarif_Motorina.pdf",
        "ACT ADIȚIONAL NR. 1 LA CONTRACTUL DE TRANSPORT NR. 18 / 16.01.2023",
        "10.08.2023",
        "Urmare a creșterii accizei la carburanți, tariful per cursă pe ruta Călărași - Port Constanța se majorează cu 8.5%, devenind 2.387 RON/cursă pentru ansamblurile de 40 tone."
    ),
    (
        "ACT-2023-04_Acord_Esalonare_Plati_CTR-2023-005.pdf",
        "ACORD DE EȘALONARE PLĂȚI TRANȘĂ UTILAJ AGRICOLE",
        "14.11.2023",
        "Părțile convin ca suma restantă de 47.500,00 EUR datorată de Beneficiar conform Facturii nr. FACT-2023-0315 să fie achitată integral prin transferuri bancare bancă-la-bancă în data de 14.11.2023, fiind stinsă orice obligație accesorie de dobândă sau penalitate."
    ),
    (
        "ACT-2024-01_Act_Aditional_CTR-2024-001_Volum_Azotat.pdf",
        "ACT ADIȚIONAL NR. 1 LA CONTRACTUL DE FURNIZARE NR. 08 / 12.01.2024",
        "18.03.2024",
        "Părțile suplimentează volumul de azotat de amoniu alocat campaniei de primăvară cu 120 tone metrice, menținând termenul de grație de 45 de zile."
    ),
    (
        "ACT-2024-02_Act_Aditional_CTR-2024-003_Grafic_Livrari_Porumb.pdf",
        "ANEXA 1 - GRAFIC DE LIVRĂRI CEREALE EXPORT",
        "02.06.2024",
        "Detaliere loturi: Lot 1 (450 to) - 15-20 Iunie 2024; Lot 2 (550 to) - 10-15 Iulie 2024; Lot 3 (500 to) - 01-10 August 2024. Cântărirea obligatorie la descărcare."
    )
]

for fname, title, data_act, text_act in acte:
    story = [
        Paragraph("ANEXĂ CONTRACTUALĂ FORMALĂ", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15),
        Paragraph(title, title_style),
        Paragraph(f"Încheiat în data de: <b>{data_act}</b>", subtitle_style),
        Spacer(1, 10),
        Paragraph(text_act, body_style),
        Spacer(1, 15),
        Paragraph("Prezentul act adițional face parte integrantă din contractul de bază și produce efecte de la data semnării de către ambele părți.", body_style),
        Spacer(1, 30),
        Table([
            [Paragraph("<b>PARTEA A</b>", body_style), Paragraph("<b>PARTEA B</b>", body_style)],
            [Paragraph("Semnătură autorizată", body_style), Paragraph("Semnătură autorizată", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm])
    ]
    create_pdf(fname, story)

print("[+] Generat 6 Acte Adiționale.")

# -------------------------------------------------------------
# 3. FACTURI FISCALE (26 DOCUMENTE)
# -------------------------------------------------------------
facturi_data = [
    ("FACT-2023-0012_AGRO-CHIM_Uree_Granulata.pdf", "AGRO-CHIM FERTILIZANTI SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0012", "18.01.2023", "17.02.2023", [("Uree Granulată 46% N saci 600kg", 50, "tone", 2400.0, 9)], "RON"),
    ("FACT-2023-0025_TRANS-CARGO_Curse_Ianuarie.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0025", "31.01.2023", "15.02.2023", [("Servicii transport rutier prelata marfa paletizata", 8, "curse", 2312.5, 19)], "RON"),
    ("FACT-2023-0041_AGRO-CHIM_Azotat_Amoniu.pdf", "AGRO-CHIM FERTILIZANTI SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0041", "20.02.2023", "22.03.2023", [("Azotat de Amoniu 33.5% N vrac", 75, "tone", 2250.0, 9)], "RON"),
    ("FACT-2023-0060_TRANS-CARGO_Curse_Februarie.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0060", "28.02.2023", "15.03.2023", [("Servicii transport basculabil azotat Constanta-Calarasi", 10, "curse", 2210.0, 19)], "RON"),
    ("FACT-2023-0082_TEHNO-UTILAJ_Tractor_JohnDeere.pdf", "TEHNO-UTILAJ BARAGAN SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0082", "25.03.2023", "10.04.2023", [("Tractor agricol John Deere 6155M sasiu W09281", 1, "buc", 485000.0, 19)], "RON"),
    ("FACT-2023-0095_AGROTERRA_Vanzare_Grau_Lot1_CEREAL_GRUP.pdf", "AGROTERRA LOGISTICS SRL", "CEREAL GRUP MOLDOVA SA", "AGR-2023-0095", "15.04.2023", "20.04.2023", [("Grau panificatie calitatea I recolta 2022 Lot 1", 500, "tone", 230.0, 9)], "EUR"),
    ("FACT-2023-0104_AGROTERRA_Vanzare_Grau_Lot2_CEREAL_GRUP.pdf", "AGROTERRA LOGISTICS SRL", "CEREAL GRUP MOLDOVA SA", "AGR-2023-0104", "24.04.2023", "29.04.2023", [("Grau panificatie calitatea I recolta 2022 Lot 2", 500, "tone", 230.0, 9)], "EUR"),
    ("FACT-2023-0112_NORDIC_Studiu_Piata_Optimizare_Logistica.pdf", "NORDIC CONSULTING & MANAGEMENT SRL", "AGROTERRA LOGISTICS SRL", "NOR-2023-0112", "29.04.2023", "29.05.2023", [("Servicii de optimizare logistica si studiu de piata trading cereale Trim II conform CTR 8/2023", 1, "serviciu", 15000.0, 19)], "EUR"),
    ("FACT-2023-0130_AGRO-CHIM_Pesticide_Erbicide.pdf", "AGRO-CHIM FERTILIZANTI SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0130", "10.05.2023", "09.06.2023", [("Erbicid sistemic cereale paioase 20L", 40, "bidoane", 1605.0, 19)], "RON"),
    ("FACT-2023-0145_TRANS-CARGO_Transport_Cereale_Mai.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0145", "31.05.2023", "15.06.2023", [("Transport rutier cereale siloz Iasi", 15, "curse", 2266.6, 19)], "RON"),
    ("FACT-2023-0188_AGROTERRA_Servicii_Depozitare_Tranzitorie.pdf", "AGROTERRA LOGISTICS SRL", "CEREAL GRUP MOLDOVA SA", "AGR-2023-0188", "28.05.2023", "15.06.2023", [("Prestari servicii manipulare mecanizata marfa vrac", 1, "pachet", 18500.0, 19)], "RON"),
    ("FACT-2023-0210_TEHNO-UTILAJ_Semantoare_Pneumatica.pdf", "TEHNO-UTILAJ BARAGAN SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0210", "14.07.2023", "30.07.2023", [("Semantoare pneumatica precizie Vaderstad Tempo", 1, "buc", 165000.0, 19)], "RON"),
    ("FACT-2023-0245_AGRO-CHIM_Complex_NPK.pdf", "AGRO-CHIM FERTILIZANTI SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0245", "22.09.2023", "22.10.2023", [("Ingrasamant chimic complex NPK 15:15:15", 40, "tone", 2750.0, 9)], "RON"),
    ("FACT-2023-0280_TRANS-CARGO_Curse_Toamna.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0280", "30.10.2023", "15.11.2023", [("Transporturi agricole campania de toamna", 18, "curse", 2305.5, 19)], "RON"),
    ("FACT-2023-0315_TEHNO-UTILAJ_Transa_Finala_Utilaje.pdf", "TEHNO-UTILAJ BARAGAN SRL", "AGROTERRA LOGISTICS SRL", "FACT-2023-0315", "10.11.2023", "14.11.2023", [("Decontare transa 3 garantie conform acord contractual utilaje agricole", 1, "tranșă", 47500.0, 0)], "EUR"),
    ("FACT-2023-0340_SILOZUL_Tarif_Receptie_Conditionare.pdf", "SILOZUL DUNAREAN BARAGAN SA", "AGROTERRA LOGISTICS SRL", "SIL-2023-0340", "15.12.2023", "30.12.2023", [("Servicii receptie, analiza laborator si uscare cereale", 1, "decont", 28600.0, 19)], "RON"),
    ("FACT-2024-0015_AGRO-CHIM_Fertilizanti_Start_Sezon.pdf", "AGRO-CHIM FERTILIZANTI SRL", "AGROTERRA LOGISTICS SRL", "FACT-2024-0015", "16.01.2024", "01.03.2024", [("Uree granulata calitatea I import", 65, "tone", 2480.0, 9)], "RON"),
    ("FACT-2024-0038_TRANS-CARGO_Transport_Primavara.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2024-0038", "28.02.2024", "15.03.2024", [("Curse transport ingrasaminte Constanta-Giurgiu", 12, "curse", 2450.0, 19)], "RON"),
    ("FACT-2024-0062_TEHNO-UTILAJ_Piese_Schimb_Combine.pdf", "TEHNO-UTILAJ BARAGAN SRL", "AGROTERRA LOGISTICS SRL", "FACT-2024-0062", "15.03.2024", "30.03.2024", [("Kit revizie sezoniere filtre, rulmenti si cutite tocator", 1, "lot", 42800.0, 19)], "RON"),
    ("FACT-2024-0089_AGROTERRA_Livrare_Grau_Siloz_BARAGAN.pdf", "AGROTERRA LOGISTICS SRL", "SILOZUL DUNAREAN BARAGAN SA", "AGR-2024-0089", "18.06.2024", "25.06.2024", [("Grau consum panificatie 18 camioane livrare directa", 450, "tone", 1100.0, 9)], "RON"),
    ("FACT-2024-0095_NORDIC_Consiliere_Expeditie_Export.pdf", "NORDIC CONSULTING & MANAGEMENT SRL", "AGROTERRA LOGISTICS SRL", "NOR-2024-0095", "25.06.2024", "25.07.2024", [("Asistenta tehnica si verificare documentatie export dane maritime", 1, "serviciu", 22000.0, 19)], "EUR"),
    ("FACT-2024-0110_TRANS-CARGO_18_Curse_Grau_Siloz.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2024-0110", "30.06.2024", "15.07.2024", [("Servicii transport rutier 18 curse cereale siloz Braila", 18, "curse", 2200.0, 19)], "RON"),
    ("FACT-2024-0135_AGRO-CHIM_Tratament_Samanta_Toamna.pdf", "AGRO-CHIM FERTILIZANTI SRL", "AGROTERRA LOGISTICS SRL", "FACT-2024-0135", "14.08.2024", "28.09.2024", [("Fungicid tratament samanta orz si grau", 35, "bidoane", 2125.0, 19)], "RON"),
    ("FACT-2024-0160_AGROTERRA_Vanzare_Porumb_BARAGAN_EXPORT.pdf", "AGROTERRA LOGISTICS SRL", "BARAGAN GRAIN EXPORT SRL", "AGR-2024-0160", "20.09.2024", "05.10.2024", [("Porumb boabe STAS umiditate max 14.5%", 750, "tone", 220.0, 9)], "EUR"),
    ("FACT-2024-0185_SILOZUL_Custodie_Uscare_Porumb.pdf", "SILOZUL DUNAREAN BARAGAN SA", "AGROTERRA LOGISTICS SRL", "SIL-2024-0185", "15.10.2024", "30.10.2024", [("Tarif uscare si conditionare lot 750 to porumb", 1, "serviciu", 36200.0, 19)], "RON"),
    ("FACT-2024-0210_TRANS-CARGO_Curse_Port_Constanta.pdf", "TRANS-CARGO NORD SRL", "AGROTERRA LOGISTICS SRL", "FACT-2024-0210", "10.11.2024", "25.11.2024", [("Transport rutier cereale dane 31-33 Port Constanta", 25, "curse", 2200.0, 19)], "RON")
]

for fname, furnizor, client, nr_fact, data_f, scadenta_f, articole, moneda in facturi_data:
    tot_fara_tva = sum(c * p for _, c, _, p, _ in articole)
    tot_tva = sum(c * p * (t / 100.0) for _, c, _, p, t in articole)
    tot_general = tot_fara_tva + tot_tva
    
    t_rows = [
        [Paragraph("<b>Nr.</b>", body_bold), 
         Paragraph("<b>Denumire produse / servicii</b>", body_bold), 
         Paragraph("<b>Cant.</b>", body_bold), 
         Paragraph("<b>U.M.</b>", body_bold), 
         Paragraph(f"<b>Preț unitar ({moneda})</b>", body_bold), 
         Paragraph(f"<b>Valoare ({moneda})</b>", body_bold), 
         Paragraph(f"<b>TVA ({moneda})</b>", body_bold)]
    ]
    for idx, (prod, cant, um, pret, tva_pct) in enumerate(articole, start=1):
        v = cant * pret
        vt = v * (tva_pct / 100.0)
        t_rows.append([
            Paragraph(str(idx), body_style),
            Paragraph(prod, body_style),
            Paragraph(f"{cant:,.2f}", body_style),
            Paragraph(um, body_style),
            Paragraph(f"{pret:,.2f}", body_style),
            Paragraph(f"{v:,.2f}", body_style),
            Paragraph(f"{vt:,.2f} ({tva_pct}%)", body_style)
        ])
    
    story = [
        Paragraph("FACTURĂ FISCALĂ", title_style),
        Paragraph(f"Seria și numărul: <b>{nr_fact}</b> | Data emiterii: <b>{data_f}</b> | Data scadenței: <b>{scadenta_f}</b>", subtitle_style),
        Spacer(1, 8),
        Table([
            [Paragraph(f"<b>FURNIZOR:</b><br/>{furnizor}<br/>Capital social: 100.000 RON<br/>IBAN: RO49BTRL00001202A19482XX<br/>Banca Transilvania", body_style),
             Paragraph(f"<b>CLIENT:</b><br/>{client}<br/>Cod TVA: RO / CIF conform legii<br/>Sediul social declarat<br/>Cont virament bancar", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm], style=[
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
            ('PADDING', (0,0), (-1,-1), 8)
        ]),
        Spacer(1, 15),
        Table(t_rows, colWidths=[1.0*cm, 6.0*cm, 1.8*cm, 1.2*cm, 2.6*cm, 2.4*cm, 2.0*cm], style=[
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#A0AEC0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5)
        ]),
        Spacer(1, 15),
        Table([
            [Paragraph("<b>TOTAL FĂRĂ TVA:</b>", body_style), Paragraph(f"<b>{tot_fara_tva:,.2f} {moneda}</b>", body_style)],
            [Paragraph("<b>TOTAL TVA:</b>", body_style), Paragraph(f"<b>{tot_tva:,.2f} {moneda}</b>", body_style)],
            [Paragraph("<b>TOTAL GENERAL DE PLATĂ:</b>", body_bold), Paragraph(f"<b>{tot_general:,.2f} {moneda}</b>", body_bold)]
        ], colWidths=[12.5*cm, 4.5*cm], style=[
            ('LINEABOVE', (0,0), (-1,0), 1, colors.HexColor("#CBD5E0")),
            ('PADDING', (0,0), (-1,-1), 4)
        ]),
        Spacer(1, 20),
        Paragraph("Factura este valabilă fără ștampilă și semnătură conform prevederilor Codului Fiscal din România (Legea 227/2015, art. 319 alin. 29).", header_box_style)
    ]
    create_pdf(fname, story)

print("[+] Generat 26 Facturi Fiscale.")

# -------------------------------------------------------------
# 4. EXTRASE BANCARE (10 DOCUMENTE)
# -------------------------------------------------------------
extrase = [
    ("EXTRAS_BANCAR_Banca_Transilvania_Ianuarie_2023.pdf", "Banca Transilvania", "IANUARIE 2023", "RO49BTRL00001202A1948201", [
        ("05.01.2023", "Sold initial disponibil", "", "", 145200.0),
        ("19.01.2023", "Plata OP cv Factura FACT-2023-0012 AGRO-CHIM FERTILIZANTI", 155652.0, "", -10452.0),
        ("20.01.2023", "Alimentare cont aport asociat Radu Teodorescu", "", 50000.0, 39548.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Aprilie_2023.pdf", "Banca Transilvania", "APRILIE 2023", "RO49BTRL00001202A1948201", [
        ("10.04.2023", "Incasare avans 50% CTR 14 CEREAL GRUP MOLDOVA", "", 125350.0, 164898.0),
        ("25.04.2023", "Plata OP furnizor TEHNO-UTILAJ Baragan", 150000.0, "", 14898.0),
        ("30.04.2023", "Incasare lichidare CTR 14 CEREAL GRUP MOLDOVA", "", 125350.0, 140248.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Mai_2023.pdf", "Banca Transilvania", "MAI 2023", "RO49BTRL00001202A1948201", [
        ("05.05.2023", "Plata virament cv Factura NOR-2023-0112 NORDIC CONSULTING", 74250.0, "", 65998.0),
        ("28.05.2023", "Comisioane bancare si pachet operatiuni", 185.0, "", 65813.0)
    ]),
    ("EXTRAS_BANCAR_BCR_Noiembrie_2023_Smurfing.pdf", "Banca Comerciala Romana (BCR)", "NOIEMBRIE 2023", "RO12RNCB0074158920140001", [
        ("14.11.2023 09:15", "Virament electronic OP 1101 cv acord transa utilaje p.1", 48510.0, "", 412500.0),
        ("14.11.2023 10:42", "Virament electronic OP 1102 cv acord transa utilaje p.2", 48015.0, "", 364485.0),
        ("14.11.2023 11:30", "Virament electronic OP 1103 cv acord transa utilaje p.3", 47025.0, "", 317460.0),
        ("14.11.2023 14:05", "Virament electronic OP 1104 cv acord transa utilaje p.4", 47520.0, "", 269940.0),
        ("14.11.2023 15:20", "Virament electronic OP 1105 cv acord transa utilaje p.5 final", 44055.0, "", 225885.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Decembrie_2023.pdf", "Banca Transilvania", "DECEMBRIE 2023", "RO49BTRL00001202A1948201", [
        ("10.12.2023", "Plata virament fact 245 AGRO-CHIM NPK (achitat intarziat)", 119900.0, "", 105985.0),
        ("31.12.2023", "Dobanda credit comercial si comisioane mentenanta", 640.0, "", 105345.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Martie_2024.pdf", "Banca Transilvania", "MARTIE 2024", "RO49BTRL00001202A1948201", [
        ("05.03.2024", "Incasari clienti campanie de primavara", "", 240000.0, 345345.0),
        ("20.03.2024", "Plata furnizori motorina si piese de schimb", 85000.0, "", 260345.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Iunie_2024.pdf", "Banca Transilvania", "IUNIE 2024", "RO49BTRL00001202A1948201", [
        ("20.06.2024", "Incasare integrala Factura AGR-2024-0089 Siloz Dunarean (450 to)", "", 539550.0, 799895.0),
        ("26.06.2024", "Plata virament Factura NOR-2024-0095 NORDIC CONSULTING", 108900.0, "", 690995.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Iulie_2024.pdf", "Banca Transilvania", "IULIE 2024", "RO49BTRL00001202A1948201", [
        ("10.07.2024", "Plata transporturi TRANS-CARGO 18 curse cereale", 47124.0, "", 643871.0),
        ("25.07.2024", "Plati impozite si contributii salarii buget de stat", 38400.0, "", 605471.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Octombrie_2024.pdf", "Banca Transilvania", "OCTOMBRIE 2024", "RO49BTRL00001202A1948201", [
        ("02.10.2024", "Incasare livrare porumb export BARAGAN EXPORT", "", 890000.0, 1495471.0),
        ("20.10.2024", "Plata prestatii uscare si custodie siloz", 43078.0, "", 1452393.0)
    ]),
    ("EXTRAS_BANCAR_Banca_Transilvania_Decembrie_2024.pdf", "Banca Transilvania", "DECEMBRIE 2024", "RO49BTRL00001202A1948201", [
        ("15.12.2024", "Inchidere an financiar si regularizare operatiuni", 12500.0, "", 1439893.0),
        ("31.12.2024", "Sold final an 2024 certificat de banca", "", "", 1439893.0)
    ])
]

for fname, banca, luna, cont_iban, tranzactii in extrase:
    t_rows = [
        [Paragraph("<b>Data / Ora</b>", body_bold),
         Paragraph("<b>Detalii operațiune / Referință</b>", body_bold),
         Paragraph("<b>Debit (RON)</b>", body_bold),
         Paragraph("<b>Credit (RON)</b>", body_bold),
         Paragraph("<b>Sold (RON)</b>", body_bold)]
    ]
    for d, det, deb, cred, sold in tranzactii:
        deb_str = f"{deb:,.2f}" if deb != "" else "-"
        cred_str = f"{cred:,.2f}" if cred != "" else "-"
        sold_str = f"{sold:,.2f}" if sold != "" else "-"
        t_rows.append([
            Paragraph(d, body_style),
            Paragraph(det, body_style),
            Paragraph(deb_str, body_style),
            Paragraph(cred_str, body_style),
            Paragraph(sold_str, body_style)
        ])
    
    story = [
        Paragraph(f"EXTRAS DE CONT BANCAR • {banca.upper()}", title_style),
        Paragraph(f"Titular: <b>SC AGROTERRA LOGISTICS SRL</b> | IBAN: <b>{cont_iban}</b> | Perioada: <b>{luna}</b>", subtitle_style),
        Spacer(1, 10),
        Table(t_rows, colWidths=[3.2*cm, 7.5*cm, 2.2*cm, 2.2*cm, 2.5*cm], style=[
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5)
        ]),
        Spacer(1, 20),
        Paragraph("Extras de cont oficial eliberat prin serviciul Internet Banking Corporate. Documentul atestă înregistrarea în sistemul electronic interbancar SENT/ReGIS.", header_box_style)
    ]
    create_pdf(fname, story)

print("[+] Generat 10 Extrase Bancare.")

# -------------------------------------------------------------
# 5. AVIZE DE ÎNSOȚIRE & TICHETE CÂNTAR (6 DOCUMENTE)
# -------------------------------------------------------------
avize_si_cantare = [
    ("AVIZ-2023-0045_Expeditie_Fertilizanti_Constanta.pdf", "AVIZ DE ÎNSOȚIRE A MĂRFII", "Seria AVZ nr. 0045 / 19.01.2023", "Expediție 50 tone Uree granulată ambalată saci mari de la depozit Constanța către Călărași. Transportator SC TRANS-CARGO NORD SRL. Camioane B-101-TRK, B-102-TRK."),
    ("AVIZ-2023-0112_Expeditie_Grau_Lot1.pdf", "AVIZ DE ÎNSOȚIRE A MĂRFII", "Seria AVZ nr. 0112 / 16.04.2023", "Expediție 500 tone grâu panificație calitatea I către Siloz Iași. Însoțit de buletin de analiză calitativă seria AL-291."),
    ("AVIZ-2023-0120_Expeditie_Grau_Lot2.pdf", "AVIZ DE ÎNSOȚIRE A MĂRFII", "Seria AVZ nr. 0120 / 25.04.2023", "Expediție tranșa 2 de 500 tone grâu panificație CPT Siloz Iași. Sigilii intacte serie RO-TRK 88192-88210."),
    ("AVIZ-2024-0089_Expeditie_Grau_18_Camioane.pdf", "AVIZ DE ÎNSOȚIRE A MĂRFII", "Seria AVZ nr. 0089 / 18.06.2024", "Expediție cantitate declarată: 450,00 tone grâu consum panificație. Număr total curse: 18 autocamioane basculabile. Destinație: Silozul Dunărean Brăila."),
    (
        "BORDEROU_CANTAR_SILOZ_2024-089_18_Camioane.pdf",
        "BORDEROU CENTRALIZATOR TICHETE DE CÂNTAR AUTO - SILOZ",
        "Borderou recepție depozit nr. 418 / 19.06.2024 (Recepție marfă Factura AGR-2024-0089)",
        "Tabelul detaliat de recepție pe cântar omologat metrologic la descărcare:\n\n" + 
        "1. B-101-TRK: Brut 39.80 to, Tara 16.20 to, Net 23.60 to\n" +
        "2. B-102-TRK: Brut 40.10 to, Tara 16.40 to, Net 23.70 to\n" +
        "3. B-103-TRK: Brut 38.50 to, Tara 16.10 to, Net 22.40 to\n" +
        "4. B-104-TRK: Brut 36.20 to, Tara 16.30 to, Net 19.90 to (corpuri străine 4.2%)\n" +
        "5. B-105-TRK: Brut 37.00 to, Tara 16.00 to, Net 21.00 to\n" +
        "6. B-106-TRK: Brut 39.40 to, Tara 16.20 to, Net 23.20 to\n" +
        "7. B-107-TRK: Brut 35.80 to, Tara 16.50 to, Net 19.30 to (umiditate ridicată 16.8%)\n" +
        "8. B-108-TRK: Brut 39.90 to, Tara 16.10 to, Net 23.80 to\n" +
        "9. B-109-TRK: Brut 36.00 to, Tara 16.40 to, Net 19.60 to\n" +
        "10. B-110-TRK: Brut 39.70 to, Tara 16.20 to, Net 23.50 to\n" +
        "11. B-111-TRK: Brut 36.50 to, Tara 16.30 to, Net 20.20 to\n" +
        "12. B-112-TRK: Brut 39.60 to, Tara 16.00 to, Net 23.60 to\n" +
        "13. B-113-TRK: Brut 35.90 to, Tara 16.40 to, Net 19.50 to (refuz calitativ parțial)\n" +
        "14. B-114-TRK: Brut 39.80 to, Tara 16.20 to, Net 23.60 to\n" +
        "15. B-115-TRK: Brut 36.40 to, Tara 16.50 to, Net 19.90 to\n" +
        "16. B-116-TRK: Brut 39.50 to, Tara 16.10 to, Net 23.40 to\n" +
        "17. B-117-TRK: Brut 35.20 to, Tara 16.30 to, Net 18.90 to\n" +
        "18. B-118-TRK: Brut 35.00 to, Tara 16.60 to, Net 18.40 to\n\n" +
        "TOTAL GREUTATE NETĂ RECEPȚIONATĂ ÎN CELULE SILOZ: 388,50 TONE.\n" +
        "Observație recepționer siloz: diferență de 61.50 tone față de avizul de expediție înregistrată pe borderoul de neconformitate."
    ),
    ("AVIZ-2024-0160_Expeditie_Porumb_Port_Constanta.pdf", "AVIZ DE ÎNSOȚIRE A MĂRFII", "Seria AVZ nr. 0160 / 21.09.2024", "Expediție 750 tone porumb boabe către dană maritimă Port Constanța. Recepționat conform raportului de supraveghere navală fără rezerve.")
]

for fname, title, num, descriere in avize_si_cantare:
    story = [
        Paragraph("DOCUMENTE OPERAȚIONALE DE TRANSPORT ȘI RECEPȚIE", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15),
        Paragraph(title, title_style),
        Paragraph(f"<b>{num}</b>", subtitle_style),
        Spacer(1, 10),
        Paragraph(descriere.replace("\n", "<br/>"), body_style),
        Spacer(1, 20),
        Table([
            [Paragraph("<b>Predat Marfa (Expeditor / Șofer)</b>", body_style), Paragraph("<b>Preluat în Gestiune (Siloz / Depozit)</b>", body_style)],
            [Paragraph("Nume: Vasile Dumitru<br/>Act identitate: CI seria RR nr. 491024<br/>Semnătură: semnat", body_style),
             Paragraph("Gestionar șef siloz: Ing. Marin Enache<br/>Ștampilă cântar electronic omologat", body_style)]
        ], colWidths=[8.5*cm, 8.5*cm])
    ]
    create_pdf(fname, story)

print("[+] Generat 6 Avize și Tichete de Cântar.")

# -------------------------------------------------------------
# 6. STENOGRAME WHATSAPP & EMAILURI (4 DOCUMENTE)
# -------------------------------------------------------------
chats_and_emails = [
    (
        "EXPORT_CHAT_WHATSAPP_MihaiStanciu_RaduTeodorescu_Aprilie2023.pdf",
        "EXPORT CONVERSAȚIE WHATSAPP • ARHIVĂ INTERNĂ DISPOZITIV",
        "Participanți: Radu Teodorescu (Administrator) & Mihai Stanciu (Director Comercial)\nInterval extras: 04.04.2023 - 08.04.2023",
        [
            ("04.04.2023, 10:14", "Mihai Stanciu", "Salut Radu. Am vorbit cu cei de la Cereal Grup Moldova pentru graul ala de 1000 de tone."),
            ("04.04.2023, 10:18", "Radu Teodorescu", "Salut. Si ce zic? Ramanem pe 230 de euro tona cum am discutat la birou?"),
            ("04.04.2023, 10:22", "Mihai Stanciu", "Nu vor la 230. Zic ca piata la bursa e jos pe Constanta, la 212-215. Au zis ca batem palma doar daca le dam la 215 euro."),
            ("04.04.2023, 11:05", "Radu Teodorescu", "Nu putem sa coboram contractul oficial la 215, ca ne strica marja raportata pe banca si avem linia de credit deschisa la BT."),
            ("04.04.2023, 11:12", "Mihai Stanciu", "Pai si atunci ce facem? Ii pierdem, ca au oferta si de la Ameropa."),
            ("04.04.2023, 11:30", "Radu Teodorescu", "Uite cum facem: lasam contractul pe firma la 230 euro/tona, asa cum am convenit initial pe hartie, iar diferenta de 15 euro pe tona o reglam dupa livrare printr-un contract separat de prestari servicii de optimizare cu firma Nordic din Giurgiu."),
            ("04.04.2023, 11:34", "Mihai Stanciu", "Au fost de acord?"),
            ("04.04.2023, 11:45", "Radu Teodorescu", "Da, a vorbit cu directorul lor financiar. Ii facturam normal 1000 tone la 230, iar dupa aia le emite Nordic factura de 15.000 euro pe studiu de piata si consultanta logistica trimestrul 2. Pregateste tu contractul nr. 14 asa."),
            ("08.04.2023, 09:10", "Mihai Stanciu", "Gata, s-a semnat contractul 14 la 230 euro. Totul e in regula.")
        ]
    ),
    (
        "EXPORT_CHAT_WHATSAPP_Sofer_Vasile_MihaiStanciu_Iunie2024.pdf",
        "EXPORT CONVERSAȚIE WHATSAPP • COORDONARE FLOTĂ AUTO",
        "Participanți: Mihai Stanciu (Director Comercial) & Vasile Dumitru (Șofer Coordonator Flotă)\nInterval extras: 18.06.2024 - 19.06.2024",
        [
            ("18.06.2024, 08:30", "Vasile Dumitru", "Sefu, au plecat toate cele 18 camioane din baza. Avem pe aviz 450 de tone trecute rotund."),
            ("18.06.2024, 14:15", "Vasile Dumitru", "Sefu, avem o problema la cantar la siloz la Braila."),
            ("18.06.2024, 14:20", "Mihai Stanciu", "Ce s-a intamplat Vasile?"),
            ("18.06.2024, 14:28", "Vasile Dumitru", "Pai la cantarirea pe pod au dat minus la vreo 5 camioane, zic ca e marfa usoara si la trei masini le-au gasit spartura si corpuri straine mari. A iesit totalul pe cantar la 388 de tone si ceva, nu iese 450 nici batut."),
            ("18.06.2024, 14:35", "Mihai Stanciu", "Stai linistit, nu te certa cu ei. A vorbit domnul Radu cu seful de baza de la siloz. Lasa-i sa treaca pe borderou ce iese pe cantar, noi emitem factura conform contractului si se regleaza pe custodie."),
            ("18.06.2024, 16:40", "Vasile Dumitru", "Am inteles sefu. Au descarcat toti, am semnat borderoul cu 388.5 tone si am plecat spre garaj.")
        ]
    ),
    (
        "EXPORT_EMAIL_Contabilitate_Scadente_Plati_Noiembrie2023.pdf",
        "SCHIMB DE MESAJE ELECTRONICE (EMAIL ARCHIVE)",
        "De la: Elena Dumitrescu <contabilitate@agroterra-logistics.ro>\nCătre: Radu Teodorescu <radu.teodorescu@agroterra-logistics.ro>\nData: 13 Noiembrie 2023, 16:45\nSubiect: Scadență tranșă utilaje Tehno-Utilaj Bărăgan",
        [
            ("13.11.2023 16:45", "Elena Dumitrescu", "Buna ziua domnule Teodorescu,\n\nVa reamintesc ca maine, 14 noiembrie, este scadenta pentru transa finala de 47.500 EUR conform acordului de esalonare la contractul de utilaje (Factura FACT-2023-0315).\nAvem disponibil in contul curent de la BCR, dar daca facem plata integrala de 47.500 EUR intr-un singur ordin de plata, sistemul bancar cere documente justificative suplimentare si se genereaza raport automat catre conformitate.\nCum procedam cu executarea platilor maine dimineata?"),
            ("13.11.2023 18:20", "Radu Teodorescu", "Buna Elena,\n\nNu ne complicam cu birocratia si intarzierile la banca, ca avem nevoie de eliberarea imediata a cartii tehnice a tractorului.\nSpargem suma in 5 ordine de plata separate pe parcursul zilei de maine, sub 10.000 euro fiecare (de exemplu 9.800, 9.700, 9.500, 9.600 si restul de 8.900 euro). Treci la detalii 'contravaloare acord transa utilaje p.1, p.2 etc.'.\nAsa se proceseaza instantaneu prin internet banking fara aprobari manuale.")
        ]
    ),
    (
        "EXPORT_EMAIL_Notificare_Intarziere_Livrare_Utilaje_Septembrie2023.pdf",
        "SCHIMB DE MESAJE ELECTRONICE (EMAIL ARCHIVE)",
        "De la: Tehno-Utilaj Bărăgan <office@tehno-utilaj.ro>\nCătre: Mihai Stanciu <mihai.stanciu@agroterra-logistics.ro>\nData: 28 Septembrie 2023, 11:10\nSubiect: Notificare întârziere piese schimb semănătoare Väderstad",
        [
            ("28.09.2023 11:10", "Ing. Cristian Vlădescu (Tehno-Utilaj)", "Stimate domnule Stanciu,\n\nVa aducem la cunostinta ca din cauza problemelor de tranzit pe canalul Suez, componentele hidraulice pentru semanatoare vor ajunge la depozitul nostru cu o intarziere de aproximativ 14 zile lucratoare.\nEchipa noastra mobila de service este pregatita sa intervina imediat ce primim coletul de la producator pentru a nu va afecta campania de insamantari de toamna. Ne cerem scuze pentru inconvenient.")
        ]
    )
]

for fname, title, meta_info, mesaje in chats_and_emails:
    story = [
        Paragraph("ARHIVĂ DIGITALĂ FORENSICĂ", header_box_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15),
        Paragraph(title, title_style),
        Paragraph(meta_info.replace("\n", "<br/>"), subtitle_style),
        Spacer(1, 10)
    ]
    for sender_time, sender_name, content in mesaje:
        msg_table = Table([
            [Paragraph(f"<b>[{sender_time}] {sender_name}:</b>", chat_meta_style)],
            [Paragraph(content.replace("\n", "<br/>"), chat_msg_style)]
        ], colWidths=[17.0*cm], style=[
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8)
        ])
        story.append(msg_table)
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("Extras conform cu jurnalul electronic de comunicații, exportat la cererea departamentului de audit intern.", header_box_style))
    create_pdf(fname, story)

print("[+] Generat 4 Stenograme WhatsApp și Emailuri.")
print(f"[*] SUCCES! Toate cele 60 de PDF-uri au fost generate cu succes in '{OUTPUT_DIR}'!")
