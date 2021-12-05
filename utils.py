from datetime import datetime

def hex_to_rgb(hex):
  rgb = []
  for i in (0, 2, 4):
    decimal = int(hex[i:i+2], 16)
    rgb.append(decimal)

  return tuple(rgb)

def period_of_day():
    now = datetime.now()
    if now.hour < 11:
        return 'morning'
    elif now.hour in [12, 13]:
        return 'noon'
    elif now.hour < 18:
        return 'afternoon'
    return 'evening'

def hasPhrase(phrases = [], text = ''):
    return any([phrase for phrase in phrases if phrase.lower() in text.lower() ])
