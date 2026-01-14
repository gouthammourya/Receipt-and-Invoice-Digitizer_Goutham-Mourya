# MydigiBill — Gemini / Google Generative AI setup

This project can use a Google service account to call the Generative Language / Gemini endpoint.

Quick steps to enable Google service-account authentication (recommended):

1. Install the Google Cloud SDK and sign in:

```powershell
# gcloud init
# login and select or create a project
```

2. Enable the Generative Language API for your project:

```powershell
gcloud services enable generativelanguage.googleapis.com
```

3. Create a service account and grant it AI/Vertex permissions (replace `PROJECT_ID`):

```powershell
gcloud iam service-accounts create my-gemini-sa --display-name="MydigiBill Gemini SA"
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:my-gemini-sa@PROJECT_ID.iam.gserviceaccount.com" --role="roles/aiplatform.user"
```

4. Create and download a key for the service account:

```powershell
gcloud iam service-accounts keys create key.json --iam-account=my-gemini-sa@PROJECT_ID.iam.gserviceaccount.com
```

5. Set `GOOGLE_APPLICATION_CREDENTIALS` to point to the downloaded JSON key (Windows persistent):

```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "D:\path\to\key.json"
```

6. In your project, create a `.env` (optional) or set env vars directly. Example `.env`:

```dotenv
GEMINI_ENDPOINT=https://generativelanguage.googleapis.com/v1/models/YOUR_MODEL:generateContent
# GOOGLE_APPLICATION_CREDENTIALS=D:\path\to\key.json  # optional if using setx
```

7. Install Python deps:

```powershell
pip install -r requirements.txt
```

8. Run the app:

```powershell
streamlit run app.py
```

Notes:
- The code will automatically use the service account JSON if `GOOGLE_APPLICATION_CREDENTIALS` is set and `google-auth` is installed.
- For quick local testing you can use:

```powershell
$env:GEMINI_API_KEY = (& gcloud auth application-default print-access-token)
# then run streamlit
streamlit run app.py
```

If you'd like, I can adapt the request payload in `ai_client.py` to a specific provider format (OpenAI, Anthropic, or Google Vertex) — tell me which provider and model you plan to use.
