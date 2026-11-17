import csv
import io
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import streamlit as st

st.set_page_config(page_title="TikTok → eBay Draft Builder", page_icon="🛍️", layout="centered")

st.title("TikTok → eBay Draft Builder")
st.caption("Semi-automated listing helper • TikTok link in, editable eBay draft out")

st.info(
    "This starter app does not scrape TikTok Shop pages or copy their photos. "
    "Paste the product link, then enter/confirm the product details yourself. "
    "Only list items you are authorized to resell, and use your own accurate photos."
)

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()

def make_title(name, brand, condition, keywords):
    parts = [clean_text(brand), clean_text(name), clean_text(condition), clean_text(keywords)]
    title = " ".join(p for p in parts if p)
    return title[:80]

def make_description(name, brand, condition, details, shipping):
    lines = [
        clean_text(name) or "Item",
        "",
        f"Brand: {clean_text(brand) or 'Not specified'}",
        f"Condition: {clean_text(condition) or 'Not specified'}",
        "",
        clean_text(details) or "Please review the photos and item details before purchasing.",
        "",
        f"Shipping: {clean_text(shipping) or 'Ships securely; handling time to be confirmed.'}",
        "",
        "Please message me with any questions before purchasing."
    ]
    return "\n".join(lines)

with st.form("listing_form"):
    st.subheader("1. Product source")
    source_url = st.text_input("TikTok Shop product URL", placeholder="https://www.tiktok.com/...")
    st.caption("The link is saved into your draft as a reference; product data is not automatically extracted.")

    st.subheader("2. Confirm the item details")
    name = st.text_input("Product name *", placeholder="e.g. Stainless steel water bottle")
    brand = st.text_input("Brand", placeholder="e.g. Contigo")
    condition = st.selectbox("Condition", ["New", "New with tags", "New without tags", "Open box", "Pre-owned"])
    details = st.text_area("Description / features", placeholder="Size, color, material, included accessories, flaws, measurements...")
    keywords = st.text_input("Extra search keywords", placeholder="e.g. insulated, travel, 24 oz")
    price = st.number_input("Your intended eBay price (USD)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
    sku = st.text_input("SKU (optional)", placeholder="Leave blank to generate one")
    shipping = st.text_input("Shipping note", value="Ships securely; handling time to be confirmed.")
    submitted = st.form_submit_button("Generate draft", type="primary")

if submitted:
    parsed = urlparse(source_url.strip())
    if not source_url.strip() or parsed.scheme not in ("http", "https") or not parsed.netloc:
        st.error("Enter a valid product URL beginning with http:// or https://.")
    elif not clean_text(name):
        st.error("Add a product name before generating the draft.")
    elif price <= 0:
        st.error("Enter a price greater than $0.")
    else:
        generated_sku = clean_text(sku) or "TT-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        draft = {
            "title": make_title(name, brand, condition, keywords),
            "description": make_description(name, brand, condition, details, shipping),
            "price": f"{price:.2f}",
            "quantity": str(quantity),
            "sku": generated_sku,
            "condition": condition,
            "source_url": source_url.strip(),
            "status": "DRAFT - REVIEW BEFORE LISTING",
        }
        st.session_state["draft"] = draft

if "draft" in st.session_state:
    draft = st.session_state["draft"]
    st.divider()
    st.subheader("3. Review and edit your draft")
    title = st.text_input("eBay title (80-character limit)", value=draft["title"], max_chars=80)
    description = st.text_area("eBay description", value=draft["description"], height=220)
    col1, col2 = st.columns(2)
    with col1:
        final_price = st.text_input("Price (USD)", value=draft["price"])
    with col2:
        final_quantity = st.number_input("Quantity ", min_value=1, value=int(draft["quantity"]), step=1)
    final_sku = st.text_input("SKU", value=draft["sku"])

    try:
        valid_price = float(final_price) > 0
    except ValueError:
        valid_price = False

    if not valid_price:
        st.warning("Enter a valid price greater than $0 to export.")
    else:
        final_draft = {
            "title": title[:80],
            "description": description,
            "price": f"{float(final_price):.2f}",
            "quantity": str(final_quantity),
            "sku": final_sku,
            "condition": draft["condition"],
            "source_url": draft["source_url"],
            "status": "DRAFT - REVIEW BEFORE LISTING",
        }
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(final_draft.keys()))
        writer.writeheader()
        writer.writerow(final_draft)
        st.download_button(
            "Download eBay draft CSV",
            data=buffer.getvalue().encode("utf-8-sig"),
            file_name="ebay_listing_draft.csv",
            mime="text/csv",
            type="primary",
        )
        st.download_button(
            "Download draft as text",
            data=(f"TITLE\n{final_draft['title']}\n\nDESCRIPTION\n{final_draft['description']}\n\n"
                  f"PRICE: ${final_draft['price']}\nQUANTITY: {final_draft['quantity']}\n"
                  f"SKU: {final_draft['sku']}\nSOURCE: {final_draft['source_url']}\n").encode("utf-8"),
            file_name="ebay_listing_draft.txt",
            mime="text/plain",
        )
        st.caption("The CSV is a portable draft for review, not a guaranteed eBay bulk-upload template.")

st.divider()
st.caption("Before listing: verify item specifics, category, shipping, fees, brand authenticity, resale rights, and eBay policies.")
