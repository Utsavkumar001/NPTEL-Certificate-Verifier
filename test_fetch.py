import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://nptel.ac.in/noc/E_Certificate/NOC26EE30S86240151404337710",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

url = "https://archive.nptel.ac.in/certificate.php?cert_num=NOC26EE30S86240151404337710"
resp = requests.get(url, headers=HEADERS, allow_redirects=True)
print("Final URL:", resp.url)
print("Status:", resp.status_code)
print("---HTML CONTENT---")
print(resp.text[:3000])