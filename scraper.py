import json
import time
import os
import sys
import re
import unicodedata
import subprocess
import threading
import hashlib
import argparse
import glob
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_FILE = os.path.join(BASE_DIR, "jobs.json")
SEEN_URLS_FILE = os.path.join(BASE_DIR, "seen_urls.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "checkpoint.json")
REQ_FILE = os.path.join(BASE_DIR, "job_requirements.md")
DELETED_FILE = os.path.join(BASE_DIR, "deleted.json")
HISTORY_FILE = os.path.join(BASE_DIR, "jobs_history.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")


class TeeLogger:
    """Mirrors every print() to both the terminal and a daily log file.

    start_capture() / stop_capture() collect lines from one scrape batch.
    Lines from each batch are accumulated in _cycle_buf; flush_cycle() returns
    and clears it so analyze_scrape_run_log() sees the whole cycle at once.
    """

    def __init__(self, log_path: str):
        self._stdout = sys.stdout
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._log_file = open(log_path, 'a', encoding='utf-8', buffering=1)
        self._capture_buf: list[str] = []
        self._capturing = False
        self._cycle_buf: list[str] = []

    def write(self, msg: str):
        self._stdout.write(msg)
        self._log_file.write(msg)
        if self._capturing:
            self._capture_buf.append(msg)

    def flush(self):
        self._stdout.flush()
        self._log_file.flush()

    def close(self):
        self._log_file.close()

    def start_capture(self):
        self._capture_buf.clear()
        self._capturing = True

    def stop_capture(self):
        """Stop capturing; append this batch's lines to the cycle buffer."""
        self._capturing = False
        lines = ''.join(self._capture_buf).splitlines()
        self._cycle_buf.extend(lines)

    def flush_cycle(self) -> list[str]:
        """Return the full cycle's accumulated lines and reset for the next cycle."""
        lines = list(self._cycle_buf)
        self._cycle_buf.clear()
        return lines

    def __getattr__(self, name):
        return getattr(self._stdout, name)


_tee_logger: TeeLogger | None = None


def _checkpoint_reached_end() -> bool:
    """True if the last scrape_all_jobs() call visited the final target."""
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            idx = json.load(f).get("target_index", 0)
        return idx >= len(generate_targets())
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# BLOCKED KEYWORDS — jobs with these keywords in the title are auto-deleted
# ─────────────────────────────────────────────────────────────────────────────
BLOCKED_TITLE_KEYWORDS = [
    # C-suite / pure-executive (non-technical)
    'director', 'vice president', 'cto', 'ceo', 'cfo',
    # Non-technical: HR & Recruiting
    'talent acquisition', 'recruiter', 'human resources',
    # Non-technical: Finance
    'financial analyst', 'finance analyst', 'accountant', 'investor relations',
    # Non-technical: Marketing (specific non-engineer roles)
    'marketing manager', 'marketing coordinator', 'marketing analyst',
    'digital marketing', 'content marketing', 'social media manager',
    # Non-technical: Sales management (not "Sales Engineer" or "Technical Account Manager")
    'sales manager', 'sales coordinator', 'inside sales',
    # Non-technical: Supply chain / sourcing / procurement
    'sourcing manager', 'supply chain analyst', 'procurement analyst',
    'supply chain manager',
    # Non-technical: Other
    'venture associate', 'venture partner',
]

# ─────────────────────────────────────────────────────────────────────────────
# JOB SOURCES — Semiconductor / VLSI / EDA domain
# ─────────────────────────────────────────────────────────────────────────────
# ── Keyword terms searched across every keyword-capable site ──────────────
_KEYWORD_TERMS = [
    "semiconductor",
    "VLSI design",
    "ASIC design",
    "FPGA engineer",
    "RTL design engineer",
    "EDA design automation",
    "power integrity",
    "advanced packaging",
    "physical design",
    "SoC design",
]

# ── Sites that accept a keyword injected into the URL ─────────────────────
_KEYWORD_SITE_TEMPLATES = [
    {
        "id_prefix": "linkedin_ww",
        "platform": "linkedin",
        "pages": 3,
        "url_template": "https://www.linkedin.com/jobs/search?keywords={term_enc}&sortBy=DD",
    },
    {
        "id_prefix": "linkedin_india",
        "platform": "linkedin",
        "pages": 3,
        "url_template": "https://www.linkedin.com/jobs/search?keywords={term_enc}&location=India&sortBy=DD",
    },
    {
        "id_prefix": "linkedin_eu",
        "platform": "linkedin",
        "pages": 2,
        "url_template": "https://www.linkedin.com/jobs/search?keywords={term_enc}&location=European%20Union&sortBy=DD",
    },
    {
        "id_prefix": "linkedin_uk",
        "platform": "linkedin",
        "pages": 2,
        "url_template": "https://www.linkedin.com/jobs/search?keywords={term_enc}&location=United%20Kingdom&sortBy=DD",
    },
    {
        "id_prefix": "linkedin_fi",
        "platform": "linkedin",
        "pages": 2,
        "url_template": "https://www.linkedin.com/jobs/search?keywords={term_enc}&location=Finland&sortBy=DD",
    },
    {
        "id_prefix": "indeed_ww",
        "platform": "indeed",
        "pages": 3,
        "url_template": "https://www.indeed.com/jobs?q={term_enc}&sort=date",
    },
    {
        "id_prefix": "indeed_india",
        "platform": "indeed",
        "pages": 3,
        "url_template": "https://www.indeed.com/jobs?q={term_enc}&l=India&sort=date",
    },
]

# ── Fixed sites (career pages, boards that don't fit a keyword URL template)
FIXED_SITES = [
    # Naukri.com — India-specific (category URLs, not keyword search)
    {"id": "naukri_vlsi",     "platform": "naukri", "scroll_count": 12, "url": "https://www.naukri.com/vlsi-design-jobs?sort=date"},
    {"id": "naukri_semi",     "platform": "naukri", "scroll_count": 12, "url": "https://www.naukri.com/semiconductor-jobs?sort=date"},
    {"id": "naukri_fpga",     "platform": "naukri", "scroll_count": 12, "url": "https://www.naukri.com/fpga-jobs?sort=date"},
    {"id": "naukri_asic",     "platform": "naukri", "scroll_count": 12, "url": "https://www.naukri.com/asic-design-jobs?sort=date"},
    {"id": "naukri_embedded", "platform": "naukri", "scroll_count": 12, "url": "https://www.naukri.com/embedded-systems-jobs?sort=date"},

    # Glassdoor
    {"id": "glassdoor_semi", "platform": "glassdoor", "scroll_count": 10, "url": "https://www.glassdoor.com/Job/semiconductor-engineer-jobs-SRCH_KO0,22.htm?sortBy=date_desc"},

    # Major Semiconductor Companies — Career Pages
    {"id": "intel_careers",           "platform": "intel",           "scroll_count": 8, "url": "https://jobs.intel.com/en/search-jobs?k=engineer"},
    {"id": "amd_careers",             "platform": "amd",             "scroll_count": 8, "url": "https://careers.amd.com/careers/SearchJobs?sort=posting_date"},
    {"id": "nvidia_careers",          "platform": "nvidia",          "scroll_count": 8, "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite?q=engineer"},
    {"id": "qualcomm_careers",        "platform": "qualcomm",        "scroll_count": 8, "url": "https://careers.qualcomm.com/careers?query=engineer&sortBy=relevance"},
    {"id": "broadcom_careers",        "platform": "broadcom",        "scroll_count": 8, "url": "https://broadcom.wd1.myworkdayjobs.com/External_Career?q=engineer"},
    {"id": "ti_careers",              "platform": "ti",              "scroll_count": 8, "url": "https://careers.ti.com/search-jobs?k=engineer"},
    {"id": "nxp_careers",             "platform": "nxp",             "scroll_count": 8, "url": "https://nxp.wd3.myworkdayjobs.com/careers?q=engineer"},
    {"id": "infineon_careers",        "platform": "infineon",        "scroll_count": 8, "url": "https://www.infineon.com/cms/en/careers/jobsearch/?query=engineer"},
    {"id": "stmicro_careers",         "platform": "stmicro",         "scroll_count": 8, "url": "https://stmicroelectronics.eightfold.ai/careers?query=engineer"},
    {"id": "microchip_careers",       "platform": "microchip",       "scroll_count": 8, "url": "https://careers.microchip.com/search-jobs?k=engineer"},
    {"id": "renesas_careers",         "platform": "renesas",         "scroll_count": 8, "url": "https://www.renesas.com/en/about/careers/search?q=engineer"},
    {"id": "marvell_careers",         "platform": "marvell",         "scroll_count": 8, "url": "https://marvell.wd1.myworkdayjobs.com/MarvellCareers2?q=engineer"},
    {"id": "adi_careers",             "platform": "adi",             "scroll_count": 8, "url": "https://analogdevices.wd1.myworkdayjobs.com/External?q=engineer"},
    {"id": "onsemi_careers",          "platform": "onsemi",          "scroll_count": 8, "url": "https://onsemi.wd1.myworkdayjobs.com/onsemiExternalSite?q=engineer"},
    {"id": "micron_careers",          "platform": "micron",          "scroll_count": 8, "url": "https://micron.eightfold.ai/careers?query=engineer"},
    {"id": "mediatek_careers",        "platform": "mediatek",        "scroll_count": 8, "url": "https://careers.mediatek.com/eREC/search?query=engineer"},
    {"id": "arm_careers",             "platform": "arm",             "scroll_count": 8, "url": "https://careers.arm.com/search-jobs?k=engineer"},
    {"id": "samsung_semi_careers",    "platform": "samsung_semi",    "scroll_count": 8, "url": "https://semiconductor.samsung.com/us/careers/job-search/?keyword=engineer"},
    {"id": "tsmc_careers",            "platform": "tsmc",            "scroll_count": 8, "url": "https://careers.tsmc.com/careers/SearchJobs?sort=posting_date"},
    {"id": "globalfoundries_careers", "platform": "globalfoundries", "scroll_count": 8, "url": "https://globalfoundries.wd1.myworkdayjobs.com/External?q=engineer"},
    {"id": "skhynix_careers",         "platform": "skhynix",         "scroll_count": 8, "url": "https://recruit.skhynix.com/eng/search.do"},

    # EDA / Design Automation Companies
    {"id": "synopsys_careers",    "platform": "synopsys",    "scroll_count": 8, "url": "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25235&siteid=5359#keyWordSearch=engineer"},
    {"id": "cadence_careers",     "platform": "cadence",     "scroll_count": 8, "url": "https://cadence.wd1.myworkdayjobs.com/External_Careers?q=engineer"},
    {"id": "siemens_eda_careers", "platform": "siemens_eda", "scroll_count": 8, "url": "https://jobs.siemens.com/careers?query=EDA&location=&pid=&domain=&sort_by=date&triggerGoButton=false"},
    {"id": "ansys_careers",       "platform": "ansys",       "scroll_count": 8, "url": "https://careers.ansys.com/search-jobs?k=semiconductor"},
    {"id": "keysight_careers",    "platform": "keysight",    "scroll_count": 8, "url": "https://jobs.keysight.com/search-jobs?k=engineer"},

    # Consultancies & Staffing
    {"id": "tata_elxsi_careers", "platform": "tata_elxsi", "scroll_count": 8, "url": "https://www.tataelxsi.com/careers/job-search.html"},
    {"id": "sifive_careers",     "platform": "sifive",     "scroll_count": 8, "url": "https://www.sifive.com/careers"},
    {"id": "tessolve_careers",   "platform": "tessolve",   "scroll_count": 8, "url": "https://www.tessolve.com/careers/"},

    # Government / Public Sector (India)
    {"id": "isro_careers", "platform": "isro", "scroll_count": 6, "url": "https://www.isro.gov.in/careers.html"},
    {"id": "drdo_careers", "platform": "drdo", "scroll_count": 6, "url": "https://www.drdo.gov.in/drdo/job-opportunities"},
    {"id": "bel_careers",  "platform": "bel",  "scroll_count": 6, "url": "https://www.bel-india.in/Ede/ContentPage.aspx?MId=21&CId=0&LId=1&link=291"},
    {"id": "cdac_careers", "platform": "cdac", "scroll_count": 6, "url": "https://www.cdac.in/index.aspx?id=ca_openpositions"},

    # Startup Job Boards
    {"id": "yc_semi",       "platform": "yc",       "scroll_count": 10, "url": "https://www.workatastartup.com/jobs?query=semiconductor"},
    {"id": "wellfound_semi","platform": "wellfound", "scroll_count": 10, "url": "https://wellfound.com/role/r/semiconductor-engineer"},
    {"id": "builtin_semi",  "platform": "builtin",   "scroll_count": 10, "url": "https://builtin.com/jobs?search=semiconductor"},

    # European / UK specialist boards
    {"id": "ic_resources",       "platform": "ic_resources",      "scroll_count": 8,  "url": "https://ic-resources.com/en/jobs/semiconductor"},
    {"id": "euro_engineer_jobs", "platform": "euro_engineer_jobs","scroll_count": 8,  "url": "https://www.euroengineerjobs.com/jobs/semiconductor"},
    {"id": "jobly_fi_engineer",  "platform": "jobly",             "scroll_count": 10, "url": "https://www.jobly.fi/tyopaikat?search=engineer"},
    {"id": "work_in_finland",    "platform": "work_in_finland",   "scroll_count": 8,  "url": "https://www.workinfinland.com/en/open-jobs/?industry=engineering"},

    # Reddit
    {"id": "reddit_chipdesign", "platform": "reddit", "scroll_count": 6, "url": "https://old.reddit.com/r/chipdesign/search?q=hiring+OR+freelance+OR+contract+OR+part-time&restrict_sr=on&sort=new&t=all"},
    {"id": "reddit_ece",        "platform": "reddit", "scroll_count": 6, "url": "https://old.reddit.com/r/ECE/search?q=hiring+OR+freelance+OR+contract+OR+part-time&restrict_sr=on&sort=new&t=all"},
    {"id": "reddit_hwstartups", "platform": "reddit", "scroll_count": 6, "url": "https://old.reddit.com/r/hwstartups/search?q=hiring+OR+freelance+OR+contract+OR+part-time&restrict_sr=on&sort=new&t=all"},
]

_DEFAULT_SCROLL_COUNT = 8


def _page_url(base_url: str, platform: str, page_idx: int) -> str:
    if page_idx == 0:
        return base_url
    if platform == 'linkedin':
        return base_url + f'&start={page_idx * 25}'
    if platform == 'indeed':
        return base_url + f'&start={page_idx * 10}'
    return base_url


def _term_slug(term: str) -> str:
    """ASCII slug from a search term for use in target IDs."""
    normalized = unicodedata.normalize('NFKD', term)
    ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '_', ascii_str.lower()).strip('_')


def generate_targets():
    from urllib.parse import quote_plus
    targets = []

    # 1. Every keyword × every keyword-capable site
    for term in _KEYWORD_TERMS:
        slug = _term_slug(term)
        term_enc = quote_plus(term)
        for tmpl in _KEYWORD_SITE_TEMPLATES:
            base_url = tmpl['url_template'].replace('{term_enc}', term_enc)
            max_pages = tmpl.get('pages', 1)
            scroll_count = tmpl.get('scroll_count', _DEFAULT_SCROLL_COUNT)
            base_id = f"{tmpl['id_prefix']}_{slug}"
            for page_idx in range(max_pages):
                url = _page_url(base_url, tmpl['platform'], page_idx)
                tid = base_id if page_idx == 0 else f"{base_id}_p{page_idx + 1}"
                targets.append({'id': tid, 'platform': tmpl['platform'], 'term': term,
                                'url': url, 'scroll_count': scroll_count})

    # 2. Fixed sites (career pages, specialist boards — no keyword injection)
    for site in FIXED_SITES:
        max_pages = site.get('pages', 1)
        scroll_count = site.get('scroll_count', _DEFAULT_SCROLL_COUNT)
        for page_idx in range(max_pages):
            url = _page_url(site['url'], site['platform'], page_idx)
            tid = site['id'] if page_idx == 0 else f"{site['id']}_p{page_idx + 1}"
            targets.append({'id': tid, 'platform': site['platform'], 'term': 'All',
                            'url': url, 'scroll_count': scroll_count})

    return targets


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_linkedin(soup):
    """Parse LinkedIn job search results page."""
    jobs = []
    for card in soup.find_all('div', class_='base-card'):
        title_elem = card.find('h3', class_='base-search-card__title')
        company_elem = card.find('h4', class_='base-search-card__subtitle')
        location_elem = card.find('span', class_='job-search-card__location')
        url_elem = card.find('a', class_='base-card__full-link')
        if title_elem and url_elem:
            title = title_elem.text.strip()
            # Check blocked keywords
            title_lower = title.lower()
            if any(kw in title_lower for kw in BLOCKED_TITLE_KEYWORDS):
                continue
            jobs.append({
                "title": title,
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": location_elem.text.strip() if location_elem else "Unknown",
                "url": url_elem['href'].split('?')[0],
                "visited": "no",
                "matches_requirements": "pending",
                "reason": ""
            })
    return jobs


def parse_reddit(soup):
    """Parse old.reddit.com search results page."""
    jobs = []
    # Old reddit search results use class 'search-result'
    for post in soup.find_all('div', class_='search-result'):
        title_elem = post.find('a', class_='search-title')
        subreddit_elem = post.find('a', class_='search-subreddit-link')
        
        if title_elem:
            title = title_elem.text.strip()
            title_lower = title.lower()
            if any(kw in title_lower for kw in BLOCKED_TITLE_KEYWORDS):
                continue
                
            url = title_elem.get('href', '')
            if url and not url.startswith('http'):
                url = 'https://old.reddit.com' + url
                
            jobs.append({
                "title": title,
                "company": subreddit_elem.text.strip() if subreddit_elem else "Reddit",
                "location": "Global / Remote / See Post",
                "url": url.split('?')[0],
                "visited": "no",
                "matches_requirements": "pending",
                "reason": ""
            })
    return jobs


def parse_naukri(soup):
    """Parse Naukri.com job search results page."""
    jobs = []
    # Naukri uses article tags with class 'jobTuple' or similar card structures
    for card in soup.find_all(['article', 'div'], class_=re.compile(r'(jobTuple|srp-jobtuple|cust-job-tuple)', re.I)):
        title_elem = card.find(['a', 'h2'], class_=re.compile(r'(title|desig)', re.I))
        company_elem = card.find(['a', 'span'], class_=re.compile(r'(comp-name|companyInfo|subTitle)', re.I))
        location_elem = card.find(['span', 'li'], class_=re.compile(r'(loc|location|locWd498)', re.I))

        if title_elem:
            title = title_elem.text.strip()
            title_lower = title.lower()
            if any(kw in title_lower for kw in BLOCKED_TITLE_KEYWORDS):
                continue

            url = ''
            if title_elem.name == 'a' and title_elem.get('href'):
                url = title_elem['href']
            elif title_elem.find('a', href=True):
                url = title_elem.find('a', href=True)['href']

            if not url:
                link = card.find('a', href=True)
                if link:
                    url = link['href']

            if url and not url.startswith('http'):
                url = 'https://www.naukri.com' + url

            if url and title and len(title) > 3:
                jobs.append({
                    "title": title.replace('\n', ' ').strip(),
                    "company": company_elem.text.strip() if company_elem else "Unknown",
                    "location": location_elem.text.strip() if location_elem else "Unknown",
                    "url": url.split('?')[0],
                    "visited": "no",
                    "matches_requirements": "pending",
                    "reason": ""
                })
    
    # Fallback: try generic link extraction if no structured cards found
    if not jobs:
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/job-listings-' in href.lower() or '/job/' in href.lower():
                title = a.text.strip()
                if 5 < len(title) < 100:
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in BLOCKED_TITLE_KEYWORDS):
                        continue
                    full_url = href if href.startswith('http') else 'https://www.naukri.com' + href
                    jobs.append({
                        "title": title.replace('\n', ' ').strip(),
                        "company": "Extract from page",
                        "location": "Extract from page",
                        "url": full_url.split('?')[0],
                        "visited": "no",
                        "matches_requirements": "pending",
                        "reason": ""
                    })
    return jobs


def parse_generic(soup, base_url):
    """Parse generic job board or career page by extracting links with job-related URL patterns."""
    jobs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Look for URL paths commonly associated with job postings
        if any(kw in href.lower() for kw in ['/job', '/career', '/position', '/vacancy', '/opening', '/requisition',
                                               '/view', '/rc/clk', '/apply', '/posting']):
            # Skip search/list filter queries, sorting options, base list pages, and non-job pages
            if any(skip in href.lower() for skip in [
                '?search=', '?q=', '?sort=', '?query=',
                '/careers?', '/job-search?', '/search-jobs?',
                'destination=search', '/login', '/signup', '/register',
                '/pricing', '/about', '/contact', '/blog',
                '/job-bookmarks', '/saved-jobs', 'apply-now'
            ]):
                continue
            clean_path = href.lower().split('?')[0].rstrip('/')
            if clean_path.endswith('/careers') or clean_path.endswith('/jobs') or clean_path.endswith('/openings'):
                continue
            title = a.text.strip()
            title_lower = title.lower()
            if any(kw in title_lower for kw in BLOCKED_TITLE_KEYWORDS):
                continue
            if 5 < len(title) < 100 and not any(skip in title.lower() for skip in [
                'read more', 'learn more', 'see all', 'show all', 'view all',
                'sign in', 'log in', 'apply now', 'click here'
            ]):
                raw_url = urljoin(base_url, href)
                # Normalize Indeed URLs to prevent duplicates
                if "indeed.com/rc/clk" in raw_url and "jk=" in raw_url:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(raw_url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if 'jk' in qs:
                        raw_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?jk={qs['jk'][0]}"

                jobs.append({
                    "title": title.replace('\n', ' ').strip(),
                    "company": "Extract from page",
                    "location": "Extract from page",
                    "url": raw_url,
                    "visited": "no",
                    "matches_requirements": "pending",
                    "reason": ""
                })
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

def clean_old_backups(backup_dir):
    """Smart backup retention: keeps 1/hr for 24h, 1/day for 7d, 1/week for 4w."""
    if not os.path.exists(backup_dir):
        return

    now = datetime.now()
    files = glob.glob(os.path.join(backup_dir, "jobs_backup_*.json"))

    parsed_files = []
    for f in files:
        basename = os.path.basename(f)
        try:
            ts_str = basename.replace("jobs_backup_", "").replace(".json", "")
            file_time = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            parsed_files.append((f, file_time))
        except ValueError:
            continue

    # Sort files from newest to oldest
    parsed_files.sort(key=lambda x: x[1], reverse=True)

    keepers = set()
    seen_hours = set()
    seen_days = set()
    seen_weeks = set()

    for filepath, file_time in parsed_files:
        age = now - file_time

        # Keep latest backup unconditionally to never delete the one we just made
        if not keepers:
            keepers.add(filepath)
            continue

        if age <= timedelta(hours=24):
            hour_key = file_time.strftime("%Y%m%d_%H")
            if hour_key not in seen_hours:
                seen_hours.add(hour_key)
                keepers.add(filepath)
        elif age <= timedelta(days=8):
            day_key = file_time.strftime("%Y%m%d")
            if day_key not in seen_days:
                seen_days.add(day_key)
                keepers.add(filepath)
        elif age <= timedelta(days=36):
            week_key = f"{file_time.isocalendar()[0]}_{file_time.isocalendar()[1]}"
            if week_key not in seen_weeks:
                seen_weeks.add(week_key)
                keepers.add(filepath)

    deleted_count = 0
    for filepath, _ in parsed_files:
        if filepath not in keepers:
            try:
                os.remove(filepath)
                deleted_count += 1
            except Exception:
                pass

    if deleted_count > 0:
        print(f"INFO: Cleaned up {deleted_count} old backups (kept {len(keepers)}).")


def save_history_snapshot(jobs):
    """Append a count snapshot to jobs_history.json for trend tracking."""
    snapshot = {
        "timestamp": datetime.now().isoformat(timespec='seconds'),
        "total": len(jobs),
        "yes": sum(1 for j in jobs if j.get('matches_requirements') == 'yes'),
        "no": sum(1 for j in jobs if j.get('matches_requirements') == 'no'),
        "maybe": sum(1 for j in jobs if j.get('matches_requirements') == 'maybe'),
        "pending": sum(1 for j in jobs if j.get('matches_requirements') == 'pending'),
        "applied": sum(1 for j in jobs if j.get('applied') == 'yes'),
    }
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(snapshot)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)


def generate_history_from_backups():
    """One-time: build jobs_history.json from all existing backup files."""
    if os.path.exists(HISTORY_FILE):
        return  # Already generated
    backup_dir = os.path.join(BASE_DIR, "backups")
    files = sorted(glob.glob(os.path.join(backup_dir, "jobs_backup_*.json")))
    history = []
    for fpath in files:
        basename = os.path.basename(fpath)
        try:
            ts_str = basename.replace("jobs_backup_", "").replace(".json", "")
            ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            with open(fpath, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
            history.append({
                "timestamp": ts.isoformat(timespec='seconds'),
                "total": len(jobs),
                "yes": sum(1 for j in jobs if j.get('matches_requirements') == 'yes'),
                "no": sum(1 for j in jobs if j.get('matches_requirements') == 'no'),
                "maybe": sum(1 for j in jobs if j.get('matches_requirements') == 'maybe'),
                "pending": sum(1 for j in jobs if j.get('matches_requirements') == 'pending'),
            })
        except Exception as e:
            print(f"WARN: Skipping {basename}: {e}")
    if history:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        print(f"INFO: Generated jobs_history.json with {len(history)} snapshots from backups.")


# ─────────────────────────────────────────────────────────────────────────────
# CLEANUP — Auto-delete blocked/expired jobs
# ─────────────────────────────────────────────────────────────────────────────

def clean_blocked_jobs():
    """Finds and moves hard-rejected jobs from jobs.json to deleted.json based on job_requirements.md criteria."""
    if not os.path.exists(JOBS_FILE):
        return

    try:
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
    except Exception as e:
        print(f"Error reading {JOBS_FILE} during cleanup: {e}")
        return

    deleted_jobs = []
    if os.path.exists(DELETED_FILE):
        try:
            with open(DELETED_FILE, 'r', encoding='utf-8') as f:
                deleted_jobs = json.load(f)
        except Exception:
            pass

    cleaned_jobs = []
    moved_count = 0

    seen_deleted = {j.get('url') for j in deleted_jobs if j.get('url')}

    for job in jobs:
        # Never auto-delete jobs the user has already explicitly reviewed
        if job.get('user_review') == 'done' or job.get('applied') == 'yes':
            cleaned_jobs.append(job)
            continue

        title = job.get('title', '').lower()
        reason = job.get('reason', '').lower()

        is_blocked = False
        deletion_reason = ""

        # 1. Blocked title keywords (non-technical roles + C-suite)
        for kw in BLOCKED_TITLE_KEYWORDS:
            if kw in title:
                is_blocked = True
                deletion_reason = f"Title contains hard-rejection keyword '{kw}'"
                break

        # 2. US citizenship / no-visa-sponsorship requirement (detected in LLM reason)
        if not is_blocked:
            if any(phrase in reason for phrase in [
                "us citizenship", "security clearance required",
                "must be a u.s. citizen", "requires us citizenship",
                "no visa sponsorship", "no sponsorship",
                "us citizen only", "must be authorized to work in the us",
                "work authorization in the us",
            ]):
                is_blocked = True
                deletion_reason = "Requires US citizenship / no visa sponsorship"

        # 3. Expired deadline (> 2 days passed)
        if not is_blocked:
            deadline_str = job.get('deadline', '')
            if deadline_str and re.match(r'^\d{4}-\d{2}-\d{2}$', str(deadline_str)):
                try:
                    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d")
                    if datetime.now() > deadline_date + timedelta(days=2):
                        is_blocked = True
                        deletion_reason = f"Deadline ({deadline_str}) passed by more than 2 days and unreviewed"
                except ValueError:
                    pass

        if is_blocked:
            job['deletion_reason'] = deletion_reason
            if job.get('url') not in seen_deleted:
                deleted_jobs.append(job)
                seen_deleted.add(job.get('url'))
            moved_count += 1
        else:
            cleaned_jobs.append(job)

    if moved_count > 0:
        print(f"INFO: Moved {moved_count} hard-rejected jobs to deleted.json.")
        try:
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(cleaned_jobs, f, indent=2)
            with open(DELETED_FILE, 'w', encoding='utf-8') as f:
                json.dump(deleted_jobs, f, indent=2)
        except Exception as e:
            print(f"Error saving files during cleanup: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def scrape_all_jobs(max_jobs=200):
    """Main scraping function: navigates to each source, extracts job listings, deduplicates, saves."""
    seen_urls = set()
    if os.path.exists(SEEN_URLS_FILE):
        try:
            with open(SEEN_URLS_FILE, 'r', encoding='utf-8') as f:
                seen_urls = set(json.load(f))
        except Exception:
            pass

    # Seed seen_urls from existing jobs so a stale seen_urls.json can't cause duplicates
    existing_jobs = []
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                existing_jobs = json.load(f)
            seen_urls.update(j['url'] for j in existing_jobs)
        except Exception:
            pass

    checkpoint_idx = 0
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                checkpoint_idx = data.get("target_index", 0)
        except Exception:
            pass

    targets = generate_targets()
    if checkpoint_idx >= len(targets):
        print("Reached end of all targets. Resetting checkpoint to 0.")
        checkpoint_idx = 0

    all_extracted_jobs = []
    limit = max_jobs if max_jobs > 0 else float('inf')

    with sync_playwright() as p:
        print("Launching Playwright browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        current_idx = checkpoint_idx
        while current_idx < len(targets) and len(all_extracted_jobs) < limit:
            target = targets[current_idx]
            print(f"\nNavigating to {target['url']} (Site: {target['id']}) ...")
            try:
                page.goto(target['url'], timeout=30000)
                scroll_count = target.get('scroll_count', _DEFAULT_SCROLL_COUNT)
                for _ in range(scroll_count):
                    page.mouse.wheel(0, 2000)
                    time.sleep(1.5)

                soup = BeautifulSoup(page.content(), 'html.parser')

                if target['platform'] == 'linkedin':
                    jobs = parse_linkedin(soup)
                elif target['platform'] == 'reddit':
                    jobs = parse_reddit(soup)
                elif target['platform'] == 'naukri':
                    jobs = parse_naukri(soup)
                else:
                    jobs = parse_generic(soup, target['url'])

                print(f"Found {len(jobs)} potential job links on {target['platform']}.")

                added = 0
                for job in jobs:
                    if len(all_extracted_jobs) >= limit:
                        break
                    if job['url'] not in seen_urls:
                        job['id'] = hashlib.md5(job['url'].encode('utf-8')).hexdigest()[:8]
                        job['source'] = target['id']
                        all_extracted_jobs.append(job)
                        seen_urls.add(job['url'])
                        added += 1

                print(f"Added {added} new unseen jobs from this source.")
            except Exception as e:
                print(f"Failed to scrape {target['id']}: {e}")

            current_idx += 1

        browser.close()

    print(f"\nTotal new jobs fetched in this run: {len(all_extracted_jobs)}")
    print(f"Stopped at target index: {current_idx} out of {len(targets)}")

    # Merge: filter out any URLs already in existing_jobs (guards against seen_urls desync)
    existing_urls = {j['url'] for j in existing_jobs}
    deduped_new = [j for j in all_extracted_jobs if j['url'] not in existing_urls]
    if len(deduped_new) < len(all_extracted_jobs):
        print(f"INFO: Dropped {len(all_extracted_jobs) - len(deduped_new)} duplicate URLs at merge time.")
    combined_jobs = existing_jobs + deduped_new

    # Save combined jobs to jobs.json
    with open(JOBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(combined_jobs, f, indent=2)

    # Create a timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f"jobs_backup_{timestamp}.json")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(combined_jobs, f, indent=2)

    print(f"Total jobs currently in jobs.json: {len(combined_jobs)}")
    print(f"Backup saved to: {backup_file}\n")

    # Append to history for trend chart
    save_history_snapshot(combined_jobs)

    # Run smart cleanup
    clean_old_backups(backup_dir)

    # Save updated seen urls history
    with open(SEEN_URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(seen_urls), f)

    # Save checkpoint
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"target_index": current_idx}, f, indent=2)

    return all_extracted_jobs


# ─────────────────────────────────────────────────────────────────────────────
# REQUIREMENTS CHANGE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_file_hash(filepath):
    """Compute MD5 hash of a file."""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def check_requirements_update():
    """Check if job_requirements.md has changed, and flag jobs for re-evaluation if it has."""
    req_hash = get_file_hash(REQ_FILE)
    if not req_hash:
        return

    checkpoint_data = {}
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
        except Exception:
            pass

    saved_hash = checkpoint_data.get("requirements_hash", "")
    if saved_hash and req_hash != saved_hash:
        print("INFO: job_requirements.md has changed! Resetting evaluation status for existing jobs...")
        if os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
            for job in jobs:
                if job.get('user_review') != 'done':
                    job['needs_re_review'] = True
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2)

    checkpoint_data["requirements_hash"] = req_hash
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TEXT PROCESSING UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def extract_json_from_text(text):
    """Finds and parses the first JSON object in a text block, handling markdown code fences."""
    text = text.strip()
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = text[start_idx:end_idx + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return json.loads(text)


def clean_page_text(text):
    """Strip cookie banners, navigation, and footer boilerplate from scraped job page text.

    This preprocessing improves LLM accuracy by removing noise that causes hallucinations
    (e.g., the LLM extracting the job board name as company name).
    """
    lines = text.split('\n')
    cleaned_lines = []

    # Common boilerplate patterns to skip (case-insensitive matching)
    skip_patterns = [
        # Cookie consent / GDPR banners
        'cookie settings', 'accept all cookies', 'reject all', 'cookie policy',
        'we use cookies', 'manage cookies', 'cookie preferences',
        # Navigation / chrome
        'skip to main content', 'sign in', 'log in', 'create account',
        'sign up', 'forgot password',
        # Search UI
        'find jobs', 'search jobs', 'browse jobs', 'job search',
        # Footer
        '© 20', 'all rights reserved', 'privacy policy', 'terms of use',
        'terms and conditions', 'privacy center', 'accessibility',
        # Action prompts
        'apply on company site', 'easy apply', 'save job',
        'report this job', 'flag as', 'share this',
        # Anti-bot
        'checking your browser', 'ddos-guard', 'please stand by',
        'please allow up to', 'cloudflare',
        # Social sharing
        'share on linkedin', 'share on twitter', 'share on facebook',
    ]

    # Single-word nav items to skip (exact match on stripped line)
    nav_words = {'home', 'about', 'help', 'contact', 'blog', 'faq', 'login', 'signup'}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()

        # Skip lines that match boilerplate patterns
        if any(pat in lower for pat in skip_patterns):
            continue

        # Skip single nav words
        if lower in nav_words:
            continue

        # Skip very short lines that are just UI labels (1-2 chars or just &nbsp;)
        if len(stripped) <= 2 or stripped == '&nbsp;':
            continue

        cleaned_lines.append(stripped)

    return '\n'.join(cleaned_lines)


def standardize_date(date_str):
    """Standardizes various date formats into YYYY-MM-DD."""
    if not date_str: return 'N/A'
    date_str = str(date_str).strip().lower()
    if date_str in ['n/a', 'unknown', 'not specified', 'none', 'null']: return 'N/A'
    if 'open' in date_str: return 'Open until filled'

    # Handle ranges by taking the end date
    if '-' in date_str and not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        parts = date_str.split('-')
        date_str = parts[-1].strip()

    # Standard YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # Indian / European DD/MM/YYYY or DD-MM-YYYY
    slash_match = re.match(r'^(\d{1,2})[/](\d{1,2})[/](\d{4})$', date_str)
    if slash_match:
        day, month, year = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Finnish / European DD.MM.YYYY
    fi_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', date_str)
    if fi_match:
        return f"{int(fi_match.group(3)):04d}-{int(fi_match.group(2)):02d}-{int(fi_match.group(1)):02d}"

    # Incomplete DD.MM. (assume current year)
    fi_short = re.match(r'^(\d{1,2})\.(\d{1,2})\.?$', date_str)
    if fi_short:
        year = datetime.now().year
        return f"{year:04d}-{int(fi_short.group(2)):02d}-{int(fi_short.group(1)):02d}"

    # ISO datetime
    try:
        if 't' in date_str:
            d = datetime.fromisoformat(date_str.split('t')[0])
            return d.strftime("%Y-%m-%d")
    except ValueError:
        pass

    today = datetime.now()

    # "today", "yesterday"
    if 'today' in date_str:
        return today.strftime("%Y-%m-%d")
    if 'yesterday' in date_str:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Relative formats: "X days ago", "X weeks ago", "X months ago"
    rel_match = re.search(r'(\d+)\s+(day|week|month|hour|min)', date_str)
    if rel_match:
        num = int(rel_match.group(1))
        unit = rel_match.group(2)
        if 'day' in unit:
            return (today - timedelta(days=num)).strftime("%Y-%m-%d")
        if 'week' in unit:
            return (today - timedelta(weeks=num)).strftime("%Y-%m-%d")
        if 'month' in unit:
            return (today - timedelta(days=num * 30)).strftime("%Y-%m-%d")
        if 'hour' in unit or 'min' in unit:
            return today.strftime("%Y-%m-%d")

    # Also "X d ago", "X w ago"
    short_rel = re.search(r'(\d+)\s*(d|w|m)\s+ago', date_str)
    if short_rel:
        num = int(short_rel.group(1))
        unit = short_rel.group(2)
        if unit == 'd': return (today - timedelta(days=num)).strftime("%Y-%m-%d")
        if unit == 'w': return (today - timedelta(weeks=num)).strftime("%Y-%m-%d")
        if unit == 'm': return (today - timedelta(days=num * 30)).strftime("%Y-%m-%d")

    # Month words: "June 15, 2026" or "15 June 2026"
    try:
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        months_short = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        parts = date_str.replace(',', '').split()
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

    return date_str


# ─────────────────────────────────────────────────────────────────────────────
# LOCATION & COMPANY EXTRACTION (Regex fallbacks)
# ─────────────────────────────────────────────────────────────────────────────

def extract_location_from_text(text):
    """Extract location from job page text using regex patterns.

    Looks for known city names from semiconductor hubs worldwide, Indian cities,
    and structured location patterns.
    """
    lines = text.split('\n')

    # Indian cities and their metro areas
    india_cities = {
        'Bengaluru': 'Bengaluru, India', 'Bangalore': 'Bengaluru, India',
        'Hyderabad': 'Hyderabad, India', 'Chennai': 'Chennai, India',
        'Pune': 'Pune, India', 'Mumbai': 'Mumbai, India',
        'Delhi': 'Delhi NCR, India', 'New Delhi': 'Delhi NCR, India',
        'Noida': 'Delhi NCR, India', 'Gurugram': 'Delhi NCR, India',
        'Gurgaon': 'Delhi NCR, India', 'Greater Noida': 'Delhi NCR, India',
        'Ahmedabad': 'Ahmedabad, India', 'Kolkata': 'Kolkata, India',
        'Thiruvananthapuram': 'Thiruvananthapuram, India',
        'Trivandrum': 'Thiruvananthapuram, India',
        'Kochi': 'Kochi, India', 'Cochin': 'Kochi, India',
        'Coimbatore': 'Coimbatore, India', 'Mysuru': 'Mysuru, India',
        'Mysore': 'Mysuru, India', 'Chandigarh': 'Chandigarh, India',
        'Lucknow': 'Lucknow, India', 'Jaipur': 'Jaipur, India',
        'Bhubaneswar': 'Bhubaneswar, India', 'Visakhapatnam': 'Visakhapatnam, India',
        'Nagpur': 'Nagpur, India', 'Indore': 'Indore, India',
        'Mohali': 'Mohali, India',
    }

    # Global semiconductor hubs
    global_cities = {
        'San Jose': 'San Jose, CA, USA', 'Santa Clara': 'Santa Clara, CA, USA',
        'San Francisco': 'San Francisco, CA, USA', 'San Diego': 'San Diego, CA, USA',
        'Austin': 'Austin, TX, USA', 'Dallas': 'Dallas, TX, USA',
        'Portland': 'Portland, OR, USA', 'Hillsboro': 'Hillsboro, OR, USA',
        'Boise': 'Boise, ID, USA', 'Chandler': 'Chandler, AZ, USA',
        'Folsom': 'Folsom, CA, USA', 'Milpitas': 'Milpitas, CA, USA',
        'Sunnyvale': 'Sunnyvale, CA, USA', 'Cupertino': 'Cupertino, CA, USA',
        'Mountain View': 'Mountain View, CA, USA', 'Irvine': 'Irvine, CA, USA',
        'Munich': 'Munich, Germany', 'Eindhoven': 'Eindhoven, Netherlands',
        'Leuven': 'Leuven, Belgium', 'Hsinchu': 'Hsinchu, Taiwan',
        'Tainan': 'Tainan, Taiwan', 'Seoul': 'Seoul, South Korea',
        'Icheon': 'Icheon, South Korea', 'Singapore': 'Singapore',
        'Penang': 'Penang, Malaysia', 'Dresden': 'Dresden, Germany',
        'Sophia Antipolis': 'Sophia Antipolis, France',
        'Grenoble': 'Grenoble, France', 'Cambridge': 'Cambridge, UK',
        'Bristol': 'Bristol, UK', 'Edinburgh': 'Edinburgh, UK',
        'London': 'London, UK', 'Espoo': 'Espoo, Finland',
        'Tampere': 'Tampere, Finland', 'Oulu': 'Oulu, Finland',
        'Helsinki': 'Helsinki, Finland', 'Turku': 'Turku, Finland',
        'Dublin': 'Dublin, Ireland', 'Cork': 'Cork, Ireland',
        'Tokyo': 'Tokyo, Japan', 'Yokohama': 'Yokohama, Japan',
        'Shenzhen': 'Shenzhen, China', 'Shanghai': 'Shanghai, China',
        'Beijing': 'Beijing, China', 'Tel Aviv': 'Tel Aviv, Israel',
        'Haifa': 'Haifa, Israel',
    }

    all_cities = {**india_cities, **global_cities}

    # Pattern 1: Line that contains "Location:" or "Location :"
    for line in lines:
        stripped = line.strip()
        if re.match(r'^(location|work location|job location)\s*[:\-]', stripped.lower()):
            loc_text = re.sub(r'^(location|work location|job location)\s*[:\-]\s*', '', stripped, flags=re.I).strip()
            if loc_text and len(loc_text) < 80:
                return loc_text

    # Pattern 2: Known city names mentioned in text
    text_words = set(re.findall(r'\b[A-Za-z]+(?:\s[A-Za-z]+)?\b', text))
    for city, formatted in all_cities.items():
        if city in text or city.lower() in text.lower():
            return formatted

    # Pattern 3: India/Remote inference
    text_lower = text.lower()
    if 'remote' in text_lower and ('worldwide' in text_lower or 'global' in text_lower):
        return "Remote (Worldwide)"
    if 'india' in text_lower and 'remote' in text_lower:
        return "Remote, India"

    return None


def extract_company_from_text(text, job_title):
    """Extract company name from job page text using structural patterns."""
    lines = text.split('\n')

    # Pattern 1: Line immediately after the job title
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and job_title and stripped.lower() == job_title.lower():
            # The next non-empty line is typically the company name
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if next_line and len(next_line) > 2 and len(next_line) < 80:
                    # Skip common non-company lines
                    if next_line.lower() in ['description', 'overview', 'about', 'requirements',
                                              'apply now', 'save', 'share', 'location']:
                        continue
                    return next_line

    # Pattern 2: Look for company indicators
    company_patterns = [
        re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Technologies|Semiconductor[s]?|Electronics|Solutions|Systems|Inc|Corp|Ltd|Pvt|Limited|LLP))\b'),
        re.compile(r'\b((?:Tata|Wipro|Infosys|HCL|TCS|Cognizant)\s+\w+)\b'),
    ]
    for pattern in company_patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()

    return None


# ─────────────────────────────────────────────────────────────────────────────
# AI-POWERED JOB EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

def analyze_scrape_run_log(lines: list[str]):
    """Send lines captured during a full scrape cycle to the LLM and print a health report."""
    llm_endpoint = os.environ.get("LOCAL_LLM_ENDPOINT")
    llm_model = os.environ.get("LOCAL_LLM_MODEL")
    if not llm_endpoint or not llm_model:
        return

    relevant = [l for l in lines if any(kw in l for kw in [
        'Navigating to', 'Found ', 'potential job links', 'Failed to scrape', 'Added ',
    ])]
    if not relevant:
        return

    log_text = '\n'.join(relevant)
    prompt = (
        "You are analysing the console log of a job-scraper run.\n"
        "Each search source prints three lines:\n"
        "  Navigating to <url> (Term: All, Site: <id>) ...\n"
        "  Found N potential job links on <platform>.\n"
        "  Added M new unseen jobs from this source.\n\n"
        "Task: identify every source that returned 0 potential job links. "
        "For each, note the site ID and URL. "
        "If ALL sources returned results, just say 'All sources returned results.' "
        "Be concise — bullet points only, no preamble.\n\n"
        f"Log:\n{log_text}"
    )

    headers = {"Content-Type": "application/json"}
    llm_api_key = os.environ.get("LOCAL_LLM_API_KEY")
    if llm_api_key:
        headers["Authorization"] = f"Bearer {llm_api_key}"

    payload = {
        "model": llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 600,
    }

    try:
        resp = requests.post(llm_endpoint, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        report = resp.json()['choices'][0]['message']['content'].strip()
        print(f"\n{'='*50}")
        print("SCRAPE HEALTH REPORT (LLM)")
        print('='*50)
        print(report)
        print('='*50)
    except Exception as e:
        print(f"[log-analysis] LLM health report failed: {e}")


def review_pending_jobs(specific_urls=None):
    """Visit URLs of pending jobs, extract description, and evaluate using a local LLM."""
    if not os.path.exists(JOBS_FILE):
        return

    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    if specific_urls is not None:
        pending_jobs = [j for j in jobs if (j.get('matches_requirements') == 'pending' or j.get('needs_re_review') == True) and j['url'] in specific_urls]
    else:
        pending_jobs = [j for j in jobs if j.get('matches_requirements') == 'pending' or j.get('needs_re_review') == True]

    if not pending_jobs:
        return

    llm_endpoint = os.environ.get("LOCAL_LLM_ENDPOINT")
    llm_model = os.environ.get("LOCAL_LLM_MODEL")

    if not llm_endpoint or not llm_model:
        print("ERROR: LOCAL_LLM_ENDPOINT and LOCAL_LLM_MODEL environment variables must be set to use a local LLM. Skipping review.")
        print("INFO: Examples to set variables:")
        print("      Bash (Linux/WSL):    export LOCAL_LLM_ENDPOINT='http://localhost:11434/v1/chat/completions'")
        print("                           export LOCAL_LLM_MODEL='llama3'")
        print("      PowerShell (Windows):$env:LOCAL_LLM_ENDPOINT='http://localhost:11434/v1/chat/completions'")
        print("                           $env:LOCAL_LLM_MODEL='llama3'")
        print("      CMD (Windows):       set LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions")
        print("                           set LOCAL_LLM_MODEL=llama3")
        return

    print(f"\nEvaluating {len(pending_jobs)} pending jobs using local LLM at {llm_endpoint} with model {llm_model}...")

    requirements_text = ""
    if os.path.exists(REQ_FILE):
        with open(REQ_FILE, 'r') as f:
            requirements_text = f.read()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        for job in pending_jobs:
            if stop_event.is_set():
                break
            print(f"Reviewing: {job['title']} at {job['url']}")
            try:
                page.goto(job['url'], timeout=30000)

                # Smart wait: detect DDoS guard / anti-bot pages and retry
                text = ""
                ddos_keywords = ['ddos-guard', 'checking your browser', 'please stand by', 'please allow up to']
                max_retries = 4
                for attempt in range(max_retries):
                    wait_time = 1.5 if attempt == 0 else 3.0
                    time.sleep(wait_time)
                    try:
                        text = page.locator('body').inner_text()
                    except Exception:
                        text = ""

                    text_lower = text.lower().strip()
                    # Check if the page is still showing a DDoS guard / anti-bot interstitial
                    if any(kw in text_lower for kw in ddos_keywords) and len(text) < 1500:
                        print(f"  [Attempt {attempt + 1}/{max_retries}] Anti-bot page detected, waiting longer...")
                        continue
                    else:
                        break

                posted_date = "N/A"
                deadline = "N/A"

                # Sanity check: if text is empty or still a DDoS guard page, treat as error
                text_lower_check = text.lower().strip()
                is_ddos_page = any(kw in text_lower_check for kw in ddos_keywords) and len(text) < 1500
                if not text.strip() or is_ddos_page:
                    match, reason = "error", "Could not extract text from page (anti-bot protection or empty page)."
                else:
                    # Clean page text to remove cookie banners, nav, footers
                    cleaned_text = clean_page_text(text)

                    today_str = datetime.now().strftime("%Y-%m-%d")
                    prompt = f"""Please act as an expert job reviewer for the semiconductor/VLSI/EDA industry. Read the following job description and evaluate it against the requirements.

Respond ONLY with a valid JSON object matching this exact structure:

### Job Requirements:
{requirements_text}

### Job Details:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
URL: {job['url']}

### Job Description:
{cleaned_text[:15000]}

### Instructions:
Return a JSON object with exactly six keys:
- "match": a string, either "yes", "maybe", or "no".
- "reason": a short 1-sentence explanation of your decision.
- "posted_date": a string, the date the job was posted formatted strictly as YYYY-MM-DD (e.g. '2026-06-12'). If a relative date like '3 days ago' is mentioned, calculate it relative to today's date ({today_str}). If not found, return 'N/A'.
- "deadline": a string, the deadline for applying formatted strictly as YYYY-MM-DD (e.g. '2026-06-30'). If it is open-ended or 'open until filled', return 'Open until filled'. If not found, return 'N/A'.
- "company": a string, the name of the hiring company as stated in the job posting (e.g. 'Intel' or 'N/A' if not found). Do NOT use the job board name (e.g. do NOT return 'Indeed' or 'LinkedIn' or 'Naukri').
- "location": a string, the city and country of the job. For Indian cities, use the format 'City, India' (e.g. 'Bengaluru, India'). For the Delhi-NCR metro area (Noida, Gurgaon, Greater Noida), return 'Delhi NCR, India'. For US cities, include the state (e.g. 'San Jose, CA, USA'). Return 'N/A' only if truly unknown. If fully remote worldwide, return 'Remote (Worldwide)'.

IMPORTANT: Extract company and location ONLY from information explicitly stated in the job description text. Do NOT guess or hallucinate values.
Do not include any conversational intro/outro or explanations outside the JSON object.
"""
                    headers = {"Content-Type": "application/json"}
                    llm_api_key = os.environ.get("LOCAL_LLM_API_KEY")
                    if llm_api_key:
                        headers["Authorization"] = f"Bearer {llm_api_key}"

                    payload = {
                        "model": llm_model,
                        "messages": [{"role": "user", "content": prompt}]
                    }

                    try:
                        response = requests.post(llm_endpoint, headers=headers, json=payload, timeout=120)
                        response.raise_for_status()

                        response_json = response.json()
                        content = response_json['choices'][0]['message']['content']

                        # Use robust JSON extraction
                        result = extract_json_from_text(content)
                        match = str(result.get("match", "no")).lower()
                        reason = str(result.get("reason", "No reason provided by LLM."))

                        # Only accept AI dates if we don't already have a valid one
                        ai_posted = standardize_date(result.get("posted_date", "N/A"))
                        current_posted = job.get("posted_date", "N/A")
                        if current_posted == "N/A" or not re.match(r'^\d{4}-\d{2}-\d{2}$', str(current_posted)):
                            posted_date = ai_posted
                        else:
                            posted_date = current_posted

                        ai_deadline = standardize_date(result.get("deadline", "N/A"))
                        current_deadline = job.get("deadline", "N/A")
                        if current_deadline == "N/A" or (not re.match(r'^\d{4}-\d{2}-\d{2}$', str(current_deadline)) and 'open' not in str(current_deadline).lower()):
                            deadline = ai_deadline
                        else:
                            deadline = current_deadline

                        # Extract company and location from LLM if scraper had placeholder/unknown
                        ai_company = str(result.get("company", "N/A"))
                        ai_location = str(result.get("location", "N/A"))

                        if ai_company != "N/A" and (job.get('company') in ["Extract from page", "Unknown", "", None]):
                            job['company'] = ai_company
                        if ai_location != "N/A" and (job.get('location') in ["Extract from page", "Unknown", "", None]):
                            job['location'] = ai_location

                        # Regex-based extraction: more reliable than LLM for structured data
                        regex_location = extract_location_from_text(cleaned_text)
                        regex_company = extract_company_from_text(cleaned_text, job.get('title', ''))

                        # Override with regex results if LLM failed or returned placeholder
                        if regex_location and (job.get('location') in ["Extract from page", "Unknown", "", None, "N/A"]):
                            job['location'] = regex_location
                        if regex_company and (job.get('company') in ["Extract from page", "Unknown", "", None, "N/A"]):
                            job['company'] = regex_company

                        if match not in ["yes", "maybe", "no"]:
                            match = "no"
                    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as llm_err:
                        match = "error"
                        reason = f"Failed to get or parse local LLM response: {llm_err}"

                # Update job dictionary in-place
                job['visited'] = "yes"
                job['matches_requirements'] = match
                job['reason'] = reason
                job['posted_date'] = posted_date
                job['deadline'] = deadline
                job.pop('needs_re_review', None)

                # If a posting matches requirements, save job description text to a file inside job_descriptions/
                if match == 'yes':
                    clean_title = re.sub(r'[^a-zA-Z0-9]', '_', job['title'].lower())[:30]
                    clean_company = re.sub(r'[^a-zA-Z0-9]', '_', job['company'].lower())[:20]
                    url_hash = hashlib.md5(job['url'].encode('utf-8')).hexdigest()[:8]
                    desc_filename = f"{clean_company}_{clean_title}_{url_hash}.txt"

                    desc_dir = os.path.join(BASE_DIR, "job_descriptions")
                    os.makedirs(desc_dir, exist_ok=True)
                    desc_path = os.path.join(desc_dir, desc_filename)
                    try:
                        with open(desc_path, 'w', encoding='utf-8') as f_desc:
                            f_desc.write(f"Title: {job['title']}\n")
                            f_desc.write(f"Company: {job['company']}\n")
                            f_desc.write(f"Location: {job['location']}\n")
                            f_desc.write(f"URL: {job['url']}\n")
                            f_desc.write(f"Posted: {posted_date}\n")
                            f_desc.write(f"Deadline: {deadline}\n")
                            f_desc.write(f"Reason: {reason}\n")
                            f_desc.write("\n" + "=" * 40 + "\n")
                            f_desc.write("JOB DESCRIPTION:\n")
                            f_desc.write("=" * 40 + "\n\n")
                            f_desc.write(text)
                        job['description_file'] = f"job_descriptions/{desc_filename}"
                    except Exception as e_desc:
                        print(f"Error writing description file: {e_desc}")
                        job['description_file'] = None
                else:
                    job['description_file'] = None

                print(f" -> {match.upper()}: {reason} (Posted: {posted_date}, Deadline: {deadline}, Company: {job['company']}, Location: {job['location']})")

            except Exception as e:
                print(f" -> ERROR: Failed to evaluate ({e})")
                job['visited'] = "yes"
                job['matches_requirements'] = "error"
                job['reason'] = "Page load or parsing error."
                job['posted_date'] = "N/A"
                job['deadline'] = "N/A"
                job['description_file'] = None

            # Save aggressively after each evaluation
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2)

        browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# GIT INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def update_git():
    """Auto-commit and push changes to GitHub."""
    print("\nUpdating GitHub repository...")
    try:
        repo_dir = os.path.dirname(os.path.abspath(__file__))

        # Clean up the environment to prevent VS Code's git helper from causing socket errors
        env = os.environ.copy()
        env.pop("GIT_ASKPASS", None)
        env["GIT_TERMINAL_PROMPT"] = "0"

        # Check if the folder is inside a Git repository
        is_git = False
        check_path = repo_dir
        while True:
            if os.path.exists(os.path.join(check_path, ".git")):
                is_git = True
                break
            parent = os.path.dirname(check_path)
            if parent == check_path:
                break
            check_path = parent

        if not is_git:
            print("INFO: Directory is not a Git repository. Skipping Git update.")
            return

        # Add updated files
        subprocess.run(["git", "add", "jobs.json", "seen_urls.json", "checkpoint.json", "job_descriptions", "jobs_history.json"], cwd=repo_dir, check=True, env=env)
        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True, env=env)
        if status.stdout.strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-update scraped jobs: {timestamp}"
            subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_dir, check=True, env=env)

            # Check for GitHub token in environment variables
            push_cmd = ["git", "push"]
            github_token = os.environ.get("GITHUB_TOKEN")
            if github_token:
                remote_result = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=repo_dir, capture_output=True, text=True)
                remote_url = remote_result.stdout.strip()
                if remote_url.startswith("https://"):
                    auth_url = remote_url.replace("https://", f"https://{github_token}@")
                    push_cmd = ["git", "push", auth_url]

            try:
                subprocess.run(push_cmd, cwd=repo_dir, check=True, env=env)
                print("Successfully pushed updates to GitHub!")
            except subprocess.CalledProcessError:
                print("Failed to push to GitHub (Check your GITHUB_TOKEN or internet connection).")
        else:
            print("No changes to commit. GitHub is already up to date.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to update Git: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# FIREBASE CLOUD SYNC
# ─────────────────────────────────────────────────────────────────────────────

def poll_firebase_feedback():
    """Polls the Firebase Firestore REST API for user feedback, updates requirements, and marks them read."""
    # TODO: Replace with your actual Firebase project ID once created
    url = "https://firestore.googleapis.com/v1/projects/vineeth-jobs-dashboard/databases/(default)/documents/user_feedback"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return  # Database not created, or empty, or permission denied

        data = response.json()
        documents = data.get("documents", [])
        if not documents:
            return

        print(f"\nINFO: Found {len(documents)} new feedback items from the cloud dashboard!")

        new_positive_rules = []
        new_negative_rules = []
        user_review_updates = {}
        match_updates = {}
        processed_urls = set()

        for doc in documents:
            doc_name = doc.get("name")
            fields = doc.get("fields", {})
            status = fields.get("status", {}).get("stringValue", "unread")

            if status == "read":
                continue

            feedback_type = fields.get("type", {}).get("stringValue", "negative")
            url_field = fields.get("url", {}).get("stringValue", "")
            if url_field:
                processed_urls.add(url_field)

            if feedback_type == "user_review_update":
                new_status = fields.get("user_review", {}).get("stringValue", "pending")
                url_field = fields.get("url", {}).get("stringValue", "")
                if url_field:
                    user_review_updates[url_field] = new_status

                # Update status to "read"
                if doc_name:
                    update_url = f"https://firestore.googleapis.com/v1/{doc_name}?updateMask.fieldPaths=status"
                    payload = {"fields": {"status": {"stringValue": "read"}}}
                    requests.patch(update_url, json=payload, timeout=10)
                continue


            if feedback_type == "applied_update":
                new_status = fields.get("applied", {}).get("stringValue", "no")
                url_field = fields.get("url", {}).get("stringValue", "")
                if url_field:
                    if 'applied_updates' not in locals():
                        applied_updates = {}
                    applied_updates[url_field] = new_status
                
                # Update status to "read"
                if doc_name:
                    update_url = f"https://firestore.googleapis.com/v1/{doc_name}?updateMask.fieldPaths=status"
                    payload = {"fields": {"status": {"stringValue": "read"}}}
                    requests.patch(update_url, json=payload, timeout=10)
                continue

            reason = fields.get("reason", {}).get("stringValue", "")

            if feedback_type == "positive":
                if url_field:
                    match_updates[url_field] = "yes"
            else:
                if url_field:
                    match_updates[url_field] = "no"

            if reason and reason.strip():
                if feedback_type == "positive":
                    new_positive_rules.append(reason.strip())
                else:
                    new_negative_rules.append(reason.strip())

            # Update the document status to "read" so we keep a history in the cloud
            if doc_name:
                update_url = f"https://firestore.googleapis.com/v1/{doc_name}?updateMask.fieldPaths=status"
                payload = {"fields": {"status": {"stringValue": "read"}}}
                requests.patch(update_url, json=payload, timeout=10)

        if new_positive_rules or new_negative_rules:
            with open(REQ_FILE, 'a', encoding='utf-8') as f:
                if new_negative_rules:
                    f.write("\n\n### Automatically Added Negative Constraints (from UI Rejections):\n")
                    for rule in new_negative_rules:
                        f.write(f"- NEGATIVE CONSTRAINT: The user explicitly rejected a previous job because: '{rule}'. Do NOT match jobs that have this issue.\n")
                if new_positive_rules:
                    f.write("\n\n### Automatically Added Positive Constraints (from UI Approvals):\n")
                    for rule in new_positive_rules:
                        f.write(f"- POSITIVE CONSTRAINT: The user explicitly approved a previous job because: '{rule}'. Make sure to MATCH jobs that have this characteristic.\n")
            print(f"INFO: Successfully updated job_requirements.md with {len(new_positive_rules)} positive and {len(new_negative_rules)} negative rules!")


        if locals().get('applied_updates'):
            try:
                if os.path.exists(JOBS_FILE):
                    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                        jobs = json.load(f)
                    changed = False
                    for j in jobs:
                        if j.get('url') in applied_updates:
                            j['applied'] = applied_updates[j['url']]
                            changed = True
                    if changed:
                        with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                            json.dump(jobs, f, indent=2)
                    print(f"INFO: Successfully synced applied status for {len(applied_updates)} jobs from the cloud.")
            except Exception as e:
                print(f"Error syncing applied status: {e}")

        if user_review_updates:
            try:
                if os.path.exists(JOBS_FILE):
                    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                        jobs = json.load(f)
                    changed = False
                    for j in jobs:
                        if j.get('url') in user_review_updates:
                            j['user_review'] = user_review_updates[j['url']]
                            changed = True
                    if changed:
                        with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                            json.dump(jobs, f, indent=2)
                    print(f"INFO: Successfully synced user_review status for {len(user_review_updates)} jobs from the cloud.")
            except Exception as e:
                print(f"Error syncing user review status: {e}")

    
        if match_updates:
            try:
                if os.path.exists(JOBS_FILE):
                    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                        jobs = json.load(f)
                    changed = False
                    for j in jobs:
                        if j.get('url') in match_updates:
                            j['matches_requirements'] = match_updates[j['url']]
                            changed = True
                    if changed:
                        with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                            json.dump(jobs, f, indent=2)
                    print(f"INFO: Successfully synced matches_requirements for {len(match_updates)} jobs from the cloud.")
            except Exception as e:
                print(f"Error syncing match updates: {e}")
        
        # Wipe shared_state since all updates are now safely in jobs.json
        if user_review_updates or match_updates:
            try:
                # Get the correct project ID based on the URL we polled
                proj_id = "vineeth-jobs-dashboard" 
                # wait, let's just use the url from the top of the function
                wipe_url = url.replace('user_feedback', 'shared_state/job_status')
                requests.patch(wipe_url, json={"fields": {}}, timeout=10)
                print("INFO: Cleared shared_state temporary queue.")
            except Exception as e:
                print(f"Error clearing shared_state: {e}")

                
    except Exception as e:
        print(f"Error polling Firebase feedback: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# DATE SELF-HEALING
# ─────────────────────────────────────────────────────────────────────────────

def self_heal_dates():
    """Run through existing jobs in jobs.json and standardize their dates using the native scraper logic."""
    if not os.path.exists(JOBS_FILE):
        return
    try:
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            jobs = json.load(f)

        changed = False
        for job in jobs:
            p = str(job.get('posted_date', ''))
            d = str(job.get('deadline', ''))

            new_p = standardize_date(p)
            new_d = standardize_date(d)

            if new_p != p:
                job['posted_date'] = new_p
                changed = True
            if new_d != d:
                job['deadline'] = new_d
                changed = True

        if changed:
            print("INFO: Natively standardized messy dates in jobs.json!")
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2)
    except Exception as e:
        print(f"Error self-healing dates: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# STATUS & CONTROL
# ─────────────────────────────────────────────────────────────────────────────

# Event flag to signal when the user wants to stop
stop_event = threading.Event()


def listen_for_input():
    """Background task waiting for the user to press Enter."""
    try:
        input()
        stop_event.set()
    except EOFError:
        pass


def print_job_summary():
    """Reads jobs.json and prints a summary of job statuses."""
    if not os.path.exists(JOBS_FILE):
        print("\nStats - No jobs.json file found.")
        return

    try:
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
            total_jobs = len(jobs_data)
            matching_jobs = sum(1 for j in jobs_data if j.get('matches_requirements') == 'yes')
            maybe_jobs = sum(1 for j in jobs_data if j.get('matches_requirements') == 'maybe')
            no_jobs = sum(1 for j in jobs_data if j.get('matches_requirements') == 'no')
            pending_jobs = sum(1 for j in jobs_data if j.get('matches_requirements') == 'pending')
            re_review_jobs = sum(1 for j in jobs_data if j.get('needs_re_review') is True)

        re_review_str = f" | Re-review: {re_review_jobs}" if re_review_jobs else ""
        print(f"\nStats - Total jobs: {total_jobs} | Yes Match: {matching_jobs} | Maybe Match: {maybe_jobs} | No Match: {no_jobs} | Pending: {pending_jobs}{re_review_str}")
    except Exception as e:
        print(f"Error reading jobs file for status display: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global _tee_logger
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = os.path.join(LOGS_DIR, f"scraper_{datetime.now().strftime('%Y%m%d')}.log")
    _tee_logger = TeeLogger(log_path)
    sys.stdout = _tee_logger

    generate_history_from_backups()
    self_heal_dates()
    parser = argparse.ArgumentParser(description="Semiconductor Job Scraper and Reviewer")
    parser.add_argument("--git-only", action="store_true", help="Only run the Git commit and push step, then exit.")
    parser.add_argument("--review-only", action="store_true", help="Only run the local LLM review step on pending jobs, then exit.")
    parser.add_argument("--scrape-only", action="store_true", help="Only run the scraping step, then exit.")
    parser.add_argument("--max-jobs", type=int, default=200, help="Maximum number of new jobs to fetch in this run (default 200). Use 0 for unlimited.")
    args = parser.parse_args()

    if args.git_only:
        update_git()
        return

    if args.review_only:
        check_requirements_update()
        while True:
            if not os.path.exists(JOBS_FILE):
                break
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                jobs = json.load(f)

            pending_urls = [j['url'] for j in jobs if j.get('matches_requirements') == 'pending' or j.get('needs_re_review') == True]
            if not pending_urls:
                print("INFO: No more pending jobs to review.")
                break

            batch_urls = pending_urls[:15]
            print(f"\nINFO: Reviewing batch of {len(batch_urls)} pending jobs (Remaining pending: {len(pending_urls)})...")
            review_pending_jobs(specific_urls=set(batch_urls))

            clean_blocked_jobs()
            update_git()
            print_job_summary()
            time.sleep(1)
        return

    if args.scrape_only:
        check_requirements_update()
        targets = generate_targets()
        total_targets = len(targets)
        visited_indices = set()

        while len(visited_indices) < total_targets:
            checkpoint_idx = 0
            if os.path.exists(CHECKPOINT_FILE):
                try:
                    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                        checkpoint_idx = json.load(f).get("target_index", 0)
                except Exception:
                    pass

            if checkpoint_idx >= total_targets or checkpoint_idx < 0:
                checkpoint_idx = 0

            print(f"\nINFO: Scraping batch of up to 15 jobs (Starting target index: {checkpoint_idx}/{total_targets})...")
            if _tee_logger:
                _tee_logger.start_capture()
            new_jobs = scrape_all_jobs(max_jobs=15)
            if _tee_logger:
                _tee_logger.stop_capture()
                if _checkpoint_reached_end():
                    analyze_scrape_run_log(_tee_logger.flush_cycle())

            new_checkpoint_idx = 0
            if os.path.exists(CHECKPOINT_FILE):
                try:
                    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                        new_checkpoint_idx = json.load(f).get("target_index", 0)
                except Exception:
                    pass

            if new_checkpoint_idx > checkpoint_idx:
                for i in range(checkpoint_idx, new_checkpoint_idx):
                    visited_indices.add(i)
            else:
                for i in range(checkpoint_idx, total_targets):
                    visited_indices.add(i)
                for i in range(0, new_checkpoint_idx):
                    visited_indices.add(i)

            clean_blocked_jobs()
            update_git()

            if not new_jobs and new_checkpoint_idx == checkpoint_idx:
                print("INFO: No progress made, stopping scrape loop.")
                break

            time.sleep(1)
        return

    # Self-heal dates before main loop
    self_heal_dates()

    print("INFO: Scraper script starting execution loop...")
    # Start the background thread to listen for user input
    input_thread = threading.Thread(target=listen_for_input, daemon=True)
    input_thread.start()

    while not stop_event.is_set():
        try:
            poll_firebase_feedback()
        except Exception as e:
            print(f"Error polling firebase: {e}")

        try:
            check_requirements_update()
        except Exception as e:
            print(f"An error occurred checking requirements: {e}")

        # 1. Gather all pending jobs
        pending_jobs = []
        if os.path.exists(JOBS_FILE):
            try:
                with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                    jobs_data = json.load(f)
                    pending_jobs = [j for j in jobs_data if j.get('matches_requirements') == 'pending' or j.get('needs_re_review') == True]
            except Exception as e:
                print(f"Error reading jobs file: {e}")

        if pending_jobs:
            # We have pending jobs, flush a batch of them first
            print(f"\nINFO: Flushing pending jobs first. {len(pending_jobs)} pending jobs remaining.")
            batch_urls = [j['url'] for j in pending_jobs[:15]]
            try:
                review_pending_jobs(specific_urls=set(batch_urls))
            except Exception as e:
                print(f"An error occurred during reviewing: {e}")

            try:
                clean_blocked_jobs()
                update_git()
            except Exception as e:
                print(f"An error occurred during Git update: {e}")

            print_job_summary()
            print("Waiting 5 seconds before moving to scrape new jobs. Press [Enter] or Ctrl+C to stop...")

            slept = 0
            while slept < 5 and not stop_event.is_set():
                time.sleep(0.5)
                slept += 0.5

            if stop_event.is_set():
                print("Stopping the scraper...")
                break
            continue

        quota = 15
        new_jobs = []

        try:
            print(f"\nINFO: Scanning for up to {quota} new unseen jobs...")
            if _tee_logger:
                _tee_logger.start_capture()
            new_jobs = scrape_all_jobs(max_jobs=quota)
            if _tee_logger:
                _tee_logger.stop_capture()
                if _checkpoint_reached_end():
                    analyze_scrape_run_log(_tee_logger.flush_cycle())
        except Exception as e:
            if _tee_logger:
                _tee_logger.stop_capture()
            print(f"An error occurred during scraping: {e}")

        # Collect URLs to review
        urls_to_review = [j['url'] for j in new_jobs]

        if urls_to_review:
            print(f"INFO: Reviewing {len(urls_to_review)} jobs in this batch (New: {len(new_jobs)}, Existing Pending: {len(urls_to_review) - len(new_jobs)})")
            try:
                review_pending_jobs(specific_urls=set(urls_to_review))
            except Exception as e:
                print(f"An error occurred during reviewing: {e}")
        else:
            print("INFO: No jobs found to review in this iteration.")

        try:
            clean_blocked_jobs()
            update_git()
        except Exception as e:
            print(f"An error occurred during Git update: {e}")

        print_job_summary()

        # Determine wait time
        wait_time = 5
        if not new_jobs:
            wait_time = 600
            print(f"\nINFO: No new unseen jobs found in this iteration. Increasing wait time to {wait_time} seconds (10 mins).")

        print(f"Waiting {wait_time} seconds before the next run. Press [Enter] or Ctrl+C to stop...")

        # This loop waits in small increments so KeyboardInterrupt can be caught immediately on Windows
        slept = 0
        while slept < wait_time and not stop_event.is_set():
            time.sleep(0.5)
            slept += 0.5

        if stop_event.is_set():
            print("Stopping the scraper...")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nINFO: Scraper stopped by user (Ctrl+C).")
        stop_event.set()
