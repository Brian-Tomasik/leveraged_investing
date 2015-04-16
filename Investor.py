import random

class Investor(object):
    """Store parameters about how an investor behaves"""

    def __init__(self, years_until_donate, initial_annual_income_for_investing, 
                 annual_real_income_growth_percent, match_percent_from_401k,
                 tax_rates, rebalance_monthly_to_increase_leverage, 
                 pay_principal_throughout, broker_max_margin_to_assets_ratio,
                 monthly_probability_of_layoff, monthly_probability_find_work_after_laid_off):
        self.years_until_donate = years_until_donate
        self.initial_annual_income_for_investing = initial_annual_income_for_investing
        self.annual_real_income_growth_percent = annual_real_income_growth_percent
        self.match_percent_from_401k = match_percent_from_401k
        self.__tax_rates = tax_rates

        assert not (rebalance_monthly_to_increase_leverage and pay_principal_throughout), "If you're paying principal throughout the history, then you don't want to undo all that work by rebalancing monthly to increase leverage!"

        self.__rebalance_monthly_to_increase_leverage = rebalance_monthly_to_increase_leverage
        self.__pay_principal_throughout = pay_principal_throughout
        self.__broker_max_margin_to_assets_ratio = broker_max_margin_to_assets_ratio
        self.__laid_off = False
        self.__monthly_probability_of_layoff = monthly_probability_of_layoff
        self.__monthly_probability_find_work_after_laid_off = monthly_probability_find_work_after_laid_off
        self.__num_times_laid_off = 0

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
    def annual_real_income_growth_percent(self):
        return self.__annual_real_income_growth_percent

    @annual_real_income_growth_percent.setter
    def annual_real_income_growth_percent(self, val):
        self.__annual_real_income_growth_percent = val

    @property
    def match_percent_from_401k(self):
        return self.__match_percent_from_401k

    @match_percent_from_401k.setter
    def match_percent_from_401k(self, val):
        self.__match_percent_from_401k = val

    @property
    def tax_rates(self):
        return self.__tax_rates

    @property
    def rebalance_monthly_to_increase_leverage(self):
        return self.__rebalance_monthly_to_increase_leverage

    @property
    def pay_principal_throughout(self):
        return self.__pay_principal_throughout

    @property
    def broker_max_margin_to_assets_ratio(self):
        return self.__broker_max_margin_to_assets_ratio

    @property
    def laid_off(self):
        return self.__laid_off

    @laid_off.setter
    def laid_off(self, val):
        self.__laid_off = val

    def current_annual_income(self, years_elapsed, inflation_rate):
        if self.__laid_off:
            return 0
        else:
            penalty_for_past_layoffs = max(.7, 1 - .05 * self.__num_times_laid_off)
            return self.initial_annual_income_for_investing * (1+self.annual_real_income_growth_percent/100.0)**years_elapsed * (1+inflation_rate)**years_elapsed * penalty_for_past_layoffs

    def randomly_update_employment_status_this_month(self):
        if not self.__laid_off:
            if random.random() < self.__monthly_probability_of_layoff:
                self.__laid_off = True
                self.__num_times_laid_off += 1
        else:
            if random.random() < self.__monthly_probability_find_work_after_laid_off:
                self.__laid_off = False