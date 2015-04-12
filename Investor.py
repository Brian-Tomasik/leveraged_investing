class Investor(object):
    """Store parameters about how an investor behaves"""

    def __init__(self, years_until_donate, initial_annual_income_for_investing, 
                 annual_income_growth_percent, match_percent_from_401k,
                 short_term_cap_gains_rate, long_term_cap_gains_rate,
                 pay_principal_throughout, max_margin_to_assets_ratio):
        self.years_until_donate = years_until_donate
        self.initial_annual_income_for_investing = initial_annual_income_for_investing
        self.annual_income_growth_percent = annual_income_growth_percent
        self.match_percent_from_401k = match_percent_from_401k
        self.short_term_cap_gains_rate = short_term_cap_gains_rate
        self.long_term_cap_gains_rate = long_term_cap_gains_rate
        self.__pay_principal_throughout = pay_principal_throughout
        self.__max_margin_to_assets_ratio = max_margin_to_assets_ratio

    @property
    def years_until_donate(self):
        return self.__years_until_donate

    @years_until_donate.setter
    def years_until_donate(self, val):
        self.__years_until_donate = val

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

    @property
    def short_term_cap_gains_rate(self):
        return self.__short_term_cap_gains_rate

    @short_term_cap_gains_rate.setter
    def short_term_cap_gains_rate(self, val):
        self.__short_term_cap_gains_rate = val

    @property
    def long_term_cap_gains_rate(self):
        return self.__long_term_cap_gains_rate

    @long_term_cap_gains_rate.setter
    def long_term_cap_gains_rate(self, val):
        self.__long_term_cap_gains_rate = val

    @property
    def pay_principal_throughout(self):
        return self.__pay_principal_throughout

    @property
    def max_margin_to_assets_ratio(self):
        return self.__max_margin_to_assets_ratio

    def current_annual_income(self, years_elapsed):
        return self.initial_annual_income_for_investing * (1+self.annual_income_growth_percent/100.0)**years_elapsed