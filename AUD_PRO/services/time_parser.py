"""
Pure Hindi Temporal Parser
Handles: Durations, Times, Calendar Dates
ASR Output: 100% Devanagari (no English alphabets)
Duckling API Compatible Output
"""

import re
import unicodedata
from datetime import datetime, timedelta
import pytz

# ==========================================================
# NORMALIZATION DICTIONARIES
# ==========================================================

# Hindi number words to digits
HINDI_NUMBERS = {
    "आधा": "0.5",
    "डेढ़": "1.5",    
    # 0-20
    "शून्य": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4",
    "पांच": "5", "पाँच": "5", "छह": "6", "छः": "6", "सात": "7",
    "आठ": "8", "नौ": "9", "दस": "10", "ग्यारह": "11", "बारह": "12",
    "तेरह": "13", "चौदह": "14", "पंद्रह": "15", "पन्द्रह": "15",
    "सोलह": "16", "सत्रह": "17", "अठारह": "18", "उन्नीस": "19", "बीस": "20",
    
    # 21-30
    "इक्कीस": "21", "बाईस": "22", "तेईस": "23", "चौबीस": "24", "पच्चीस": "25",
    "छब्बीस": "26", "सत्ताईस": "27", "अट्ठाईस": "28", "उनतीस": "29", "तीस": "30",
    
    # Tens
    "चालीस": "40", "पचास": "50", "साठ": "60", "सत्तर": "70",
    "अस्सी": "80", "नब्बे": "90", "सौ": "100",
}

# Hindi digit conversion
HINDI_DIGIT_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Time of day keywords
TIME_OF_DAY = {
    "सुबह": ("morning", 6),
    "सवेरे": ("morning", 6),
    "प्रातः": ("morning", 6),
    "दोपहर": ("afternoon", 12),
    "शाम": ("evening", 18),
    "साँझ": ("evening", 18),
    "रात": ("night", 21),
    "मध्यरात्रि": ("midnight", 0),
}

# AM/PM markers (from ASR)
AMPM_MARKERS = {
    "एएम": "AM",
    "ए एम": "AM",
    "पीएम": "PM",
    "पी एम": "PM",
}

# Day names (Hindi)
DAY_NAMES_HINDI = {
    "सोमवार": 0, "मंगलवार": 1, "बुधवार": 2, "गुरुवार": 3,
    "शुक्रवार": 4, "शनिवार": 5, "रविवार": 6,
}

# Day names (English transliterated)
DAY_NAMES_ENGLISH = {
    "मंडे": 0, "मण्डे": 0,
    "ट्यूजडे": 1, "ट्यूज़डे": 1,
    "वेडनेसडे": 2, "वेडनेज़डे": 2,
    "थर्सडे": 3, "थर्सडे": 3,
    "फ्राइडे": 4, "फ्राईडे": 4,
    "सैटरडे": 5, "सैटर्डे": 5,
    "संडे": 6, "सण्डे": 6,
}

# Relative day markers
RELATIVE_DAYS = {
    "आज": 0,
    "कल": 1,  # Tomorrow (context: future)
    "परसों": 2,
    "अभी": 0,
}

MONTH_NAMES_HINDI = {
    "जनवरी": 1, "जनवरि": 1,
    "फरवरी": 2, "फरवरि": 2, "फ़रवरी": 2,
    "मार्च": 3,
    "अप्रैल": 4, "अप्रेल": 4,
    "मई": 5,
    "जून": 6,
    "जुलाई": 7, "जुलाइ": 7,
    "अगस्त": 8, "अगस्ट": 8,
    "सितंबर": 9, "सितम्बर": 9, "सिप्तंबर": 9,
    "अक्टूबर": 10, "अक्तूबर": 10, "अक्टोबर": 10,
    "नवंबर": 11, "नवम्बर": 11,
    "दिसंबर": 12, "दिसम्बर": 12, "दिसम्बर": 12,
}

# Duration units
DURATION_UNITS = {
    "सेकंड": 1, "सेकण्ड": 1,
    "मिनट": 60, "मिनिट": 60,
    "घंटा": 3600, "घंटे": 3600, "घण्टा": 3600, "घण्टे": 3600,
    "दिन": 86400,
}

# Variant normalization
VARIANT_NORMALIZATION = {
    "घण्टा": "घंटा",
    "घण्टे": "घंटे",
    "मिनिट": "मिनट",
    "सेकण्ड": "सेकंड",
    "बजकर": "बजे",
    "बाजे": "बजे",
}

# ==========================================================
# NORMALIZATION
# ==========================================================

def normalize_text(text: str) -> str:
    """Normalize Hindi text"""
    if not text:
        return ""
    
    # Unicode normalization
    text = unicodedata.normalize("NFC", text)
    
    # Convert Hindi digits to English
    for hindi, english in HINDI_DIGIT_MAP.items():
        text = text.replace(hindi, english)
    
    # Convert number words to digits (LONGEST FIRST to avoid conflicts)
    sorted_numbers = sorted(HINDI_NUMBERS.items(), key=lambda x: len(x[0]), reverse=True)
    for word, digit in sorted_numbers:
        text = re.sub(rf"\b{word}\b", digit, text)
    
    # Variant normalization
    for old, new in VARIANT_NORMALIZATION.items():
        text = re.sub(rf"\b{old}\b", new, text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# ==========================================================
# FRACTIONAL TIME HANDLING
# ==========================================================

def extract_fractional_duration(text: str):
    """
    Handle fractional time expressions
    """
    # आधा घंटा/घंटे (half hour) - with or without unit
    if re.search(r"\bआधा\s+(घंटा|घंटे|घण्टा|घण्टे)\b", text):
        return 1800
    
    # Just "आधा" alone (context: timer/duration)
    if re.search(r"\bआधा\b", text):
        return 1800
    
    # डेढ़ घंटा/घंटे (1.5 hours) - with or without unit
    if re.search(r"\bडेढ़\s+(घंटा|घंटे|घण्टा|घण्टे)\b", text):
        return 5400
    
    # Just "डेढ़" alone
    if re.search(r"\bडेढ़\b", text):
        return 5400
    
    # ढाई घंटा/घंटे (2.5 hours)
    if re.search(r"\bढाई\s+(घंटा|घंटे)\b", text):
        return 9000
    
    # साढ़े X घंटा/घंटे (X.5 hours)
    sadhe = re.search(r"साढ़े\s+(\d+)\s+(घंटा|घंटे)", text)
    if sadhe:
        base = int(sadhe.group(1))
        return base * 3600 + 1800
    
    # सवा घंटा/घंटे (1.25 hours)
    sawa = re.search(r"सवा\s+(\d+)?\s*(घंटा|घंटे)", text)
    if sawa:
        base = int(sawa.group(1)) if sawa.group(1) else 1
        return base * 3600 + 900
    
    # पौने X घंटा/घंटे (X - 0.25 hours)
    paune = re.search(r"पौने\s+(\d+)\s+(घंटा|घंटे)", text)
    if paune:
        base = int(paune.group(1))
        return base * 3600 - 900
    
    # आधा मिनट
    if re.search(r"\bआधा\s+मिनट\b", text):
        return 30
    
    return None

# ==========================================================
# DURATION EXTRACTION
# ==========================================================

def extract_duration(text: str, start_idx=0, end_idx=None):
    """
    Extract duration
    
    Handles:
        - 10 मिनट का टाइमर
        - डेढ़ घंटे का टाइमर
        - आधा घंटा
    """
    if end_idx is None:
        end_idx = len(text)
    print(f"DEBUG extract_duration input: '{text}'")  # ADD THIS
    frac = extract_fractional_duration(text)
    print(f"DEBUG fractional result: {frac}")  # ADD THIS
    if frac:
        # Find the span
        body = text.strip()
        
        return {
            "body": body,
            "start": start_idx,
            "value": {
                "value": frac,
                "unit": "second",
                "normalized": {"value": frac, "unit": "second"}
            },
            "end": end_idx,
            "dim": "duration",
            "latent": False
        }
    
    # Pattern: number + unit (+ optional "का")
    pattern = r"(\d+)\s+(" + "|".join(DURATION_UNITS.keys()) + r")(?:\s+का)?"
    match = re.search(pattern, text)
    
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        seconds = value * DURATION_UNITS[unit]
        
        return {
            "body": match.group(0),
            "start": start_idx + match.start(),
            "value": {
                "value": seconds,
                "unit": "second",
                "normalized": {"value": seconds, "unit": "second"}
            },
            "end": start_idx + match.end(),
            "dim": "duration",
            "latent": False
        }
    
    return None

# ==========================================================
# TIME EXTRACTION
# ==========================================================

def extract_time(text: str, ref_dt=None, start_idx=0, end_idx=None):
    """
    Extract time from text
    
    Handles:
        - पांच बजे का अलार्म
        - कल शाम पांच बजे का अलार्म
        - सुबह सात बजे
        - 10 एएम
        - शाम 6:30 बजे
        - शाम छह बजे तीस मिनट (FIX: Not "बजकर", just time description)
    """
    if ref_dt is None:
        ref_dt = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    if end_idx is None:
        end_idx = len(text)
    
    result_dt = None
    day_offset = 0
    hour = None
    minute = 0
    time_of_day_hint = None
    is_ampm_explicit = False
    
    # 1. Extract day offset
    for day_word, offset in RELATIVE_DAYS.items():
        if day_word in text:
            day_offset = offset
            break
    
    # 2. Check for weekday names
    all_day_names = {**DAY_NAMES_HINDI, **DAY_NAMES_ENGLISH}
    for day_name, weekday in all_day_names.items():
        if day_name in text:
            current_weekday = ref_dt.weekday()
            days_ahead = weekday - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            
            if "नेक्स्ट" in text or "अगले" in text:
                if days_ahead < 7:
                    days_ahead += 7
            
            day_offset = days_ahead
            break
    
    # 3. Extract time of day hint
    for keyword, (period, default_hour) in TIME_OF_DAY.items():
        if keyword in text:
            time_of_day_hint = period
            break
    
    # 4. Extract hour and minute (priority order matters!)
    
    # FIX: Pattern for "X बजे Y मिनट" (without बजकर) - this is time, not duration
    # e.g., "शाम छह बजे तीस मिनट" means 6:30 PM
    baje_minute_match = re.search(r"(\d+)\s*बजे\s+(\d+)\s*मिनट", text)
    if baje_minute_match:
        hour = int(baje_minute_match.group(1))
        minute = int(baje_minute_match.group(2))
    
    # Pattern: X बजकर Y मिनट (old pattern, kept for compatibility)
    if hour is None:
        bajkar_match = re.search(r"(\d+)\s*बजकर\s*(\d+)\s*मिनट", text)
        if bajkar_match:
            hour = int(bajkar_match.group(1))
            minute = int(bajkar_match.group(2))
    
    # Pattern: HH:MM
    if hour is None:
        hhmm_match = re.search(r"(\d+):(\d+)", text)
        if hhmm_match:
            hour = int(hhmm_match.group(1))
            minute = int(hhmm_match.group(2))
    
    # Pattern: X एएम/पीएम
    if hour is None:
        for marker_text, marker in AMPM_MARKERS.items():
            if marker_text in text:
                ampm_match = re.search(rf"(\d+)\s+{re.escape(marker_text)}", text)
                if ampm_match:
                    hour = int(ampm_match.group(1))
                    is_ampm_explicit = True
                    
                    if marker == "PM" and hour < 12:
                        hour += 12
                    elif marker == "AM" and hour == 12:
                        hour = 0
                    
                    break
    
    # Pattern: X बजे
    if hour is None:
        baje_match = re.search(r"(\d+)\s*बजे", text)
        if baje_match:
            hour = int(baje_match.group(1))
    
    # 5. Smart AM/PM inference ONLY if not explicit
    if hour is not None and not is_ampm_explicit:
        if hour <= 12:
            if time_of_day_hint in ["evening", "night"]:
                if hour < 12:
                    hour += 12
            elif time_of_day_hint in ["morning"]:
                pass
            elif time_of_day_hint in ["afternoon"]:
                if hour <= 6:
                    hour += 12
            else:
                if ref_dt.hour >= 12 and hour <= 11:
                    hour += 12
    
    # 6. Build datetime
    if hour is not None:
        result_dt = ref_dt.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
        result_dt += timedelta(days=day_offset)
        
        if result_dt < ref_dt and day_offset == 0:
            result_dt += timedelta(days=1)
        
        return {
            "body": text.strip(),
            "start": start_idx,
            "value": {
                "value": result_dt.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
                "grain": "minute",
                "type": "value"
            },
            "end": end_idx,
            "dim": "time",
            "latent": False
        }
    
    return None

# ==========================================================
# CALENDAR DATE EXTRACTION
# ==========================================================

def extract_calendar_date(text: str, ref_dt=None, start_idx=0, end_idx=None):
    """Extract calendar dates"""
    if ref_dt is None:
        ref_dt = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    if end_idx is None:
        end_idx = len(text)
    
    result_dt = None
    day = None
    month = None
    year = ref_dt.year
    hour = None
    minute = 0
    
    # 1. Extract day number
    date_match = re.search(r"(\d+)\s+तारीख", text)
    if date_match:
        day = int(date_match.group(1))
    
    # 2. Extract month
    for month_name, month_num in MONTH_NAMES_HINDI.items():
        if month_name in text:
            month = month_num
            
            if not day:
                day_month = re.search(rf"(\d+)\s+{re.escape(month_name)}", text)
                if day_month:
                    day = int(day_month.group(1))
            break
    
    # 3. Check for "अगले महीने"
    if "अगले महीने" in text or "नेक्स्ट मंथ" in text:
        month = ref_dt.month + 1
        if month > 12:
            month = 1
            year += 1
    
    # 4. If day but no month, assume current/next month
    if day and not month:
        month = ref_dt.month
        if day < ref_dt.day:
            month += 1
            if month > 12:
                month = 1
                year += 1
    
    # 5. Extract time component (if present)
    time_result = extract_time(text, ref_dt)
    if time_result:
        time_dt = datetime.strptime(time_result['value']['value'], "%Y-%m-%dT%H:%M:%S.000%z")
        hour = time_dt.hour
        minute = time_dt.minute
    
    # 6. Build datetime
    if day and month:
        try:
            if hour is not None:
                result_dt = datetime(year, month, day, hour, minute, 0, 0, tzinfo=pytz.timezone('Asia/Kolkata'))
            else:
                result_dt = datetime(year, month, day, 0, 0, 0, 0, tzinfo=pytz.timezone('Asia/Kolkata'))
            
            return {
                "body": text.strip(),
                "start": start_idx,
                "value": {
                    "value": result_dt.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
                    "grain": "day",
                    "type": "value"
                },
                "end": end_idx,
                "dim": "time",
                "latent": False
            }
        except ValueError:
            pass
    
    return extract_time(text, ref_dt, start_idx, end_idx)

# ==========================================================
# MAIN PARSER
# ==========================================================

def parse_temporal(text: str, tz="Asia/Kolkata", reftime=None):
    """Main parsing function - Duckling compatible"""
    if not text or not isinstance(text, str):
        return []
    
    # Normalize
    original_text = text
    text = normalize_text(text)
    
    # Reference time
    if reftime:
        if isinstance(reftime, str):
            # Parse ISO format or timestamp
            if 'T' in reftime or '+' in reftime or 'Z' in reftime:
                ref_dt = datetime.fromisoformat(reftime.replace('Z', '+00:00'))
                ref_dt = ref_dt.astimezone(pytz.timezone(tz))
            else:
                # Assume timestamp in milliseconds
                ref_dt = datetime.fromtimestamp(int(reftime) / 1000, pytz.timezone(tz))
        else:
            ref_dt = datetime.fromtimestamp(reftime / 1000, pytz.timezone(tz))
    else:
        ref_dt = datetime.now(pytz.timezone(tz))
    
    results = []
    
    # Priority 1: Check for "टाइमर" keyword to force duration parsing
    if "टाइमर" in text or "timer" in text.lower():
        duration = extract_duration(text, 0, len(original_text))
        if duration:
            results.append(duration)
            return results
    
    # Priority 2: Check if it's a time expression with "बजे" (not duration)
    # "X बजे Y मिनट" is TIME (6:30), not DURATION
    if "बजे" in text and ("अलार्म" in text or "alarm" in text.lower() or re.search(r"\d+\s*बजे", text)):
        time_result = extract_time(text, ref_dt, 0, len(original_text))
        if time_result:
            results.append(time_result)
            return results
    
    # Priority 3: Try duration
    duration = extract_duration(text, 0, len(original_text))
    if duration:
        results.append(duration)
        return results
    
    # Priority 4: Try calendar date
    if "तारीख" in text or any(month in text for month in MONTH_NAMES_HINDI.keys()):
        cal_date = extract_calendar_date(text, ref_dt, 0, len(original_text))
        if cal_date:
            results.append(cal_date)
            return results
    
    # Priority 5: Try time
    time_result = extract_time(text, ref_dt, 0, len(original_text))
    if time_result:
        results.append(time_result)
        return results
    
    return []

# ==========================================================
# FLASK SERVER (Duckling API Compatible)
# ==========================================================

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def index():
    return {"message": "quack! (Hindi Temporal Parser - Duckling Compatible)"}


@app.post("/parse")
async def parse_endpoint(
    locale: str = Form("hi_IN"),
    text: str = Form(""),
    reftime: str = Form(None),
    dims: str = Form('["time", "duration"]')
):
    """
    Duckling-compatible endpoint
    Accepts form-data exactly like Duckling
    """
    try:
        if not text:
            return JSONResponse(content=[])

        results = parse_temporal(text, reftime=reftime)

        return JSONResponse(content=results)

    except Exception as e:
        print(f"Parse error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content=[])


@app.get("/health")
async def health():
    return {"status": "ok"}

# ==========================================================
# TEST CASES
# ==========================================================

if __name__ == '__main__':
    # Test in CLI mode
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_cases = [
            # Durations
            "दस मिनट का टाइमर",
            "डेढ़ घंटे का टाइमर",
            "आधा घंटा",
            "साढ़े तीन घंटे",
            
            # Times
            "पांच बजे अलार्म",
            "कल शाम पांच बजे का अलार्म",
            "सुबह सात बजे",
            "दस एएम",
            "शाम छह बजे तीस मिनट",  # FIX: This should be 6:30 PM, not duration
            
            # Calendar dates
            "पंद्रह तारीख को मीटिंग",
            "पच्चीस दिसंबर को पार्टी",
            "नेक्स्ट मंडे दस एएम",
            "अगले शुक्रवार पांच बजे",
            "अगले महीने दस तारीख को",
        ]
        
        print("=" * 70)
        print("Hindi Temporal Parser - Test Cases")
        print("=" * 70)
        
        for test in test_cases:
            print(f"\nInput: {test}")
            results = parse_temporal(test)
            if results:
                for r in results:
                    if r['dim'] == 'time':
                        dt_str = r['value']['value']
                        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.000%z")
                        print(f"  → Time: {dt.strftime('%Y-%m-%d %H:%M %Z')}")
                        print(f"     Duckling format: {r}")
                    elif r['dim'] == 'duration':
                        secs = r['value']['value']
                        print(f"  → Duration: {secs}s ({secs//60}min)")
                        print(f"     Duckling format: {r}")
            else:
                print("  → No parse")
    
    else:
        import uvicorn
        print("Starting server on http://localhost:8000")
        uvicorn.run(app, host="127.0.0.1", port=8000)