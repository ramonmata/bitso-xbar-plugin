#!/usr/bin/env PYTHONIOENCODING=UTF-8 /usr/bin/python3

#
#  <xbar.title>Coin Market Data From Bitso</xbar.title>
#  <xbar.version>v1.0</xbar.version>
#  <xbar.author>Ramón Mata</xbar.author>
#  <xbar.author.github>ramonmata</xbar.author.github>
#  <xbar.desc>Displays Price Data from Bitso</xbar.desc>
#  <xbar.image>https://github.com/ramonmata/bitso-xbar-plugin/blob/main/docs/screen_shoot.jpg?raw=true</xbar.image>
#  <xbar.dependencies>python3</xbar.dependencies>
#  <xbar.abouturl>https://github.com/ramonmata/bitso-xbar-plugin</xbar.abouturl>
#
#  Preferences in the app:
#  <xbar.var>string(VAR_COIN_MARKET="btc_mxn"): The Bitso Market to display (btc_mxn, btc_usd, eth_mxn, etc)</xbar.var>
#  <xbar.var>number(VAR_COIN_INVESTMENT=0.00051407): How mucho crypto coin you own.</xbar.var>
#  <xbar.var>select(VAR_TALK="Yes"): Your Mac will speak to you when last price is close to high/low prices. [Yes, No]</xbar.var>
#  <xbar.var>number(VAR_HIGH_LIMIT_PERCENT=15): The % from high price to thet alerted. (e.g. If last price is 15% from low price then speak the alert)</xbar.var>
#  <xbar.var>string(VAR_CLOSE_TO_HIGH_ALERT="Coin is moving high!"): The message when coin is close to high limit % from highest price.</xbar.var>
#  <xbar.var>number(VAR_LOW_LIMIT_PERCENT=15): The % from low price to get alerted. (e.g. If last price is 15% from low price then speak the alert)</xbar.var>
#  <xbar.var>string(VAR_CLOSE_TO_LOW_ALERT="Coin is moving down!"): The message when coin is close to low limit % from lowest price.</xbar.var>

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import sqlite3
import os
import subprocess

def getPercentParameter(name) :
    p = 15
    try:
        p = int(os.getenv(name))
    except:
        p = 15
    return p

def norm (value, min, max) :
    return (value - min) / (max - min)

def lerp (norm, min, max) :
    return (max - min) * norm + min

def map (value, srcMin, srcMax, dstMin, dstMax) :
    return lerp(norm(value, srcMin, srcMax), dstMin, dstMax)

def convertDateToLocalDateTime(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%A, %d %B %Y, %I:%M %p")

# GET USER PREFERENCES FOR PLUGIN
COIN_MARKET = os.getenv('VAR_COIN_MARKET')
if COIN_MARKET is None:
    print('Configure with plugin browser!')
    quit()

COIN_NAME = COIN_MARKET.upper().split('_')[0]
MARKET_NAME = COIN_MARKET.upper().split('_')[1]
COIN_INVESTMENT = os.getenv('VAR_COIN_INVESTMENT')
TALK = os.getenv('VAR_TALK')
HIGH_LIMIT_PERCENT = getPercentParameter('VAR_HIGH_LIMIT_PERCENT')
CLOSE_TO_HIGH_ALERT = os.getenv('VAR_CLOSE_TO_HIGH_ALERT')
LOW_LIMIT_PERCENT = 100 - getPercentParameter('VAR_LOW_LIMIT_PERCENT')
CLOSE_TO_LOW_ALERT = os.getenv('VAR_CLOSE_TO_LOW_ALERT')
DARKMODE = os.getenv('XBARDarkMode')


# INIT DATABASE
con = sqlite3.connect(os.getenv('HOME') + '/.xbar_bitsodata.db')
cur = con.cursor()
schema = "CREATE TABLE IF NOT EXISTS bitsodata (CoinMarket TEXT PRIMARY KEY, LastDistanceFromHigh REAL NULL, LastHighPrice REAL NULL, LastLowPrice REAL NULL)"
cur.executescript(schema)

# REQUEST DATA
request = Request("https://api.bitso.com/v3/ticker/?book=" + COIN_MARKET, headers={'User-Agent': 'Mozilla/5.0'})
data = urlopen(request).read().decode('utf-8')
jsonData = json.loads(data)

status = jsonData['success']
payload = jsonData['payload']

lastPriceFloat = float(payload['last'])
highPriceFloat = float(payload['high'])
lowPriceFloat = float(payload['low'])
askPriceFloat = float(payload['ask'])
bidPriceFloat = float(payload['bid'])
volumePriceFloat = float(payload['volume'])
volumewapPriceFloat = float(payload['vwap'])
percentageLossFromMax = round(map(lastPriceFloat, lowPriceFloat, highPriceFloat, 100, 0))

# SPEAK ALERT
if TALK.upper() == "YES":
    cur.execute("select LastDistanceFromHigh, LastHighPrice, LastLowPrice from bitsodata where CoinMarket = ?", (COIN_MARKET,))
    row = cur.fetchone()
    if row:
        lastPercentageLossFromMax = row[0]
        lastHighPrice = row[1]
        lastLowPrice = row[2]
        cur.execute("update bitsodata set LastDistanceFromHigh = ?, LastHighPrice = ?, LastLowPrice = ? where CoinMarket = ?", (percentageLossFromMax, highPriceFloat, lowPriceFloat, COIN_MARKET))
        # Hande high price alerts
        if lastHighPrice and lastHighPrice < highPriceFloat:
            subprocess.call(['say', 'There is a new High Price!'])
        elif lastPercentageLossFromMax != percentageLossFromMax and percentageLossFromMax < lastPercentageLossFromMax and percentageLossFromMax <= HIGH_LIMIT_PERCENT : 
            subprocess.call(['say', CLOSE_TO_HIGH_ALERT])
        
        # Hande low price alerts
        if lastLowPrice and lastLowPrice > lowPriceFloat:
            subprocess.call(['say', 'There is a new Low Price!'])
        elif lastPercentageLossFromMax != percentageLossFromMax and percentageLossFromMax > lastPercentageLossFromMax and percentageLossFromMax >= LOW_LIMIT_PERCENT :
            subprocess.call(['say', CLOSE_TO_LOW_ALERT])
    else: # When no record, we init the database with a record with initial values
        lastPercentageLossFromMax = percentageLossFromMax
        cur.execute("insert into bitsodata (CoinMarket, LastDistanceFromHigh, LastHighPrice, LastLowPrice) VALUES (?,?,?,?)", (COIN_MARKET, percentageLossFromMax, highPriceFloat, lowPriceFloat))

# CLOSE DATABASE
con.commit()
con.close()

# CALCULATE COLOR FOR CURRENT PRICE
distanceColor = ""
if percentageLossFromMax<50 :
    rbColor = hex(round(map(percentageLossFromMax,0,49,0,228))).split('x')[1]
    if len(rbColor)== 1 : rbColor = '0' + rbColor
    distanceColor = "#{}FF{}".format(rbColor,rbColor)
elif percentageLossFromMax==50 :
    distanceColor = "#FFFFFF"
else :
    rbColor = hex(round(map(percentageLossFromMax,51,100,228,0))).split('x')[1]
    if len(rbColor)== 1 : rbColor = '0' + rbColor
    distanceColor = "#FF{}{}".format(rbColor,rbColor)

# OUTPUT
printColor = "#000000"
if DARKMODE == 'true' :
    printColor = "#FFFFFF"
    print("{} ${:,} {} | color={}".format(COIN_NAME, lastPriceFloat, MARKET_NAME, distanceColor))
else :
    print("{} ${:,} {}".format(COIN_NAME, lastPriceFloat, MARKET_NAME))
print('---')
print('My Investment')
print("{:,} {} | color={}".format(float(COIN_INVESTMENT), COIN_NAME, printColor))
print("${:,} {} | color={}".format(round(lastPriceFloat*float(COIN_INVESTMENT),2), MARKET_NAME, printColor))
print('---')
print('Last Price Distance')
print("Distance From High: {:.0%} | color={}".format(percentageLossFromMax/100, printColor))
print("Distance From Low: {:.0%} | color={}".format(1-percentageLossFromMax/100, printColor))
print('---')
print('Trading Data')
print("High: ${:,} {} | color=#0000ff".format(highPriceFloat, MARKET_NAME))
print("Low: ${:,} {} | color=#ff00ff".format(lowPriceFloat, MARKET_NAME))
print("Bid: ${:,} {} | color=#00ff00".format(bidPriceFloat, MARKET_NAME))
print("Ask: ${:,} {} | color=#ff0000".format(askPriceFloat, MARKET_NAME))
print("Spread: ${:,} {} | color={}".format(round(askPriceFloat-bidPriceFloat,2), MARKET_NAME, printColor))
print("Volume (24h): {:,} {} | color={}".format(round(volumePriceFloat,2), COIN_NAME, printColor))
print("Volume WAP: ${:,} {} | color={}".format(volumewapPriceFloat, MARKET_NAME, printColor))
print("{} | color={}".format(convertDateToLocalDateTime(payload['created_at']),printColor))
print('---')
print('Bitso')
print('-- Bitso Wallet | href=https://bitso.com/wallet')
print('-- Bitso Alpha | href=https://bitso.com/alpha/btc/mxn')
