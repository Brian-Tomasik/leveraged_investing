class Investor(object):
    """Store parameters about how an investor behaves"""

    def __init__(self, years_until_retirement, initial_annual_income_for_investing, 
                 annual_income_growth_percent, match_percent_from_401k):
        self.years_until_retirement = years_until_retirement
        self.initial_annual_income_for_investing = initial_annual_income_for_investing
        self.annual_income_growth_percent = annual_income_growth_percent
        self.match_percent_from_401k = match_percent_from_401k

    @property
    def years_until_retirement(self):
        return self.__years_until_retirement

    @years_until_retirement.setter
    def years_until_retirement(self, val):
        self.__years_until_retirement = val

    @property
    def initial_annual_income_for_investing(self):
        return self.__initial_annual_income_for_investing

    @initial_annual_income_for_investing.setter
    def initial_annual_income_for_investing(self, val):
        self.__initial_annual_income_for_investing = val

    @property
    def annual_income_growth_percent(self):
        return self.__annual_income_growth_percent

    @annual_income_growth_percent.setter
    def annual_income_growth_percent(self, val):
        self.__annual_income_growth_percent = val

    @property
    def match_percent_from_401k(self):
        return self.__match_percent_from_401k

    @match_percent_from_401k.setter
    def match_percent_from_401k(self, val):
        self.__match_percent_from_401k = val

    def current_annual_income(self, years_elapsed):
        return self.initial_annual_income_for_investing * (1+self.annual_income_growth_percent/100.0)**years_elapsed