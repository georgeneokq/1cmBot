import matplotlib.pyplot as plt
from oneinch_api import OneInchAPI
from datetime import datetime
from io import BytesIO


def generate_chart(chain_id, token0, token1):
    oneinch = OneInchAPI()
    chart_data = oneinch.get_historical_chart_data(chain_id, token0, token1)  # "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "0xDC3326e71D45186F113a2F448984CA0e8D201995")
    chart_data = chart_data["data"]
    times = [datetime.utcfromtimestamp(entry['time']) for entry in chart_data]
    values = [entry['value'] for entry in chart_data]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(times, values, marker='o', linestyle='-', color='b')

    # Formatting the plot
    plt.title('TOKEN0/TOKEN1')
    plt.xlabel('Time (UTC)')
    plt.ylabel('Price')
    plt.grid(True)

    # Rotate the x-axis labels for better readability
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt_file = BytesIO()
    fig = plot.get_figure()
    fig.savefig(plt_file, format=png)
    plt_file.seek(0)

    return plt_file


