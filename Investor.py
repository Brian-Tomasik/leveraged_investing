import random
import TaxRates

class Investor(object):
    """Store parameters about how an investor behaves"""

    def __init__(self, years_until_donate=15, initial_annual_income_for_investing=30000, 
                 annual_real_income_growth_percent=2, match_percent_from_401k=50,
                 taper_off_leverage_toward_end=True,
                 tax_rates=TaxRates.TaxRates(), rebalance_monthly_to_increase_leverage=True, 
                 pay_principal_throughout=False, broker_max_margin_to_assets_ratio=.5,
                 monthly_probability_of_layoff=.01, monthly_probability_find_work_after_laid_off=.2,
                 does_broker_liquidation_sell_tax_favored_first=False, do_tax_loss_harvesting=True,
                 only_paid_in_first_month_of_sim=False,
                 initial_personal_max_margin_to_assets_relative_to_broker_max=.9):
        self.years_until_donate = years_until_donate
        self.initial_annual_income_for_investing = initial_annual_income_for_investing
        self.annual_real_income_growth_percent = annual_real_income_growth_percent
        self.match_percent_from_401k = match_percent_from_401k
        self.__taper_off_leverage_toward_end = taper_off_leverage_toward_end
        self.__tax_rates = tax_rates

        assert not (rebalance_monthly_to_increase_leverage and pay_principal_throughout), "If you're paying principal throughout the history, then you don't want to undo all that work by rebalancing monthly to increase leverage!"

        self.__rebalance_monthly_to_increase_leverage = rebalance_monthly_to_increase_leverage
        self.__pay_principal_throughout = pay_principal_throughout
        self.__broker_max_margin_to_assets_ratio = broker_max_margin_to_assets_ratio
        self.__laid_off = False
        self.__monthly_probability_of_layoff = monthly_probability_of_layoff
        self.__monthly_probability_find_work_after_laid_off = monthly_probability_find_work_after_laid_off
        self.__num_times_laid_off = 0
        self.__does_broker_liquidation_sell_tax_favored_first = does_broker_liquidation_sell_tax_favored_first
        self.__do_tax_loss_harvesting = do_tax_loss_harvesting
        self.__only_paid_in_first_month_of_sim = only_paid_in_first_month_of_sim
        self.__initial_personal_max_margin_to_assets_relative_to_broker_max = initial_personal_max_margin_to_assets_relative_to_broker_max

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
    def taper_off_leverage_toward_end(self):
        return self.__taper_off_leverage_toward_end

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

    @broker_max_margin_to_assets_ratio.setter
    def broker_max_margin_to_assets_ratio(self, val):
        self.__broker_max_margin_to_assets_ratio = val

    @property
    def laid_off(self):
        return self.__laid_off

    @laid_off.setter
    def laid_off(self, val):
        self.__laid_off = val

    @property
    def monthly_probability_of_layoff(self):
        return self.__monthly_probability_of_layoff

    @property
    def monthly_probability_find_work_after_laid_off(self):
        return self.__monthly_probability_find_work_after_laid_off

    @property
    def does_broker_liquidation_sell_tax_favored_first(self):
        return self.__does_broker_liquidation_sell_tax_favored_first

    @property
    def do_tax_loss_harvesting(self):
        return self.__do_tax_loss_harvesting

    @property
    def initial_personal_max_margin_to_assets_relative_to_broker_max(self):
        return self.__initial_personal_max_margin_to_assets_relative_to_broker_max

    def current_annual_income(self, years_elapsed, day, inflation_rate):
        if self.__laid_off or (self.__only_paid_in_first_month_of_sim and day > 0):
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