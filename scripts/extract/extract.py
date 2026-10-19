import requests


myToken = "MqYvWIaKCAWV7ExU3RFmRmuD8FaJBobWcGMDQfxidsw-vuykTHU"
url = f"https://api.pandascore.co/matches/upcoming"
headers = {"Authorization": myToken}
reponse = requests.get(url, headers=headers, timeout=10)


print(reponse.status_code)   
data = reponse.json()       
print(data["name"])