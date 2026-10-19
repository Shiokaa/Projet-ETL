import requests

from config import headers, url

def test():
    requestUrl = f"{url}/tournaments"
    reponse = requests.get(requestUrl, headers=headers, timeout=10)

    data = reponse.json()
    print(data)
