import json
import re
from datetime import datetime, timedelta

def clean_date_str(d_str):
    """Standardizes various date formats into YYYY-MM-DD."""
    if not d_str: return 'N/A'
    d_str = str(d_str).strip().lower()
    if d_str in ['n/a', 'unknown', 'not specified', 'none', 'null']: return 'N/A'
    if 'open' in d_str: return 'Open until filled'
    
    # Handle ranges like "15.6. - 21.6." or "June 15 - June 21" by taking the end date
    if '-' in d_str and not re.match(r'^\d{4}-\d{2}-\d{2}$', d_str):
        parts = d_str.split('-')
        d_str = parts[-1].strip()
        
    # Standard YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', d_str):
        return d_str
        
    # Indian / European DD/MM/YYYY or DD-MM-YYYY
    slash_match = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', d_str)
    if slash_match:
        day, month, year = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
        
    # Finnish / European DD.MM.YYYY
    fi_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', d_str)
    if fi_match:
        return f"{int(fi_match.group(3)):04d}-{int(fi_match.group(2)):02d}-{int(fi_match.group(1)):02d}"
        
    # Incomplete DD.MM. (assume current year)
    fi_short = re.match(r'^(\d{1,2})\.(\d{1,2})\.?$', d_str)
    if fi_short:
        year = datetime.now().year
        return f"{year:04d}-{int(fi_short.group(2)):02d}-{int(fi_short.group(1)):02d}"

    # ISO datetime
    try:
        if 't' in d_str:
            d = datetime.fromisoformat(d_str.split('t')[0])
            return d.strftime("%Y-%m-%d")
    except ValueError:
        pass
        
    today = datetime.now()
    
    # "today", "yesterday"
    if 'today' in d_str:
        return today.strftime("%Y-%m-%d")
    if 'yesterday' in d_str:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
    # Relative formats: "X days ago", "X weeks ago", "X months ago"
    rel_match = re.search(r'(\d+)\s+(day|week|month|hour|min)', d_str)
    if rel_match:
        num = int(rel_match.group(1))
        unit = rel_match.group(2)
        if 'day' in unit:
            return (today - timedelta(days=num)).strftime("%Y-%m-%d")
        if 'week' in unit:
            return (today - timedelta(weeks=num)).strftime("%Y-%m-%d")
        if 'month' in unit:
            return (today - timedelta(days=num*30)).strftime("%Y-%m-%d")
        if 'hour' in unit or 'min' in unit:
            return today.strftime("%Y-%m-%d")
            
    # Also "X d ago", "X w ago"
    short_rel = re.search(r'(\d+)\s*(d|w|m)\s+ago', d_str)
    if short_rel:
        num = int(short_rel.group(1))
        unit = short_rel.group(2)
        if unit == 'd': return (today - timedelta(days=num)).strftime("%Y-%m-%d")
        if unit == 'w': return (today - timedelta(weeks=num)).strftime("%Y-%m-%d")
        if unit == 'm': return (today - timedelta(days=num*30)).strftime("%Y-%m-%d")
        
    # Month words: "June 15, 2026" or "15 June 2026" etc.
    try:
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        months_short = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        parts = d_str.replace(',', '').split()
        if len(parts) >= 3:
            year_part = [p for p in parts if p.isdigit() and len(p) == 4]
            day_part = [p for p in parts if p.isdigit() and len(p) <= 2]
            month_part = [p for p in parts if p in months or p in months_short]
            if year_part and day_part and month_part:
                m_str = month_part[0]
                m_idx = months.index(m_str) + 1 if m_str in months else months_short.index(m_str) + 1
                y = int(year_part[0])
                d = int(day_part[0])
                return f"{y:04d}-{m_idx:02d}-{d:02d}"
    except Exception:
        pass

    return d_str

def process_jobs():
    """Read jobs.json and standardize all dates."""
    with open('jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)
        
    changed = 0
    for job in jobs:
        p = str(job.get('posted_date', ''))
        d = str(job.get('deadline', ''))
        
        new_p = clean_date_str(p)
        new_d = clean_date_str(d)
        
        if new_p != p.lower() and new_p != p:
            job['posted_date'] = new_p
            changed += 1
            
        if new_d != d.lower() and new_d != d:
            job['deadline'] = new_d
            changed += 1
            
    with open('jobs.json', 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=2)
        
    print(f"Fixed {changed} dates.")
    
if __name__ == "__main__":
    process_jobs()
