from playwright.sync_api import sync_playwright
import time

def scrape_google_maps(industry: str, location: str, total: int = 5):
    search_query = f"{industry} in {location}"
    print(f"🚀 [Sync] Searching: {search_query}...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="en-GB")
        page = context.new_page()

        try:
            # 1. Go to Maps
            page.goto("https://www.google.com/maps", timeout=60000)

            # 2. Handle Cookies
            try:
                page.wait_for_selector("button[aria-label='Accept all']", timeout=3000)
                page.click("button[aria-label='Accept all']")
            except:
                pass

            # 3. Search
            page.wait_for_selector("input[name='q']", timeout=15000)
            page.fill("input[name='q']", search_query)
            page.keyboard.press("Enter")
            
            # Wait for results to load
            try:
                page.wait_for_selector('div[role="feed"]', timeout=10000)
            except:
                print("⚠️ Could not find feed, trying to scrape anyway.")

            # 4. Scroll to load initial items
            print("📜 Scrolling to load results...")
            page.hover('div[role="feed"]')
            for _ in range(2): 
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(1000)

            # 5. Extract Leads (Click & Verify Mode)
            print("🔍 Clicking each result to verify data...")
            
            # We grab the list items again to ensure they are fresh
            listings = page.query_selector_all('div[role="article"]')
            
            for i, card in enumerate(listings[:total]):
                try:
                    # --- A. CLICK THE CARD ---
                    print(f"   👉 Clicking item {i+1}...")
                    card.click()
                    
                    # Wait for the details panel to load (The "Back to results" button usually appears)
                    # Or we wait for the main header (h1) to change
                    page.wait_for_timeout(2000) 

                    # --- B. SCRAPE DETAILS PANEL ---
                    # Now we look at the 'page' content, not the 'card' content
                    
                    # 1. Get Business Name (from the big H1 in details)
                    name_el = page.query_selector('h1.DUwDvf')
                    name = name_el.inner_text() if name_el else "Unknown"

                    # 2. Check for Website Button (Specific to Details Panel)
                    # Look for the "Website" button which usually has data-item-id="authority"
                    website_btn = page.query_selector('a[data-item-id="authority"]')
                    
                    # Fallback: Look for any link with "Website" in aria-label
                    if not website_btn:
                        website_btn = page.query_selector('a[aria-label*="Website"]')

                    has_website = True if website_btn else False
                    website_url = website_btn.get_attribute("href") if website_btn else None

                    # 3. Get Phone Number
                    # Phone usually has a specific icon or starts with "phone:" in data-item-id
                    phone = None
                    phone_btn = page.query_selector('button[data-item-id^="phone:tel:"]')
                    if phone_btn:
                        phone = phone_btn.get_attribute("aria-label") # Usually "Phone: 01234 56789"
                        if phone: phone = phone.replace("Phone:", "").strip()
                    
                    # Fallback Phone: Search in text body if button is missing
                    if not phone:
                        main_content = page.locator('div[role="main"]').inner_text()
                        for line in main_content.split('\n'):
                            # Simple check for phone-like patterns
                            if any(c.isdigit() for c in line) and len(line) > 8 and ("+" in line or "-" in line):
                                phone = line
                                break

                    print(f"      ✅ Found: {name} | Website: {has_website}")

                    results.append({
                        "business_name": name,
                        "industry": industry,
                        "location": location,
                        "has_website": has_website,
                        "website_url": website_url,
                        "phone": phone
                    })
                    
                except Exception as e:
                    print(f"      ❌ Failed to scrape item {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Critical Error: {e}")
        finally:
            browser.close()
            
    return results