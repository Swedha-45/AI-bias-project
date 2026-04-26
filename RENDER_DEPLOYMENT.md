# Render Deployment Guide

This guide explains how to deploy the AI Bias Auditor backend to Render.

## Prerequisites

1. A [Render](https://render.com) account
2. Your project pushed to GitHub

## Deployment Steps

### 1. Prepare Your Code for Deployment

The app needs modifications to work on Render's cloud environment.

### 2. Create a New Web Service on Render

1. Go to your Render Dashboard
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:

**Service Settings:**
- **Name**: `ai-bias-auditor-backend` (or your choice)
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### 3. Environment Variables

Add these environment variables in Render:

- `GOOGLE_API_KEY`: Your Google Gemini API key (optional, for AI insights)
- `SECRET_KEY`: A secure random string for JWT tokens (required)

### 4. Database Considerations

**Important**: SQLite databases don't persist on Render between deployments. For production use:

1. **Option 1**: Use Render's PostgreSQL database (recommended)
2. **Option 2**: Use a persistent disk for SQLite (limited free tier)
3. **Option 3**: Accept that data resets on each deploy (development only)

## Common Deployment Issues

### Issue: "Address already in use" or Port binding errors
**Solution**: The app must bind to `0.0.0.0` and use the `$PORT` environment variable.

### Issue: CORS errors with frontend
**Solution**: Update CORS origins in `app.py` to allow your deployed frontend domain.

### Issue: Static files not loading
**Solution**: The current setup has separate frontend files. You have two options:

1. **Deploy frontend separately** (recommended):
   - Deploy HTML/CSS/JS files to Vercel, Netlify, or Render Static Site
   - Update CORS origins to match the frontend URL

2. **Serve static files from backend**:
   - Add static file serving to FastAPI
   - Upload frontend files to the same repository

### Issue: Database data disappears
**Solution**: SQLite files are ephemeral on Render. Use PostgreSQL for persistent data.

## Frontend Deployment

Since your frontend is separate HTML files, deploy it separately:

### Option 1: Vercel (Recommended)
1. Create a new project on Vercel
2. Connect your GitHub repo
3. Set build settings:
   - **Build Command**: (leave empty)
   - **Output Directory**: `.` (root directory)
   - **Install Command**: (leave empty - no build needed)

### Option 2: Netlify
1. Drag and drop your HTML files to Netlify
2. Or connect GitHub repo with:
   - **Build Command**: `echo "No build step"`
   - **Publish Directory**: `.`

### Option 3: Render Static Site
1. Create "Static Site" instead of "Web Service"
2. Set publish directory to `.`

## Post-Deployment Configuration

1. **Update CORS origins** in `app.py`:
   ```python
   allow_origins=[
       "https://your-frontend-domain.vercel.app",  # Replace with actual domain
       "http://localhost:5500",  # Keep for local development
   ]
   ```

2. **Update API endpoints** in your frontend HTML files:
   - Change `http://127.0.0.1:8000` to your Render backend URL
   - Example: `https://ai-bias-auditor-backend.onrender.com`

3. **Test the deployment**:
   - Visit your frontend URL
   - Try uploading a CSV and running an audit
   - Check browser console for any CORS or API errors

## Troubleshooting

### Check Render Logs
- Go to your service dashboard
- Click "Logs" to see build and runtime logs
- Look for Python errors or port binding issues

### Test Locally First
Before deploying, test with production-like settings:
```bash
export PORT=8000
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Common Errors

**"Module not found"**: Check `requirements.txt` includes all dependencies

**"Port already in use"**: Make sure you're using `$PORT` and `0.0.0.0`

**"CORS error"**: Update `allow_origins` in `app.py`

**"Database error"**: SQLite won't persist - consider PostgreSQL

## Need Help?

- Check Render's [Python deployment docs](https://docs.render.com/deploy-python)
- Review FastAPI [deployment guide](https://fastapi.tiangolo.com/deployment/)
- Test API endpoints with tools like Postman or curl