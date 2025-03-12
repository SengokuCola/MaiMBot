import requests
response = requests.post("http://localhost:8080/api/reload-config")
print(response.json())