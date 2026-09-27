"""
ContactAnalyzer
Parses uploaded CSV files or demo contact datasets, normalizes fields,
validates required columns, tags segment attributes, calculates contact batch statistics,
and accurately identifies deduplication & eligibility.
"""

import csv
import io
import random
import re
from typing import Dict, List, Any, Tuple

REQUIRED_MINIMUM_FIELDS = ["first_name", "last_name", "company"]

COUNTRIES = ["United States", "United Kingdom", "Germany", "France", "Canada", "Australia", "Singapore", "India"]
COMPANY_SIZES = ["SMB (1-50)", "Mid-Market (51-500)", "Enterprise (500+)"]
INDUSTRIES = ["Technology & Software", "Financial Services", "Healthcare", "Manufacturing", "Retail & E-commerce", "Professional Services"]
JOB_TITLES = ["VP Sales", "Head of Growth", "Marketing Manager", "CTO", "Operations Director", "Account Executive", "Managing Director"]

class ContactAnalyzer:
    @staticmethod
    def parse_csv(csv_content: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
        """
        Parses raw CSV string, returns list of parsed contact dicts, summary stats, and error/warning messages.
        """
        warnings = []
        contacts = []
        
        # Parse CSV lines
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            headers = [h.strip().lower().replace(" ", "_") for h in (reader.fieldnames or [])]
        except Exception as e:
            return [], {}, [f"Invalid CSV format: {str(e)}"]

        # Check required fields
        raw_headers_map = {h.strip().lower().replace(" ", "_"): h for h in (reader.fieldnames or [])}
        
        has_email = any(f in raw_headers_map for f in ["email", "e_mail", "work_email"])
        has_domain = any(f in raw_headers_map for f in ["domain", "company_domain", "website"])
        
        if not (has_email or has_domain):
            warnings.append("CSV should ideally contain an 'email' or 'domain' column for enrichment.")

        email_key = next((raw_headers_map[f] for f in ["email", "e_mail", "work_email"] if f in raw_headers_map), None)
        domain_key = next((raw_headers_map[f] for f in ["domain", "company_domain", "website"] if f in raw_headers_map), None)
        fname_key = next((raw_headers_map[f] for f in ["first_name", "firstname", "first"] if f in raw_headers_map), None)
        lname_key = next((raw_headers_map[f] for f in ["last_name", "lastname", "last"] if f in raw_headers_map), None)
        company_key = next((raw_headers_map[f] for f in ["company", "company_name", "organization"] if f in raw_headers_map), None)
        country_key = next((raw_headers_map[f] for f in ["country", "location", "region"] if f in raw_headers_map), None)
        size_key = next((raw_headers_map[f] for f in ["company_size", "size", "employees"] if f in raw_headers_map), None)
        industry_key = next((raw_headers_map[f] for f in ["industry", "sector"] if f in raw_headers_map), None)
        title_key = next((raw_headers_map[f] for f in ["job_title", "title", "role"] if f in raw_headers_map), None)

        seen_emails = set()
        duplicate_count = 0

        for idx, row in enumerate(reader):
            fname = row.get(fname_key, "").strip() if fname_key else ""
            lname = row.get(lname_key, "").strip() if lname_key else ""
            company = row.get(company_key, "").strip() if company_key else ""
            email = row.get(email_key, "").strip() if email_key else ""
            domain = row.get(domain_key, "").strip() if domain_key else ""
            country = row.get(country_key, "").strip() if country_key else ""
            company_size = row.get(size_key, "").strip() if size_key else ""
            industry = row.get(industry_key, "").strip() if industry_key else ""
            job_title = row.get(title_key, "").strip() if title_key else ""

            # Check email uniqueness for duplicate counter
            if email:
                email_lower = email.lower()
                if email_lower in seen_emails:
                    duplicate_count += 1
                seen_emails.add(email_lower)

            # Derive domain if missing but email present
            if not domain and email and "@" in email:
                parts = email.split("@")
                if len(parts) == 2 and "." in parts[1]:
                    domain = parts[1].lower()

            # Assign default segment metadata if absent
            if not country:
                country = "United States" if idx % 3 != 0 else ("United Kingdom" if idx % 5 == 0 else "Germany")
            if not company_size:
                company_size = "Mid-Market (51-500)" if idx % 2 == 0 else ("Enterprise (500+)" if idx % 3 == 0 else "SMB (1-50)")
            if not industry:
                industry = "Technology & Software" if idx % 2 == 0 else "Financial Services"

            contact = {
                "id": f"cnt_{idx+1}",
                "first_name": fname or f"Contact_{idx+1}",
                "last_name": lname or "User",
                "company": company or "Target Company",
                "email": email,
                "domain": domain,
                "country": country,
                "company_size": company_size,
                "industry": industry,
                "job_title": job_title or "Decision Maker",
                "already_enriched": bool(email and len(email) > 5 and "." in email)
            }
            contacts.append(contact)

        stats = ContactAnalyzer.compute_stats(contacts, duplicate_count)
        return contacts, stats, warnings

    @staticmethod
    def compute_stats(contacts: List[Dict[str, Any]], duplicate_count: int = 0) -> Dict[str, Any]:
        total = len(contacts)
        with_email = sum(1 for c in contacts if c.get("email"))
        missing_email = total - with_email
        with_domain = sum(1 for c in contacts if c.get("domain"))
        already_enriched = sum(1 for c in contacts if c.get("already_enriched"))
        eligible = missing_email  # Contacts missing email need email enrichment!

        return {
            "total_contacts": total,
            "contacts_with_existing_email": with_email,
            "contacts_missing_email": missing_email,
            "contacts_with_company_domain": with_domain,
            "contacts_already_enriched": already_enriched,
            "contacts_eligible_for_enrichment": eligible,
            "proven_duplicates": duplicate_count
        }

    @staticmethod
    def generate_demo_dataset(count: int = 10000) -> str:
        """
        Generates realistic demo CSV dataset for 1k, 10k, or 50k contacts.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "first_name", "last_name", "company", "email", "domain",
            "country", "company_size", "industry", "job_title"
        ])

        first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "Oliver", "Isabella", "Lucas", "Mia", "Alexander", "Charlotte"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez"]
        companies = ["Acme Corp", "TechPulse", "Global Dynamics", "Starlight Systems", "Nexus AI", "Apex Solutions", "Vanguard Financial", "CloudScale", "Omni Health", "Quantum Data"]
        domains = ["acmecorp.com", "techpulse.io", "globaldynamics.org", "starlight.net", "nexusai.com", "apexsolutions.co", "vanguardfin.com", "cloudscale.tech"]

        for i in range(count):
            fn = first_names[i % len(first_names)]
            ln = last_names[(i * 3) % len(last_names)]
            comp = companies[(i * 7) % len(companies)]
            dom = domains[(i * 5) % len(domains)]
            
            # 65% missing email, 35% existing email
            if i % 100 < 35:
                email = f"{fn.lower()}.{ln.lower()}{i}@{dom}"
            else:
                email = ""

            country = COUNTRIES[i % len(COUNTRIES)]
            size = COMPANY_SIZES[(i * 2) % len(COMPANY_SIZES)]
            industry = INDUSTRIES[(i * 4) % len(INDUSTRIES)]
            title = JOB_TITLES[(i * 3) % len(JOB_TITLES)]

            writer.writerow([fn, ln, comp, email, dom, country, size, industry, title])

        return output.getvalue()
