import math
import util
DAYS_PER_YEAR = 365

class EtfLot(object):
    """Store characteristics about an ETF (or stock, etc.) purchase 
    for determining capital gains. Note that (http://www.investopedia.com/terms/l/lot.asp):
    'In terms of stocks, the lot is the number of shares you purchase in one transaction.'"""

    def __init__(self, purchase_price, fee_per_dollar_traded, purchase_day):
        self.__purchase_price = purchase_price * (1-fee_per_dollar_traded)
        self.__purchase_day = purchase_day
        self.__current_price = self.__purchase_price

    @property
    def current_price(self):
        return self.__current_price

    def update_price(self, rate_of_return):
        (self.__current_price, price_fell_to_zero) = util.update_price(
            self.__current_price, rate_of_return)
        return price_fell_to_zero

    def __capital_gain(self):
        return self.__current_price - self.__purchase_price

    def capital_gains_tax_rate(self, day, tax_rates):
        """What's the fraction of capital-gains tax paid per dollar of the lot that's sold?"""
        if (day - self.__purchase_day) / DAYS_PER_YEAR >= 1:
            return ((self.__capital_gain() * (tax_rates.long_term_cap_gains_rate_plus_state())) / self.__current_price, "longterm")
        else:
            return ((self.__capital_gain() * (tax_rates.short_term_cap_gains_rate_plus_state())) / self.__current_price, "shortterm")

    def sell(self, cash_still_need_to_get, fee_per_dollar_traded, day, taxes):
        """Sell some or all of the lot to get needed $."""
        (tax_rate, long_or_short) = self.capital_gains_tax_rate(day, taxes.tax_rates)
        after_fee_value_of_lot = self.__current_price * (1-fee_per_dollar_traded)
        cur_price_before_sell_any_portion = self.__current_price

        if after_fee_value_of_lot > cash_still_need_to_get:
            amount_to_sell = cash_still_need_to_get / (1-fee_per_dollar_traded) # selling this amount leaves us with an after-fee amount of cash_still_need_to_get
            self.__current_price -= amount_to_sell
            if self.__current_price < .1:
               print "WARNING! Stock price is only", self.__current_price ,
            fraction_of_total_cap_gain_incurred = self.__capital_gain() * amount_to_sell / cur_price_before_sell_any_portion
            assert abs(fraction_of_total_cap_gain_incurred) <= abs(self.__capital_gain()), "Fractional capital gain is too big!"
            self.__record_cap_gains(taxes, long_or_short, fraction_of_total_cap_gain_incurred)
            
            """
            # debugging
            if abs(fraction_of_total_cap_gain_incurred) > 0:
                print "day = ", day
                print "cap gain = ", self.__capital_gain()
                print "fraction_of_total_cap_gain_incurred = ", fraction_of_total_cap_gain_incurred
                print "total_gain_or_loss = ", taxes.total_gain_or_loss()
            """

            return (0, False) # tells the caller: (no more cash is needed, this lot is not empty)
        else: # sell the whole security
            self.__record_cap_gains(taxes, long_or_short, self.__capital_gain())

            """
            # debugging
            print "day = ", day
            print "cap gain = ", self.__capital_gain()
            print "total_gain_or_loss = ", taxes.total_gain_or_loss()
            """

            cash_still_needed_now = cash_still_need_to_get - after_fee_value_of_lot
            self.__current_price = 0
            return (cash_still_needed_now, True) # tells the caller: (how much more cash is needed, this lot is empty)

    def harvest(self, fee_per_dollar_traded, day, taxes):
        """Sell the whole lot for tax-loss harvesting."""
        (tax_rate, long_or_short) = self.capital_gains_tax_rate(day, taxes.tax_rates)
        after_fee_value_of_lot = self.__current_price * (1-fee_per_dollar_traded)
        self.__record_cap_gains(taxes, long_or_short, self.__capital_gain())
        return after_fee_value_of_lot

    def __record_cap_gains(self, taxes, long_or_short, amount_to_add):
        if long_or_short == "longterm":
            taxes.add_long_term_cap_gains(amount_to_add)
        elif long_or_short == "shortterm":
            taxes.add_short_term_cap_gains(amount_to_add)
        else:
            raise Exception("long_or_short doesn't match possible cases")

    def __repr__(self):
        return '{}: Purchased at {}, currently at {}'.format(self.__class__.__name__,
                                  self.__purchase_price,
                                  self.__current_price)
