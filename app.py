import streamlit as st
import pandas as pd
import requests
import re
import json
import csv
import io
import hmac
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from supabase import create_client

st.set_page_config(
    page_title="TikTok to eBay Manager",
    page_icon="🛍️",
    layout="wide"
)

# --------------------------------
# SECURITY
# --------------------------------

st.title("🛍️ TikTok → eBay Manager")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

try:
    APP_PASSWORD = st.secrets["APP_PASSWORD"]
except Exception:
    st.error("APP_PASSWORD is missing from Streamlit Secrets.")
    st.stop()

if not st.session_state.authenticated:
    password = st.text_input("Dashboard password", type="password")

    if st.button("Log in", type="primary"):
        if hmac.compare_digest(password, APP_PASSWORD):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

# --------------------------------
# DATABASE CONNECTION
# --------------------------------

@st.cache_resource
def get_database():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SECRET_KEY"]
    )

try:
    db = get_database()
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# --------------------------------
# PRODUCT EXTRACTION
# --------------------------------

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def find_product(data):
    if isinstance(data, list):
        for item in data:
            result = find_product(item)
            if result:
                return result

    if isinstance(data, dict):
        if data.get("@type") == "Product" or (
            isinstance(data.get("@type"), list)
            and "Product" in data.get("@type", [])
        ):
            return data

        for value in data.values():
            result = find_product(value)
            if result:
                return result

    return None


def extract_product(url):
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid URL.")

    host = (parsed.hostname or "").lower()

    is_tiktok = (
        host == "tiktok.com"
        or host.endswith(".tiktok.com")
    )

    is_amazon = (
        host == "amazon.com"
        or host.endswith(".amazon.com")
        or host == "amzn.to"
    )

    if not is_tiktok and not is_amazon:
        raise ValueError(
            "Please enter a TikTok Shop or Amazon product URL."
        )

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
            )
        },
        timeout=20,
        allow_redirects=True
    )

    response.raise_for_status()

    # Verify that redirects stay on an accepted platform.
    final_host = (
        urlparse(response.url).hostname or ""
    ).lower()

    final_tiktok = (
        final_host == "tiktok.com"
        or final_host.endswith(".tiktok.com")
    )

    final_amazon = (
        final_host == "amazon.com"
        or final_host.endswith(".amazon.com")
    )

    if not final_tiktok and not final_amazon:
        raise ValueError(
            "The link redirected to an unsupported website."
        )

    soup = BeautifulSoup(response.text, "html.parser")

    def meta(*names):
        for name in names:
            tag = soup.find(
                "meta", attrs={"property": name}
            )

            if not tag:
                tag = soup.find(
                    "meta", attrs={"name": name}
                )

            if tag and tag.get("content"):
                return clean(tag["content"])

        return ""

    product = {}

    for tag in soup.find_all(
        "script", type="application/ld+json"
    ):
        try:
            data = json.loads(
                tag.string or tag.get_text()
            )

            product = find_product(data) or {}

            if product:
                break

        except Exception:
            continue

    name = clean(product.get("name"))

    if not name:
        name = meta("og:title", "twitter:title")

    if not name and soup.title:
        name = clean(soup.title.string)

    description = clean(product.get("description"))

    if not description:
        description = meta(
            "og:description", "description"
        )

    brand = product.get("brand", "")

    if isinstance(brand, dict):
        brand = brand.get("name", "")

    if not brand:
        brand = meta("product:brand")

    price = ""
    offers = product.get("offers", {})

    if isinstance(offers, list) and offers:
        offers = offers[0]

    if isinstance(offers, dict):
        price = offers.get("price", "")

    if not price:
        price = meta(
            "product:price:amount",
            "og:price:amount"
        )

    return {
        "name": name,
        "description": description,
        "brand": clean(brand),
        "price": price
    }

# --------------------------------
# SKU GENERATOR
# --------------------------------

def generate_sku():
    result = db.table("inventory").select("sku").execute()

    highest = 0

    for item in result.data or []:
        match = re.fullmatch(
            r"TTE-(\d+)",
            item.get("sku", "")
        )
        if match:
            highest = max(highest, int(match.group(1)))

    return f"TTE-{highest + 1:05d}"


# --------------------------------
# SIDEBAR NAVIGATION
# --------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose a section",
    [
        "Create Listing",
        "My Inventory",
        "Dashboard"
    ]
)

if st.sidebar.button("Log out"):
    st.session_state.authenticated = False
    st.rerun()

# --------------------------------
# CREATE LISTING
# --------------------------------

if page == "Create Listing":

    st.header("Create an eBay Listing")

    source_platform = st.selectbox(
        "Where is your product from?",
        ["TikTok Shop", "Amazon"]
    )

    st.write(f"Paste your {source_platform} product link.")

    url = st.text_input(
        f"{source_platform} Product URL",
        placeholder=(
            "https://www.tiktok.com/..."
            if source_platform == "TikTok Shop"
            else "https://www.amazon.com/..."
        )
    )

    if st.button("Extract Product Information"):
        if not url:
            st.error("Paste a product link first.")
        else:
            try:
                extracted = extract_product(url)
st.session_state.extracted = extracted
st.session_state.source_url = url
st.session_state.source_platform = source_platform

                if extracted["name"]:
                    st.success("Product information retrieved.")
                else:
                    st.warning(
                        "TikTok did not provide a product name. "
                        "Please enter it manually."
                    )

            except Exception as e:
                st.warning(
                    "Automatic extraction was unsuccessful. "
                    "TikTok may restrict access to its product pages."
                )
                st.caption(str(e))
                st.session_state.extracted = {}
                st.session_state.source_url = url
                st.session_state.source_platform = source_platform

    if "extracted" in st.session_state:

        data = st.session_state.extracted

        st.divider()
        st.subheader("Review Product Information")

        name = st.text_input(
            "Product Name",
            value=data.get("name", "")
        )

        brand = st.text_input(
            "Brand",
            value=data.get("brand", "")
        )

        description = st.text_area(
            "Product Description",
            value=data.get("description", ""),
            height=140
        )

        condition = st.selectbox(
            "Condition",
            [
                "New",
                "New with tags",
                "New without tags",
                "Open box",
                "Pre-owned"
            ]
        )

        price_default = 0.0
        try:
            price_default = float(data.get("price") or 0)
        except (ValueError, TypeError):
            pass

        price = st.number_input(
            "eBay Selling Price ($)",
            min_value=0.0,
            value=price_default,
            step=1.0
        )

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1
        )

        keywords = st.text_input(
            "Additional Search Keywords"
        )

        if st.button("Generate eBay Draft", type="primary"):

            if not name.strip():
                st.error("Enter a product name.")
            elif price <= 0:
                st.error("Enter a valid selling price.")
            else:

                title = " ".join(
                    x for x in [
                        brand,
                        name,
                        condition,
                        keywords
                    ] if clean(x)
                )[:80]

                final_description = (
                    f"{name}\n\n"
                    f"Brand: {brand or 'Not specified'}\n"
                    f"Condition: {condition}\n\n"
                    f"{description}\n\n"
                    "Please review all photos and details "
                    "before purchasing."
                )

                st.session_state.draft = {
                    "sku": generate_sku(),
                    "product_name": name,
                    "brand": brand,
                    "title": title,
                    "description": final_description,
                    "price": price,
                    "quantity": quantity,
                    "condition": condition,
                    "source_url": st.session_state.source_url,
                    "source_platform": st.session_state.source_platform

                }

                st.rerun()

    if "draft" in st.session_state:

        draft = st.session_state.draft

        st.divider()
        st.subheader("Your Generated eBay Draft")

        st.success(f"Assigned SKU: {draft['sku']}")

        final_title = st.text_input(
            "eBay Title",
            value=draft["title"],
            max_chars=80
        )

        final_description = st.text_area(
            "eBay Description",
            value=draft["description"],
            height=200
        )

        final_price = st.number_input(
            "Final Price ($)",
            min_value=0.01,
            value=float(draft["price"]),
            step=1.0
        )

        ebay_csv = {
            "SKU": draft["sku"],
            "Title": final_title,
            "Description": final_description,
            "Price": f"{final_price:.2f}",
            "Quantity": str(draft["quantity"]),
            "Condition": draft["condition"]
        }

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=ebay_csv.keys()
        )
        writer.writeheader()
        writer.writerow(ebay_csv)

        st.download_button(
            "Download eBay Draft CSV",
            data=buffer.getvalue().encode("utf-8-sig"),
            file_name=f"{draft['sku']}.csv",
            mime="text/csv"
        )

        st.info(
            "After creating the listing on eBay, "
            "return here and confirm that it is listed."
        )

        ebay_url = st.text_input(
            "Your eBay Listing URL",
            placeholder="https://www.ebay.com/itm/..."
        )

        if st.button("Confirm Listed & Save to Inventory", type="primary"):

            parsed = urlparse(ebay_url.strip())

            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or not (
                    parsed.hostname == "ebay.com"
                    or parsed.hostname.endswith(".ebay.com")
                )
            ):
                st.error("Enter a valid eBay listing URL.")
            else:
                record = {
                    "sku": draft["sku"],
                    "product_name": draft["product_name"],
                    "brand": draft["brand"],
                    "tiktok_url": draft["source_url"],
                    "source_url": draft["source_url"],
                    "source_platform": draft["source_platform"],
                    "ebay_url": ebay_url.strip(),
                    "ebay_title": final_title,
                    "description": final_description,
                    "price": float(final_price),
                    "quantity": int(draft["quantity"]),
                    "status": "Active"
                }

                try:
                    db.table("inventory").insert(record).execute()

                    st.success(
                        f"Successfully saved {draft['sku']} "
                        "to your inventory!"
                    )

                    del st.session_state["draft"]
                    st.rerun()

                except Exception as e:
                    st.error(f"Could not save listing: {e}")


# --------------------------------
# MY INVENTORY
# --------------------------------

elif page == "My Inventory":

    st.header("📦 My eBay Inventory")

    try:
        result = (
            db.table("inventory")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        inventory = result.data or []

        if not inventory:
            st.info("You haven't saved any listings yet.")

        else:
            st.write(f"Total saved products: {len(inventory)}")

            for item in inventory:

                with st.expander(
                    f"{item['sku']} — {item['product_name']}"
                ):

                    st.write(
                        f"**Brand:** {item.get('brand') or 'Not specified'}"
                    )

                    st.write(
                        f"**Price:** ${item.get('price') or 0:.2f}"
                    )

                    st.write(
                        f"**Status:** {item.get('status', 'Active')}"
                    )

                    st.markdown(
                        f"[Open TikTok Product]({item['tiktok_url']})"
                    )

                    if item.get("ebay_url"):
                        platform = item.get("source_platform") or "TikTok Shop"
                        source_link = item.get("source_url") or item.get("tiktok_url")

                        st.markdown(
                            f"[Open {platform} Product]({source_link})"
                        )

                    new_status = st.selectbox(
                        "Update Listing Status",
                        ["Active", "Sold", "Ended"],
                        index=["Active", "Sold", "Ended"].index(
                            item.get("status", "Active")
                            if item.get("status") in
                            ["Active", "Sold", "Ended"]
                            else "Active"
                        ),
                        key=f"status_{item['id']}"
                    )

                    new_ebay_url = st.text_input(
                        "eBay URL",
                        value=item.get("ebay_url") or "",
                        key=f"url_{item['id']}"
                    )

                    if st.button(
                        "Save Changes",
                        key=f"save_{item['id']}"
                    ):
                        db.table("inventory").update({
                            "status": new_status,
                            "ebay_url": new_ebay_url
                        }).eq("id", item["id"]).execute()

                        st.success("Inventory updated.")
                        st.rerun()

    except Exception as e:
        st.error(f"Could not load inventory: {e}")


# --------------------------------
# DASHBOARD
# --------------------------------

elif page == "Dashboard":

    st.header("📊 Inventory Dashboard")

    try:
        result = db.table("inventory").select("*").execute()
        items = result.data or []

        active = sum(
            1 for x in items if x.get("status") == "Active"
        )

        sold = sum(
            1 for x in items if x.get("status") == "Sold"
        )

        ended = sum(
            1 for x in items if x.get("status") == "Ended"
        )

        revenue = sum(
            float(x.get("price") or 0)
            for x in items
            if x.get("status") == "Sold"
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Listings", len(items))
        col2.metric("Active", active)
        col3.metric("Sold", sold)
        col4.metric("Ended", ended)

        st.divider()

        st.metric(
            "Value of Sold Listings",
            f"${revenue:,.2f}"
        )

        if items:
            df = pd.DataFrame(items)

            st.subheader("Recent Inventory")

            st.dataframe(
                df[
                    [
                        "sku",
                        "product_name",
                        "price",
                        "quantity",
                        "status"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"Dashboard error: {e}")


st.divider()

st.caption(
    "TikTok → eBay Manager | Inventory stored securely in Supabase. "
    "Verify all product details and eBay policies before listing."
)
