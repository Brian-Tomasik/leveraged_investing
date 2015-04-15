class TaxRates(object):
    """Investor's tax-rate info"""

    def __init__(self, short_term_cap_gains_rate, 
                 long_term_cap_gains_rate, state_income_tax):
        self.__short_term_cap_gains_rate = short_term_cap_gains_rate
        self.__long_term_cap_gains_rate = long_term_cap_gains_rate
        self.__state_income_tax = state_income_tax

    @property
    def short_term_cap_gains_rate(self):
        return self.__short_term_cap_gains_rate

    @property
    def long_term_cap_gains_rate(self):
        return self.__long_term_cap_gains_rate

    @property
    def state_income_tax(self):
        """Since most states don't distinguish short- vs. long-term 
        capital gains (see http://www.aaii.com/journal/article/capital-pains-rules-for-capital-losses.touch ,
        section 'State Income Taxes'), this can probably just be
        one number, without distinguishing short- vs. long-term."""
        return self.__state_income_tax