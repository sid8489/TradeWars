import numpy as np

def generate_stock_time_series(initial_price, duration_seconds):
    """Generates a semi-realistic stock price time series."""
    dt = 1  # Time step (1 second)
    num_steps = duration_seconds
    mu = 0.001  # Drift (small upward trend)
    sigma = 0.02  # Volatility (adjust for desired fluctuation)
    price = initial_price
    prices = [price]
    for _ in range(num_steps):
        drift = mu * price * dt
        shock = sigma * price * np.random.normal()
        price += drift + shock
        prices.append(price)
    return prices

