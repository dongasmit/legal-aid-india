from fpdf import FPDF
import os

def create_landmark_judgments():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    cases = [
        {
            "title": "Arnesh Kumar vs. State of Bihar (2014) - Arrest Guidelines",
            "content": """
            SUPREME COURT OF INDIA
            CASE: Arnesh Kumar vs. State of Bihar (2014) 8 SCC 273
            BENCH: Justice Chandramauli Kr. Prasad, Justice Pinaki Chandra Ghose
            
            RATIO DECIDENDI (CORE RULING):
            The Supreme Court held that arrests should not be automatic in cases where the offense is punishable with imprisonment for a term which may be less than seven years (e.g., Section 498-A IPC / Section 85 BNS).
            
            GUIDELINES ISSUED:
            1. Police officers shall not automatically arrest the accused when a case under Section 498-A IPC is registered.
            2. They must satisfy themselves about the necessity for arrest under the parameters laid down in Section 41 CrPC (now Section 35 BNSS).
            3. Police must furnish the reasons and materials which necessitated the arrest to the Magistrate.
            4. Failure to comply will render police officers liable for departmental action and Contempt of Court.
            """
        },
        {
            "title": "D.K. Basu vs. State of West Bengal (1997) - Rights of Arrestee",
            "content": """
            SUPREME COURT OF INDIA
            CASE: D.K. Basu vs. State of West Bengal (1997) 1 SCC 416
            
            RATIO DECIDENDI:
            Custodial torture is a naked violation of human dignity. The Court issued 11 commandments for police during arrest and detention.
            
            KEY REQUIREMENTS:
            1. The police personnel carrying out the arrest and handling the interrogation of the arrestee should bear accurate, visible and clear identification and name tags with their designations.
            2. A memo of arrest must be prepared at the time of arrest and strictly attested by at least one witness.
            3. The person arrested must be informed of his right to have someone informed of his arrest or detention.
            """
        },
        {
            "title": "Lalita Kumari vs. Govt. of U.P. (2014) - Mandatory FIR",
            "content": """
            SUPREME COURT OF INDIA
            CASE: Lalita Kumari vs. Govt. of U.P. (2014) 2 SCC 1
            
            RATIO DECIDENDI:
            Registration of FIR is mandatory under Section 154 of CrPC (now Section 173 BNSS) if the information discloses commission of a cognizable offence.
            
            RULING:
            1. No preliminary inquiry is permissible in such a situation.
            2. If the information received does not disclose a cognizable offence but indicates the necessity for an inquiry, a preliminary inquiry may be conducted only to ascertain whether a cognizable offence is disclosed or not.
            3. The scope of preliminary inquiry is not to verify the veracity or otherwise of the information received but only to ascertain whether the information reveals any cognizable offence.
            """
        }
    ]
    
    pdf.cell(200, 10, txt="LANDMARK CRIMINAL JUDGMENTS (CRITICAL REFERENCE)", ln=True, align='C')
    pdf.ln(10)
    
    for case in cases:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt=case["title"], ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 10, txt=case["content"])
        pdf.ln(10)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
    if not os.path.exists("source_docs"):
        os.makedirs("source_docs")
        
    pdf.output("source_docs/Landmark_Judgments.pdf")
    print(" Created 'source_docs/Landmark_Judgments.pdf'. Ready for ingestion!")

if __name__ == "__main__":
    create_landmark_judgments()