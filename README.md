Simulations of leveraged investing vs. non-leveraged. For further explanation, see http://reducing-suffering.org/why-and-how-to-leverage-investments/

# Margin simulations

To dp margin-investing simulations, run "margin_leverage.py" You can edit the section at the bottom to choose how to run different variations. Note that if you set use_multiprocessing=True, the program will use 100% of your CPU and make other applications slower because I haven't yet figured out a cross-platform way to reduce the priority of the processes that get created.

A run of a single variant of the simulation with 1000 random samples of 30-year investing takes 1-2 hours on my laptop. A lot of the computational cost seems to come from my use of big lists of individual ETF lots rather than pooling the investor's equity into one big "assets" variable. The reason I suspect this is that the simulation slowed down many times when I added full histories of ETF purchases. Using full histories of ETF purchases allows for proper accounting of capital gains for taxes.

# Leveraged-ETF simulations

Run "simulate_leveraged_etf.py"
