DAYS_PER_YEAR = 365

class EtfLot(object):
    """Store characteristics about an ETF (or stock, etc.) purchase 
    for determining capital gains. Note that (http://www.investopedia.com/terms/l/lot.asp):
    'In terms of stocks, the lot is the number of shares you purchase in one transaction.'"""

    def __init__(self, purchase_price, purchase_day):
        self.__purchase_price = purchase_price
        self.__purchase_day = purchase_day
        self.__current_price = purchase_price

    @property
    def current_price(self):
        return self.__current_price

    def update_price(self, rate_of_return):
        self.__current_price *= (1+rate_of_return)

    def capital_gains_tax(self, day, short_term_cap_gains_rate, long_term_cap_gains_rate):
        """What's the fraction of capital-gains tax paid per dollar of the lot that's sold?"""
        capital_gain = self.__current_price - self.__purchase_price
        if (day - self.__purchase_day) / DAYS_PER_YEAR > 1:
            return (capital_gain * long_term_cap_gains_rate) / self.__current_price
        else:
            return (capital_gain * short_term_cap_gains_rate) / self.__current_price

    def sell(self, cash_still_need_to_get, day, short_term_cap_gains_rate, long_term_cap_gains_rate):
        """We want to take out some amount A of after-tax cash. If the tax rate
        is T, that means we want to sell some amount S such that S(1-T) = A, i.e.,
        S = A/(1-T). If S exceeds the amount of money in the lot, sell the whole lot
        and return how much more cash still needs to be gotten."""
        tax_rate = self.capital_gains_tax(day, short_term_cap_gains_rate, long_term_cap_gains_rate)
        amount_need_to_sell_to_get_full_cash_request = cash_still_need_to_get / (1-tax_rate)
        if self.__current_price > amount_need_to_sell_to_get_full_cash_request:
            self.__current_price -= amount_need_to_sell_to_get_full_cash_request
            return (0, False) # tells the caller: (no more cash is needed, this lot is not empty)
        else:
            cash_still_needed_now = amount_need_to_sell_to_get_full_cash_request - self.__current_price
            self.__current_price = 0
            return (cash_still_needed_now, True) # tells the caller: (how much more cash is needed, this lot is empty)

    def myfake(self):
        return 1

    def __repr__(self):
        return '{}: Purchased at {}, currently at {}'.format(self.__class__.__name__,
                                  self.__purchase_price,
                                  self.__current_price)
