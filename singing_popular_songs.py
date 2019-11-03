import requests
from bs4 import BeautifulSoup

response = requests.get("http://www.ikaraoke.kr/isong/hit_song_monthly.asp")
html = response.text
soup = BeautifulSoup(html, 'html.parser')
title_soup = soup.select('td > a')
popular_songs = []
for t in title_soup[:52]:
    if t.text:
        try:
            popular_songs.append(t['title'])
        except KeyError:
            popular_songs.append(t.text.strip())
popular_songs = [popular_songs[i:i+2] for i in range(0, len(popular_songs), 2)]
print(popular_songs)
