import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
import io
import os
import re

# Your Bot Token
BOT_TOKEN = "7998836245:AAEpOJa601PsgXjrdCU0kCuwC715gvvNI94"

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('नमस्ते! मुझे एक HTML फाइल भेजें, और मैं उससे Videos, PDFs और Other links अलग-अलग extract करके एक HTML फाइल में भेजूंगा।')

# HTML parsing
def parse_html_content(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        results = {"videos": [], "pdfs": [], "others": []}

        # Videos
        videos_div = soup.find('div', id='videos')
        if videos_div:
            video_links = videos_div.find_all('a', href=True)
            for link in video_links:
                url = link.get('href', '')
                title = link.get_text(strip=True)
                if title and url and url != '#' and link.get('target') == '_blank':
                    results["videos"].append({"title": title, "url": url})
                elif url == '#' and 'onclick' in link.attrs:
                    onclick = link.get('onclick', '')
                    match = re.search(r"playVideo\('([^']+)'\)", onclick)
                    if match and title:
                        video_url = match.group(1)
                        results["videos"].append({"title": title, "url": video_url})

        # PDFs
        pdfs_div = soup.find('div', id='pdfs')
        if pdfs_div:
            pdf_links = pdfs_div.find_all('a', href=lambda value: value and value.endswith('.pdf'), target="_blank")
            for link in pdf_links:
                url = link.get('href', '')
                title = link.get_text(strip=True)
                if title and "download" not in title.lower() and "📥" not in title:
                    results["pdfs"].append({"title": title, "url": url})

        # Others
        others_div = soup.find('div', id='others')
        if others_div:
            other_links = others_div.find_all('a', href=True, target="_blank")
            for link in other_links:
                url = link.get('href', '')
                title = link.get_text(strip=True)
                if title and url:
                    results["others"].append({"title": title, "url": url})

        return results

    except Exception as e:
        logging.error(f"HTML parsing error: {e}")
        return None

# Generate HTML in memory
def generate_html_output(extracted_data, header_text):
    try:
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{header_text} - Extracted Links</title>
<style>
:root {{ --bg:#111; --card:#0b1225; --accent:#facc15; --text:#e5e7eb; }}
html,body {{ margin:0; padding:0; height:100%; font-family:'Poppins',sans-serif; background:var(--bg); color:var(--text); overflow-x:hidden; }}
.header {{ background:var(--accent); color:#111; padding:15px; font-size:22px; font-weight:bold; text-align:center; }}
.search-bar input {{ width:100%; padding:10px; border-radius:10px; border:none; font-size:16px; background: var(--card); color: var(--text); margin:10px 0; }}
.container {{ display:flex; justify-content:space-around; margin:10px; gap:5px; flex-wrap:wrap; }}
.tab {{ background: var(--accent); padding:8px 12px; border-radius:20px; cursor:pointer; font-weight:bold; color:#111; text-align:center; flex:1 1 auto; min-width:80px; box-sizing:border-box; }}
.content-wrapper {{ padding:0 10px 10px 10px; }}
.content {{ display:none; }}
.content h2 {{ color: var(--accent); margin-top:10px; }}
.video-list, .pdf-list, .other-list {{ display:flex; flex-direction:column; gap:10px; }}
.video-item {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
.video-link, .pdf-link, .other-link {{ flex:1; padding:10px 12px; border-radius:8px; background: var(--card); color: var(--text); text-decoration:none; word-break:break-word; }}
.video-link:hover, .pdf-link:hover, .other-link:hover {{ background: var(--accent); color:#111; }}
.download-btn {{ background: rgba(0,0,0,0.3); border:none; color: var(--text); cursor:pointer; padding:8px 10px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:12px; white-space:nowrap; height:fit-content; flex-shrink:0; }}
.download-btn:hover {{ color:#111; background-color: var(--accent); }}
.toast {{ position:fixed; bottom:20px; left:50%; transform:translateX(-50%); background-color: var(--accent); color:#111; padding:10px 20px; border-radius:5px; font-weight:bold; opacity:0; transition:opacity 0.3s; z-index:1000; }}
.toast.show {{ opacity:1; }}
</style>
</head>
<body>
<div class="header">{header_text}</div>
<div class="search-bar"><input type="text" id="searchInput" placeholder="🔍 Search here..." oninput="filterContent()"></div>
<div id="noResults" class="no-results">No results found.</div>
<div class="container">
<div class="tab" onclick="showContent('videos')">🎥 Videos</div>
<div class="tab" onclick="showContent('pdfs')">📑 PDFs</div>
<div class="tab" onclick="showContent('others')">📦 Others</div>
</div>
<div class="content-wrapper">
<div id="videos" class="content"><h2>All Video Lectures</h2><div class="video-list">"""
        
        # Add video items
        for item in extracted_data["videos"]:
            html_content += f'\n<div class="video-item"><a href="{item["url"]}" target="_blank" class="video-link">{item["title"]}</a><button class="download-btn" onclick="handleDownload(\'{item["url"]}\')">⬇️ Download</button></div>'
        
        html_content += "</div></div><div id='pdfs' class='content'><h2>All PDFs</h2><div class='pdf-list'>"
        
        # Add PDF items
        for item in extracted_data["pdfs"]:
            html_content += f'\n<a href="{item["url"]}" target="_blank" class="pdf-link">{item["title"]}</a>'
        
        html_content += "</div></div><div id='others' class='content'><h2>Other Resources</h2><div class='other-list'>"
        
        # Add other items
        for item in extracted_data["others"]:
            html_content += f'\n<a href="{item["url"]}" target="_blank" class="other-link">{item["title"]}</a>'
        
        html_content += """</div></div></div>
<div id="toast" class="toast">Opening in IDM...</div>
<script>
function showContent(tabName){const sections=document.querySelectorAll('.content');sections.forEach(sec=>sec.style.display='none');document.getElementById(tabName).style.display='block';filterContent();}
function filterContent(){const searchTerm=document.getElementById('searchInput').value.toLowerCase();const activeTab=document.querySelector('.content[style*="block"]');if(!activeTab)return;const items=activeTab.querySelectorAll(".video-item, .pdf-list a, .other-list a");let found=false;items.forEach(item=>{const textContent=item.textContent.toLowerCase();if(textContent.includes(searchTerm)){item.style.display=item.classList.contains('video-item')?"flex":"block";found=true;}else{item.style.display='none';}});document.getElementById("noResults").style.display=found?"none":"block";}
function handleDownload(videoUrl){openInIDM(videoUrl);}
function openInIDM(videoUrl){showToast();const intentUrl=`intent://${videoUrl.replace(/https?:\\/\\//,'')}#Intent;scheme=https;action=android.intent.action.VIEW;end`;[()=>{window.location.href=intentUrl;},()=>{const iframe=document.createElement('iframe');iframe.style.display='none';iframe.src=intentUrl;document.body.appendChild(iframe);setTimeout(()=>document.body.removeChild(iframe),100);},()=>{window.open(intentUrl,'_system');}].forEach(fn=>{try{fn();}catch(e){console.error(e);}});}
function showToast(){const toast=document.getElementById('toast');toast.classList.add('show');setTimeout(()=>{toast.classList.remove('show');},3000);}
document.addEventListener("DOMContentLoaded",()=>{showContent("videos");});
</script>
</body>
</html>"""
        return html_content.encode('utf-8')  # return as bytes
    except Exception as e:
        logging.error(f"HTML output generation error: {e}")
        return None

# Memory-based document handler
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        document = update.message.document
        
        # Check if the file is HTML
        if document.mime_type != 'text/html' and not document.file_name.endswith('.html'):
            await update.message.reply_text('कृपया सिर्फ HTML फाइलें (.html) भेजें।')
            return

        await update.message.reply_text('HTML फाइल मिली! Links extract कर रहा हूँ...')

        # Download the file
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        html_content = file_bytes.decode('utf-8')
        
        # Parse the HTML content
        extracted_data = parse_html_content(html_content)
        original_filename = document.file_name
        header_text = os.path.splitext(original_filename)[0]

        if extracted_data:
            html_bytes = generate_html_output(extracted_data, header_text)
            if html_bytes:
                # Send the processed file back
                output_filename = f"processed_{original_filename}"
                await update.message.reply_document(
                    document=io.BytesIO(html_bytes),
                    filename=output_filename,
                    caption="यहाँ आपके extract किए गए लिंक्स हैं!"
                )
            else:
                await update.message.reply_text('HTML output file बनाने में error आई।')
        else:
            await update.message.reply_text('फाइल को parse करने में error आई। कोई डेटा नहीं मिला।')
            
    except Exception as e:
        logging.error(f"Error handling document: {e}")
        await update.message.reply_text('फाइल प्रोसेस करते समय एक error आई।')

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text('Sorry, कुछ error आ गया है।')

# Main function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_error_handler(error_handler)

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()