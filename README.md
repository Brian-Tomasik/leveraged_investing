Simulations of leveraged investing vs. non-leveraged. For further explanation, see http://reducing-suffering.org/should-altruists-leverage-investments/

The version of Python I used was:
Python 2.7.6 (default, Nov 10 2013, 19:24:18) [MSC v.1500 32 bit (Intel)] on win32

# Margin simulations

To do margin-investing simulations, run "margin_leverage.py". You can edit the section at the bottom to choose how to run different variations. Note that if you set approx_num_simultaneous_processes too high, the program will use 100% of your CPU and make other applications slower because I haven't yet figured out a cross-platform way to reduce the priority of the processes that get created.

To generate the HTML and corresponding images of my essay about leverage, run "write_essay.py". If you already have data generated from a previous round, you can set DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP to its timestamp to avoid recomputing the results.

A run of a single variant of the simulation with 1000 random samples of 30-year investing takes 1-2 hours on my laptop. A lot of the computational cost seems to come from my use of big lists of individual ETF lots rather than pooling the investor's equity into one big "assets" variable. The reason I suspect this is that the simulation slowed down many times when I added full histories of ETF purchases. Using full histories of ETF purchases allows for proper accounting of capital gains for taxes.

# Leveraged-ETF simulations

New version: "leveraged_etf_returns.py"

Old version: "oldversion_leveraged_etf_returns.py"
