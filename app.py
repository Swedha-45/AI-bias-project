import json
import io
import math
import os
import sqlite3
from datetime import datetime, timedelta
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
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
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
        'comment', 'remarks', 'notes', 'description', 'resume', 'cv'
    }
    included_keywords = {
        'gender', 'sex', 'age', 'location', 'region', 'state', 'country',
        'degree', 'education', 'qualification', 'department', 'team',
        'experience', 'tenure', 'salary', 'pay', 'race', 'ethnicity',
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
    """Fuzzy matching to find columns and identify all potential protected attributes"""
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
    protected_attributes = {}
    
    # Process known attributes
    clean = pd.DataFrame()
    
    # Gender (binary)
    clean['gender_bin'] = df[final_cols['gender']].apply(lambda x: 1 if str(x).lower() in ['male', 'm', 'man'] else 0)
    protected_attributes['gender'] = 'gender_bin'
    
    # Age (binary: >=30 vs <30)
    clean['age_val'] = pd.to_numeric(df[final_cols['age']], errors='coerce').fillna(30)
    clean['age_bin'] = clean['age_val'].apply(lambda x: 1 if x >= 30 else 0)
    protected_attributes['age'] = 'age_bin'
    
    # Target variable (hired)
    clean['target_bin'] = df[final_cols['hired']].apply(
        lambda x: 1 if str(x).lower() in ['1', 'yes', 'true', 'hired', 'no'] else 0
    )
    
    # Identify and process additional categorical columns for bias analysis
    # Skip the already processed columns and the target column
    processed_cols = {final_cols['gender'], final_cols['age'], final_cols['hired']}
    
    for col in df.columns:
        if col not in processed_cols:
            if not is_relevant_attribute(col, df[col]):
                continue

            # Check if column is suitable for bias analysis
            unique_vals = df[col].dropna().unique()
            
            # Only analyze columns with reasonable number of categories (2-10)
            if 2 <= len(unique_vals) <= 10:
                try:
                    # Try to convert to numeric or treat as categorical
                    if pd.api.types.is_numeric_dtype(df[col]):
                        # Numeric column - create binary (median split)
                        median_val = df[col].median()
                        bin_col = f"{col}_bin"
                        clean[bin_col] = df[col].apply(lambda x: 1 if pd.notna(x) and x >= median_val else 0)
                        protected_attributes[col] = bin_col
                    else:
                        # Categorical column - convert to binary (first category vs others)
                        first_cat = str(unique_vals[0]).lower()
                        bin_col = f"{col}_bin"
                        clean[bin_col] = df[col].apply(lambda x: 1 if str(x).lower() == first_cat else 0)
                        protected_attributes[col] = bin_col
                except Exception as e:
                    # Skip columns that can't be processed
                    continue
    
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
        try:
            from aif360.datasets import BinaryLabelDataset
            from aif360.metrics import BinaryLabelDatasetMetric
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Audit dependencies are missing: {exc}"
            )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        contents = await file.read()
        raw_df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='ignore')))
        
        # 1. Clean Data
        clean_df, mapped_info, protected_attributes = run_smart_cleaning(raw_df)

        # 2. Local AIF360 Math - Analyze all protected attributes
        results = {"metrics": {}, "mapped_columns": mapped_info, "protected_attributes": list(protected_attributes.keys())}
        
        for attr_name, bin_col in protected_attributes.items():
            try:
                ds = BinaryLabelDataset(df=clean_df[[bin_col, 'target_bin']], label_names=['target_bin'], 
                                         protected_attribute_names=[bin_col], favorable_label=1, unfavorable_label=0)
                metric = BinaryLabelDatasetMetric(ds, unprivileged_groups=[{bin_col: 0}], privileged_groups=[{bin_col: 1}])
                results["metrics"][attr_name] = {
                    "di": sanitize_number(metric.disparate_impact(), fallback=1.0),
                    "spd": sanitize_number(metric.statistical_parity_difference(), fallback=0.0)
                }
            except Exception as e:
                # Skip attributes that can't be analyzed
                results["metrics"][attr_name] = {
                    "di": 1.0,
                    "spd": 0.0,
                    "error": f"Could not analyze: {str(e)}"
                }

        # 3. Gemini Agent Insight
        prompt = f"Explain these HR bias metrics: {json.dumps(results['metrics'])}. Identify the bias and give 1 fix. Max 45 words."
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
        
        timestamp = datetime.utcnow().isoformat()
        history_entry = {
            "id": len(user_history[username]) + 1,
            "timestamp": timestamp,
            "filename": file.filename,
            "metrics": results["metrics"],
            "insight": results["insight"],
            "mapped_columns": results["mapped_columns"]
        }
        
        # Save to in-memory cache
        user_history[username].append(history_entry)
        
        # Save to database for persistence
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO analysis_history 
                   (username, timestamp, filename, metrics, insight, mapped_columns) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (username, timestamp, file.filename, json.dumps(results["metrics"]), 
                 results["insight"], json.dumps(results["mapped_columns"]))
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
            """SELECT timestamp, filename, metrics, insight, mapped_columns 
               FROM analysis_history WHERE username = ? ORDER BY timestamp DESC""",
            (username,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        # Build history list from database
        history = []
        for idx, (timestamp, filename, metrics_json, insight, mapped_json) in enumerate(rows, 1):
            history.append({
                "id": idx,
                "timestamp": timestamp,
                "filename": filename,
                "metrics": sanitize_json_payload(json.loads(metrics_json)),
                "insight": insight,
                "mapped_columns": json.loads(mapped_json)
            })
        
        # Cache in memory for future requests
        user_history[username] = history
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
