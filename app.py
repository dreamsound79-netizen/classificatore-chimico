# ====================================================================================================
# PROGETTO: SISTEMA ESPERTO AUDIT E CLASSIFICAZIONE FORMULATI FINITI (REACH - CLP - ADR - GHS)
# VERSIONE WEB STREAMLIT CON MANUALE D'USO E AMBITO NORMATIVO INTEGRATI NELL'APP
# ====================================================================================================
# 
# 🎯 1. SCOPO E ARCHITETTURA DEL SOFTWARE:
#    - Web Application per audit e conformità normativa di formulati chimici finiti (Sezione 3 SDS / Batch Record).
#    - Sezioni disponibili:
#        1. 🧪 AUDIT FORMULATO FINITO: calcolo additività CLP, assegnazione ADR con specifiche tecniche
#           N.A.S., screening SVHC REACH e download scheda HTML.
#        2. 🚚 CALCOLATORE ESENZIONE ADR (1.1.3.6): calcolo 1000 punti con conversione Kg/Litri via densità.
#        3. 📖 MANUALE D'USO & NORMATIVE: guida operativa, quadro normativo (CLP/REACH/ADR) e figure target.
#        4. ⚡ ARCHIVIO SOSTANZE OFFLINE: gestione della cache locale.
#
# 🛑 2. REGOLA D'ORO OPERATIVA PER L'ASSISTENTE AI:
#    - L'UTENTE NON È UN PROGRAMMATORE E NON EFFETTUA MODIFICHE MANUALI AL CODICE.
#    - Per ogni futura richiesta, correzione o estensione:
#      L'AI DEVE SEMPRE E TASSATIVAMENTE RISCRIVERE L'INTERO SCRIPT COMPLETO AL 100%.
#      NON fornire mai snippet parziali, diff o istruzioni manuali.
# ====================================================================================================

import os
import json
import re
import urllib.parse
import datetime
import requests
import streamlit as st

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

CACHE_FILE = "archivio_sostanze_cache.json"

# =====================================================================
# 1. DATABASE DENSITÀ INDUSTRIALE (Kg/L a 20°C per conversione ADR)
# =====================================================================
DENSITY_DATABASE = {
    "1330-20-7": 0.86,   # Xilene
    "108-88-3": 0.87,    # Toluene
    "67-64-1": 0.79,     # Acetone
    "75-09-2": 1.33,     # Diclorometano
    "67-66-3": 1.49,     # Cloroformio
    "79-01-6": 1.46,     # Tricloroetilene
    "64-17-5": 0.79,     # Etanolo
    "67-56-1": 0.79,     # Metanolo
    "67-63-0": 0.785,    # Isopropanolo
    "78-93-3": 0.805,    # MEK (Butanone)
    "108-10-1": 0.80,    # MIBK
    "141-78-6": 0.90,    # Acetato di etile
    "123-86-4": 0.88,    # Acetato di butile
    "109-99-9": 0.89,    # THF
    "60-29-7": 0.71,     # Etere etilico
    "68-12-2": 0.94,     # DMF
    "67-68-5": 1.10,     # DMSO
    "7647-01-0": 1.19,   # Acido cloridrico sol. 37%
    "7664-93-9": 1.84,   # Acido solforico 96%
    "7697-37-2": 1.41,   # Acido nitrico 65%
    "7664-38-2": 1.68,   # Acido fosforico 85%
    "7732-18-5": 1.00,   # Acqua
    "64742-82-1": 0.78,  # Acquaragia / White spirit
    "64742-49-0": 0.69,  # Etere di petrolio
    "64742-95-6": 0.87   # Solvente Nafta
}

# =====================================================================
# 2. FRASI H E CONSIGLI P UFFICIALI CE 1272/2008 (CLP)
# =====================================================================
H_STATEMENTS_IT = {
    "H220": "Gas altamente infiammabile",
    "H221": "Gas infiammabile",
    "H224": "Liquido e vapori altamente infiammabili",
    "H225": "Liquido e vapori facilmente infiammabili",
    "H226": "Liquido e vapori infiammabili",
    "H280": "Contiene gas sotto pressione; può esplodere se riscaldato",
    "H281": "Contiene gas refrigerato; può provocare ustioni o lesioni criogeniche",
    "H300": "Letale se ingerito",
    "H301": "Tossico se ingerito",
    "H302": "Nocivo se ingerito",
    "H304": "Può essere letale in caso di ingestione e di penetrazione nelle vie respiratorie",
    "H310": "Letale per contatto con la pelle",
    "H311": "Tossico per contatto con la pelle",
    "H312": "Nocivo per contatto con la pelle",
    "H314": "Provoca gravi ustioni cutanee e gravi lesioni oculari",
    "H315": "Provoca irritazione cutanea",
    "H318": "Provoca gravi lesioni oculari",
    "H319": "Provoca grave irritazione oculare",
    "H330": "Letale se inalato",
    "H331": "Tossico se inalato",
    "H332": "Nocivo se inalato",
    "H335": "Può irritare le vie respiratorie",
    "H336": "Può provocare sonnolenza o vertigini",
    "H350": "Può provocare il cancro",
    "H351": "Sospettato di provocare il cancro",
    "H360": "Può nuocere alla fertilità o al feto",
    "H372": "Provoca danni agli organi in caso di esposizione prolungata o ripetuta",
    "H400": "Molto tossico per gli organismi acquatici",
    "H410": "Molto tossico per gli organismi acquatici con effetti di lunga durata",
    "H411": "Tossico per gli organismi acquatici con effetti di lunga durata",
    "H412": "Nocivo per gli organismi acquatici con effetti di lunga durata"
}

P_STATEMENTS_IT = {
    "P102": "Tenere fuori dalla portata dei bambini.",
    "P210": "Tenere lontano da fonti di calore, superfici calde, scintille, fiamme libere o altre fonti di accensione. Non fumare.",
    "P233": "Tenere il recipiente ben chiuso.",
    "P260": "Non respirare la polvere/i fumi/i gas/la nebbia/i vapori/gli aerosol.",
    "P264": "Lavare accuratamente le mani dopo l'uso.",
    "P273": "Non disperdere nell'ambiente.",
    "P280": "Indossare guanti protettivi/indumenti protettivi/proteggere gli occhi/il viso.",
    "P301+P310": "IN CASO DI INGESTIONE: contattare immediatamente un CENTRO ANTIVELENI o un medico.",
    "P301+P330+P331": "IN CASO DI INGESTIONE: sciacquare la bocca. NON provocare il vomito.",
    "P303+P361+P353": "IN CASO DI CONTATTO CON LA PELLE: togliersi di dosso immediatamente tutti gli indumenti contaminati. Sciacquare la pelle.",
    "P305+P351+P338": "IN CASO DI CONTATTO CON GLI OCCHI: sciacquare accuratamente per parecchi minuti. Togliere le lenti a contatto se agevole farlo. Continuare a sciacquare.",
    "P331": "NON provocare il vomito.",
    "P501": "Smaltire il prodotto/recipiente in conformità alla regolamentazione locale e nazionale."
}

# =====================================================================
# 3. GESTORE CACHE LOCALE OFFLINE
# =====================================================================
class ChemicalCacheManager:
    @staticmethod
    def load_cache() -> dict:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @staticmethod
    def save_cache(cache: dict):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

# =====================================================================
# 4. DATABASE LOCALE TAGLI PETROLIFERI UVCB
# =====================================================================
INDUSTRIAL_UVCB_TABLE = {
    "64742-82-1": {
        "cas": "64742-82-1",
        "common_name": "Acquaragia / White Spirit",
        "iupac_name": "Idrocarburi, C9-C12, n-alcani, isoalcani, ciclici, aromatici (2-25%)",
        "formula": "Miscela UVCB (C9-C12)",
        "mw": "N/D (UVCB)",
        "h_codes": ["H226", "H304", "H336", "H372", "H411"],
        "pictograms": ["GHS02", "GHS07", "GHS08", "GHS09"],
        "signal": "PERICOLO",
        "is_liquid": True,
        "adr_override": {"regulated": True, "un": "UN 1300", "class": "3", "pg": "III", "desc": "SUCCEDANEO DELLA TREMENTINA", "cat": 3}
    },
    "64742-49-0": {
        "cas": "64742-49-0",
        "common_name": "Etere di Petrolio (Frazione leggera)",
        "iupac_name": "Idrocarburi, C6-C7, n-alcani, isoalcani, ciclici, <5% n-esano",
        "formula": "Miscela UVCB (C6-C7)",
        "mw": "N/D (UVCB)",
        "h_codes": ["H225", "H304", "H315", "H336", "H411"],
        "pictograms": ["GHS02", "GHS07", "GHS08", "GHS09"],
        "signal": "PERICOLO",
        "is_liquid": True,
        "adr_override": {"regulated": True, "un": "UN 1268", "class": "3", "pg": "II", "desc": "DISTILLATI DI PETROLIO, N.A.S.", "cat": 2}
    },
    "64742-95-6": {
        "cas": "64742-95-6",
        "common_name": "Solvente Nafta Leggero (Aromatico)",
        "iupac_name": "Idrocarburi, C9, aromatici",
        "formula": "Miscela UVCB (Aromatici C9)",
        "mw": "N/D (UVCB)",
        "h_codes": ["H226", "H304", "H335", "H336", "H411"],
        "pictograms": ["GHS02", "GHS07", "GHS08", "GHS09"],
        "signal": "PERICOLO",
        "is_liquid": True,
        "adr_override": {"regulated": True, "un": "UN 1268", "class": "3", "pg": "III", "desc": "DISTILLATI DI PETROLIO, N.A.S.", "cat": 3}
    },
    "64742-94-5": {
        "cas": "64742-94-5",
        "common_name": "Solvente Nafta Pesante (Aromatico)",
        "iupac_name": "Idrocarburi, C10, aromatici, <1% naftalene",
        "formula": "Miscela UVCB (Aromatici C10)",
        "mw": "N/D (UVCB)",
        "h_codes": ["H304", "H336", "H411"],
        "pictograms": ["GHS07", "GHS08", "GHS09"],
        "signal": "PERICOLO",
        "is_liquid": True,
        "adr_override": {"regulated": True, "un": "UN 3082", "class": "9", "pg": "III", "desc": "MATERIA PERICOLOSA PER L'AMBIENTE, LIQUIDA, N.A.S.", "cat": 3}
    }
}

KNOWN_CAS_TO_CID = {
    "1330-20-7": 7929,   # Xilene miscela commerciale -> m-xylene (CID 7929)
    "1319-77-3": 1073    # Cresolo miscela commerciale -> p-cresol (CID 1073)
}

# =====================================================================
# 5. DIZIONARIO BILINGUE IT <-> EN / CAS
# =====================================================================
BILINGUAL_DICTIONARY = {
    # Tagli petroliferi
    "acquaragia": "64742-82-1", "white spirit": "64742-82-1", "ragia minerale": "64742-82-1",
    "etere di petrolio": "64742-49-0", "petroleum ether": "64742-49-0", "ligroina": "64742-49-0",
    "solvente nafta": "64742-95-6", "solvent naphtha": "64742-95-6", "solvesso 100": "64742-95-6", "solvesso 150": "64742-94-5",

    # Idrocarburi Aromatici e Alifatici
    "toluene": "108-88-3", "toluolo": "108-88-3",
    "benzene": "71-43-2", "benzolo": "71-43-2",
    "xilene": "1330-20-7", "xylene": "1330-20-7", "xilolo": "1330-20-7", "xileni": "1330-20-7", "xylenes": "1330-20-7",
    "o-xilene": "95-47-6", "o-xylene": "95-47-6",
    "m-xilene": "108-38-3", "m-xylene": "108-38-3",
    "p-xilene": "106-42-3", "p-xylene": "106-42-3",
    "cicloesano": "110-82-7", "cyclohexane": "110-82-7",
    "esano": "110-54-3", "hexane": "110-54-3", "n-esano": "110-54-3",
    "eptano": "142-82-5", "heptane": "142-82-5",

    # Chetoni ed Esteri
    "acetone": "67-64-1",
    "metiletilchetone": "78-93-3", "methyl ethyl ketone": "78-93-3", "mek": "78-93-3", "butanone": "78-93-3",
    "metilisobutilchetone": "108-10-1", "methyl isobutyl ketone": "108-10-1", "mibk": "108-10-1",
    "cicloesanone": "108-94-1", "cyclohexanone": "108-94-1",
    "acetato di etile": "141-78-6", "ethyl acetate": "141-78-6",
    "acetato di butile": "123-86-4", "butyl acetate": "123-86-4",
    "acetato di metile": "79-20-9", "methyl acetate": "79-20-9",
    "acetato di isopropile": "108-21-4", "isopropyl acetate": "108-21-4",

    # Alcoli e Glicoli
    "acqua": "7732-18-5", "water": "7732-18-5", "h2o": "7732-18-5",
    "etanolo": "64-17-5", "alcol etilico": "64-17-5", "ethanol": "64-17-5",
    "metanolo": "67-56-1", "alcol metilico": "67-56-1", "methanol": "67-56-1",
    "isopropanolo": "67-63-0", "alcol isopropilico": "67-63-0", "isopropanol": "67-63-0", "ipa": "67-63-0",
    "butanolo": "71-36-3", "n-butanolo": "71-36-3", "butanol": "71-36-3",
    "isobutanolo": "78-83-1", "isobutanol": "78-83-1",
    "glicole etilenico": "107-21-1", "ethylene glycol": "107-21-1",
    "glicole propilenico": "57-55-6", "propylene glycol": "57-55-6",
    "glicerina": "56-81-5", "glycerol": "56-81-5",
    "cicloesanolo": "108-93-0", "cyclohexanol": "108-93-0",

    # Eteri e Dipolari
    "etere etilico": "60-29-7", "diethyl ether": "60-29-7", "etere": "60-29-7",
    "tetraidrofurano": "109-99-9", "tetrahydrofuran": "109-99-9", "thf": "109-99-9",
    "diossano": "123-91-1", "1,4-dioxane": "123-91-1",
    "dimetilformammide": "68-12-2", "dimethylformamide": "68-12-2", "dmf": "68-12-2",
    "dimetilsolfossido": "67-68-5", "dimethyl sulfoxide": "67-68-5", "dmso": "67-68-5",

    # Clorurati
    "diclorometano": "75-09-2", "dichloromethane": "75-09-2", "dcm": "75-09-2", "cloruro di metilene": "75-09-2",
    "cloroformio": "67-66-3", "chloroform": "67-66-3",
    "tricloroetilene": "79-01-6", "trichloroethylene": "79-01-6", "tria": "79-01-6",
    "tetracloroetilene": "127-18-4", "percloroetilene": "127-18-4", "perc": "127-18-4",

    # Acidi
    "acido cloridrico": "7647-01-0", "hydrochloric acid": "7647-01-0", "hcl": "7647-01-0",
    "acido solforico": "7664-93-9", "sulfuric acid": "7664-93-9", "h2so4": "7664-93-9",
    "acido nitrico": "7697-37-2", "nitric acid": "7697-37-2", "hno3": "7697-37-2",
    "acido fosforico": "7664-38-2", "phosphoric acid": "7664-38-2", "h3po4": "7664-38-2",
    "acido fluoridrico": "7664-39-3", "hydrofluoric acid": "7664-39-3", "hf": "7664-39-3",
    "acido acetico": "64-19-7", "acetic acid": "64-19-7",
    "acido formico": "64-18-6", "formic acid": "64-18-6",

    # Basi
    "soda caustica": "1310-73-2", "idrossido di sodio": "1310-73-2", "sodium hydroxide": "1310-73-2", "naoh": "1310-73-2",
    "potassa caustica": "1310-58-3", "idrossido di potassio": "1310-58-3", "potassium hydroxide": "1310-58-3", "koh": "1310-58-3",
    "ammoniaca": "7664-41-7", "ammonia": "7664-41-7", "nh3": "7664-41-7",

    # Gas
    "metano": "74-82-8", "methane": "74-82-8", "ch4": "74-82-8",
    "propano": "74-98-6", "propane": "74-98-6",
    "butano": "106-97-8", "butane": "106-97-8",
    "ossigeno": "7782-44-7", "oxygen": "7782-44-7",
    "azoto": "7727-37-9", "nitrogen": "7727-37-9",

    # Sali e Ossidanti
    "candeggina": "7681-52-9", "ipoclorito di sodio": "7681-52-9", "sodium hypochlorite": "7681-52-9",
    "acqua ossigenata": "7722-84-1", "perossido di idrogeno": "7722-84-1", "hydrogen peroxide": "7722-84-1", "h2o2": "7722-84-1",
    "sale": "7647-14-5", "cloruro di sodio": "7647-14-5", "sodium chloride": "7647-14-5", "nacl": "7647-14-5"
}

STANDARD_FORMULAS = {
    "7647-01-0": "HCl", "7664-93-9": "H2SO4", "7697-37-2": "HNO3",
    "7664-38-2": "H3PO4", "1310-73-2": "NaOH", "1310-58-3": "KOH",
    "7664-41-7": "NH3", "7647-14-5": "NaCl", "7722-84-1": "H2O2",
    "7732-18-5": "H2O", "74-82-8": "CH4"
}

def fix_chemical_formula(raw: str, cas: str) -> str:
    if cas in STANDARD_FORMULAS: return STANDARD_FORMULAS[cas]
    corrections = {"ClH": "HCl", "BrH": "HBr", "FH": "HF", "IH": "HI", "HNaO": "NaOH", "HKO": "KOH", "H3N": "NH3"}
    return corrections.get(raw, raw)

# =====================================================================
# 6. REGOLAMENTI REACH (SVHC & ALLEGATO XVII)
# =====================================================================
REACH_SVHC_DATABASE = {
    "71-43-2": {"substance": "Benzene", "reason": "Cancerogeno e Mutageno (Art. 57a/b)"},
    "117-81-7": {"substance": "DEHP (Ftalato)", "reason": "Tossico riproduzione (Art. 57c)"},
    "50-00-0": {"substance": "Formaldeide", "reason": "Cancerogeno e Mutageno"},
    "110-80-5": {"substance": "2-etossietanolo", "reason": "Tossico per la riproduzione"},
    "68-12-2": {"substance": "Dimetilformammide (DMF)", "reason": "Tossico per la riproduzione (Art. 57c)"},
    "79-01-6": {"substance": "Tricloroetilene", "reason": "Cancerogeno (Art. 57a)"},
    "123-91-1": {"substance": "1,4-Diossano", "reason": "Cancerogeno ed Equivalente livello di preoccupazione"}
}

REACH_ANNEX_XVII = {
    "71-43-2": "Restrizione 5 (Benzene: vietato in giocattoli e articoli a contatto consumatore)",
    "67-56-1": "Restrizione 69 (Metanolo: max 0.6% nei lavavetri per il pubblico)",
    "75-09-2": "Restrizione 59 (Diclorometano: vietato l'uso professionale e consumatore negli sverniciatori)",
    "79-01-6": "Allegato XIV / Restrizione (Tricloroetilene: autorizzazione REACH necessaria)"
}

# =====================================================================
# 7. MOTORE INCOMPATIBILITÀ E REAZIONI PERICOLOSE
# =====================================================================
class IncompatibilityAnalyzer:
    ACIDI_FORTI = {"7647-01-0", "7664-93-9", "7697-37-2", "7664-39-3", "7664-38-2"}
    BASI_FORTI = {"1310-73-2", "1310-58-3", "7664-41-7"}
    IPOCLORITI = {"7681-52-9"}
    OSSIDANTI_FORTI = {"7722-84-1", "7697-37-2"}
    SOLVENTI_INFIAMMABILI = {
        "67-64-1", "108-88-3", "1330-20-7", "64-17-5", "67-56-1", "67-63-0",
        "78-93-3", "108-10-1", "141-78-6", "123-86-4", "109-99-9", "60-29-7",
        "64742-82-1", "64742-49-0", "64742-95-6"
    }

    @classmethod
    def analyze(cls, recipe: list) -> list:
        alerts = []
        cas_presenti = {item["info"]["cas"] for item in recipe if item["effective_conc"] > 0}

        if bool(cas_presenti & cls.ACIDI_FORTI) and bool(cas_presenti & cls.IPOCLORITI):
            alerts.append("💀 PERICOLO LETALE: Miscela di Acido con Ipoclorito (Candeggina)! Sviluppo istantaneo di GAS CLORO TOSSICO (Cl2).")

        if bool(cas_presenti & cls.ACIDI_FORTI) and bool(cas_presenti & cls.BASI_FORTI):
            alerts.append("⚠️ REAZIONE ESOTERMICA VIOLENTA: Co-presenza di Acido Forte e Base Forte. Rischio ebollizione istantanea e schizzi caustici.")

        if bool(cas_presenti & cls.OSSIDANTI_FORTI) and bool(cas_presenti & cls.SOLVENTI_INFIAMMABILI):
            alerts.append("🔥 RISCHIO INCENDIO / ESPLOSIONE: Ossidante Forte in contatto con Solventi Organici Infiammabili.")

        if "7697-37-2" in cas_presenti and bool(cas_presenti & cls.SOLVENTI_INFIAMMABILI):
            alerts.append("💥 PERICOLO DEFLAGRAZIONE: L'Acido Nitrico con composti organici forma composti nitrati instabili ed esplosivi.")

        return alerts

# =====================================================================
# 8. RISOLUTORE SOSTANZE CON CACHE OFFLINE
# =====================================================================
class UniversalChemicalResolver:
    BASE_PUG_REST = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    BASE_PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

    @classmethod
    def resolve_to_cid(cls, query: str) -> tuple[int | None, str, dict | None]:
        clean_q = query.strip().lower()
        mapped_target = BILINGUAL_DICTIONARY.get(clean_q, clean_q)
        found_cas = mapped_target if re.match(r"^\d{2,7}-\d{2}-\d$", mapped_target) else None

        if found_cas and found_cas in INDUSTRIAL_UVCB_TABLE:
            data = INDUSTRIAL_UVCB_TABLE[found_cas].copy()
            data["query_input"] = query
            return None, found_cas, data

        if found_cas and found_cas in KNOWN_CAS_TO_CID:
            return KNOWN_CAS_TO_CID[found_cas], found_cas, None

        candidates = [mapped_target]
        if clean_q != mapped_target:
            candidates.append(clean_q)

        if "xilen" in clean_q or "xylen" in clean_q:
            candidates.extend(["xylene", "m-xylene", "o-xylene", "p-xylene"])

        for cand in candidates:
            encoded_query = urllib.parse.quote(cand)
            url_cid = f"{cls.BASE_PUG_REST}/compound/name/{encoded_query}/cids/JSON"
            try:
                r_cid = requests.get(url_cid, headers=HEADERS, timeout=6)
                if r_cid.status_code == 200:
                    cid = r_cid.json()["IdentifierList"]["CID"][0]
                    return cid, found_cas, None
            except Exception:
                continue

        if found_cas:
            try:
                sub_url = f"{cls.BASE_PUG_REST}/substance/name/{found_cas}/cids/JSON"
                r_sub = requests.get(sub_url, headers=HEADERS, timeout=6)
                if r_sub.status_code == 200:
                    cid = r_sub.json()["InformationList"]["Information"][0]["CID"][0]
                    return cid, found_cas, None
            except Exception:
                pass

        raise ValueError(f"Sostanza '{query}' non riconosciuta né in Italiano né in Inglese.")

    @classmethod
    def get_cas_from_cid(cls, cid: int) -> str:
        url = f"{cls.BASE_PUG_REST}/compound/cid/{cid}/synonyms/JSON"
        try:
            r = requests.get(url, headers=HEADERS, timeout=6)
            if r.status_code == 200:
                synonyms = r.json().get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
                for syn in synonyms:
                    if re.match(r"^\d{2,7}-\d{2}-\d$", syn):
                        return syn
        except Exception:
            pass
        return "N/D"

    @classmethod
    def get_substance(cls, query: str) -> dict:
        norm_key = query.strip().lower()
        cache = ChemicalCacheManager.load_cache()

        if norm_key in cache:
            cached_data = cache[norm_key].copy()
            cached_data["query_input"] = query
            cached_data["from_cache"] = True
            return cached_data

        cid, cas, uvcb_data = cls.resolve_to_cid(query)

        if uvcb_data:
            cache[norm_key] = uvcb_data
            ChemicalCacheManager.save_cache(cache)
            uvcb_data["from_cache"] = False
            return uvcb_data

        if not cas:
            cas = cls.get_cas_from_cid(cid)

        prop_url = f"{cls.BASE_PUG_REST}/compound/cid/{cid}/property/Title,MolecularFormula,MolecularWeight,IUPACName/JSON"
        props = requests.get(prop_url, headers=HEADERS, timeout=8).json()["PropertyTable"]["Properties"][0]

        common_name = props.get("Title", query.capitalize())
        iupac_name = props.get("IUPACName", common_name)
        formula = fix_chemical_formula(props.get("MolecularFormula", "N/D"), cas)
        mw = props.get("MolecularWeight", "N/D")

        ghs_url = f"{cls.BASE_PUG_VIEW}/data/compound/{cid}/JSON?heading=GHS+Classification"
        r_ghs = requests.get(ghs_url, headers=HEADERS, timeout=8)
        raw_text = r_ghs.text if r_ghs.status_code == 200 else requests.get(f"{cls.BASE_PUG_VIEW}/data/compound/{cid}/JSON", headers=HEADERS, timeout=8).text

        h_codes = sorted(list(set(re.findall(r"\b(H\d{3}[a-zA-Z]?)\b", raw_text))))
        pics = sorted(list(set(re.findall(r"\b(GHS0\d)\b", raw_text))))
        signal = "PERICOLO" if "Danger" in raw_text else ("ATTENZIONE" if "Warning" in raw_text else "Nessuna")

        result = {
            "query_input": query,
            "cas": cas,
            "common_name": common_name,
            "iupac_name": iupac_name,
            "formula": formula,
            "mw": mw,
            "h_codes": h_codes,
            "pictograms": pics,
            "signal": signal,
            "adr_override": None,
            "from_cache": False
        }

        cache[norm_key] = result
        ChemicalCacheManager.save_cache(cache)
        return result

# =====================================================================
# 9. CLASSIFICATORE TRASPORTO ADR (CON SPECIFICA TECNICA N.A.S. 3.1.2.8)
# =====================================================================
class ADRClassifier:
    SPECIFIC_UN = {
        "dichloromethane": {"un": "UN 1593", "desc": "DICLOROMETANO", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},
        "diclorometano": {"un": "UN 1593", "desc": "DICLOROMETANO", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},
        "cloruro di metilene": {"un": "UN 1593", "desc": "DICLOROMETANO", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},
        "chloroform": {"un": "UN 1888", "desc": "CLOROFORMIO", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},
        "cloroformio": {"un": "UN 1888", "desc": "CLOROFORMIO", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},
        "trichloroethylene": {"un": "UN 1710", "desc": "TRICLOROETILENE", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},
        "tricloroetilene": {"un": "UN 1710", "desc": "TRICLOROETILENE", "pg": "III", "class": "6.1", "cat": 3, "is_liquid": True},

        "xylene": {"un": "UN 1307", "desc": "XILENI", "pg": "III", "class": "3", "cat": 3, "is_liquid": True},
        "xilene": {"un": "UN 1307", "desc": "XILENI", "pg": "III", "class": "3", "cat": 3, "is_liquid": True},
        "toluene": {"un": "UN 1294", "desc": "TOLUENE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "acetone": {"un": "UN 1090", "desc": "ACETONE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "methanol": {"un": "UN 1230", "desc": "METANOLO", "pg": "II", "class": "3 (6.1)", "cat": 2, "is_liquid": True},
        "metanolo": {"un": "UN 1230", "desc": "METANOLO", "pg": "II", "class": "3 (6.1)", "cat": 2, "is_liquid": True},
        "ethanol": {"un": "UN 1170", "desc": "ETANOLO IN SOLUZIONE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "etanolo": {"un": "UN 1170", "desc": "ETANOLO IN SOLUZIONE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "ethyl acetate": {"un": "UN 1173", "desc": "ACETATO DI ETILE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "butyl acetate": {"un": "UN 1123", "desc": "ACETATI DI BUTILE", "pg": "III", "class": "3", "cat": 3, "is_liquid": True},
        "methyl ethyl ketone": {"un": "UN 1193", "desc": "METILETILCHETONE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "butanone": {"un": "UN 1193", "desc": "METILETILCHETONE", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "tetrahydrofuran": {"un": "UN 2056", "desc": "TETRAIDROFURANO", "pg": "II", "class": "3", "cat": 2, "is_liquid": True},
        "tetraidrofurano": {"un": "UN 2056", "desc": "TETRAIDROFURANO", "pg": "II", "class": "3", "cat": 2, "is_liquid": True}
    }

    @classmethod
    def map_adr(cls, data: dict) -> dict:
        if data.get("adr_override"):
            return data["adr_override"]

        name = (data.get("common_name", "") + " " + data.get("iupac_name", "") + " " + data.get("query_input", "")).lower()
        h_codes = data.get("h_codes", [])

        for k, v in cls.SPECIFIC_UN.items():
            if k in name:
                return {
                    "regulated": True,
                    "un": v["un"],
                    "class": v.get("class", "3"),
                    "pg": v["pg"],
                    "desc": v["desc"],
                    "cat": v.get("cat", 3),
                    "is_liquid": v.get("is_liquid", True)
                }

        if any(h in h_codes for h in ["H220", "H221"]) or "methane" in name or "metano" in name:
            return {"regulated": True, "un": "UN 1971 / UN 1954", "class": "2", "pg": "Non applicabile", "desc": "GAS INFIAMMABILE", "cat": 2, "is_liquid": False}
        if any(h in h_codes for h in ["H280", "H281"]):
            return {"regulated": True, "un": "UN 1956", "class": "2", "pg": "Non applicabile", "desc": "GAS COMPRESSO / REFRIGERATO", "cat": 3, "is_liquid": False}

        if "H224" in h_codes or "H225" in h_codes:
            return {"regulated": True, "un": "UN 1993", "class": "3", "pg": "II", "desc": "LIQUIDO INFIAMMABILE, N.A.S.", "cat": 2, "is_liquid": True}
        if "H226" in h_codes:
            return {"regulated": True, "un": "UN 1993", "class": "3", "pg": "III", "desc": "LIQUIDO INFIAMMABILE, N.A.S.", "cat": 3, "is_liquid": True}

        if "H314" in h_codes:
            return {"regulated": True, "un": "UN 1760", "class": "8", "pg": "II", "desc": "MATERIA CORROSIVA, N.A.S.", "cat": 2, "is_liquid": True}

        if any(h in h_codes for h in ["H300", "H310", "H330", "H301", "H311", "H331"]):
            return {"regulated": True, "un": "UN 2810", "class": "6.1", "pg": "II", "desc": "MATERIA TOSSICA, N.A.S.", "cat": 2, "is_liquid": True}

        return {"regulated": False, "un": "Nessuno", "class": "Non regolamentato", "pg": "N/A", "desc": "Non pericoloso ai fini del trasporto", "cat": 4, "is_liquid": False}

    @staticmethod
    def calculate_1000_points(category: int, quantity: float) -> tuple[float, bool]:
        multipliers = {0: 0, 1: 50, 2: 3, 3: 1, 4: 0}
        mult = multipliers.get(category, 1)
        points = quantity * mult
        is_exempt = points <= 1000.0
        return points, is_exempt

# =====================================================================
# 10. GENERATORE DI SCHEDA TECNICA DI AUDIT (REPORT HTML)
# =====================================================================
class ReportGenerator:
    @staticmethod
    def build_html_string(title: str, components: list, reach_alerts: list, clp_info: dict, adr_info: dict, incomp_alerts: list) -> str:
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        
        comp_rows = ""
        for idx, c in enumerate(components, 1):
            info = c["info"]
            batch_c = c.get("batch_conc", 100.0)
            assay = c.get("assay", 100.0)
            eff_c = c.get("effective_conc", batch_c)
            comp_rows += f"""
            <tr>
                <td><strong>{idx}</strong></td>
                <td>{info['common_name']}</td>
                <td><code>{info['cas']}</code></td>
                <td>{batch_c:.2f}%</td>
                <td>{assay:.1f}%</td>
                <td><strong>{eff_c:.2f}%</strong></td>
                <td>{info['formula']}</td>
            </tr>
            """

        incomp_html = ""
        if incomp_alerts:
            incomp_html = "<div class='card alert-incomp'><h3>⚠️ ALLARMI INCOMPATIBILITÀ E RISCHIO REAZIONI</h3><ul>"
            for a in incomp_alerts:
                incomp_html += f"<li>{a}</li>"
            incomp_html += "</ul></div>"

        reach_html = ""
        if reach_alerts:
            reach_html = "<div class='card alert-reach'><h3>🇪🇺 AUDIT REACH (SVHC & ALLEGATO XVII)</h3><ul>"
            for r in reach_alerts:
                reach_html += f"<li>{r}</li>"
            reach_html += "</ul></div>"
        else:
            reach_html = "<p style='color: #276749; font-weight: 500;'>🟢 Nessun componente SVHC sopra soglia di notifica SCIP (0.1% p/p).</p>"

        h_html = "<ul>"
        for h in clp_info["h_codes"]:
            desc = H_STATEMENTS_IT.get(h, "Descrizione standard")
            h_html += f"<li><strong>{h}</strong>: {desc}</li>"
        h_html += "</ul>" if clp_info["h_codes"] else "<p>Materia non classificata pericolosa ai fini CLP.</p>"

        p_html = "<ul>"
        for p in clp_info["p_codes"]:
            desc = P_STATEMENTS_IT.get(p, "Consiglio standard")
            p_html += f"<li><strong>{p}</strong>: {desc}</li>"
        p_html += "</ul>"

        pic_badges = "".join([f"<span class='badge-pic'>{p}</span>" for p in clp_info["pictograms"]]) or "Nessuno"

        return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Scheda di Omologazione Formulato - {title}</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 30px; background-color: #f8fafc; color: #1e293b; }}
    .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); color: white; padding: 24px; border-radius: 10px; margin-bottom: 25px; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .header p {{ margin: 6px 0 0 0; opacity: 0.85; font-size: 13px; }}
    .card {{ background: white; padding: 22px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 20px; border: 1px solid #e2e8f0; }}
    h2 {{ color: #1e3a8a; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; margin-top: 0; font-size: 17px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #f1f5f9; }}
    th {{ background-color: #f8fafc; color: #475569; font-weight: 600; }}
    .alert-incomp {{ background-color: #fef2f2; border-left: 5px solid #ef4444; }}
    .alert-incomp h3 {{ color: #991b1b; margin-top: 0; font-size: 15px; }}
    .alert-reach {{ background-color: #fffbeb; border-left: 5px solid #f59e0b; }}
    .badge-pic {{ display: inline-block; background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; padding: 3px 8px; margin-right: 6px; font-weight: 600; font-size: 12px; color: #0f172a; }}
    .badge-danger {{ color: white; background: #dc2626; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 12px; }}
    .badge-warning {{ color: white; background: #d97706; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 12px; }}
    .footer {{ text-align: center; font-size: 11px; color: #94a3b8; margin-top: 40px; }}
    @media print {{ body {{ background: white; margin: 0; }} .card {{ box-shadow: none; border: 1px solid #cbd5e1; }} }}
</style>
</head>
<body>
    <div class="header">
        <h1>VERIFICA DI CONFORMITÀ NORMATIVA FORMULATO FINITO</h1>
        <p>Data di Omologazione: {now_str} | Standard: CLP (CE 1272/2008) - REACH - ADR</p>
    </div>

    {incomp_html}

    <div class="card">
        <h2>📋 Composizione del Formulato Finito (Sezione 3 SDS)</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Denominazione Componente</th>
                    <th>Numero CAS</th>
                    <th>% Formulato</th>
                    <th>Titolo/Assay</th>
                    <th>% Attivo Reale</th>
                    <th>Formula Chimica</th>
                </tr>
            </thead>
            <tbody>
                {comp_rows}
            </tbody>
        </table>
    </div>

    {reach_html}

    <div class="card">
        <h2>🏷️ Classificazione di Pericolo GHS / CLP</h2>
        <p><strong>Avvertenza:</strong> <span class="{'badge-danger' if clp_info['signal'] == 'PERICOLO' else 'badge-warning'}">{clp_info['signal']}</span></p>
        <p><strong>Pittogrammi di Pericolo:</strong> {pic_badges}</p>
        <h3>Indicazioni di Pericolo (Frasi H):</h3>
        {h_html}
        <h3>Consigli di Prudenza Raccomandati (Frasi P):</h3>
        {p_html}
    </div>

    <div class="card">
        <h2>🚚 Classificazione Trasporto Merci Pericolose (ADR)</h2>
        <p><strong>Stato Spedizione:</strong> {'🚨 MERCE SOGGETTA AD ADR' if adr_info['regulated'] else '🟢 MERCE NON PERICOLOSA'}</p>
        <p><strong>Designazione Ufficiale Completa:</strong> <code style="font-size: 14px; color: #1e3a8a;">{adr_info['desc']}</code></p>
        <p><strong>Classe ADR:</strong> {adr_info['class']} | <strong>Gruppo Imballo:</strong> {adr_info['pg']}</p>
        <p><strong>Categoria di Trasporto:</strong> Categoria {adr_info.get('cat', 3)}</p>
    </div>

    <div class="footer">
        Documento di Audit Normativo conforme alle linee guida ECHA.
    </div>
</body>
</html>"""

# =====================================================================
# 11. GENERATORE CONSIGLI DI PRUDENZA P-CODES
# =====================================================================
def get_p_codes_from_h(h_codes: list, signal: str) -> list:
    p_codes = set()
    p_codes.add("P102")
    p_codes.add("P501")

    if any(h in h_codes for h in ["H224", "H225", "H226", "H220"]):
        p_codes.add("P210")
        p_codes.add("P233")

    if any(h in h_codes for h in ["H314", "H318", "H315", "H319"]):
        p_codes.add("P280")
        p_codes.add("P264")

    if "H314" in h_codes:
        p_codes.add("P260")
        p_codes.add("P301+P330+P331")
        p_codes.add("P303+P361+P353")

    if "H304" in h_codes:
        p_codes.add("P301+P310")
        p_codes.add("P331")

    if any(h in h_codes for h in ["H400", "H410", "H411"]):
        p_codes.add("P273")

    return sorted(list(p_codes))

# =====================================================================
# 12. PARSER DELLA DISTINTA FORMULATO (SEZIONE 3 SDS)
# =====================================================================
def parse_smart_input(text: str) -> list:
    chunks = re.split(r"[,+;\n]+", text.strip())
    parsed_items = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk: continue

        match_conc = re.search(r"[:\s]+(\d+[\.,]?\d*)\s*%?$", chunk)
        if match_conc:
            batch_conc = float(match_conc.group(1).replace(",", "."))
            raw_substance = chunk[:match_conc.start()].strip()
        else:
            batch_conc = None
            raw_substance = chunk.strip()

        assay = 100.0
        assay_match = re.search(r"[\(\[\s]?(?:titolo|assay|purezza|purity|al)?\s*(\d+[\.,]?\d*)\s*%\s*[\)\]]?", raw_substance, re.IGNORECASE)
        if assay_match:
            try:
                found_assay = float(assay_match.group(1).replace(",", "."))
                if 0.0 < found_assay <= 100.0:
                    assay = found_assay
                    raw_substance = raw_substance[:assay_match.start()] + raw_substance[assay_match.end():]
                    raw_substance = re.sub(r"[\(\)\[\]]", "", raw_substance).strip()
            except Exception:
                pass

        query = raw_substance.strip()

        if query:
            parsed_items.append({
                "query": query,
                "batch_conc": batch_conc,
                "assay": assay
            })

    if len(parsed_items) == 1 and parsed_items[0]["batch_conc"] is None:
        parsed_items[0]["batch_conc"] = 100.0

    return parsed_items

# =====================================================================
# 13. MOTORE DI CALCOLO E AUDIT (BACKEND CONDIVISO)
# =====================================================================
def process_formulation_audit(items: list) -> dict:
    recipe = []
    for it in items:
        b_val = it["batch_conc"] if it["batch_conc"] is not None else 0.0
        assay_val = it["assay"]
        info = UniversalChemicalResolver.get_substance(it["query"])

        eff_val = b_val * (assay_val / 100.0)
        carrier_val = b_val * (1.0 - (assay_val / 100.0))

        recipe.append({
            "info": info,
            "batch_conc": b_val,
            "assay": assay_val,
            "effective_conc": eff_val,
            "carrier_conc": carrier_val
        })

    if len(recipe) == 1 and recipe[0]["batch_conc"] >= 100.0 and recipe[0]["assay"] >= 100.0:
        single = recipe[0]["info"]
        cas = single["cas"]
        adr = ADRClassifier.map_adr(single)
        is_svhc = cas in REACH_SVHC_DATABASE
        annex_xvii = REACH_ANNEX_XVII.get(cas, "Nessuna restrizione specifica attiva")
        p_codes = get_p_codes_from_h(single["h_codes"], single["signal"])

        reach_list = [f"🚨 SVHC: {REACH_SVHC_DATABASE[cas]['reason']}"] if is_svhc else []
        if annex_xvii != "Nessuna restrizione specifica attiva":
            reach_list.append(f"⚖️ {annex_xvii}")

        clp_info = {
            "signal": single["signal"],
            "pictograms": single["pictograms"],
            "h_codes": single["h_codes"],
            "p_codes": p_codes
        }

        html_report = ReportGenerator.build_html_string(single["common_name"], recipe, reach_list, clp_info, adr, [])

        return {
            "is_single": True,
            "recipe": recipe,
            "single_info": single,
            "adr": adr,
            "reach_alerts": reach_list,
            "clp_info": clp_info,
            "incomp_alerts": [],
            "html_report": html_report,
            "total_batch": 100.0
        }

    total_batch_conc = sum(c["batch_conc"] for c in recipe)
    incomp_alerts = IncompatibilityAnalyzer.analyze(recipe)

    reach_alerts = []
    for item in recipe:
        cas = item["info"]["cas"]
        eff = item["effective_conc"]
        if cas in REACH_SVHC_DATABASE and eff >= 0.1:
            reach_alerts.append(f"🚨 SVHC: {REACH_SVHC_DATABASE[cas]['substance']} presente al {eff:.2f}% (≥ 0.1% p/p). Obbligo SCIP e Sezione 3 SDS.")

    mix_h = set()
    mix_pics = set()
    signal = "Nessuna"

    flam_contributors = []
    corr_contributors = []
    flam_conc = 0.0
    corr_conc = 0.0
    eye_conc = 0.0

    for c in recipe:
        eff = c["effective_conc"]
        h_list = c["info"]["h_codes"]
        c_name = c["info"]["common_name"]

        if any(h in h_list for h in ["H224", "H225", "H226"]):
            flam_conc += eff
            flam_contributors.append(c_name)

        if "H314" in h_list:
            corr_conc += eff
            corr_contributors.append(c_name)

        if "H319" in h_list:
            eye_conc += eff

        if eff >= 0.1 and "H350" in h_list:
            mix_h.add("H350")
            mix_pics.add("GHS08")
            signal = "PERICOLO"

    if flam_conc >= 30.0:
        mix_h.add("H225")
        mix_pics.add("GHS02")
        signal = "PERICOLO"
    elif flam_conc >= 10.0:
        mix_h.add("H226")
        mix_pics.add("GHS02")
        if signal != "PERICOLO": signal = "ATTENZIONE"

    if corr_conc >= 5.0:
        mix_h.add("H314")
        mix_pics.add("GHS05")
        signal = "PERICOLO"
    elif eye_conc >= 10.0 or corr_conc >= 1.0:
        mix_h.add("H319")
        mix_pics.add("GHS07")
        if signal != "PERICOLO": signal = "ATTENZIONE"

    p_codes = get_p_codes_from_h(list(mix_h), signal)

    tech_flam = ", ".join(list(dict.fromkeys(flam_contributors))[:2])
    tech_corr = ", ".join(list(dict.fromkeys(corr_contributors))[:2])

    if "H314" in mix_h and "H225" in mix_h:
        spec = f" (contiene {tech_flam} e {tech_corr})" if (tech_flam and tech_corr) else ""
        adr = {"regulated": True, "un": "UN 2924", "class": "3 (8)", "pg": "II", "desc": f"UN 2924 LIQUIDO INFIAMMABILE, CORROSIVO, N.A.S.{spec}", "cat": 2}
    elif "H314" in mix_h:
        spec = f" (contiene {tech_corr})" if tech_corr else ""
        adr = {"regulated": True, "un": "UN 1760", "class": "8", "pg": "II", "desc": f"UN 1760 LIQUIDO CORROSIVO, N.A.S.{spec}", "cat": 2}
    elif "H225" in mix_h:
        spec = f" (contiene {tech_flam})" if tech_flam else ""
        adr = {"regulated": True, "un": "UN 1993", "class": "3", "pg": "II", "desc": f"UN 1993 LIQUIDO INFIAMMABILE, N.A.S.{spec}", "cat": 2}
    elif "H226" in mix_h:
        spec = f" (contiene {tech_flam})" if tech_flam else ""
        adr = {"regulated": True, "un": "UN 1993", "class": "3", "pg": "III", "desc": f"UN 1993 LIQUIDO INFIAMMABILE, N.A.S.{spec}", "cat": 3}
    else:
        adr = {"regulated": False, "un": "Nessuno", "class": "Non regolamentato", "pg": "N/A", "desc": "MERCE NON PERICOLOSA AI FINI DEL TRASPORTO", "cat": 4}

    clp_info = {
        "signal": signal,
        "pictograms": sorted(list(mix_pics)),
        "h_codes": sorted(list(mix_h)),
        "p_codes": p_codes
    }

    html_report = ReportGenerator.build_html_string("Formulato Finito", recipe, reach_alerts, clp_info, adr, incomp_alerts)

    return {
        "is_single": False,
        "recipe": recipe,
        "adr": adr,
        "reach_alerts": reach_alerts,
        "clp_info": clp_info,
        "incomp_alerts": incomp_alerts,
        "html_report": html_report,
        "total_batch": total_batch_conc
    }

# =====================================================================
# 14. INTERFACCIA WEB STREAMLIT
# =====================================================================
def main():
    st.set_page_config(
        page_title="Audit Formulati Chimici EHS",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
        <style>
        .main-header { font-size: 24px; font-weight: bold; color: #1e3a8a; margin-bottom: 5px; }
        .sub-header { color: #64748b; font-size: 14px; margin-bottom: 20px; }
        .badge-danger { background-color: #fee2e2; color: #b91c1c; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .badge-warning { background-color: #fef3c7; color: #b45309; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .badge-ok { background-color: #dcfce7; color: #15803d; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar Navigazione
    st.sidebar.image("https://img.icons8.com/fluency/96/test-tube.png", width=60)
    st.sidebar.title("Sistema Esperto EHS")
    st.sidebar.caption("Audit Formulati • CLP • REACH • ADR 2025")

    mode = st.sidebar.radio(
        "Seleziona Funzionalità:",
        [
            "🧪 Audit Formulato Finito",
            "🚚 Calcolatore Furgoni ADR (1.1.3.6)",
            "📖 Manuale d'Uso & Normative",
            "⚡ Archivio Sostanze Offline"
        ]
    )

    # -----------------------------------------------------------------
    # SEZIONE 1: AUDIT FORMULATO FINITO
    # -----------------------------------------------------------------
    if mode == "🧪 Audit Formulato Finito":
        st.markdown("<div class='main-header'>🧪 Verifica e Omologazione Formulato Finito</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Inserisci la distinta componenti (Sezione 3 SDS o Batch Record) per verificare la conformità CLP, REACH e ADR.</div>", unsafe_allow_html=True)

        col_input, col_preset = st.columns([3, 1])

        with col_preset:
            st.markdown("**Esempi Rapidi:**")
            if st.button("🧪 Miscela Solventi"):
                st.session_state["formula_input"] = "Acetone 40%, Xilene 30%, White Spirit 30%"
            if st.button("⚖️ Acido Tecnico (37%)"):
                st.session_state["formula_input"] = "Acido cloridrico (titolo 37%) 20%, Acqua 80%"
            if st.button("🚨 Sostanza SVHC (DMF)"):
                st.session_state["formula_input"] = "Dimetilformammide 5%, Toluene 45%, Acetato di etile 50%"
            if st.button("⚠️ Rischio Reazione"):
                st.session_state["formula_input"] = "Candeggina 50%, Acido cloridrico 50%"

        with col_input:
            formula_text = st.text_area(
                "Distinta Formulato / Miscela:",
                value=st.session_state.get("formula_input", "Acetone 40%, Xilene 30%, White Spirit 30%"),
                height=110,
                help="Puoi indicare il titolo ad es. 'Acido cloridrico (titolo 37%) 10%'"
            )

        if st.button("🚀 Avvia Audit di Conformità", type="primary"):
            items = parse_smart_input(formula_text)
            if not items:
                st.error("❌ Nessun componente rilevato. Inserisci una formula valida.")
                return

            with st.spinner("Risoluzione chimica e calcolo normativo in corso..."):
                try:
                    res = process_formulation_audit(items)
                except Exception as e:
                    st.error(f"❌ Errore durante l'audit: {e}")
                    return

            st.markdown("---")

            # 1. Incompatibilità
            if res["incomp_alerts"]:
                for alert in res["incomp_alerts"]:
                    st.error(alert)

            # 2. REACH SVHC
            if res["reach_alerts"]:
                for r in res["reach_alerts"]:
                    st.warning(r)
            else:
                st.success("🟢 REACH: Nessun componente SVHC sopra la soglia dello 0.1% p/p.")

            # 3. Tabella Composizione
            st.subheader("📋 Composizione e Principi Attivi Reali")
            table_data = []
            for idx, c in enumerate(res["recipe"], 1):
                info = c["info"]
                table_data.append({
                    "#": idx,
                    "Materia Prima": info["common_name"],
                    "Numero CAS": info["cas"],
                    "% in Ricetta": f"{c['batch_conc']:.2f}%",
                    "Titolo (Assay)": f"{c['assay']:.1f}%",
                    "% Attivo Reale": f"{c['effective_conc']:.2f}%",
                    "Formula": info["formula"]
                })
            st.dataframe(table_data, use_container_width=True)

            if abs(res["total_batch"] - 100.0) > 0.5:
                st.info(f"ℹ️ Nota Bilancio: Il totale dosato differisce dal 100% (Somma rilevata: {res['total_batch']:.1f}%)")

            # 4. Colonne CLP e ADR
            col_clp, col_adr = st.columns(2)

            with col_clp:
                st.subheader("🏷️ Classificazione Pericolo CLP (CE 1272/2008)")
                signal_badge = f"<span class='{'badge-danger' if res['clp_info']['signal'] == 'PERICOLO' else 'badge-warning'}'>{res['clp_info']['signal']}</span>"
                st.markdown(f"**Avvertenza:** {signal_badge}", unsafe_allow_html=True)
                
                pics = " ".join([f"`{p}`" for p in res["clp_info"]["pictograms"]]) or "*Nessun pittogramma*"
                st.markdown(f"**Pittogrammi:** {pics}")

                st.markdown("**Frasi di Rischio (H-Codes):**")
                if res["clp_info"]["h_codes"]:
                    for h in res["clp_info"]["h_codes"]:
                        st.markdown(f"- **{h}**: {H_STATEMENTS_IT.get(h, '')}")
                else:
                    st.markdown("*Nessun pericolo identificato (Formulato non pericoloso).*")

                st.markdown("**Consigli di Prudenza (P-Codes):**")
                for p in res["clp_info"]["p_codes"]:
                    st.markdown(f"- **{p}**: {P_STATEMENTS_IT.get(p, '')}")

            with col_adr:
                st.subheader("🚚 Trasporto Merci Pericolose (ADR)")
                adr = res["adr"]
                status_badge = "<span class='badge-danger'>🚨 MERCE SOGGETTA AD ADR</span>" if adr["regulated"] else "<span class='badge-ok'>🟢 NON REGOLAMENTATO</span>"
                st.markdown(f"**Stato:** {status_badge}", unsafe_allow_html=True)
                st.markdown(f"**Designazione Ufficiale:** `{adr['desc']}`")
                st.markdown(f"**Classe:** `{adr['class']}` | **Gruppo Imballo:** `{adr['pg']}`")
                st.markdown(f"**Categoria di Trasporto:** `Categoria {adr.get('cat', 3)}`")

            st.markdown("---")

            # 5. Download Scheda
            st.subheader("📄 Esportazione Scheda di Omologazione")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"omologazione_formulato_{timestamp}.html"
            st.download_button(
                label="📥 Scarica Scheda Tecnica Ufficiale (HTML Stampabile)",
                data=res["html_report"],
                file_name=filename,
                mime="text/html",
                type="primary"
            )

    # -----------------------------------------------------------------
    # SEZIONE 2: CALCOLATORE FURGONI ADR (1000 PUNTI)
    # -----------------------------------------------------------------
    elif mode == "🚚 Calcolatore Furgoni ADR (1.1.3.6)":
        st.markdown("<div class='main-header'>🚚 Calcolatore Esenzione Trasporto ADR (Regola dei 1000 Punti)</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Verifica se un quantitativo di solvente o formulato può viaggiare su normale furgone senza patentino ADR (Cap. 1.1.3.6).</div>", unsafe_allow_html=True)

        col_chem, col_qty = st.columns(2)
        with col_chem:
            adr_chem = st.text_input("Solvente o Sostanza:", value="Xilene", help="Es. Xilene, Toluene, Acetone, Diclorometano...")
        with col_qty:
            adr_qty_str = st.text_input("Quantità da trasportare (con unità):", value="860 kg", help="Puoi scrivere '860 kg' oppure '1000 L'")

        if st.button("⚖️ Calcola Esenzione 1.1.3.6", type="primary"):
            try:
                data = UniversalChemicalResolver.get_substance(adr_chem)
                adr = ADRClassifier.map_adr(data)

                if not adr["regulated"]:
                    st.success(f"🟢 **{data['common_name']}** non è soggetta ad ADR. Nessun limite di punti.")
                    return

                cat = adr.get("cat", 3)
                multipliers = {0: 0, 1: 50, 2: 3, 3: 1, 4: 0}
                mult = multipliers.get(cat, 1)
                cas = data.get("cas", "")
                density = DENSITY_DATABASE.get(cas, 1.0)

                num_match = re.search(r"(\d+[\.,]?\d*)", adr_qty_str)
                if not num_match:
                    st.error("❌ Quantità numerica non valida.")
                    return

                val_numeric = float(num_match.group(1).replace(",", "."))
                is_kg = "kg" in adr_qty_str.lower() or "chili" in adr_qty_str.lower()
                is_liquid = adr.get("is_liquid", True)

                if is_liquid and is_kg:
                    liters = val_numeric / density
                    st.info(f"⚖️ **Conversione Densità Automatica:** {val_numeric} Kg di liquido (densità {density} kg/L) corrispondono a **{liters:.1f} Litri nominali ADR**.")
                    final_adr_qty = liters
                    unit_disp = f"{liters:.1f} Litri (da {val_numeric} Kg)"
                elif is_liquid:
                    final_adr_qty = val_numeric
                    unit_disp = f"{val_numeric} Litri"
                else:
                    final_adr_qty = val_numeric
                    unit_disp = f"{val_numeric} Kg"

                points, is_exempt = ADRClassifier.calculate_1000_points(cat, final_adr_qty)

                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("Materia", data['common_name'])
                col_res2.metric("Categoria ADR", f"Cat. {cat} (x{mult})")
                col_res3.metric("Punti ADR Calcolati", f"{points:.1f} / 1000")

                st.markdown("---")
                if is_exempt:
                    st.success(f"""
                    ### 🟢 ESENZIONE PARZIALE ATTIVA (Totale Punti: {points:.1f})
                    * **Regime Operativo:** Trasportabile su furgone normale **SENZA patentino ADR (CFP)**, senza pannelli arancioni e senza kit ADR completo.
                    * **Requisiti minimi:** Estintore da 2 kg a bordo e documento di trasporto con indicazione dei punti calcolati.
                    """)
                else:
                    st.error(f"""
                    ### 🚨 SOGLIA 1000 PUNTI SUPERATA (Totale Punti: {points:.1f})
                    * **Regime Operativo:** **OBBLIGO REGIME ADR COMPLETO**.
                    * **Requisiti:** Autista munito di patentino ADR (CFP), veicolo con pannelli arancioni aperti, istruzioni scritte di emergenza e dotazione DPI/borsa ADR completa.
                    """)

            except Exception as e:
                st.error(f"❌ Errore durante il calcolo: {e}")

    # -----------------------------------------------------------------
    # SEZIONE 3: MANUALE D'USO & QUADRO NORMATIVO (NUOVA)
    # -----------------------------------------------------------------
    elif mode == "📖 Manuale d'Uso & Normative":
        st.markdown("<div class='main-header'>📖 Manuale Operativo & Quadro Normativo</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Guida tecnica per responsabili HSE, RSPP, tecnici di laboratorio e logistica trasporti.</div>", unsafe_allow_html=True)

        tab_dest, tab_norm, tab_sintassi, tab_esenzione = st.tabs([
            "🎯 Destinatari",
            "⚖️ Normative Applicate",
            "✍️ Guida all'Inserimento",
            "🚚 Regola 1000 Punti ADR"
        ])

        with tab_dest:
            st.markdown("### Figure Professionali di Riferimento")
            st.markdown("""
            * **Responsabili HSE e RSPP:**  
              Verifica istantanea di conformità documentale per formulati e lotti in uscita; screening sistematico dei rischi chimici e prevenzione incidenti da incompatibilità nello stoccaggio e nella miscelazione.
            * **Tecnici R&D e Operatori di Laboratorio/Formulazione:**  
              Controllo immediato dei pericoli generati dalle nuove ricette; gestione automatizzata del **titolo commerciale (assay)** delle materie prime tecniche (es. acidi o basi in soluzione acquosa) per calcolare l'attivo effettivo e non sovrastimare i pericoli.
            * **Ufficio Logistica, Spedizioni e Trasportatori:**  
              Classificazione su strada e verifica immediata dei **1000 punti ADR (Cap. 1.1.3.6)** per stabilire all'istante se un ordine può partire con furgone ordinario senza patentino o necessita di regime ADR completo.
            """)

        with tab_norm:
            st.markdown("### Quadro Normativo di Riferimento")
            st.markdown("""
            1. **Regolamento (CE) n. 1272/2008 (CLP / GHS):**  
               Applicazione delle regole di **additività e soglie di pericolo generiche/specifiche** per infiammabilità (H225/H226), corrosione cutanea (H314), lesioni oculari (H318/H319), tossicità da aspirazione (H304) e sostanze CMR (H350, cancerogenesi $\ge 0{,}1\%$).
            2. **Regolamento (CE) n. 1907/2006 (REACH):**  
               Monitoraggio costante della **Candidate List (SVHC - Art. 57)** con soglia critica dello **$0{,}1\%$ peso/peso** (obblighi di notifica SCIP e Sezione 3 SDS) e controllo delle restrizioni d'uso dell'**Allegato XVII**.
            3. **Accordo Internazionale ADR (Trasporto Merci Pericolose):**  
               Attribuzione Numero ONU, Classe, Gruppo Imballo e Categoria di Trasporto. Applicazione della **Regola ADR 3.1.2.8.1** per l'indicazione automatica dei costituenti tecnici nelle designazioni N.A.S. (es. `UN 1993 LIQUIDO INFIAMMABILE, N.A.S. (contiene ACETONE e XILENE)`).
            4. **Sicurezza dei Luoghi di Lavoro (D.Lgs. 81/2008):**  
               Matrice automatica per la prevenzione di reazioni chimiche pericolose involontarie (es. sviluppo di gas cloro tossico da acidi + candeggina, reazioni esotermiche violente acido-base).
            """)

        with tab_sintassi:
            st.markdown("### Guida alla Sintassi di Inserimento")
            st.markdown("""
            Il software accetta nomi comuni in italiano, denominazioni internazionali inglesi, numeri CAS e formule convenzionali:
            
            * **Formulato con percentuali finite già note:**  
              `Acetone 40%, Xilene 30%, White Spirit 30%`
            * **Formulato con materie prime tecniche e Titolo/Assay:**  
              `Acido cloridrico (titolo 37%) 20%, Acqua 80%`  
              *(Il sistema calcola in automatico l'attivo reale al 7.4% e assegna il 12.6% all'acqua vettore nel bilancio)*.
            * **Componente singolo puro al 100%:**  
              `Diclorometano` (oppure `DCM`, `Xilene`, `Toluene`)
            """)

        with tab_esenzione:
            st.markdown("### Calcolo Esenzione Parziale ADR (Capitolo 1.1.3.6)")
            st.markdown("""
            La regola dei 1000 punti consente il trasporto di merci pericolose su veicoli ordinari **senza obbligo di patentino ADR (CFP)**, pannelli arancioni o kit DPI, purché il totale punti sia **$\le 1000$**:
            
            * **Categoria 1 (Materie molto pericolose):** Moltiplicatore $\\times 50$ (Max 20 unità).
            * **Categoria 2 (Infiammabili PG II, es. Acetone, Toluene, Etanolo):** Moltiplicatore $\\times 3$ (Max 333 unità).
            * **Categoria 3 (Infiammabili PG III, Corrosivi PG III, es. Xilene, DCM, Acquaragia):** Moltiplicatore $\\times 1$ (Max 1000 unità).
            * **Conversione Densità:** Per i liquidi l'ADR conteggia i **Litri nominali**. Se l'operatore inserisce i **Chilogrammi** (dato da bilancia), l'app applica la densità reale del solvente per determinare i litri effettivi prima del calcolo.
            """)

    # -----------------------------------------------------------------
    # SEZIONE 4: ARCHIVIO SOSTANZE LOCALE OFFLINE
    # -----------------------------------------------------------------
    elif mode == "⚡ Archivio Sostanze Offline":
        st.markdown("<div class='main-header'>⚡ Archivio Locale Offline delle Sostanze</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Visualizza le sostanze già scaricate e memorizzate localmente per l'uso senza connessione internet.</div>", unsafe_allow_html=True)

        cache = ChemicalCacheManager.load_cache()
        st.metric("Sostanze archiviate localmente", len(cache))

        if cache:
            cache_rows = []
            for k, v in cache.items():
                cache_rows.append({
                    "Chiave": k,
                    "Nome Comune": v.get("common_name", ""),
                    "Numero CAS": v.get("cas", ""),
                    "Formula": v.get("formula", ""),
                    "Pericoli": ", ".join(v.get("h_codes", []))
                })
            st.dataframe(cache_rows, use_container_width=True)

            if st.button("🗑️ Svuota Cache Locale"):
                ChemicalCacheManager.save_cache({})
                st.success("Cache svuotata con successo!")
        else:
            st.info("Nessuna sostanza attualmente presente nella cache locale.")

if __name__ == "__main__":
    main()
