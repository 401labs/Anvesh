from playwright.sync_api import sync_playwright
import time
from app.db import insert_lead

def scrape_google_maps(industry: str, location: str, total: int = -1, stop_signal=None):
    """
    Scrapes Google Maps for leads.
    :param total: Number of leads to scrape. -1 for unlimited.
    :param stop_signal: A callable that returns True if the scraper should stop.
    """
    search_query = f"{industry} in {location}"
    print(f"🚀 [Sync] Searching: {search_query}...")
    
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 🟢 FIX 1: Set Timezone to reduce "Near Me" bias (using Toronto/NY as generic NA)
        context = browser.new_context(
            locale="en-US",
            timezone_id="America/Toronto",
            permissions=[],  # Deny location permissions
            geolocation=None
        )
        page = context.new_page()

        try:
            # 🟢 FIX: Go directly to the search URL to bypass "Near Me" autocomplete bias
            # This forces Google to search exactly what we want (e.g., "Bakery in USA")
            encoded_query = search_query.replace(" ", "+")
            search_url = f"https://www.google.com/maps/search/{encoded_query}?hl=en"
            
            print(f"🌍 Navigating directly to: {search_url}")
            page.goto(search_url, timeout=60000)

            # Handle Cookies (Sometimes they appear on search results page too)
            try:
                page.wait_for_selector("button[aria-label='Accept all']", timeout=3000)
                page.click("button[aria-label='Accept all']")
            except:
                pass

            # We skipped the typing part, so we go straight to waiting for results
            
            # Wait for results feed
            try:
                page.wait_for_selector('div[role="feed"]', timeout=15000)
            except:
                print("⚠️ Could not find feed. Search might have failed or zero results.")
                return results

            # Initial scroll to load some data
            print("📜 Initial Scroll...")
            page.hover('div[role="feed"]')
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(2000)

            print("🔍 Clicking & Verifying...")
            
            valid_leads_count = 0
            processed_indices = set()
            consecutive_no_new_leads = 0
            
            # Infinite scrolling loop for "Unlimited" mode
            while True:
                # Check Global Stop Signal
                if stop_signal and stop_signal():
                    print("🛑 Stop signal received. Exiting scraper.")
                    break

                # Stop if we hit the limit (and limit is not -1)
                if total != -1 and valid_leads_count >= total:
                    break
                
                # Check for "End of list" message (Class based)
                if page.query_selector("div.HlvSq"):
                    print("🏁 Reached end of the list (Marker Found).")
                    break
                
                # Check for "End of list" message (Text based - More reliable)
                try:
                    # check if the element is visible without throwing error if not found immediately
                    if page.get_by_text("You've reached the end of the list").is_visible():
                        print("🏁 Reached end of the list (Text Detected).")
                        break
                except:
                    pass

                listings = page.query_selector_all('div[role="article"]')
                
                # Check if we have processed everything visible
                if len(listings) == len(processed_indices):
                    # No new items loaded yet, scroll more
                    print("📜 Scrolling for more...")
                    page.hover('div[role="feed"]')
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(3000) # Give it time to load
                    
                    # If count didn't change after scroll, maybe we are stuck or at end
                    new_listings_count = len(page.query_selector_all('div[role="article"]'))
                    if new_listings_count == len(listings):
                        consecutive_no_new_leads += 1
                        if consecutive_no_new_leads > 3:
                            print("⚠️ No new items loading after 3 scrolls. Ending.")
                            break
                    else:
                        consecutive_no_new_leads = 0
                    continue

                # Process new items only
                for i, card in enumerate(listings):
                    if i in processed_indices:
                        continue
                    
                    processed_indices.add(i)

                    if stop_signal and stop_signal():
                        break
                    
                    if total != -1 and valid_leads_count >= total:
                        break

                    try:
                        card.click()
                        page.wait_for_timeout(1000) # Wait for details panel

                        # --- SCRAPE DETAILS ---
                        name_el = page.query_selector('h1.DUwDvf')
                        name = name_el.inner_text() if name_el else "Unknown"

                        # Get Address
                        address = "N/A"
                        address_btn = page.query_selector('button[data-item-id="address"]')
                        if address_btn:
                            address_text_div = address_btn.query_selector('div.Io6YTe')
                            if address_text_div:
                                address = address_text_div.inner_text()
                            else:
                                raw_addr = address_btn.get_attribute("aria-label")
                                if raw_addr: address = raw_addr.replace("Address:", "").strip()

                        # Get Website
                        website_btn = page.query_selector('a[data-item-id="authority"]')
                        if not website_btn:
                            website_btn = page.query_selector('a[aria-label*="Website"]')
                        has_website = True if website_btn else False
                        website_url = website_btn.get_attribute("href") if website_btn else None

                        # Get Phone
                        phone = None
                        phone_btn = page.query_selector('button[data-item-id^="phone:tel:"]')
                        if phone_btn:
                            phone = phone_btn.get_attribute("aria-label")
                            if phone: phone = phone.replace("Phone:", "").strip()
                        if not phone:
                            main_content = page.locator('div[role="main"]').inner_text()
                            for line in main_content.split('\\n'):
                                if any(c.isdigit() for c in line) and len(line) > 8 and ("+" in line or "-" in line):
                                    phone = line
                                    break
                        # --- 5. NEW: Reviews & Rating ---
                        rating = None
                        reviews = 0
                        
                        # Look for rating element, can be a div or a span
                        rating_el = page.query_selector('[aria-label*="stars"]')
                        if rating_el:
                            aria_text = rating_el.get_attribute("aria-label") # e.g., "4.4 stars "
                            if aria_text:
                                try:
                                    # Extract the first part, which should be the number
                                    rating_str = aria_text.split(" ")[0]
                                    rating = float(rating_str)
                                except (ValueError, IndexError):
                                    pass # Keep rating as None

                        # Look for reviews element separately
                        reviews_el = page.query_selector('[aria-label*="reviews"]')
                        if reviews_el:
                             aria_text = reviews_el.get_attribute("aria-label") # e.g., "17 reviews"
                             if aria_text:
                                try:
                                    reviews_str = aria_text.split(" ")[0].replace(",", "")
                                    # Handle suffixes like K for thousands, M for millions
                                    if 'K' in reviews_str.upper():
                                        reviews = int(float(reviews_str.upper().replace('K', '')) * 1000)
                                    elif 'M' in reviews_str.upper():
                                        reviews = int(float(reviews_str.upper().replace('M', '')) * 1000000)
                                    else:
                                        reviews = int(reviews_str)
                                except (ValueError, IndexError):
                                    pass # Keep reviews as 0
                        
                        # --- 6. NEW: "Claim this Business" Status ---
                        # If this link exists, the profile is UNCLAIMED (High Value Lead)
                        is_claimed = True
                        # Look for the specific "Claim this business" text or link
                        claim_btn = page.query_selector('a[aria-label*="Claim this business"]')
                        if not claim_btn:
                            claim_btn = page.locator("text=Claim this business").count() > 0
                            if claim_btn: is_claimed = False # Button exists, so it's NOT claimed
                        else:
                            is_claimed = False # Button found

                        # --- 7. NEW: Business Category ---
                        # Usually appears right under the title, e.g., "Interior Designer"
                        category = "N/A"
                        # It's usually the button with the specific class for category
                        cat_btn = page.query_selector('button[jsaction*="category"]')
                        if cat_btn:
                            category = cat_btn.inner_text()

                        # -----------------------------------

                        print(f"      ✅ Found: {name} | ⭐ {rating} ({reviews}) | Claimed: {is_claimed}")

                        results.append({
                            "business_name": name,
                            "industry": industry,
                            "category": category,      # NEW
                            "location": location,
                            "address": address,
                            "rating": rating,          # NEW
                            "review_count": reviews,   # NEW
                            "is_claimed": is_claimed,  # NEW
                            "has_website": has_website,
                            "website_url": website_url,
                            "phone": phone
                        })

                        lead_data = {
                            "business_name": name,
                            "industry": industry,
                            "location": location,
                            "address": address,
                            "has_website": has_website,
                            "website_url": website_url,
                            "phone": phone,
                            "rating": rating,          # NEW
                            "review_count": reviews,   # NEW
                            "is_claimed": is_claimed,  # NEW
                            "category": category       # NEW
                        }
                        
                        # --- INSERT TO DB ---
                        is_new = insert_lead(lead_data)
                        
                        if is_new:
                            print(f"      ✅ Saved: {name} | {address[:20]}...")
                            results.append(lead_data)
                            valid_leads_count += 1
                        else:
                            # print(f"      Duplicate skipped: {name}")
                            pass

                    except Exception as e:
                        # print(f"      ❌ Failed item: {e}")
                        continue
                
                # Check constraints
                if total != -1 and valid_leads_count >= total:
                    break

        except Exception as e:
            print(f"❌ Critical Error: {e}")
        finally:
            browser.close()
            
    return results