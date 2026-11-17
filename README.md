# TikTok-to-eBay Draft Builder

A free, semi-automated Streamlit starter app. Paste a TikTok Shop product URL, manually confirm the item details, generate an editable listing title/description, and download a CSV/text draft.

## Important limitations

- This app does **not** scrape TikTok Shop pages or download product images.
- You manually enter the product name, brand, condition, details, price, quantity, and shipping note.
- The CSV is a portable draft for your review. It is **not** guaranteed to be an eBay Seller Hub bulk-upload file.
- This starter version does not publish listings to eBay and does not connect to eBay's API.
- Only resell products you are authorized to sell. Check eBay rules, intellectual-property rights, product safety rules, and the supplier's resale terms. Use your own accurate photos and descriptions.
- eBay account holders generally need to be 18 or older. If you are under 18, have a parent or guardian handle the seller account and any sales activity in accordance with eBay's terms.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

5. Open the local URL Streamlit prints (usually `http://localhost:8501`).

## Deploy free with GitHub + Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `app.py`, `requirements.txt`, `README.md`, and `secrets.toml.example`.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Choose **Create app**, select your repository and branch, and set the main file path to `app.py`.
5. Deploy.

No secrets are needed for this starter version.

## Files

- `app.py` — Streamlit application.
- `requirements.txt` — Python dependencies.
- `README.md` — setup instructions.
- `secrets.toml.example` — example only; no credentials are required.

## Next possible upgrade

A later version could use eBay's official APIs to create unpublished offers, but that requires an eBay developer application, OAuth authorization, required item specifics, shipping/return/payment policies, and careful testing. Never put API keys or tokens in source code or commit them to GitHub.
