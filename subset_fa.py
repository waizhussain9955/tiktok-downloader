import os
import re

head_replacement = """
    <!-- Fonts & Icons (Optimized) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preload" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
    <noscript>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap">
    </noscript>
"""

fa_css = """
@font-face {
    font-family: 'Font Awesome 6 Free';
    font-style: normal;
    font-weight: 900;
    font-display: swap;
    src: url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2') format('woff2');
}
@font-face {
    font-family: 'Font Awesome 6 Brands';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2') format('woff2');
}
.fas, .fab, .fa-brands, .fa-solid {
    -moz-osx-font-smoothing: grayscale;
    -webkit-font-smoothing: antialiased;
    display: inline-block;
    font-style: normal;
    font-variant: normal;
    text-rendering: auto;
    line-height: 1;
}
.fa-brands { font-family: 'Font Awesome 6 Brands'; font-weight: 400; }
.fas, .fa-solid { font-family: 'Font Awesome 6 Free'; font-weight: 900; }
.fa-tiktok:before{content:"\\e07b"}
.fa-moon:before{content:"\\f186"}
.fa-sun:before{content:"\\f185"}
.fa-link:before{content:"\\f0c1"}
.fa-paste:before{content:"\\f0ea"}
.fa-play:before{content:"\\f04b"}
.fa-heart:before{content:"\\f004"}
.fa-share:before{content:"\\f064"}
.fa-download:before{content:"\\f019"}
.fa-facebook:before{content:"\\f39e"}
.fa-instagram:before{content:"\\f16d"}
.fa-x-twitter:before{content:"\\e61b"}
.fa-youtube:before{content:"\\f167"}
.fa-linkedin:before{content:"\\f08c"}
.fa-whatsapp:before{content:"\\f232"}
.fa-magic:before{content:"\\f0d0"}
.fa-hand-holding-heart:before{content:"\\f4be"}
.fa-video:before{content:"\\f03d"}
.fa-shield-halved:before{content:"\\f3ed"}
.fa-chevron-down:before{content:"\\f078"}
"""

files = [f for f in os.listdir(".") if f.endswith(".html")]

for filename in files:
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Update font loads in head
    content = re.sub(r'<!-- Fonts & Icons.*?-->', head_replacement, content, flags=re.DOTALL)
    content = re.sub(r'<link rel="preload" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome.*?>', '', content)
    content = re.sub(r'<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome.*?>', '', content)
    # Be careful with closing tag of noscript if it contains FontAwesome
    content = re.sub(r'<noscript>.*?font-awesome.*?</noscript>', '', content, flags=re.DOTALL)

    # 2. Add minimal FA CSS to the inlined <style> block
    if "<style>" in content:
        # Find the end of the existing @font-face or beginning of :root
        content = content.replace("<style>", "<style>" + fa_css)
    
    # Clean up redundant font-face definitions I added earlier
    content = re.sub(r'/\* Font Display Swap for Icons \*/.*?}:root', ':root', content, flags=re.DOTALL)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

print("Minimal FontAwesome inline optimization complete")
