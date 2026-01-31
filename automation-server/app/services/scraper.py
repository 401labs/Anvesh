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
                    page.wait_for_timeout(5000) # Give it time to load (Increased to 5s)
                    
                    # If count didn't change after scroll, maybe we are stuck or at end
                    new_listings_count = len(page.query_selector_all('div[role="article"]'))
                    if new_listings_count == len(listings):
                        consecutive_no_new_leads += 1
                        if consecutive_no_new_leads > 3:
                            print("⚠️ No new items loading after 3 scrolls. Ending.")
                            break
                    else:
                        consecutive_no_new_leads = 0
                        # --- FIX: Give new items time to 'hydrate' after scroll ---
                        print("... letting new items settle (15s)...")
                        page.wait_for_timeout(15000) # Increased to 15s per user request for reliability 
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
                        # --- SLOW AND STEADY APPROACH ---
                        
                        # 1. Get the expected name from the card itself before clicking
                        expected_name_el = card.query_selector('div.qBF1Pd')
                        expected_name = expected_name_el.inner_text().strip() if expected_name_el else None
                        
                        if not expected_name:
                            print("      ⚠️ Could not find name on card. Skipping.")
                            continue

                        # 2. Smart Click & Verify
                        # Sometimes a click doesn't "take" (missed click, UI shift). 
                        # We retry the click if the name doesn't appear.
                        
                        max_click_attempts = 10 # Increased to 10 per user request
                        click_success = False
                        
                        for attempt in range(max_click_attempts):
                            try:
                                card.scroll_into_view_if_needed()
                                if attempt > 0:
                                    print(f"      🔄 Retry click attempt {attempt+1} for '{expected_name}'...")
                                    page.wait_for_timeout(1000)
                                else:
                                    page.wait_for_timeout(500)
                                
                                card.click(force=True)
                                print(f"  ... Clicked '{expected_name}' (Attempt {attempt+1}), verifying...")

                                # Short wait to see if it worked
                                quick_check_start = time.time()
                                matched = False
                                while time.time() - quick_check_start < 3: # 3s quick check
                                    # Check for Global H1 match
                                    name_el = page.query_selector('h1.DUwDvf')
                                    curr = name_el.inner_text() if name_el else ""
                                    
                                    if not curr:
                                         div_el = page.query_selector('div.fontHeadlineSmall')
                                         curr = div_el.inner_text() if div_el else ""
                                    
                                    if expected_name.lower().replace("'", "") in curr.lower().replace("'", ""):
                                        matched = True
                                        break
                                    page.wait_for_timeout(500)
                                
                                if matched:
                                    click_success = True
                                    break
                                # If not matched, loop continues -> clicks again
                                
                            except Exception as e:
                                print(f"      ⚠️ Click error: {e}")
                        
                        if not click_success:
                             print(f"      ❌ Failed to open details for '{expected_name}' after {max_click_attempts} clicks. Skipping.")
                             continue
                             
                        
                        print(f"      ✅ Details loaded for '{expected_name}'. Scraping...")
                        
                        # --- ENHANCED RELIABILITY: Wait for Name Sync ---
                        # We must ensure the Detail Panel matches the Clicked Item.
                        
                        found_name = False
                        name = "Unknown"
                        
                        try:
                            # Retry loop: Wait for valid Name to appear
                            start_time = time.time()
                            while time.time() - start_time < 10: # Wait up to 10 seconds for the CORRECT name
                                # 1. Try Global H1
                                name_el = page.query_selector('h1.DUwDvf')
                                current_text = ""
                                if name_el:
                                    current_text = name_el.inner_text().strip()
                                
                                # 2. Fallback: Title Div
                                if not current_text:
                                    name_div = page.query_selector('div.fontHeadlineSmall')
                                    if name_div:
                                         current_text = name_div.inner_text().strip()
                                
                                # 3. Fallback: Main H1
                                if not current_text:
                                    main_h1 = page.query_selector('h1')
                                    if main_h1:
                                        current_text = main_h1.inner_text().strip()

                                # CHECK MATCH
                                if current_text:
                                    # Fuzzy match: check if expected name is roughly in current text or vice versa
                                    exp_clean = expected_name.lower().replace("'", "").replace(".", "")
                                    curr_clean = current_text.lower().replace("'", "").replace(".", "")
                                    
                                    if exp_clean in curr_clean or curr_clean in exp_clean:
                                        name = current_text
                                        found_name = True
                                        break
                                
                                page.wait_for_timeout(1000)
                            
                        except Exception as e:
                            # If browser is closed, re-raise to exit the main loop safely
                            if "closed" in str(e) or "Target page" in str(e):
                                raise e 
                            print(f"      ⚠️ Error waiting for name sync: {e}")

                        if not found_name:
                            print(f"      ❌ Name Mismatch/Timeout. Scraper saw '{name}' but expected '{expected_name}'. Skipping to ensure quality.")
                            # Close panel if possible and continue
                            try:
                                close_btn = page.query_selector('button[aria-label="Close"]')
                                if close_btn: close_btn.click()
                            except: pass
                            continue # SKIP THIS ITEM to avoid saving false data
                            
                        # 3. After waiting for NAME, ensure other DETAILS are loaded (Address/Rating)
                        # This fixes the "First Item Empty" issue where name loads but details lag behind.
                        try:
                            page.wait_for_selector(
                                'button[data-item-id="address"], div.fontDisplayLarge, button[data-item-id^="phone:tel:"]', 
                                timeout=5000
                            )
                            # Small buffer strictly for rendering
                            page.wait_for_timeout(1000) 
                        except:
                            # It's possible some legit businesses don't have address/phone/rating.
                            # We just proceed if the NAME was verified.
                            pass
                        panel_selector = 'div.m6QErb'
                        panel = page.query_selector(panel_selector)
                        
                        # Fallback: if popup not found, check if main panel updated
                        if not panel:
                             main_h1 = page.query_selector('h1.DUwDvf')
                             if main_h1 and expected_name in main_h1.inner_text():
                                 print("      ... Using main page as panel.")
                                 panel = page
                             else:
                                 print(f"      ⚠️ Panel not found for '{expected_name}' after wait. Skipping.")
                                 continue
                        
                        # --- SCRAPE DETAILS (Name is already found above) ---
                        # We use 'name' from the sync block above.

                        # Get Address
                        address = "N/A"
                        # Use page instead of panel to avoid scoping issues with wrong m6QErb container
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
                            # Fallback scan of main text (still needs a valid container, try page locator?)
                            # This specific fallback is risky globally. Let's try a specific role=main if possible.
                            main_element = page.query_selector('div[role="main"][aria-label*="' + (expected_name or "") + '"]')
                            if not main_element:
                                 # Fallback: Just look for any div[role="main"] that IS NOT the feed
                                 mains = page.query_selector_all('div[role="main"]')
                                 for m in mains:
                                     if "Search result" not in (m.get_attribute("aria-label") or ""):
                                         main_element = m
                                         break
                            
                            if main_element:
                                main_content = main_element.inner_text()
                                for line in main_content.split('\n'):
                                    if any(c.isdigit() for c in line) and len(line) > 8 and ("+" in line or "-" in line):
                                        phone = line
                                        break
                        # --- 5. NEW: Reviews & Rating ---
                        rating = None
                        reviews = 0

                        # --- RATING ---
                        # Try selector for detailed review summary block
                        rating_el = page.query_selector('div.jANrlb > div.fontDisplayLarge')
                        if not rating_el:
                             rating_el = page.query_selector('div.fontDisplayLarge')
                        
                        if rating_el:
                            try:
                                rating = float(rating_el.inner_text())
                            except (ValueError, TypeError):
                                rating = None # Explicitly set to None on failure
                        
                        # --- REVIEWS ---
                        # Try selector for detailed review summary block
                        reviews_el = page.query_selector('button[jsaction*="reviewChart.moreReviews"] span')
                        if reviews_el:
                            try:
                                reviews_text = reviews_el.inner_text() # "61 reviews"
                                reviews_str = reviews_text.split(" ")[0].replace(",", "")
                                if 'K' in reviews_str.upper():
                                    reviews = int(float(reviews_str.upper().replace('K', '')) * 1000)
                                elif 'M' in reviews_str.upper():
                                    reviews = int(float(reviews_str.upper().replace('M', '')) * 1000000)
                                else:
                                    reviews = int(reviews_str)
                            except (ValueError, IndexError):
                                reviews = 0
                        
                        # --- 6. NEW: "Claim this Business" Status ---
                        # If this link exists, the profile is UNCLAIMED (High Value Lead)
                        is_claimed = True
                        # Look for the specific "Claim this business" text or link
                        claim_btn = page.query_selector('a[aria-label*="Claim this business"]')
                        if not claim_btn:
                            claim_text_el = page.query_selector("text=Claim this business")
                            if claim_text_el: is_claimed = False # Button exists, so it's NOT claimed
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

                        # --- NEW: Close the pop-up if it was used ---
                        if panel != page: # Only close if we used the pop-up panel
                            try:
                                close_button = panel.query_selector('button[aria-label="Close"]')
                                if close_button:
                                    close_button.click()
                                    page.wait_for_timeout(500) # Give it a moment to close
                                    # Optional: Wait for the panel to be hidden/removed
                                    # panel.wait_for_selector_state("detached", timeout=2000)
                            except Exception as close_e:
                                print(f"      ⚠️ Failed to close pop-up: {close_e}")
                                # Don't re-raise, continue with next item

                    except Exception as e:
                        print(f"      ❌ Failed item: {e}")
                        continue
                
                # Check constraints
                if total != -1 and valid_leads_count >= total:
                    break

        except Exception as e:
            print(f"❌ Critical Error: {e}")
        finally:
            browser.close()
            
    return results