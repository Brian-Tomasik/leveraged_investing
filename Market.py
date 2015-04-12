import random
import math

TRADING_DAYS_PER_YEAR = 252

class Market(object):
    """Parameters about the behavior of the stock market and interest rates"""

    def __init__(self, annual_mu, annual_sigma, annual_margin_interest_rate):
        self.annual_mu = annual_mu
        self.annual_sigma = annual_sigma
        self.annual_margin_interest_rate = annual_margin_interest_rate

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

    def random_daily_return(self):
        delta_t = 1.0/TRADING_DAYS_PER_YEAR
        return self.annual_sigma * random.gauss(0,1) * math.sqrt(delta_t) + self.annual_mu * delta_t #GBM for stock; for an example of this equation, see the first equation in section 7.1 of 'Path-dependence of Leveraged ETF returns', http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf; remember that yearly_sigma = daily_sigma * sqrt(252), so given that delta_t = 1/252, then daily_sigma = yearly_sigma * sqrt(delta_t)

    def present_value(self, amount, years_in_future):
        #return amount / (1+self.annual_mu)**years_in_future
        return amount * math.exp(- self.annual_mu * years_in_future) # use continuous interest like GBM model does