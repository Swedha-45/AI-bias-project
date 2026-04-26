# CSV Upload Format Guide

This document specifies the required format and column structure for hiring dataset uploads to the AI Bias Auditor.

## File Requirements

- **Format**: CSV (Comma-Separated Values)
- **Encoding**: UTF-8
- **Delimiter**: Comma (`,`)
- **Header Row**: Required (first row must contain column names)

---

## Required Columns

These columns **must** be present in your CSV file:

| Column Name | Data Type | Description | Example Values |
|-------------|-----------|-------------|-----------------|
| `gender` | Text/String | Employee gender (demographic attribute) | Male, Female, Non-binary, Other |
| `age` | Number | Employee age (demographic attribute) | 25, 45, 32 |
| `hired` | Number (0 or 1) | Hiring decision (outcome being audited) | 0 (not hired), 1 (hired) |

---

## Recommended Columns

These columns are **optional but recommended** for more comprehensive bias analysis:

| Column Name | Data Type | Description | Example Values |
|-------------|-----------|-------------|-----------------|
| `name` | Text/String | Employee name (for reference, not analyzed) | James Wilson, Priya Sharma |
| `race` | Text/String | Employee race/ethnicity (demographic attribute) | White, Black, Asian, Hispanic, Other |
| `education` | Text/String | Education level (demographic attribute) | High School, Bachelor, Master, PhD |
| `experience_years` | Number | Years of professional experience | 0, 5, 15 |
| `test_score` | Number | Standardized test score | 0-100 |
| `interview_score` | Number | Interview evaluation score | 0-100 |

---

## Column Requirements & Constraints

### For Analysis:
- **Categorical columns** (text-based): Should have **2-10 unique values** for proper bias analysis
- **Numeric columns** (numbers): Can have any range of values
- **Excluded columns**: Any column with more than 10 categories or fewer than 2 will be skipped

### Quality Standards:
- **No missing values** in required columns (`gender`, `age`, `hired`)
- **Consistent formatting**: Gender and race values should use consistent casing and spelling across all rows
- **Valid numeric ranges**: Age should be positive; scores/ratings should be in reasonable ranges (e.g., 0-100)

---

## Example CSV Format

```csv
name,age,gender,race,experience_years,test_score,education,interview_score,hired
James Wilson,28,Male,White,5,85,Bachelor,78,1
Priya Sharma,27,Female,Asian,5,87,Bachelor,80,0
Marcus Johnson,29,Male,Black,6,88,Bachelor,79,0
Sarah Mitchell,26,Female,White,4,83,Bachelor,77,0
Ahmed Hassan,31,Male,Middle Eastern,8,91,Master,85,1
Yuki Tanaka,25,Female,Asian,2,79,Bachelor,72,0
```

---

## Column Auto-Mapping

The system will **automatically detect** and map the following column names:

### Automatic Recognition (case-insensitive):
- **Gender**: `gender`, `sex`, `Gender`, `SEX`
- **Age**: `age`, `Age`, `AGE`
- **Outcome/Hired**: `hired`, `hired_decision`, `decision`, `outcome`, `label`
- **Race/Ethnicity**: `race`, `ethnicity`, `Race`, `Ethnicity`
- **Education**: `education`, `education_level`, `Education`, `EDUCATION`

If your column names differ, the system will prompt you to manually map them during upload.

---

## Data Validation Rules

Before upload, ensure:

1. ✅ **Hired column** contains only `0` (not hired) or `1` (hired)
2. ✅ **Age column** contains positive integers
3. ✅ **Numeric columns** have no letters or special characters (except decimals)
4. ✅ **Categorical columns** use consistent values (e.g., "Female" not "female" and "Female")
5. ✅ **No blank rows** between headers and data

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Column not found" error | Verify column name spelling and check the auto-mapping suggestions |
| "Invalid data type" error | Ensure numeric columns contain only numbers (no commas, letters, or symbols) |
| Bias analysis missing some attributes | Check if categorical columns have 2-10 unique values |
| Results show partial data | Re-check for blank cells in required columns (`gender`, `age`, `hired`) |

---

## Upload Steps

1. Open **home.html** in your browser
2. Click **"Upload CSV File"** button
3. Select your CSV file from your computer
4. Review the **auto-mapped columns** display
5. Manually adjust column mappings if needed
6. Click **"Run Audit"** to begin bias analysis

---

## Need Help?

- Check `README.md` for full project documentation
- Review the example `hiring_dataset.csv` in this project folder
- Ensure your CSV matches the format described above
