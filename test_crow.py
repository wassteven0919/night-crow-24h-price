from flask import Flask, render_template_string
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates
import io
import base64

app = Flask(__name__)

# API URL
url = 'https://api.wemixplay.com/info/v2/price-chart?symbol=CROW&range=1d'

def fetch_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

def parse_data(data):
    if not data or data['Result'] != 0:
        print("Error in data")
        return [], []
    
    chart = data['data']['chart']
    times = [datetime.fromtimestamp(point['t']) for point in chart]
    prices = [point['p'] for point in chart]
    
    return times, prices

def create_plot(times, prices):
    plt.figure(figsize=(10, 6))

    # Threshold price for color change
    threshold = 0.75

    # Loop through prices and plot segments according to whether they're above or below threshold
    for i in range(1, len(prices)):
        if prices[i-1] < threshold and prices[i] < threshold:
            # Both previous and current price below threshold, plot in red
            plt.plot(times[i-1:i+1], prices[i-1:i+1], color='red', linestyle='-')
        elif prices[i-1] >= threshold and prices[i] >= threshold:
            # Both previous and current price above threshold, plot in green
            plt.plot(times[i-1:i+1], prices[i-1:i+1], color='green', linestyle='-')
        else:
            # If the price crosses the threshold, calculate where it crosses
            crossing_time = times[i-1] + (times[i] - times[i-1]) * (threshold - prices[i-1]) / (prices[i] - prices[i-1])
            # Plot the segment below the threshold
            plt.plot([times[i-1], crossing_time], [prices[i-1], threshold], color='red', linestyle='-')
            # Plot the segment above the threshold
            plt.plot([crossing_time, times[i]], [threshold, prices[i]], color='green', linestyle='-')

    plt.title('CROW Price Chart')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.gcf().autofmt_xdate()  # Rotate date labels
    plt.grid(True)

    # Save plot to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()

    return img_base64





def calculate_average(prices):
    if len(prices) == 0:
        return 0
    return sum(prices) / len(prices)

def check_average_price(prices, threshold=0.75):
    average_price = calculate_average(prices)
    return average_price >= threshold, average_price

@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

@app.route('/')
def index():
    data = fetch_data(url)
    times, prices = parse_data(data)
    
    if not times or not prices:
        return "Error fetching or parsing data."
    
    img_base64 = create_plot(times, prices)
    threshold_exceeded, average_price = check_average_price(prices)
    notification_message = ''
    
    if threshold_exceeded:
        notification_message = 'Alert: The average price has reached or exceeded 0.75!'
    
    # HTML template for displaying the chart and notifications
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Virtual Currency Price Chart</title>
        <script>
            // Function to reload the page every 5 minutes
            function autoRefresh() {
                setInterval(function(){
                    window.location.reload();
                }, 1000);  // second
            }
            window.onload = autoRefresh;
        </script>
    </head>
    <body>
        <h1>CROW Price Chart</h1>
        <img src="data:image/png;base64,{{ img_base64 }}" alt="Price Chart">
        <h2>{{ notification_message }}</h2>
        <p><strong>24-Hour Average Price:</strong> {{ average_price }}</p>
    </body>
    </html>
    '''
    
    return render_template_string(html_template, img_base64=img_base64, notification_message=notification_message, average_price=f'{average_price:.7f}')

def run_server():
    app.run(port=1234)

if __name__ == "__main__":
    run_server()