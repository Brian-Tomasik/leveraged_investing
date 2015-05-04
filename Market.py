import random
import math

class Market(object):
    """Parameters about the behavior of the stock market and interest rates"""

    def __init__(self, annual_mu=.054, annual_sigma=.22, annual_margin_interest_rate=.03,
                 inflation_rate=.03, use_VIX_data_for_volatility=False, 
                 medium_black_swan_prob=.004, annual_sigma_for_medium_black_swan=1.1,
                 large_black_swan_prob=.0001, 
                 annual_sigma_for_large_black_swan=4.1,
                 trading_days_per_year=252):
        self.annual_mu = annual_mu
        self.annual_sigma = annual_sigma
        self.annual_margin_interest_rate = annual_margin_interest_rate
        """Current margin interest rates are extremely low, such that Interactive Brokers
        offers ~1.5%. But interest rates in general are extremely low in 2015, and this
        isn't true historically: http://www.fedprimerate.com/libor/libor_rates_history.htm
        3% seems like a more reasonable average over the past 10-15 years. Long-run margin
        interest rates are what matter for long-run margin-investing plans. As a result,
        the default settings of this program will be overly conservative for short-term
        margin investing."""

        self.__inflation_rate = inflation_rate
        self.__use_VIX_data_for_volatility = use_VIX_data_for_volatility
        self.__VIX_data = None
        self.__num_days_VIX_data = 0
        self.__medium_black_swan_prob = medium_black_swan_prob
        self.__annual_sigma_for_medium_black_swan = annual_sigma_for_medium_black_swan
        self.__large_black_swan_prob = large_black_swan_prob
        self.__annual_sigma_for_large_black_swan = annual_sigma_for_large_black_swan
        self.__trading_days_per_year = trading_days_per_year

        # Get VIX data if needed
        if self.__use_VIX_data_for_volatility:
            self.read_VIX_data()
            self.__num_days_VIX_data = len(self.__VIX_data)

    @property
    def annual_mu(self):
        return self.__annual_mu

    @annual_mu.setter
    def annual_mu(self, val):
        self.__annual_mu = val

    @property
    def annual_sigma(self):
        return self.__annual_sigma

    @annual_sigma.setter
    def annual_sigma(self, val):
        self.__annual_sigma = val

    @property
    def annual_margin_interest_rate(self):
        return self.__annual_margin_interest_rate

    @annual_margin_interest_rate.setter
    def annual_margin_interest_rate(self, val):
        self.__annual_margin_interest_rate = val

    @property
    def inflation_rate(self):
        return self.__inflation_rate

    @property
    def use_VIX_data_for_volatility(self):
        return self.__use_VIX_data_for_volatility

    @property
    def medium_black_swan_prob(self):
        return self.__medium_black_swan_prob

    @property
    def annual_sigma_for_medium_black_swan(self):
        return self.__annual_sigma_for_medium_black_swan

    @property
    def large_black_swan_prob(self):
        return self.__large_black_swan_prob

    @property
    def annual_sigma_for_large_black_swan(self):
        return self.__annual_sigma_for_large_black_swan

    @property
    def trading_days_per_year(self):
        return self.__trading_days_per_year

    def read_VIX_data(self):
        """Read in daily VIX prices, which I took from 
        http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv ,
        which is linked from http://www.cboe.com/micro/vix/historical.aspx , 
        on 12 Apr 2015"""
        with open("vix_close_2Jan2004_to_10Apr2015.txt", "r") as data:
            self.__VIX_data = [float(price.strip())/100 for price in data.readlines()]

    def random_daily_return(self, day, randgenerator, num_times_randgenerator_was_called):
        delta_t = 1.0/self.__trading_days_per_year
        if self.__use_VIX_data_for_volatility:
            sigma_to_use = self.__VIX_data[day % self.__num_days_VIX_data]
            """ ^ Cycle through the VIX data in order, repeating after we hit the end"""
        else:
            sigma_to_use = self.annual_sigma
        mu_to_use = self.annual_mu

        # See if we have black swans
        rand_float = randgenerator.random() if randgenerator else random.random()
        if randgenerator:
            num_times_randgenerator_was_called += 1
        if rand_float < self.__large_black_swan_prob:
            sigma_to_use = self.__annual_sigma_for_large_black_swan
            mu_to_use = 0
        elif rand_float < (self.__large_black_swan_prob + self.__medium_black_swan_prob):
            sigma_to_use = self.__annual_sigma_for_medium_black_swan
            mu_to_use = 0

        randgauss = randgenerator.gauss(0,1) if randgenerator else random.gauss(0,1)
        if randgenerator:
            num_times_randgenerator_was_called += 1
        return (sigma_to_use * randgauss * math.sqrt(delta_t) + mu_to_use * delta_t, \
            num_times_randgenerator_was_called)
        """
        The above is a GBM for stock; for an example of this equation, see the first equation 
        in section 7.1 of 'Path-dependence of Leveraged ETF returns', 
        http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf; 
        remember that yearly_sigma = daily_sigma * sqrt(252), so given that 
        delta_t = 1/252, then daily_sigma = yearly_sigma * sqrt(delta_t)
        """

    def real_present_value(self, amount, years_in_future):
        #return amount / (1+self.annual_mu)**years_in_future
        return amount * math.exp(- self.annual_mu * years_in_future) / (1+self.__inflation_rate)**years_in_future # use continuous interest for discounting like GBM model does