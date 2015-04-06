class InvestmentComparison:

    def __init__(self, years_held, trading_days_per_year, annual_mu, annual_sigma, 
                 leverage_ratio, initial_value, annual_leverage_interest_rate, 
                 annual_leverage_expense_ratio):
        self.years_held = years_held
        self.trading_days_per_year = trading_days_per_year
        self.annual_mu = annual_mu
        self.annual_sigma = annual_sigma
        self.leverage_ratio = leverage_ratio
        self.initial_value = initial_value
        self.annual_leverage_interest_rate = annual_leverage_interest_rate
        self.annual_leverage_expense_ratio = annual_leverage_expense_ratio

    @property
    def years_held(self):
        return self.__years_held

    @years_held.setter
    def years_held(self, val):
        self.__years_held = val

    @property
    def trading_days_per_year(self):
        return self.__trading_days_per_year

    @trading_days_per_year.setter
    def trading_days_per_year(self, val):
        self.__trading_days_per_year = val

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
    def leverage_ratio(self):
        return self.__leverage_ratio

    @leverage_ratio.setter
    def leverage_ratio(self, val):
        self.__leverage_ratio = val

    @property
    def initial_value(self):
        return self.__initial_value

    @initial_value.setter
    def initial_value(self, val):
        self.__initial_value = val

    @property
    def annual_leverage_interest_rate(self):
        return self.__annual_leverage_interest_rate

    @annual_leverage_interest_rate.setter
    def annual_leverage_interest_rate(self, val):
        self.__annual_leverage_interest_rate = val

    @property
    def annual_leverage_expense_ratio(self):
        return self.__annual_leverage_expense_ratio

    @annual_leverage_expense_ratio.setter
    def annual_leverage_expense_ratio(self, val):
        self.__annual_leverage_expense_ratio = val