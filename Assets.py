import smtplib
import mysql.connector
import requests
import pandas as pd
#import talib as ta
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Database Handler Class
class BitcoinPriceDatabase:
    def __init__(self):
        username, password, database = self.getCredentials()
        self.db = mysql.connector.connect(user=username, password=password,
                                          host='127.0.0.1', database=database, auth_plugin='mysql_native_password')
        self.cursor = self.db.cursor()

    def getCredentials(self):
        with open('DBcredentials.txt') as f:
            lines = f.readlines()
            username = lines[0].strip()
            password = lines[1].strip()
            database = lines[2].strip()
        return username, password, database

    def save_bitcoin_price(self, price, timestamp):
        """Save Bitcoin price to database"""
        query = "INSERT INTO bitcoin_prices (price, timestamp) VALUES (%s, %s)"
        self.cursor.execute(query, (price, timestamp))
        self.db.commit()

    def get_data_for_period(self, start_time, end_time):
        """Fetch price data for a specific period"""
        query = "SELECT price, timestamp FROM bitcoin_prices WHERE timestamp BETWEEN %s AND %s"
        self.cursor.execute(query, (start_time, end_time))
        return self.cursor.fetchall()

    def get_ohlc_for_period(self, period='1D'):
        """Calculate OHLC (Open, High, Low, Close) for the given period"""
        if period == '1D':
            query = "SELECT price, timestamp FROM bitcoin_prices WHERE timestamp >= CURDATE()"
        data = self.get_data_for_period('2024-01-01', '2024-12-31')
        df = pd.DataFrame(data, columns=['price', 'timestamp'])
        
        # Calculate OHLC values
        open_price = df.iloc[0]['price']
        high_price = df['price'].max()
        low_price = df['price'].min()
        close_price = df.iloc[-1]['price']
        
        return {'open': open_price, 'high': high_price, 'low': low_price, 'close': close_price}

# Bitcoin Price Fetcher Class
class BitcoinPriceFetcher:
    def __init__(self):
        self.url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"
    
    def get_current_price(self):
        """Fetch the current Bitcoin price"""
        response = requests.get(self.url)
        data = response.json()
        price = data['bpi']['USD']['rate_float']
        return price

# Email Alerts Class with Rate Limiting
class RateLimitedAlerts:
    def __init__(self, throttle_time=300):
        self.throttle_time = throttle_time  # Default throttle time of 5 minutes
        self.last_alert_time = None

    def send_alert(self, recipient_email, subject, message):
        """Send an email alert with a specified subject and message"""
        current_time = datetime.now()
        if self.last_alert_time and (current_time - self.last_alert_time).seconds < self.throttle_time:
            print(f"Alert throttled. Next alert can be sent after {self.throttle_time - (current_time - self.last_alert_time).seconds} seconds.")
            return
        
        self.last_alert_time = current_time
        sender_email = "your_email@gmail.com"
        password = "your_email_password"
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print("Alert sent!")

# Bitcoin Trend Analyzer Class
class BitcoinTrendAnalyzer:
    def __init__(self, db_handler, fetcher):
        self.db_handler = db_handler
        self.fetcher = fetcher
        self.alert_system = RateLimitedAlerts()

    def get_advanced_trend(self, period='1H'):
        """Get advanced trend analysis including MACD and other indicators"""
        trend, prices = self.get_trend(period)
        df = pd.DataFrame(prices, columns=['price'])
        
        # Calculate MACD and other indicators
        df['MACD'], df['Signal'], df['Hist'] = ta.MACD(df['price'], fastperiod=12, slowperiod=26, signalperiod=9)
        return df

    def send_trend_alert(self, recipient_email, period='1H'):
        """Send an alert when MACD crosses Signal Line"""
        df = self.get_advanced_trend(period)
        # Trigger an alert when MACD crosses Signal
        if df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
            message = f"Bitcoin MACD Bullish Signal for {period}!"
            self.alert_system.send_alert(recipient_email, f"Bitcoin MACD Bullish Signal {period}", message)
        elif df['MACD'].iloc[-1] < df['Signal'].iloc[-1]:
            message = f"Bitcoin MACD Bearish Signal for {period}!"
            self.alert_system.send_alert(recipient_email, f"Bitcoin MACD Bearish Signal {period}", message)

# Backtesting Class
class Backtesting:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def run_backtest(self, strategy):
        """Run backtest for the provided strategy"""
        data = self.db_handler.get_data_for_period('2024-01-01', '2024-12-31')
        df = pd.DataFrame(data, columns=['price', 'timestamp'])
        signals = strategy(df)
        return signals

# Bitcoin System Class
class BitcoinSystem:
    def __init__(self):
        self.db_handler = BitcoinPriceDatabase()
        self.fetcher = BitcoinPriceFetcher()
        self.trend_analyzer = BitcoinTrendAnalyzer(self.db_handler, self.fetcher)
        self.alert_system = RateLimitedAlerts()

    def run(self):
        """Run the Bitcoin system: Fetch price, save to DB, and check for alerts"""
        current_price = self.fetcher.get_current_price()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.db_handler.save_bitcoin_price(current_price, timestamp)
        
        print(f"Current Bitcoin price: {current_price}")
        
        # Check for new all-time high or low alerts
        self.check_for_all_time_high(current_price)
        
        # Generate and send trend alerts
        self.trend_analyzer.send_trend_alert('abc@hotmail.com', '1H')
        
    def check_for_all_time_high(self, current_price):
        """Check if the price hits a new all-time high"""
        query = "SELECT MAX(price) FROM bitcoin_prices"
        self.db_handler.cursor.execute(query)
        all_time_high = self.db_handler.cursor.fetchone()[0]

        if current_price > all_time_high:
            self.alert_system.send_alert('abc@hotmail.com', "New All-Time High", f"Bitcoin price has reached a new all-time high: {current_price}")

    def generate_trend_chart(self, period='1D'):
        """Generate trend chart with technical indicators like MACD"""
        df = self.trend_analyzer.get_advanced_trend(period)
        # Simple example of plotting the price with MACD
        df[['price', 'MACD', 'Signal']].plot(title=f"Bitcoin {period} Trend")
        
# Main System Execution
if __name__ == "__main__":
    bitcoin_system = BitcoinSystem()
    bitcoin_system.run()
    bitcoin_system.generate_trend_chart('1D')
