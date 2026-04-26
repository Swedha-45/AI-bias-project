import json
import io
import math
import os
import sqlite3
from datetime import datetime, timedelta, timezone
import pandas as pd
import bcrypt
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

# Security Setup
SECRET_KEY = "JEC_ENGINEERING_SECRET"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database Setup
DB_PATH = "users_auth.db"

def init_database():
    """Initialize SQLite database and create users table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            filename TEXT NOT NULL,
            metrics TEXT NOT NULL,
            insight TEXT NOT NULL,
            mapped_columns TEXT NOT NULL,
            protected_attributes TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    cursor.execute("PRAGMA table_info(analysis_history)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if 'protected_attributes' not in existing_columns:
        cursor.execute("ALTER TABLE analysis_history ADD COLUMN protected_attributes TEXT")
    
    conn.commit()
    conn.close()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
init_database()

# In-memory cache for analysis history (for performance)
user_history = {}

# --- HELPER FUNCTIONS ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def hash_password(password: str) -> str:
    safe_password = password[:72].encode("utf-8")
    return bcrypt.hashpw(safe_password, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    safe_password = password[:72].encode("utf-8")
    return bcrypt.checkpw(safe_password, password_hash.encode("utf-8"))


def sanitize_number(value: float, fallback: float = 0.0) -> float:
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return fallback
    return round(value, 3)


def normalize_text_value(value) -> str:
    if pd.isna(value):
        return "Unknown"

    text = str(value).strip()
    if not text or text.lower() in {'nan', 'none', 'null'}:
        return "Unknown"
    return text


def encode_target_value(value) -> int:
    normalized = normalize_text_value(value).lower()
    positive_values = {'1', 'true', 't', 'yes', 'y', 'hired', 'selected', 'accept', 'accepted', 'pass'}
    negative_values = {'0', 'false', 'f', 'no', 'n', 'rejected', 'not hired', 'declined', 'fail'}

    if normalized in positive_values:
        return 1
    if normalized in negative_values:
        return 0

    try:
        return 1 if float(normalized) > 0 else 0
    except ValueError:
        return 0


def prepare_comparable_attribute(series: pd.Series) -> pd.Series | None:
    non_null = series.dropna()
    if non_null.empty:
        return None

    numeric = pd.to_numeric(series, errors='coerce')
    numeric_non_null = numeric.dropna()

    if len(numeric_non_null) >= max(4, len(series) // 4):
        unique_numeric = numeric_non_null.nunique()
        if unique_numeric >= 4:
            quantiles = min(4, unique_numeric)
            try:
                bucketed = pd.qcut(numeric.fillna(numeric.median()), q=quantiles, duplicates='drop')
                labels = bucketed.astype(str).str.replace(', ', ' to ', regex=False)
                labels = labels.str.replace('[', '', regex=False).str.replace(']', '', regex=False)
                labels = labels.str.replace('(', '', regex=False)
                return labels.fillna("Unknown")
            except ValueError:
                pass

        median_val = numeric_non_null.median()
        return numeric.fillna(median_val).apply(lambda x: f">= {round(median_val, 2)}" if x >= median_val else f"< {round(median_val, 2)}")

    normalized = series.apply(normalize_text_value)
    unique_count = normalized.nunique(dropna=True)
    if 2 <= unique_count <= 10:
        return normalized

    return None


def compute_group_fairness(attribute_series: pd.Series, target_series: pd.Series):
    grouped = pd.DataFrame({
        'attribute': attribute_series,
        'target': target_series
    }).dropna()

    if grouped.empty:
        return None

    group_stats = []
    for group_name, group_df in grouped.groupby('attribute'):
        count = int(len(group_df))
        if count == 0:
            continue
        selection_rate = float(group_df['target'].mean())
        selected_count = int(group_df['target'].sum())
        group_stats.append({
            'group': str(group_name),
            'count': count,
            'selected_count': selected_count,
            'selection_rate': sanitize_number(selection_rate)
        })

    if len(group_stats) < 2:
        return None

    total_selected = sum(g['selected_count'] for g in group_stats)
    for g in group_stats:
        g['proportion'] = sanitize_number(g['selected_count'] / total_selected) if total_selected > 0 else 0.0

    group_stats.sort(key=lambda item: (item['selection_rate'], item['count']))
    unprivileged = group_stats[0]
    privileged = group_stats[-1]

    priv_rate = privileged['selection_rate']
    unpriv_rate = unprivileged['selection_rate']
    di = 1.0 if priv_rate == 0 else unpriv_rate / priv_rate
    spd = unpriv_rate - priv_rate

    return {
        'di': sanitize_number(di, fallback=1.0),
        'spd': sanitize_number(spd, fallback=0.0),
        'mean_difference': sanitize_number(spd, fallback=0.0),
        'privileged_group': privileged['group'],
        'unprivileged_group': unprivileged['group'],
        'privileged_rate': priv_rate,
        'unprivileged_rate': unpriv_rate,
        'group_count': len(group_stats),
        'groups': group_stats
    }


def sanitize_json_payload(value):
    if isinstance(value, dict):
        return {key: sanitize_json_payload(val) for key, val in value.items()}
    if isinstance(value, list):
        return [sanitize_json_payload(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def is_relevant_attribute(column_name: str, series: pd.Series) -> bool:
    normalized = column_name.strip().lower()

    excluded_keywords = {
        'id', 'name', 'first_name', 'last_name', 'fullname', 'full_name',
        'email', 'phone', 'mobile', 'contact', 'address', 'city',
        'employee_id', 'candidate_id', 'user_id', 'uuid', 'guid',
        'dob', 'timestamp', 'date', 'created_at', 'updated_at',
        'comment', 'remarks', 'notes', 'description', 'resume', 'cv',
        'stock', 'training', 'satisfaction', 'involvement', 'performance',
        'relationship', 'worklife', 'overtime', 'travel', 'distance',
        'hike', 'income', 'rate', 'standardhours', 'employeecount',
        'employeenumber', 'yearswithcurrmanager', 'yearssincelastpromotion',
        'yearsincurrentrole', 'yearsatcompany', 'totalworkingyears'
    }
    included_keywords = {
        'gender', 'sex', 'age', 'location', 'region', 'state', 'country',
        'degree', 'education', 'qualification', 'department', 'team',
        'experience', 'tenure', 'race', 'ethnicity',
        'marital', 'disability', 'veteran', 'role', 'designation'
    }

    if normalized in excluded_keywords:
        return False

    if any(keyword in normalized for keyword in excluded_keywords):
        return False

    non_null = series.dropna()
    if non_null.empty:
        return False

    unique_count = non_null.nunique()
    row_count = len(non_null)

    # Person-level identifiers tend to be nearly unique.
    if row_count > 0 and unique_count / row_count > 0.8:
        return False

    # Long free-text fields are not useful for fairness comparison charts.
    if non_null.dtype == object:
        avg_length = non_null.astype(str).str.len().mean()
        if avg_length and avg_length > 25:
            return False

    if any(keyword in normalized for keyword in included_keywords):
        return True

    return 2 <= unique_count <= 10

def run_smart_cleaning(df: pd.DataFrame):
    """Find outcome columns and prepare all comparable attributes for fairness analysis."""
    df.columns = df.columns.str.strip().str.lower()
    
    # Define variations of common HR column names
    mapping = {
        'gender': ['gender', 'sex', 'm_f', 'gender_identity'],
        'age': ['age', 'years', 'dob', 'age_group'],
        'hired': ['hired', 'status', 'outcome', 'selection', 'attrition', 'hiring_decision']
    }

    final_cols = {}
    for target, variants in mapping.items():
        match = next((col for col in df.columns if col in variants), None)
        if not match:
            raise ValueError(f"Could not find a column for {target}. Please check your CSV.")
        final_cols[target] = match

    # Identify additional protected attributes (columns that can be analyzed for bias)
    clean = pd.DataFrame()
    clean['target_bin'] = df[final_cols['hired']].apply(encode_target_value)

    protected_attributes = {}
    processed_cols = {final_cols['gender'], final_cols['age'], final_cols['hired']}

    for col in df.columns:
        if col in processed_cols or not is_relevant_attribute(col, df[col]):
            continue

        prepared = prepare_comparable_attribute(df[col])
        if prepared is not None and prepared.nunique(dropna=True) >= 2:
            clean[col] = prepared
            protected_attributes[col] = col

    for mandatory_attr in ('gender', 'age'):
        source_col = final_cols[mandatory_attr]
        if source_col not in clean.columns:
            prepared = prepare_comparable_attribute(df[source_col])
            if prepared is not None and prepared.nunique(dropna=True) >= 2:
                clean[mandatory_attr] = prepared
                protected_attributes[mandatory_attr] = mandatory_attr

    return clean, final_cols, protected_attributes

# --- AUTH ROUTES ---
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    """Register a new user with persistent storage"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="User already exists")
        
        password_hash = hash_password(password)
        
        # Insert new user
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        
        conn.commit()
        conn.close()
        
        return {"message": "Registration Successful"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/token")
async def login(username: str = Form(...), password: str = Form(...)):
    """Login user and return JWT token"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get user from database
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not verify_password(password, result[0]):
            raise HTTPException(status_code=401, detail="Invalid Credentials")
        
        # Generate JWT token
        access_token = create_access_token({"sub": username})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
# --- PROTECTED AUDIT ROUTE ---
@app.post("/audit")
async def audit(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        contents = await file.read()
        raw_df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='ignore')))
        
        # 1. Clean Data
        clean_df, mapped_info, protected_attributes = run_smart_cleaning(raw_df)

        # 2. Analyze all protected attributes
        results = {"metrics": {}, "mapped_columns": mapped_info, "protected_attributes": list(protected_attributes.keys())}
        
        for attr_name, comparable_col in protected_attributes.items():
            metric_payload = compute_group_fairness(clean_df[comparable_col], clean_df['target_bin'])
            if metric_payload is not None:
                results["metrics"][attr_name] = metric_payload

        # 3. Gemini Agent Insight
        prompt = (
            f"Analyze the HR bias metrics from this hiring data audit: {json.dumps(results['metrics'])}. "
            "Provide a detailed explanation for HR professionals on why this dataset shows bias. "
            "For each protected attribute (gender, education, age, race, etc.), explain the disparities in hiring rates, "
            "what the numbers mean (e.g., disparate impact, statistical parity difference), and the potential causes of bias. "
            "Highlight the most biased categories and suggest specific actions to address the bias in hiring practices. "
            "Focus on the data evidence, avoid generic advice, and explain implications for diversity and fairness. "
            "Make it comprehensive but concise, around 250-300 words."
        )
        try:
            from google import genai

            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            results["insight"] = resp.text
        except Exception:
            results["insight"] = "Math complete. AI insight currently unavailable."

        results = sanitize_json_payload(results)

        # 4. Save to user history (database + in-memory cache)
        if username not in user_history:
            user_history[username] = []
        
        timestamp = datetime.now(timezone.utc).isoformat()
        history_entry = {
            "id": len(user_history[username]) + 1,
            "timestamp": timestamp,
            "filename": file.filename,
            "metrics": results["metrics"],
            "insight": results["insight"],
            "mapped_columns": results["mapped_columns"],
            "protected_attributes": results["protected_attributes"]
        }
        
        # Save to in-memory cache
        user_history[username].append(history_entry)
        
        # Save to database for persistence
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO analysis_history 
                   (username, timestamp, filename, metrics, insight, mapped_columns, protected_attributes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (username, timestamp, file.filename, json.dumps(results["metrics"]), 
                 results["insight"], json.dumps(results["mapped_columns"]), json.dumps(results["protected_attributes"]))
            )
            conn.commit()
            conn.close()
        except Exception as db_error:
            print(f"Warning: Failed to save to database: {db_error}")
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- HISTORY ROUTE ---
@app.get("/history")
async def get_history(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        # Try to load from in-memory cache first
        if username in user_history and user_history[username]:
            return {"history": user_history[username]}
        
        # Load from database if not in cache
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT timestamp, filename, metrics, insight, mapped_columns, protected_attributes 
               FROM analysis_history WHERE username = ? ORDER BY timestamp DESC""",
            (username,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        # Build history list from database
        history = []
        for idx, (timestamp, filename, metrics_json, insight, mapped_json, protected_json) in enumerate(rows, 1):
            history.append({
                "id": idx,
                "timestamp": timestamp,
                "filename": filename,
                "metrics": sanitize_json_payload(json.loads(metrics_json)),
                "insight": insight,
                "mapped_columns": json.loads(mapped_json),
                "protected_attributes": json.loads(protected_json) if protected_json else list(json.loads(metrics_json).keys())
            })
        
        # Cache in memory for future requests
        user_history[username] = history
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
