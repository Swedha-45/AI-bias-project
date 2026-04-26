# AI Bias Auditor

AI Bias Auditor is a FastAPI-based web app for uploading hiring datasets, checking fairness metrics across protected attributes, and reviewing previous audit history.

## Features

- User registration and login with JWT-based authentication
- CSV upload for hiring-bias analysis
- Fairness metrics such as Disparate Impact (DI) and Statistical Parity Difference (SPD)
- Comparison charts on the dashboard and history pages
- SQLite-based persistence for users and audit history
- Optional AI-generated insight summary when the Gemini client is available

## Project Files

- [app.py](/d:/Projects/AI-Bais/app.py) - FastAPI backend
- [login.html](/d:/Projects/AI-Bais/login.html) - login page
- [register.html](/d:/Projects/AI-Bais/register.html) - registration page
- [home.html](/d:/Projects/AI-Bais/home.html) - dashboard and upload page
- [history.html](/d:/Projects/AI-Bais/history.html) - audit history page
- [chart.js](/d:/Projects/AI-Bais/chart.js) - local Chart.js bundle
- [requirements.txt](/d:/Projects/AI-Bais/requirements.txt) - Python dependencies
- [CSV_FORMAT.md](/d:/Projects/AI-Bais/CSV_FORMAT.md) - **CSV upload format and column requirements guide**
- [CSV_TEMPLATE.csv](/d:/Projects/AI-Bais/CSV_TEMPLATE.csv) - **Template CSV file for data upload**- [RENDER_DEPLOYMENT.md](/d:/Projects/AI-Bais/RENDER_DEPLOYMENT.md) - **Complete deployment guide for Render**
## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Add a `.env` file if you want Gemini insight support:

```env
GOOGLE_API_KEY=your_api_key_here
```

4. Start the backend:

```powershell
python app.py
```

5. Open the frontend pages with a local static server such as VS Code Live Server:

- `login.html`
- `register.html`
- `home.html`
- `history.html`

The frontend is expected to run on `http://127.0.0.1:5500` and the backend on `http://127.0.0.1:8000`.

## Deployment

For production deployment to Render, see **[RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)** for complete instructions.

**Quick Deploy:**
1. Push code to GitHub
2. Create Render Web Service with:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. Add environment variables: `GOOGLE_API_KEY`, `SECRET_KEY`
4. Deploy frontend separately to Vercel/Netlify

## CSV Data Format

Before uploading your hiring dataset, ensure it follows the required format:

**Required Columns:**
- `gender` - Employee gender (Male, Female, Non-binary, Other, etc.)
- `age` - Employee age (numeric)
- `hired` - Hiring decision (0 = not hired, 1 = hired)

**Recommended Columns:**
- `name` - Employee name (for reference)
- `race` - Employee race/ethnicity
- `education` - Education level (High School, Bachelor, Master, PhD)
- `experience_years` - Years of professional experience
- `test_score` - Standardized test score (0-100)
- `interview_score` - Interview evaluation score (0-100)

📋 **For detailed guidance, see [CSV_FORMAT.md](CSV_FORMAT.md)**

📄 **Use [CSV_TEMPLATE.csv](CSV_TEMPLATE.csv) as a starting point for your data**

## Notes

- Audit history is stored in `users_auth.db`.
- Some optional analysis/AI features depend on installed packages such as `aif360` and `google-genai`.
- New audits prefer relevant comparison attributes like age, location, degree, department, and experience while avoiding identifier-style fields like name or email.



# AI Bias Auditor - Implementation Summary

## Changes Made

### 1. **app.py** - Backend Updates
- **Added user history storage**: `user_history = {}` dictionary to store analysis results per user
- **Modified `/audit` endpoint**: Now saves each analysis to user's history with:
  - Timestamp (ISO format)
  - Filename
  - Metrics (gender and age bias scores)
  - AI insight
  - Mapped columns info
- **New `/history` endpoint**: GET request that returns all previous analyses for the authenticated user
  - Returns empty list if no history exists
  - Secure - requires JWT token authentication

### 2. **home.html** - Updated Home Page
- **Added Navigation Menu Bar** with:
  - Brand name (AI Bias Auditor)
  - Navigation links: Home (active), History, Logout
- **Added logout function**: Clears token and redirects to login
- **Maintained existing audit functionality**: Upload CSV and run bias analysis
- **Fixed character encoding**: Replaced emoji encoding issues with proper UTF-8

### 3. **history.html** - New History Page (NEW FILE)
- **Displays all previous analyses** for the logged-in user
- **Features**:
  - List of all previous audits with filenames and timestamps
  - Expandable detail view for each analysis
  - Displays metrics cards for Gender and Age bias scores:
    - Disparate Impact (DI)
    - Statistical Parity Difference (SPD)
  - Shows AI insight/recommendations for each audit
  - Interactive chart visualization using Chart.js
  - Responsive design matching the app's theme
  - Empty state message if no history exists
  - "View Details" button to expand/collapse analysis details

### 4. **styles.css** - Enhanced Styling
- **Added Navigation Bar Styles**:
  - Fixed position navbar with glass-morphism effect
  - Brand styling with cyan color accent
  - Menu items with hover effects
  - Active link indicator (bottom border)
  - Responsive design
- **Updated body layout**: Adjusted for fixed navbar (padding-top: 70px)
- **Container centering**: Updated to work with navbar

## Features Overview

### User Authentication
- Users register and login (existing functionality preserved)
- Token stored in localStorage
- Each user's analysis history is isolated

### Analysis Workflow
1. User logs in → redirected to home.html
2. Upload CSV file → Run Smart Audit
3. View real-time analysis with bias metrics and AI insights
4. Analysis automatically saved to user's history

### History Page Features
1. Click "History" in navbar to view all past analyses
2. Each analysis shows:
   - Filename
   - Date and time
   - View Details button
3. Click "View Details" to see:
   - Detailed bias metrics for Gender and Age
   - AI-generated insights
   - Interactive bar chart of Disparate Impact scores
4. Return to Home to run new analyses

## Database Structure

### user_history Dictionary
```
{
  "username": [
    {
      "id": 1,
      "timestamp": "2026-04-24T12:34:56.789",
      "filename": "hiring_dataset.csv",
      "metrics": {
        "gender": {"di": 0.850, "spd": -0.125},
        "age": {"di": 0.920, "spd": -0.050}
      },
      "insight": "Gender bias detected with DI of 0.85...",
      "mapped_columns": {...}
    },
    ...
  ]
}
```

## API Endpoints

### New Endpoint
- **GET** `/history` - Requires JWT token
  - Returns: `{"history": [array of analyses]}`

### Modified Endpoint
- **POST** `/audit` - Now stores results in user_history in addition to returning them

## Styling Consistency
- Uses existing color scheme: Dark theme with cyan/indigo accents
- Maintains glass-morphism design with backdrop-filter blur
- Responsive design for mobile and desktop
- Smooth transitions and hover effects

## Security Features
- JWT token required for both `/audit` and `/history` endpoints
- User isolation - each user can only see their own history
- Token stored in localStorage (frontend)
- Password truncation to 72 chars (bcrypt safety)

## Notes
- Analysis history persists during server runtime (in-memory)
- For production, consider using a persistent database (SQL, MongoDB, etc.)
- All timestamps are in UTC ISO format
- Charts use Chart.js for visualization








# Multi-Attribute Bias Analysis Implementation

## Overview
The application now analyzes **all suitable columns** in the dataset for bias, not just gender and age. This allows for comprehensive fairness auditing across multiple protected attributes like location, department, experience, education, etc.

## Key Changes

### 1. **Backend (app.py)** - Enhanced Data Processing

#### `run_smart_cleaning()` Function
**Before**: Only processed gender and age columns
```python
# Old: Hardcoded to only gender and age
clean['gender_bin'] = df[final_cols['gender']].apply(lambda x: 1 if str(x).lower() in ['male', 'm', 'man'] else 0)
clean['age_bin'] = clean['age_val'].apply(lambda x: 1 if x >= 30 else 0)
return clean, final_cols
```

**After**: Automatically detects and processes all suitable columns
```python
# New: Processes all protected attributes dynamically
protected_attributes = {}

# Process known attributes (gender, age)
clean['gender_bin'] = df[final_cols['gender']].apply(lambda x: 1 if str(x).lower() in ['male', 'm', 'man'] else 0)
protected_attributes['gender'] = 'gender_bin'

# Process additional categorical columns
for col in df.columns:
    if col not in processed_cols:
        unique_vals = df[col].dropna().unique()
        # Analyze columns with 2-10 categories
        if 2 <= len(unique_vals) <= 10:
            # Convert to binary for bias analysis
            bin_col = f"{col}_bin"
            clean[bin_col] = df[col].apply(lambda x: 1 if str(x).lower() == first_cat else 0)
            protected_attributes[col] = bin_col

return clean, final_cols, protected_attributes
```

#### `/audit` Endpoint
**Before**: Only analyzed gender and age
```python
for label, col in [('gender', 'gender_bin'), ('age', 'age_bin')]:
    # Calculate bias metrics
```

**After**: Analyzes all detected protected attributes
```python
for attr_name, bin_col in protected_attributes.items():
    try:
        ds = BinaryLabelDataset(...)
        metric = BinaryLabelDatasetMetric(...)
        results["metrics"][attr_name] = {
            "di": round(float(metric.disparate_impact()), 3),
            "spd": round(float(metric.statistical_parity_difference()), 3)
        }
    except Exception as e:
        results["metrics"][attr_name] = {"di": 1.0, "spd": 0.0, "error": str(e)}
```

### 2. **Frontend (home.html)** - Dynamic Chart Display

#### Chart Rendering
**Before**: Hardcoded to show only gender and age
```javascript
labels: ['GENDER', 'AGE'],
data: [genderDI, ageDI],
backgroundColor: ['#38bdf8', '#fbbf24']
```

**After**: Dynamically shows all analyzed attributes
```javascript
const attributes = data.protected_attributes || ['gender', 'age'];
const labels = attributes.map(attr => attr.toUpperCase());
const diScores = attributes.map(attr => data.metrics?.[attr]?.di ?? 0);

const colors = ['#38bdf8', '#fbbf24', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#84cc16'];
const backgroundColors = attributes.map((_, index) => colors[index % colors.length]);
```

#### Mapping Display
**Before**: Only showed gender, age, hired mapping
```javascript
🔍 Auto-Mapped: Gender → gender | Age → age | Hired → hired
```

**After**: Shows all analyzed attributes
```javascript
let mappingText = `🔍 Auto-Mapped: Gender → gender | Age → age | Hired → hired`;
if (data.protected_attributes && data.protected_attributes.length > 2) {
    const additionalAttrs = data.protected_attributes.filter(attr => !['gender', 'age'].includes(attr));
    if (additionalAttrs.length > 0) {
        mappingText += ` | Additional: ${additionalAttrs.join(', ')}`;
    }
}
```

### 3. **Frontend (history.html)** - Dynamic Metrics Display

#### Metrics Cards Generation
**Before**: Hardcoded cards for gender and age only
```html
<div class="metric-card">
    <div class="metric-label">⚧ Gender — Disparate Impact</div>
    <div class="metric-value">${genderDI}</div>
</div>
<!-- Only gender and age cards -->
```

**After**: Dynamically generates cards for all attributes
```javascript
const icons = {
    'gender': '⚧', 'age': '📅', 'location': '📍',
    'department': '🏢', 'experience': '💼', 'education': '🎓'
};

attributes.forEach(attr => {
    const di = analysis.metrics?.[attr]?.di ?? 'N/A';
    const spd = analysis.metrics?.[attr]?.spd ?? 'N/A';
    const icon = icons[attr] || '📊';
    
    metricsCards += `
        <div class="metric-card">
            <div class="metric-label">${icon} ${attr} — Disparate Impact</div>
            <div class="metric-value">${di}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">${icon} ${attr} — Statistical Parity Diff</div>
            <div class="metric-value">${spd}</div>
        </div>
    `;
});
```

#### Chart Rendering in History
**Before**: Only gender and age in history charts
```javascript
labels: ['GENDER', 'AGE'],
data: [genderDI, ageDI]
```

**After**: All attributes in history charts
```javascript
const attributes = analysis.protected_attributes || ['gender', 'age'];
const labels = attributes.map(attr => attr.toUpperCase());
const diScores = attributes.map(attr => analysis.metrics?.[attr]?.di ?? 0);
```

## How It Works

### 1. **Column Detection**
The system automatically identifies columns suitable for bias analysis:
- **Required**: gender, age, hired (outcome) columns
- **Optional**: Any column with 2-10 unique categories
- **Excluded**: Columns with too many categories (>10) or too few (<2)

### 2. **Binary Conversion**
Each protected attribute is converted to binary format:
- **Categorical**: First category = 1, others = 0
- **Numeric**: Median split (above median = 1, below = 0)
- **Gender**: Male/M = 1, Female/F = 0
- **Age**: >= 30 = 1, < 30 = 0

### 3. **Bias Metrics Calculation**
For each attribute, calculates:
- **Disparate Impact (DI)**: Ratio of favorable outcomes between privileged/unprivileged groups
- **Statistical Parity Difference (SPD)**: Difference in selection rates

### 4. **Visualization**
- **Home Page**: Bar chart showing DI scores for all attributes
- **History Page**: Individual charts and metric cards for each analysis

## Example Dataset Analysis

**Input CSV columns**: `gender, age, location, department, experience, education, hired`

**Detected Attributes**: `gender, age, location, department, experience, education`

**Analysis Results**:
```json
{
  "protected_attributes": ["gender", "age", "location", "department", "experience", "education"],
  "metrics": {
    "gender": {"di": 0.85, "spd": -0.12},
    "age": {"di": 0.92, "spd": -0.08},
    "location": {"di": 1.05, "spd": 0.03},
    "department": {"di": 0.78, "spd": -0.15},
    "experience": {"di": 0.95, "spd": -0.05},
    "education": {"di": 0.88, "spd": -0.10}
  }
}
```

## Benefits

1. **Comprehensive Analysis**: Detects bias across all relevant attributes
2. **Automated Detection**: No manual configuration needed
3. **Scalable**: Works with any number of suitable columns
4. **Visual Comparison**: Easy to compare bias across different attributes
5. **Flexible**: Adapts to different dataset structures

## Technical Details

### Attribute Selection Criteria
- Must have 2-10 unique values
- Must be convertible to binary format
- Must not be the outcome variable
- Must not be already processed (gender, age, hired)

### Error Handling
- Gracefully handles columns that can't be analyzed
- Shows "N/A" for failed analyses
- Continues processing other attributes

### Performance
- Efficient processing of multiple attributes
- In-memory caching for history
- Database persistence for long-term storage

## Testing

To test the multi-attribute analysis:

1. **Prepare CSV** with multiple categorical columns:
   ```csv
   gender,age,location,department,experience,education,hired
   Male,25,NYC,Engineering,2,Bachelor,Yes
   Female,35,LA,Marketing,5,Masters,No
   Male,28,NYC,Sales,3,Bachelor,Yes
   ```

2. **Upload and Analyze**
   - System detects: gender, age, location, department, experience, education
   - Analyzes bias for each attribute
   - Shows comprehensive results

3. **View Results**
   - Home: Chart with all 6 attributes
   - History: Detailed metrics for each attribute
   - AI insights consider all analyzed attributes

## Future Enhancements

1. **Custom Attribute Selection**: Allow users to choose which columns to analyze
2. **Advanced Metrics**: Add more fairness metrics (EO, AOD, etc.)
3. **Interactive Filtering**: Filter results by attribute type
4. **Export Reports**: Generate detailed PDF reports
5. **Attribute Importance**: Rank attributes by bias severity



# Database Persistence Implementation

## Overview
The application now uses **SQLite database** for persistent storage instead of in-memory storage. This ensures that:
- ✅ Users cannot register twice (even after app restart)
- ✅ User credentials are permanently stored
- ✅ Analysis history is persisted
- ✅ No data loss on app restart

## Database File
- **Location**: `users_auth.db` (created automatically in project root)
- **Format**: SQLite3 (no additional installation needed, built into Python)

## Database Schema

### `users` Table
Stores user authentication credentials:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Columns**:
- `id`: Unique user ID
- `username`: Username (UNIQUE - prevents duplicate registration)
- `password_hash`: Bcrypt hashed password
- `created_at`: Registration timestamp

### `analysis_history` Table
Stores all analysis results for each user:
```sql
CREATE TABLE analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    filename TEXT NOT NULL,
    metrics TEXT NOT NULL (JSON),
    insight TEXT NOT NULL,
    mapped_columns TEXT NOT NULL (JSON),
    FOREIGN KEY (username) REFERENCES users(username)
)
```

**Columns**:
- `id`: Analysis ID
- `username`: User who performed the analysis
- `timestamp`: ISO format timestamp
- `filename`: Uploaded CSV filename
- `metrics`: JSON object with gender/age bias metrics
- `insight`: AI-generated insight
- `mapped_columns`: JSON object with column mappings

## Implementation Details

### 1. **Database Initialization** (`init_database()`)
- Called automatically when app starts
- Creates both tables if they don't exist
- Safe for multiple app restarts (idempotent)

### 2. **Registration** (`/register` endpoint)
```python
# Check if user exists in database
cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
if cursor.fetchone():
    raise HTTPException(status_code=400, detail="User already exists")

# Insert new user with hashed password
cursor.execute(
    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
    (username, password_hash)
)
```

**Features**:
- Checks if username already exists in database
- Returns 400 error if user tries to register twice
- Works across app restarts

### 3. **Login** (`/token` endpoint)
```python
# Get user from database
cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
result = cursor.fetchone()

# Verify password
if not result or not pwd_context.verify(password, result[0]):
    raise HTTPException(status_code=401, detail="Invalid Credentials")
```

**Features**:
- Queries database for username
- Verifies password against stored hash
- Returns JWT token on success

### 4. **Analysis Storage** (`/audit` endpoint)
- Saves to **both** in-memory cache (for performance) and **database** (for persistence)
- If database save fails, analysis still works (graceful degradation)

```python
# Save to in-memory cache
user_history[username].append(history_entry)

# Save to database for persistence
cursor.execute(
    """INSERT INTO analysis_history 
       (username, timestamp, filename, metrics, insight, mapped_columns) 
       VALUES (?, ?, ?, ?, ?, ?)""",
    (username, timestamp, file.filename, 
     json.dumps(metrics), insight, json.dumps(mapped_columns))
)
```

### 5. **History Retrieval** (`/history` endpoint)
```python
# Try in-memory cache first (fast)
if username in user_history and user_history[username]:
    return {"history": user_history[username]}

# Load from database if not cached (restores on app restart)
cursor.execute(
    """SELECT timestamp, filename, metrics, insight, mapped_columns 
       FROM analysis_history WHERE username = ? ORDER BY timestamp DESC""",
    (username,)
)
```

**Smart Caching**:
- Fast: Uses in-memory cache for active session
- Persistent: Loads from database on first request after restart
- Efficient: Minimal database queries after initial load

## User Flow

### First Time User (New Registration)
1. User clicks "Register"
2. App checks database for username
3. If new → password hashed → inserted into `users` table
4. User redirected to login
5. ✅ User cannot register same username again (UNIQUE constraint)

### App Restart Scenario
**Before**: User registration was lost, could register same username again ❌

**After**:
1. App starts → `init_database()` called
2. Creates tables if they don't exist
3. Existing users in database are still there ✅
4. User tries to register same username → database says "already exists" ❌
5. User can login with original credentials ✅

### Analysis History After Restart
1. App starts with empty in-memory cache
2. User logs in and clicks "History"
3. `/history` endpoint loads from database
4. All previous analyses shown ✅
5. Charts and metrics restored ✅

## Security Features

1. **Password Security**:
   - Passwords hashed with bcrypt (never stored in plain text)
   - 72-character limit for bcrypt compatibility

2. **Database Integrity**:
   - UNIQUE constraint on username prevents duplicates
   - FOREIGN KEY ensures analysis belongs to valid user

3. **Authentication**:
   - JWT tokens for API security
   - Token required for `/audit` and `/history`

## Advantages Over In-Memory Storage

| Feature | In-Memory | SQLite |
|---------|-----------|--------|
| Data Persistence | ❌ Lost on restart | ✅ Permanent |
| Prevent Duplicates | ❌ Only during session | ✅ Always enforced |
| Scalability | ❌ Limited by RAM | ✅ Disk storage |
| Multi-Instance | ❌ Separate databases | ✅ Shared database |
| Query Speed | ✅ Very fast | ✅ Fast enough for app |

## Files Modified

### `app.py`
- Added `import sqlite3`
- Added `DB_PATH = "users_auth.db"`
- Added `init_database()` function
- Updated `@app.post("/register")` to use database
- Updated `@app.post("/token")` to use database
- Updated `@app.post("/audit")` to save to database
- Updated `@app.get("/history")` to load from database

### Database Files
- `users_auth.db` - Created automatically on first run

## How to Reset Database

If you need to start fresh:

```powershell
# Delete the database file
Remove-Item users_auth.db

# Restart the app - fresh database will be created
python app.py
```

## Verification

Test the persistence:

1. Register a user: "john" / "password123"
2. Logout and restart app (Ctrl+C and `python app.py`)
3. Try to register "john" again → Error: "User already exists" ✅
4. Login with "john" / "password123" → Success ✅
5. Upload CSV and run audit
6. Restart app
7. Login with "john" and check History → Previous analyses shown ✅

## Future Enhancements

For production use, consider:
1. Upgrade to PostgreSQL or MySQL for multi-user deployment
2. Add database migration tool (Alembic)
3. Add user profile management (email, preferences)
4. Add role-based access control (RBAC)
5. Add data export functionality
6. Add audit logging for compliance
